package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/AndreasX42/restapi/config"
	"github.com/AndreasX42/restapi/middlewares"
	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Initialize environment variables
	initEnvs()

	// Initialize dependency container
	container := config.NewContainer()

	// Setup Gin server
	server := gin.Default()

	// Configure CORS middleware
	server.Use(cors.New(middlewares.GetCORSConfig()))

	// Configure Sentry middleware
	server.Use(middlewares.SentryMiddleware(container.SentryConfig))

	// Register routes with dependency injection
	registerRoutes(server, container)

	// Create HTTP server
	srv := &http.Server{
		Addr:    ":8080",
		Handler: server,
	}

	// Start server in a goroutine
	go func() {
		log.Println("Starting server on :8080")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	// Wait for interrupt signal to gracefully shut down the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	// Flush Sentry events
	if container.SentryConfig != nil {
		log.Println("Flushing Sentry events...")
		container.SentryConfig.Flush()
	}

	// Give a 5-second timeout for the server to finish handling requests
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("Server exiting")
}

func registerRoutes(server *gin.Engine, container *config.Container) {
	// Initialize JWT middleware
	authMiddleware, err := middlewares.JWTMiddleware(container.UserService)
	if err != nil {
		log.Fatal("JWT Error: " + err.Error())
	}

	// Create API route group
	api := server.Group("/api")
	{
		// Health check routes
		api.GET("/health", container.HealthHandler.HealthCheck)

		// Public routes
		api.POST("/auth/register", container.UserHandler.Register)
		api.POST("/auth/confirm-email", container.UserHandler.ConfirmEmail)
		api.POST("/auth/resend-code", container.UserHandler.ResendConfirmationCode)
		api.POST("/auth/reset-password", container.UserHandler.ResetPassword)

		// OAuth routes
		api.GET("/auth/google/login", container.OAuthHandler.GoogleLogin)
		api.GET("/auth/google/callback", container.OAuthHandler.GoogleCallback)

		// Search routes
		api.POST("/search", container.SearchHandler.SearchVocabulary)

		// Logging routes (public, but can be secured later if needed)
		api.POST("/log", container.SentryHandler.LogEvent)

		// JWT routes
		api.POST("/auth/login", authMiddleware.LoginHandler)
		api.POST("/auth/logout", authMiddleware.LogoutHandler)
		api.POST("/auth/refresh", createRefreshHandler(authMiddleware, container))

		// Authenticated routes
		authenticated := api.Group("/")
		authenticated.Use(authMiddleware.MiddlewareFunc())
		{
			// Auth routes (authenticated)
			authenticated.GET("/auth/me", container.UserHandler.GetCurrentUser)

			// User routes
			userRoutes := authenticated.Group("/users")
			userRoutes.DELETE("/delete", container.UserHandler.Delete)
			userRoutes.PUT("/update", container.UserHandler.Update)

			// Vocabulary list routes
			vocabListRoutes := authenticated.Group("/vocabs")
			{
				// List management
				vocabListRoutes.POST("/", container.VocabListHandler.CreateList)
				vocabListRoutes.GET("/", container.VocabListHandler.GetLists)
				vocabListRoutes.GET("/:listId", container.VocabListHandler.GetList)
				vocabListRoutes.PUT("/:listId", container.VocabListHandler.UpdateList)
				vocabListRoutes.DELETE("/:listId", container.VocabListHandler.DeleteList)

				// Word management within lists
				vocabListRoutes.POST("/:listId/words", container.VocabListHandler.AddWordToList)
				vocabListRoutes.GET("/:listId/words", container.VocabListHandler.GetWordsInList)
				vocabListRoutes.DELETE("/:listId/words/:wordId", container.VocabListHandler.RemoveWordFromList)
				vocabListRoutes.PUT("/:listId/words/:wordId/status", container.VocabListHandler.UpdateWordStatus)
			}
		}
	}
}

func createRefreshHandler(authMiddleware *jwt.GinJWTMiddleware, container *config.Container) gin.HandlerFunc {
	return func(c *gin.Context) {
		userID, err := extractUserIDFromToken(c)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"message": "Unauthorized",
				"details": gin.H{"error": err.Error()},
			})
			return
		}

		// Check if user still exists
		if _, err := container.UserService.GetUserByID(c.Request.Context(), userID); err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"message": "Unauthorized",
				"details": gin.H{"error": "user does not exist"},
			})
			return
		}

		// Delegate to the default refresh logic
		authMiddleware.RefreshHandler(c)
	}
}

func extractUserIDFromToken(c *gin.Context) (string, error) {
	authHeader := c.GetHeader("Authorization")
	if authHeader == "" {
		return "", errors.New("missing token")
	}

	tokenString := strings.TrimPrefix(authHeader, "Bearer ")
	if tokenString == authHeader {
		return "", errors.New("invalid token format")
	}

	parts := strings.Split(tokenString, ".")
	if len(parts) != 3 {
		return "", errors.New("invalid token format")
	}

	payload := parts[1]
	if len(payload)%4 != 0 {
		payload += strings.Repeat("=", 4-len(payload)%4)
	}

	claimsBytes, err := base64.URLEncoding.DecodeString(payload)
	if err != nil {
		return "", errors.New("invalid token claims")
	}

	var claims map[string]interface{}
	if err := json.Unmarshal(claimsBytes, &claims); err != nil {
		return "", errors.New("invalid token claims")
	}

	userID, ok := claims["user_id"].(string)
	if !ok {
		return "", errors.New("user_id not found in claims")
	}

	return userID, nil
}

func initEnvs() {
	// In production/release mode, use environment variables passed to container
	if os.Getenv("GIN_MODE") == "release" {
		log.Println("Running in release mode, using system environment variables")
		return
	}

	// In development mode, try to load .env files
	err := godotenv.Load("/app/.env", ".env")
	if err != nil {
		log.Println("No .env file found, using system environment variables:", err)
	} else {
		log.Println("Loaded .env file successfully")
	}
}
