package middlewares

import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"io"
	"log/slog"
	"net/http"
	"os"
	"runtime/debug"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/gin-gonic/gin"
)

const (
	maxLoggedBodyBytes     = 8 * 1024
	maxLoggedResponseBytes = 16 * 1024
)

type Phase string

const (
	PhaseStart  Phase = "start"
	PhaseEnd    Phase = "end"
	PhaseFailed Phase = "failed"
)

type requestLoggerConfig struct {
	RequestIDHeader string
}

// RequestLoggerMiddleware logs structured JSON for each request:
// - <event>.start before handler
// - <event>.end on success
// - <event>.failed on errors (status>=500 or gin context errors) including stacktrace
//
// Event naming:
// - Defaults to "http.<METHOD>.<ROUTE>" (sanitized)
// - If handlers set c.Set("event_name", "delete.list"), that overrides the base
func RequestLoggerMiddleware() gin.HandlerFunc {
	cfg := requestLoggerConfig{RequestIDHeader: "X-Request-Id"}

	return func(c *gin.Context) {
		startedAt := time.Now()

		requestID := getOrCreateRequestID(c, cfg.RequestIDHeader)
		eventBase := getEventBase(c)

		reqBody := captureAndRestoreRequestBody(c, maxLoggedBodyBytes)

		// Wrap writer to capture response body.
		bw := &bodyCaptureWriter{
			ResponseWriter: c.Writer,
			limit:          maxLoggedResponseBytes,
		}
		c.Writer = bw

		startEntry := RequestLogEntry{
			Timestamp:  time.Now().UTC().Format(time.RFC3339Nano),
			Phase:      PhaseStart,
			Event:      eventBase + ".start",
			AppVersion: os.Getenv("APP_VERSION"),
			RequestID:  requestID,
			Method:     c.Request.Method,
			Path:       c.Request.URL.Path,
			Route:      c.FullPath(),
			Query:      c.Request.URL.RawQuery,
			IP:         c.ClientIP(),
			UserAgent:  c.Request.UserAgent(),
			Params:     paramsToMap(c.Params),
			Body:       reqBody,
			UserID:     getUserIDFromContext(c),
		}
		slog.Info("request", "entry", startEntry)

		c.Next()

		durationMs := time.Since(startedAt).Milliseconds()
		status := c.Writer.Status()

		respBody := bw.bodyString()
		ginErrs := make([]string, 0, len(c.Errors))
		for _, e := range c.Errors {
			if e == nil || e.Err == nil {
				continue
			}
			ginErrs = append(ginErrs, e.Err.Error())
		}
		if len(ginErrs) == 0 {
			ginErrs = nil
		}

		entry := RequestLogEntry{
			Timestamp:   time.Now().UTC().Format(time.RFC3339Nano),
			AppVersion:  os.Getenv("APP_VERSION"),
			RequestID:   requestID,
			Method:      c.Request.Method,
			Path:        c.Request.URL.Path,
			Route:       c.FullPath(),
			Query:       c.Request.URL.RawQuery,
			IP:          c.ClientIP(),
			UserAgent:   c.Request.UserAgent(),
			Params:      paramsToMap(c.Params),
			Body:        reqBody,
			UserID:      getUserIDFromContext(c),
			StatusCode:  status,
			DurationMs:  durationMs,
			Response:    respBody,
			GinErrors:   ginErrs,
			WasAborted:  c.IsAborted(),
			ContentType: c.Writer.Header().Get("Content-Type"),
		}

		isFailure := status >= 500 || len(c.Errors) > 0
		if isFailure {
			entry.Phase = PhaseFailed
			entry.Event = eventBase + ".failed"
			entry.Stacktrace = string(debug.Stack())
			slog.Error("request", "entry", entry)
			return
		}

		entry.Phase = PhaseEnd
		entry.Event = eventBase + ".end"
		slog.Info("request", "entry", entry)
	}
}

