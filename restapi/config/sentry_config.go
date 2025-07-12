package config

import (
	"log"
	"os"
	"time"

	"github.com/getsentry/sentry-go"
)

type SentryConfig struct {
	Client *sentry.Client
}

func NewSentryConfig() *SentryConfig {
	dsn := os.Getenv("SENTRY_DSN")
	if dsn == "" {
		log.Println("SENTRY_DSN not set, Sentry logging will be disabled")
		return &SentryConfig{Client: nil}
	}

	environment := os.Getenv("SENTRY_ENVIRONMENT")
	if environment == "" {
		environment = "development"
	}

	release := os.Getenv("SENTRY_RELEASE")
	if release == "" {
		release = os.Getenv("APP_VERSION")
		if release == "" {
			release = "unknown"
		}
	}

	err := sentry.Init(sentry.ClientOptions{
		Dsn:              dsn,
		Environment:      environment,
		Release:          release,
		TracesSampleRate: 1.0,
		AttachStacktrace: true,
		BeforeSend: func(event *sentry.Event, hint *sentry.EventHint) *sentry.Event {
			// Filter out health check requests and other noise
			if event.Request != nil && event.Request.URL != "" {
				if event.Request.URL == "/api/health" {
					return nil // Don't send health check errors
				}
			}
			return event
		},
	})

	if err != nil {
		log.Printf("Failed to initialize Sentry: %v", err)
		return &SentryConfig{Client: nil}
	}

	log.Printf("Sentry initialized successfully - Environment: %s, Release: %s", environment, release)
	return &SentryConfig{Client: sentry.CurrentHub().Client()}
}

// CaptureError captures an error with additional context
func (sc *SentryConfig) CaptureError(err error, tags map[string]string, extra map[string]any) {
	if sc.Client == nil {
		return
	}

	sentry.WithScope(func(scope *sentry.Scope) {
		// Add tags
		for key, value := range tags {
			scope.SetTag(key, value)
		}

		// Add extra context
		for key, value := range extra {
			scope.SetExtra(key, value)
		}

		sentry.CaptureException(err)
	})
}

// CaptureMessage captures a message with level and context
func (sc *SentryConfig) CaptureMessage(message string, level sentry.Level, tags map[string]string, extra map[string]any) {
	if sc.Client == nil {
		return
	}

	sentry.WithScope(func(scope *sentry.Scope) {
		scope.SetLevel(level)

		// Add tags
		for key, value := range tags {
			scope.SetTag(key, value)
		}

		// Add extra context
		for key, value := range extra {
			scope.SetExtra(key, value)
		}

		sentry.CaptureMessage(message)
	})
}

// Flush ensures all events are sent before shutdown
func (sc *SentryConfig) Flush() {
	if sc.Client == nil {
		return
	}
	sentry.Flush(2 * time.Second)
}
