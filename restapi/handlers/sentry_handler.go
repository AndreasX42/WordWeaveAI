package handlers

import (
	"net/http"
	"time"

	"github.com/getsentry/sentry-go"
	"github.com/gin-gonic/gin"
)

type SentryHandler struct {
	sentryClient *sentry.Client
}

func NewSentryHandler(sentryClient *sentry.Client) *SentryHandler {
	return &SentryHandler{
		sentryClient: sentryClient,
	}
}

// LogRequest represents the structure for frontend log requests
// Supports both simple logging and enhanced error reporting
type LogRequest struct {
	// Simple logging format
	Level     string                 `json:"level"`
	Message   string                 `json:"message"`
	Tags      map[string]string      `json:"tags,omitempty"`
	Extra     map[string]interface{} `json:"extra,omitempty"`
	UserAgent string                 `json:"user_agent,omitempty"`
	URL       string                 `json:"url,omitempty"`
	Error     *ErrorDetails          `json:"error,omitempty"`

	// Enhanced frontend error structure
	Timestamp string          `json:"timestamp,omitempty"`
	ErrorData *FrontendError  `json:"error,omitempty"` // This will conflict with simple Error field, handled in logic
	Context   *RequestContext `json:"context,omitempty"`
}

// FrontendError represents comprehensive error information from the frontend
type FrontendError struct {
	Message       string      `json:"message,omitempty"`
	Stack         string      `json:"stack,omitempty"`
	Status        int         `json:"status,omitempty"`
	StatusText    string      `json:"statusText,omitempty"`
	URL           string      `json:"url,omitempty"`
	UserAgent     string      `json:"userAgent,omitempty"`
	Type          string      `json:"type,omitempty"`
	OriginalError interface{} `json:"originalError,omitempty"`
}

// RequestContext represents the context information from frontend
type RequestContext struct {
	CurrentURL string `json:"currentUrl,omitempty"`
	UserID     string `json:"userId,omitempty"`
	SessionID  string `json:"sessionId,omitempty"`
}

// ErrorDetails represents simple error information (for backward compatibility)
type ErrorDetails struct {
	Name       string `json:"name,omitempty"`
	Message    string `json:"message,omitempty"`
	Stack      string `json:"stack,omitempty"`
	FileName   string `json:"filename,omitempty"`
	LineNumber int    `json:"lineno,omitempty"`
	ColNumber  int    `json:"colno,omitempty"`
}

// LogEvent handles logging events from the frontend
func (h *SentryHandler) LogEvent(c *gin.Context) {
	if h.sentryClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"message": "Logging service is not available",
		})
		return
	}

	var logRequest map[string]interface{}
	if err := c.ShouldBindJSON(&logRequest); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Invalid request format",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	// Determine if this is the enhanced frontend error structure or simple logging
	isEnhancedError := h.isEnhancedErrorStructure(logRequest)

	// Get Sentry hub from context or create a new one
	hub := sentry.GetHubFromContext(c.Request.Context())
	if hub == nil {
		hub = sentry.CurrentHub().Clone()
	}

	if isEnhancedError {
		h.handleEnhancedError(hub, logRequest, c)
	} else {
		h.handleSimpleLog(hub, logRequest, c)
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Event logged successfully",
	})
}

// isEnhancedErrorStructure determines if the request is using the enhanced frontend error structure
func (h *SentryHandler) isEnhancedErrorStructure(data map[string]interface{}) bool {
	// Check if it has the enhanced structure with nested error and context objects
	if errorData, exists := data["error"]; exists {
		if errorMap, ok := errorData.(map[string]interface{}); ok {
			// Check for fields that are specific to the enhanced structure
			_, hasType := errorMap["type"]
			_, hasOriginalError := errorMap["originalError"]
			_, hasContext := data["context"]
			return hasType || hasOriginalError || hasContext
		}
	}
	return false
}

