package handlers

import (
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
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
	Level     string            `json:"level"`
	Message   string            `json:"message"`
	Tags      map[string]string `json:"tags,omitempty"`
	Extra     map[string]any    `json:"extra,omitempty"`
	UserAgent string            `json:"user_agent,omitempty"`
	URL       string            `json:"url,omitempty"`

	// Enhanced frontend error structure
	Timestamp string         `json:"timestamp,omitempty"`
	Error     map[string]any `json:"error,omitempty"` // Unified error field
	Context   map[string]any `json:"context,omitempty"`
}

// FrontendError represents a unified error structure from frontend logging
type FrontendError struct {
	Message string
	Data    map[string]any
}

// Error implements the error interface
func (e *FrontendError) Error() string {
	if e.Message != "" {
		return e.Message
	}
	return "Frontend error"
}

// LogEvent handles logging events from the frontend
func (h *SentryHandler) LogEvent(c *gin.Context) {
	if h.sentryClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"message": "Logging service is not available"})
		return
	}

	var req LogRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Invalid request format",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	hub := sentry.GetHubFromContext(c.Request.Context())
	if hub == nil {
		hub = sentry.CurrentHub().Clone()
	}

	hub.WithScope(func(scope *sentry.Scope) {
		h.configureSentryScope(scope, &req, c)
		h.captureLog(hub, scope, &req)
	})

	c.JSON(http.StatusOK, gin.H{"message": "Event logged successfully"})
}

// configureSentryScope configures the Sentry scope with data from the log request
func (h *SentryHandler) configureSentryScope(scope *sentry.Scope, req *LogRequest, c *gin.Context) {
	isEnhanced := req.Error != nil

	// Set base tags
	scope.SetTag("source", "frontend")
	if isEnhanced {
		scope.SetTag("error_handler", "enhanced")
	} else {
		scope.SetTag("error_handler", "simple")
	}

	// Process error data for enhanced logging
	if isEnhanced {
		if errorType := safeGetString(req.Error, "type"); errorType != "" {
			scope.SetTag("error_type", errorType)
		}
		if status := safeGetString(req.Error, "status"); status != "" {
			scope.SetTag("http_status", status)
		}
		if userAgent := safeGetString(req.Error, "userAgent"); userAgent != "" {
			scope.SetTag("user_agent", userAgent)
		}
		scope.SetExtra("error_details", req.Error)
	} else {
		// Process simple logging fields
		if req.UserAgent != "" {
			scope.SetTag("user_agent", req.UserAgent)
		}
		if req.URL != "" {
			scope.SetTag("page_url", req.URL)
		}
	}

	// Process context for both simple and enhanced
	if req.Context != nil {
		if userID := safeGetString(req.Context, "userId"); userID != "" {
			scope.SetUser(sentry.User{ID: userID})
		}
		if sessionID := safeGetString(req.Context, "sessionId"); sessionID != "" {
			scope.SetTag("session_id", sessionID)
		}
		if currentURL := safeGetString(req.Context, "currentUrl"); currentURL != "" {
			scope.SetTag("page_url", currentURL)
		}
		scope.SetExtra("request_context", req.Context)
	}

	// Add custom tags and extra data
	for k, v := range req.Tags {
		scope.SetTag(k, v)
	}
	for k, v := range req.Extra {
		scope.SetExtra(k, v)
	}

	// Timestamps
	if req.Timestamp != "" {
		scope.SetExtra("frontend_timestamp", req.Timestamp)
	}
	scope.SetExtra("server_timestamp", time.Now().UTC())

	// Override user from JWT if available
	if user, exists := c.Get("principal"); exists {
		if u, ok := user.(*entities.User); ok {
			scope.SetUser(sentry.User{ID: u.ID})
		}
	}
}

func (h *SentryHandler) captureLog(hub *sentry.Hub, scope *sentry.Scope, req *LogRequest) {
	level := h.getSentryLevel(req.Level)
	scope.SetLevel(level)

	if level == sentry.LevelError && req.Error != nil {
		errorName := safeGetString(req.Error, "name")
		if errorName == "" {
			errorName = "FrontendError"
		}

		errorType := safeGetString(req.Error, "type")
		errorMessage := safeGetString(req.Error, "message")
		if errorMessage == "" {
			errorMessage = errorType
		}
		if errorMessage == "" {
			errorMessage = "No message provided"
		}

		displayType := errorName
		if errorType != "" && errorType != errorMessage {
			displayType = errorName + ": " + errorType
		}

		stacktrace := parseJSStacktrace(safeGetString(req.Error, "stack"))

		hub.CaptureEvent(&sentry.Event{
			Level:    sentry.LevelError,
			Message:  errorMessage,
			Platform: "javascript",
			Exception: []sentry.Exception{
				{
					Value:      errorMessage,
					Type:       displayType,
					Module:     "frontend",
					Stacktrace: stacktrace,
				},
			},
			Fingerprint: []string{
				"frontend",
				errorName,
				errorType,
			},
			Extra: map[string]interface{}{
				"error_name": errorName,
				"error_type": errorType,
				"url":        safeGetString(req.Error, "url"),
			},
		})
	} else {
		message := req.Message
		if message == "" {
			message = "No message provided"
		}
		hub.CaptureMessage(message)
	}
}

func parseJSStacktrace(stack string) *sentry.Stacktrace {
	if stack == "" {
		return nil
	}

	// Regex to capture function name, file path, line number, and column number
	re := regexp.MustCompile(`(?m)^(.*)@(.*):(\d+):(\d+)`)
	lines := strings.Split(stack, "\n")
	frames := []sentry.Frame{}

	for _, line := range lines {
		matches := re.FindStringSubmatch(line)

		if len(matches) == 5 {
			lineNo, _ := strconv.Atoi(matches[3])
			colNo, _ := strconv.Atoi(matches[4])

			frame := sentry.Frame{
				Function: matches[1],
				AbsPath:  matches[2],
				Lineno:   lineNo,
				Colno:    colNo,
				InApp:    true, // You might want to customize this based on file path
			}
			frames = append(frames, frame)
		} else {
			// Handle cases where the line doesn't match the expected format
			// Could be a simple message line or a different format
			frames = append(frames, sentry.Frame{
				Function: line,
				InApp:    true,
			})
		}
	}
	// Reverse frames to have the call stack in the correct order (oldest to newest)
	for i, j := 0, len(frames)-1; i < j; i, j = i+1, j-1 {
		frames[i], frames[j] = frames[j], frames[i]
	}

	return &sentry.Stacktrace{
		Frames: frames,
	}
}

// getSentryLevel converts a log level string to a Sentry level
func (h *SentryHandler) getSentryLevel(levelStr string) sentry.Level {
	switch strings.ToLower(levelStr) {
	case "error":
		return sentry.LevelError
	case "warning":
		return sentry.LevelWarning
	case "info":
		return sentry.LevelInfo
	case "debug":
		return sentry.LevelDebug
	default:
		return sentry.LevelInfo
	}
}

// safeGetString extracts a string from a map[string]any safely
func safeGetString(m map[string]any, key string) string {
	if val, ok := m[key].(string); ok {
		return val
	}
	return ""
}

// safeGetMap extracts a map[string]any from a map[string]any safely
func safeGetMap(m map[string]any, key string) map[string]any {
	if val, ok := m[key].(map[string]any); ok {
		return val
	}
	return nil
}
