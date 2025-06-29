package middlewares

import (
	"fmt"
	"net/http"
	"runtime/debug"
	"time"

	"github.com/AndreasX42/restapi/config"
	"github.com/getsentry/sentry-go"
	"github.com/gin-gonic/gin"
)

// SentryMiddleware creates a middleware that automatically captures errors and panics
func SentryMiddleware(sentryConfig *config.SentryConfig) gin.HandlerFunc {
	return func(c *gin.Context) {
		if sentryConfig == nil || sentryConfig.Client == nil {
			c.Next()
			return
		}

		// Create a new Sentry hub for this request
		hub := sentry.GetHubFromContext(c.Request.Context())
		if hub == nil {
			hub = sentry.CurrentHub().Clone()
		}

		// Set request context
		hub.Scope().SetRequest(c.Request)
		hub.Scope().SetTag("route", c.FullPath())
		hub.Scope().SetTag("method", c.Request.Method)

		// Get user information if available (from JWT claims)
		if userID, exists := c.Get("user_id"); exists {
			hub.Scope().SetUser(sentry.User{
				ID: fmt.Sprintf("%v", userID),
			})
		}

		// Add the hub to the request context
		c.Request = c.Request.WithContext(sentry.SetHubOnContext(c.Request.Context(), hub))

		// Panic recovery
		defer func() {
			if err := recover(); err != nil {
				// Capture the panic
				hub.RecoverWithContext(c.Request.Context(), err)

				// Send stack trace as extra info
				hub.Scope().SetExtra("stack_trace", string(debug.Stack()))

				// Return 500 error
				c.JSON(http.StatusInternalServerError, gin.H{
					"message": "Internal server error",
					"details": gin.H{"error": "An unexpected error occurred"},
				})
				c.Abort()
			}
		}()

		// Process request
		start := time.Now()
		c.Next()
		duration := time.Since(start)

		// Capture errors based on status code
		status := c.Writer.Status()
		if status >= 400 {
			hub.Scope().SetTag("status_code", fmt.Sprintf("%d", status))
			hub.Scope().SetExtra("response_time", duration.String())

			// Get any errors from the gin context
			errors := c.Errors
			if len(errors) > 0 {
				for _, ginErr := range errors {
					hub.CaptureException(ginErr.Err)
				}
			} else {
				// Create a generic error for non-500 status codes
				if status >= 500 {
					hub.WithScope(func(scope *sentry.Scope) {
						scope.SetLevel(sentry.LevelError)
						hub.CaptureMessage(fmt.Sprintf("HTTP %d: %s %s", status, c.Request.Method, c.Request.URL.Path))
					})
				} else if status >= 400 {
					hub.WithScope(func(scope *sentry.Scope) {
						scope.SetLevel(sentry.LevelWarning)
						hub.CaptureMessage(fmt.Sprintf("HTTP %d: %s %s", status, c.Request.Method, c.Request.URL.Path))
					})
				}
			}
		}

		// Log slow requests
		if duration > 5*time.Second {
			hub.WithScope(func(scope *sentry.Scope) {
				scope.SetLevel(sentry.LevelWarning)
				scope.SetExtra("response_time", duration.String())
				hub.CaptureMessage(fmt.Sprintf("Slow request: %s %s took %s", c.Request.Method, c.Request.URL.Path, duration))
			})
		}
	}
}

// CaptureErrorFromContext captures an error using the Sentry hub from the request context
func CaptureErrorFromContext(c *gin.Context, err error, tags map[string]string, extra map[string]interface{}) {
	hub := sentry.GetHubFromContext(c.Request.Context())
	if hub == nil {
		return
	}

	hub.WithScope(func(scope *sentry.Scope) {
		// Add tags
		for key, value := range tags {
			scope.SetTag(key, value)
		}

		// Add extra context
		for key, value := range extra {
			scope.SetExtra(key, value)
		}

		hub.CaptureException(err)
	})
}

// CaptureMessageFromContext captures a message using the Sentry hub from the request context
func CaptureMessageFromContext(c *gin.Context, message string, level sentry.Level, tags map[string]string, extra map[string]interface{}) {
	hub := sentry.GetHubFromContext(c.Request.Context())
	if hub == nil {
		return
	}

	hub.WithScope(func(scope *sentry.Scope) {
		scope.SetLevel(level)

		// Add tags
		for key, value := range tags {
			scope.SetTag(key, value)
		}

		// Add extra context
		for key, value := range extra {
			scope.SetExtra(key, value)
		}

		hub.CaptureMessage(message)
	})
}