// handleEnhancedError processes the comprehensive frontend error structure
func (h *SentryHandler) handleEnhancedError(hub *sentry.Hub, data map[string]interface{}, c *gin.Context) {
	hub.WithScope(func(scope *sentry.Scope) {
		// Set level to error for enhanced error reports
		scope.SetLevel(sentry.LevelError)

		// Add frontend-specific tags
		scope.SetTag("source", "frontend")
		scope.SetTag("error_handler", "enhanced")

		// Process error data
		if errorData, exists := data["error"]; exists {
			if errorMap, ok := errorData.(map[string]interface{}); ok {
				// Set error type as tag
				if errorType, exists := errorMap["type"]; exists {
					scope.SetTag("error_type", errorType.(string))
				}

				// Add HTTP status if available
				if status, exists := errorMap["status"]; exists {
					scope.SetTag("http_status", status.(string))
				}

				// Add user agent
				if userAgent, exists := errorMap["userAgent"]; exists {
					scope.SetTag("user_agent", userAgent.(string))
				}

				// Add all error details as extra context
				scope.SetExtra("error_details", errorMap)
			}
		}

		// Process context data
		if contextData, exists := data["context"]; exists {
			if contextMap, ok := contextData.(map[string]interface{}); ok {
				// Set user information if available
				if userID, exists := contextMap["userId"]; exists && userID != nil {
					scope.SetUser(sentry.User{
						ID: userID.(string),
					})
				}

				// Add session ID as tag
				if sessionID, exists := contextMap["sessionId"]; exists && sessionID != nil {
					scope.SetTag("session_id", sessionID.(string))
				}

				// Add current URL
				if currentURL, exists := contextMap["currentUrl"]; exists {
					scope.SetTag("page_url", currentURL.(string))
				}

				// Add all context as extra
				scope.SetExtra("request_context", contextMap)
			}
		}

		// Add timestamp if available
		if timestamp, exists := data["timestamp"]; exists {
			scope.SetExtra("frontend_timestamp", timestamp)
		}

		// Add server timestamp
		scope.SetExtra("server_timestamp", time.Now().UTC())

		// Get user information from JWT if available (will override frontend user if set)
		if userID, exists := c.Get("user_id"); exists {
			scope.SetUser(sentry.User{
				ID: userID.(string),
			})
		}

		// Create error message
		var message string
		if errorData, exists := data["error"]; exists {
			if errorMap, ok := errorData.(map[string]interface{}); ok {
				if msg, exists := errorMap["message"]; exists {
					message = msg.(string)
				}
			}
		}
		if message == "" {
			message = "Frontend error occurred"
		}

		// Create custom error for better stack trace handling
		err := &EnhancedFrontendError{
			Message: message,
			Data:    data,
		}

		hub.CaptureException(err)
	})
}

// handleSimpleLog processes the simple logging structure (backward compatibility)
func (h *SentryHandler) handleSimpleLog(hub *sentry.Hub, data map[string]interface{}, c *gin.Context) {
	// Validate log level
	levelStr, exists := data["level"]
	if !exists {
		levelStr = "info" // default
	}

	var sentryLevel sentry.Level
	switch levelStr.(string) {
	case "error":
		sentryLevel = sentry.LevelError
	case "warning":
		sentryLevel = sentry.LevelWarning
	case "info":
		sentryLevel = sentry.LevelInfo
	case "debug":
		sentryLevel = sentry.LevelDebug
	default:
		sentryLevel = sentry.LevelInfo
	}

	hub.WithScope(func(scope *sentry.Scope) {
		// Set level
		scope.SetLevel(sentryLevel)

		// Add frontend-specific tags
		scope.SetTag("source", "frontend")
		scope.SetTag("error_handler", "simple")

		// Add user agent if available
		if userAgent, exists := data["user_agent"]; exists {
			scope.SetTag("user_agent", userAgent.(string))
		}

		// Add URL if available
		if url, exists := data["url"]; exists {
			scope.SetTag("page_url", url.(string))
		}

		// Add custom tags
		if tags, exists := data["tags"]; exists {
			if tagsMap, ok := tags.(map[string]interface{}); ok {
				for key, value := range tagsMap {
					scope.SetTag(key, value.(string))
				}
			}
		}

		// Add extra context
		scope.SetExtra("timestamp", time.Now().UTC())
		if extra, exists := data["extra"]; exists {
			if extraMap, ok := extra.(map[string]interface{}); ok {
				for key, value := range extraMap {
					scope.SetExtra(key, value)
				}
			}
		}

		// Get user information if available (from JWT claims)
		if userID, exists := c.Get("user_id"); exists {
			scope.SetUser(sentry.User{
				ID: userID.(string),
			})
		}

		// Get message
		message := "No message provided"
		if msg, exists := data["message"]; exists {
			message = msg.(string)
		}

		// If it's an error with error details, capture as exception
		if sentryLevel == sentry.LevelError {
			if errorData, exists := data["error"]; exists {
				if errorMap, ok := errorData.(map[string]interface{}); ok {
					err := &SimpleFrontendError{
						Message: message,
						Details: errorMap,
					}
					scope.SetExtra("error_details", errorMap)
					hub.CaptureException(err)
					return
				}
			}
		}

		// Capture as message
		hub.CaptureMessage(message)
	})
}

// EnhancedFrontendError represents an error from the enhanced frontend structure
type EnhancedFrontendError struct {
	Message string
	Data    map[string]interface{}
}

// Error implements the error interface
func (e *EnhancedFrontendError) Error() string {
	if e.Message != "" {
		return e.Message
	}
	return "Enhanced frontend error"
}

// SimpleFrontendError represents an error from the simple frontend structure
type SimpleFrontendError struct {
	Message string
	Details map[string]interface{}
}

// Error implements the error interface
func (e *SimpleFrontendError) Error() string {
	if e.Message != "" {
		return e.Message
	}
	return "Frontend error"
}
