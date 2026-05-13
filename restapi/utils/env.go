package utils

import (
	"log"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"
)

// EnvInt parses an environment variable as int; on empty or invalid, logs and exits.
func EnvInt(key string, defaultVal int) int {
	s := strings.TrimSpace(os.Getenv(key))
	if s == "" {
		return defaultVal
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		log.Fatalf("Invalid int value for %s: %s: %v", key, s, err)
	}
	return v
}

// EnvPositiveInt parses an env var as positive int; invalid or non-positive logs and exits.
func EnvPositiveInt(key string, defaultVal int) int {
	v := EnvInt(key, defaultVal)
	if v <= 0 {
		log.Fatalf("Invalid positive int value for %s: %d", key, v)
	}
	return v
}

// EnvBool parses 1/true/yes (case-insensitive) as true, 0/false/no as false; empty uses defaultVal.
func EnvBool(key string, defaultVal bool) bool {
	s := strings.ToLower(strings.TrimSpace(os.Getenv(key)))
	switch s {
	case "":
		return defaultVal
	case "1", "true", "yes", "y", "on":
		return true
	case "0", "false", "no", "n", "off":
		return false
	default:
		log.Fatalf("Invalid bool value for %s: %s", key, s)
		return defaultVal
	}
}

func EnvMilliseconds(key string, defaultMs int) time.Duration {
	return time.Duration(EnvPositiveInt(key, defaultMs)) * time.Millisecond
}

// HTTPListenPort resolves PORT, default ":8080".
func HTTPListenPort() string {
	if p := strings.TrimSpace(os.Getenv("PORT")); p != "" {
		return p
	}
	return "8080"
}

// SlogLevel parses LOG_LEVEL (debug, info, warn, error); invalid or empty defaults to info.
func SlogLevel() slog.Level {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("LOG_LEVEL"))) {
	case "debug":
		return slog.LevelDebug
	case "warn", "warning":
		return slog.LevelWarn
	case "err", "error":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}
