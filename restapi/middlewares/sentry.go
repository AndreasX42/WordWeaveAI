package middlewares

import (
	"fmt"
	"net/http"
	"runtime/debug"
	"time"

	"github.com/AndreasX42/restapi/config"
	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/utils"
	"github.com/getsentry/sentry-go"
	"github.com/gin-gonic/gin"
)

func slowRequestThreshold() time.Duration {
	return utils.EnvMilliseconds("SENTRY_SLOW_REQUEST_THRESHOLD_MS", 5000)
}

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

		// Add the hub to the request context
		c.Request = c.Request.WithContext(sentry.SetHubOnContext(c.Request.Context(), hub))

		// Panic recovery
		defer func() {
			if err := recover(); err != nil {
				// Capture panic with stack trace context.
				hub.WithScope(func(scope *sentry.Scope) {
					scope.SetContext("panic", map[string]any{
						"stack_trace": string(debug.Stack()),
					})
					hub.RecoverWithContext(c.Request.Context(), err)
				})

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
		setSentryUserFromContext(c, hub)

		// Capture errors based on status code
		status := c.Writer.Status()
		if status >= 400 {
			hub.Scope().SetTag("status_code", fmt.Sprintf("%d", status))
			hub.Scope().SetTag("response_time", duration.String())

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
		if duration > slowRequestThreshold() {
			hub.WithScope(func(scope *sentry.Scope) {
				scope.SetLevel(sentry.LevelWarning)
				scope.SetTag("response_time", duration.String())
				hub.CaptureMessage(fmt.Sprintf("Slow request: %s %s took %s", c.Request.Method, c.Request.URL.Path, duration))
			})
		}
	}
}

func setSentryUserFromContext(c *gin.Context, hub *sentry.Hub) {
	if user, exists := c.Get("principal"); exists {
		if entityUser, ok := user.(*entities.User); ok {
			hub.Scope().SetUser(sentry.User{ID: entityUser.ID})
			return
		}
	}

	if user, exists := c.Get("user"); exists {
		if entityUser, ok := user.(*entities.User); ok {
			hub.Scope().SetUser(sentry.User{ID: entityUser.ID})
		}
	}
}

// CaptureErrorFromContext captures an error using the Sentry hub from the request context
func CaptureErrorFromContext(c *gin.Context, err error, tags map[string]string, extra map[string]any) {
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
		if len(extra) > 0 {
			scope.SetContext("extra", extra)
		}

		hub.CaptureException(err)
	})
}

// CaptureMessageFromContext captures a message using the Sentry hub from the request context
func CaptureMessageFromContext(c *gin.Context, message string, level sentry.Level, tags map[string]string, extra map[string]any) {
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
		if len(extra) > 0 {
			scope.SetContext("extra", extra)
		}

		hub.CaptureMessage(message)
	})
}
