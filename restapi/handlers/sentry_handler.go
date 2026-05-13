package handlers

import (
	"fmt"
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
	if req.Error != nil && req.Level == "" {
		// Treat structured frontend error payloads as errors by default.
		level = sentry.LevelError
	}
	scope.SetLevel(level)

	if level == sentry.LevelError && req.Error != nil {
		errorName := safeGetAsString(req.Error, "name")
		if errorName == "" {
			errorName = "FrontendError"
		}

		errorType := safeGetAsString(req.Error, "type")
		errorMessage := safeGetAsString(req.Error, "message")
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

		stacktrace := parseJSStacktrace(safeGetAsString(req.Error, "stack"))

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
			Extra: map[string]any{
				"error_name": errorName,
				"error_type": errorType,
				"url":        safeGetAsString(req.Error, "url"),
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

	// Support both Firefox ("func@file:line:col") and Chromium ("at func (file:line:col)") stack formats.
	firefoxRe := regexp.MustCompile(`^(.*?)@(.*):(\d+):(\d+)$`)
	chromiumWithFnRe := regexp.MustCompile(`^\s*at\s+(.*?)\s+\((.*):(\d+):(\d+)\)\s*$`)
	chromiumNoFnRe := regexp.MustCompile(`^\s*at\s+(.*):(\d+):(\d+)\s*$`)
	lines := strings.Split(stack, "\n")
	frames := []sentry.Frame{}

	for _, line := range lines {
		trimmedLine := strings.TrimSpace(line)
		if trimmedLine == "" {
			continue
		}

		if matches := firefoxRe.FindStringSubmatch(trimmedLine); len(matches) == 5 {
			lineNo, _ := strconv.Atoi(matches[3])
			colNo, _ := strconv.Atoi(matches[4])
			frames = append(frames, sentry.Frame{
				Function: strings.TrimSpace(matches[1]),
				AbsPath:  strings.TrimSpace(matches[2]),
				Lineno:   lineNo,
				Colno:    colNo,
				InApp:    true,
			})
			continue
		}

		if matches := chromiumWithFnRe.FindStringSubmatch(trimmedLine); len(matches) == 5 {
			lineNo, _ := strconv.Atoi(matches[3])
			colNo, _ := strconv.Atoi(matches[4])
			frames = append(frames, sentry.Frame{
				Function: strings.TrimSpace(matches[1]),
				AbsPath:  strings.TrimSpace(matches[2]),
				Lineno:   lineNo,
				Colno:    colNo,
				InApp:    true,
			})
			continue
		}

		if matches := chromiumNoFnRe.FindStringSubmatch(trimmedLine); len(matches) == 4 {
			lineNo, _ := strconv.Atoi(matches[2])
			colNo, _ := strconv.Atoi(matches[3])
			frame := sentry.Frame{
				Function: "(anonymous)",
				AbsPath:  strings.TrimSpace(matches[1]),
				Lineno:   lineNo,
				Colno:    colNo,
				InApp:    true,
			}
			frames = append(frames, frame)
			continue
		}

		frames = append(frames, sentry.Frame{
			Function: trimmedLine,
			InApp:    true,
		})
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

// safeGetAsString converts primitive values to a string representation.
func safeGetAsString(m map[string]any, key string) string {
	if m == nil {
		return ""
	}

	switch val := m[key].(type) {
	case string:
		return val
	case fmt.Stringer:
		return val.String()
	case float64:
		return strconv.FormatFloat(val, 'f', -1, 64)
	case float32:
		return strconv.FormatFloat(float64(val), 'f', -1, 32)
	case int:
		return strconv.Itoa(val)
	case int8, int16, int32, int64:
		return fmt.Sprintf("%d", val)
	case uint, uint8, uint16, uint32, uint64:
		return fmt.Sprintf("%d", val)
	case bool:
		return strconv.FormatBool(val)
	default:
		return ""
	}
}
