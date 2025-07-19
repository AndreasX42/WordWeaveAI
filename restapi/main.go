package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/AndreasX42/restapi/config"
	"github.com/AndreasX42/restapi/middlewares"
	"github.com/AndreasX42/restapi/utils"
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

	// Set up Gin server
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

		// Search and vocabularyroutes
		api.POST("/search", container.SearchHandler.SearchVocabulary)
		api.GET("/vocab", container.SearchHandler.GetVocabularyByPkSk)
		api.GET("/vocabs/:sourceLanguage/:targetLanguage/:pos/:word", container.SearchHandler.GetVocabularyByParams)

		// JWT routes
		api.POST("/auth/login", authMiddleware.LoginHandler)
		api.POST("/auth/logout", authMiddleware.LogoutHandler)
		api.POST("/auth/refresh", createRefreshHandler(authMiddleware, container))

		// Logging routes
		api.POST("/log", container.SentryHandler.LogEvent)

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

			// Logging routes
			// authenticated.POST("/log", container.SentryHandler.LogEvent)

			// Media routes
			authenticated.GET("/media/:mediaRef", container.SearchHandler.GetMediaByRef)

		}
	}
}

func createRefreshHandler(authMiddleware *jwt.GinJWTMiddleware, container *config.Container) gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"message": "Unauthorized",
				"details": gin.H{"error": "missing token"},
			})
			return
		}

		tokenString := strings.TrimPrefix(authHeader, "Bearer ")
		if tokenString == authHeader {
			c.JSON(http.StatusUnauthorized, gin.H{
				"message": "Unauthorized",
				"details": gin.H{"error": "invalid token format"},
			})
			return
		}

		userID, err := utils.VerifyJWT(tokenString)
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