type RequestLogEntry struct {
	Timestamp   string            `json:"timestamp"`
	Phase       Phase             `json:"phase"`
	Event       string            `json:"event"`
	AppVersion  string            `json:"app_version,omitempty"`
	RequestID   string            `json:"request_id"`
	Method      string            `json:"method"`
	Path        string            `json:"path"`
	Route       string            `json:"route"`
	Query       string            `json:"query,omitempty"`
	IP          string            `json:"ip,omitempty"`
	UserAgent   string            `json:"user_agent,omitempty"`
	UserID      string            `json:"user_id,omitempty"`
	Params      map[string]string `json:"params,omitempty"`
	Body        string            `json:"body,omitempty"`
	StatusCode  int               `json:"status_code,omitempty"`
	DurationMs  int64             `json:"duration_ms,omitempty"`
	Response    string            `json:"response,omitempty"`
	ContentType string            `json:"content_type,omitempty"`
	WasAborted  bool              `json:"was_aborted,omitempty"`
	GinErrors   []string          `json:"gin_errors,omitempty"`
	Stacktrace  string            `json:"stacktrace,omitempty"`
}

type bodyCaptureWriter struct {
	gin.ResponseWriter
	buf   bytes.Buffer
	limit int
}

func (w *bodyCaptureWriter) Write(p []byte) (int, error) {
	if w.limit > 0 && w.buf.Len() < w.limit {
		remain := w.limit - w.buf.Len()
		if len(p) <= remain {
			_, _ = w.buf.Write(p)
		} else {
			_, _ = w.buf.Write(p[:remain])
		}
	}
	return w.ResponseWriter.Write(p)
}

func (w *bodyCaptureWriter) bodyString() string {
	s := strings.TrimSpace(w.buf.String())
	return s
}

func paramsToMap(params gin.Params) map[string]string {
	if len(params) == 0 {
		return nil
	}
	out := make(map[string]string, len(params))
	for _, p := range params {
		out[p.Key] = p.Value
	}
	return out
}

func getEventBase(c *gin.Context) string {
	if v, ok := c.Get("event_name"); ok {
		if s, ok := v.(string); ok && s != "" {
			return s
		}
	}
	route := c.FullPath()
	if route == "" {
		route = c.Request.URL.Path
	}
	base := "http." + c.Request.Method + "." + route
	return sanitizeEventName(base)
}

func sanitizeEventName(s string) string {
	s = strings.ReplaceAll(s, " ", "_")
	s = strings.ReplaceAll(s, "/", ".")
	s = strings.ReplaceAll(s, ":", "")
	s = strings.ReplaceAll(s, "__", "_")
	s = strings.Trim(s, ".")
	return s
}

func captureAndRestoreRequestBody(c *gin.Context, limit int64) string {
	if c.Request == nil || c.Request.Body == nil || c.Request.Body == http.NoBody {
		return ""
	}
	raw, err := io.ReadAll(io.LimitReader(c.Request.Body, limit+1))
	if err != nil {
		c.Request.Body = io.NopCloser(bytes.NewBuffer(nil))
		return ""
	}
	c.Request.Body = io.NopCloser(bytes.NewBuffer(raw))
	if int64(len(raw)) > limit {
		raw = raw[:limit]
	}
	return strings.TrimSpace(string(raw))
}

func getUserIDFromContext(c *gin.Context) string {
	if v, ok := c.Get("principal"); ok {
		if u, ok := v.(*entities.User); ok && u != nil {
			return u.ID
		}
	}
	if v, ok := c.Get("user"); ok {
		if u, ok := v.(*entities.User); ok && u != nil {
			return u.ID
		}
	}
	return ""
}

func getOrCreateRequestID(c *gin.Context, header string) string {
	if v := c.GetHeader(header); v != "" {
		return v
	}
	if v := c.Writer.Header().Get(header); v != "" {
		return v
	}
	id := newRequestID()
	c.Writer.Header().Set(header, id)
	return id
}

func newRequestID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return hex.EncodeToString([]byte(time.Now().UTC().Format(time.RFC3339Nano)))
	}
	return hex.EncodeToString(b)
}

