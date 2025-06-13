package middlewares

import (
	"log"
	"os"
	"strings"
	"time"

	"github.com/gin-contrib/cors"
)

// GetCORSConfig returns CORS configuration based on environment
func GetCORSConfig() cors.Config {
	// Default allowed origins for development
	defaultOrigins := []string{
		"http://localhost:3000",
		"http://localhost:3001",
		"http://localhost:8080",
		"http://127.0.0.1:3000",
		"http://127.0.0.1:3001",
		"http://127.0.0.1:8080",
	}

	// Get allowed origins from environment variable
	allowedOrigins := os.Getenv("CORS_ALLOWED_ORIGINS")

	if allowedOrigins != "" {
		// Split by comma and trim spaces
		origins := strings.Split(allowedOrigins, ",")
		for i, origin := range origins {
			origins[i] = strings.TrimSpace(origin)
		}
		defaultOrigins = origins
	}

	if len(defaultOrigins) == 0 {
		log.Fatal("CORS_ALLOWED_ORIGINS is not set")
	}

	config := cors.Config{
		AllowAllOrigins: false,
		AllowOrigins:    defaultOrigins,
		AllowMethods: []string{
			"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH",
		},
		AllowHeaders: []string{
			"Origin",
			"Content-Type",
			"Accept",
			"Authorization",
			"X-Requested-With",
			"Access-Control-Request-Method",
			"Access-Control-Request-Headers",
		},
		ExposeHeaders: []string{
			"Content-Length",
			"Authorization",
			"Content-Type",
		},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}

	return config
}

// GetCORSConfigForDevelopment returns a permissive CORS config for development
func GetCORSConfigForDevelopment() cors.Config {
	return cors.Config{
		AllowAllOrigins:  true,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"},
		AllowHeaders:     []string{"*"},
		ExposeHeaders:    []string{"*"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}
}
