package main

import (
	"context"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/AndreasX42/restapi/config"
	"github.com/AndreasX42/restapi/middlewares"
	"github.com/AndreasX42/restapi/utils"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Initialize environment variables
	initEnvs()

	// Structured JSON logging (stdout -> CloudWatch)
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: utils.SlogLevel(),
	})))

	// Initialize dependency container
	container := config.NewContainer()

	// Set up Gin server
	server := gin.Default()

	// Configure CORS middleware
	server.Use(cors.New(middlewares.GetCORSConfig()))

	// Structured request logging middleware
	server.Use(middlewares.RequestLoggerMiddleware())

	// Configure Sentry middleware
	server.Use(middlewares.SentryMiddleware(container.SentryConfig))

	// Register routes with dependency injection
	registerRoutes(server, container)

	addr := utils.HTTPListenPort()

	// Create HTTP server
	srv := &http.Server{
		Addr:    ":" + addr,
		Handler: server,
	}

	// Start server in a goroutine
	go func() {
		log.Println("Starting server on", addr)
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

	shutdownMs := utils.EnvPositiveInt("SHUTDOWN_TIMEOUT_MS", 5000)
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(shutdownMs)*time.Millisecond)
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

	// Set handlers that need JWT middleware
	container.SetUserHandler(authMiddleware)
	container.SetOAuthHandler(authMiddleware)

	// Create API route group
	api := server.Group("/api")
	{
		// Health check routes
		api.GET("/health", container.HealthHandler.HealthCheck)

		// Stats routes
		api.GET("/stats", container.StatsHandler.GetAppStats)

		// Public routes
		api.POST("/auth/register", container.UserHandler.Register)
		api.POST("/auth/confirm-email", container.UserHandler.ConfirmEmail)
		api.POST("/auth/resend-code", container.UserHandler.ResendConfirmationCode)
		api.POST("/auth/reset-password", container.UserHandler.ResetPassword)

		// JWT routes
		api.POST("/auth/login", authMiddleware.LoginHandler)
		api.POST("/auth/logout", authMiddleware.LogoutHandler)
		api.POST("/auth/refresh", authMiddleware.RefreshHandler)

		// OAuth routes
		api.GET("/auth/google/login", container.OAuthHandler.GoogleLogin)
		api.GET("/auth/google/callback", container.OAuthHandler.GoogleCallback)

		// Search and vocab routes
		api.POST("/vocabs/search", container.SearchHandler.SearchVocabulary)
		api.GET("/vocabs/get", container.SearchHandler.GetVocabularyByPkSk)
		api.GET("/vocabs/get/:sourceLanguage/:targetLanguage/:pos/:word", container.SearchHandler.GetVocabularyByParams)

		// Logging routes
		api.POST("/log", container.SentryHandler.LogEvent)

		// Authenticated routes
		authenticated := api.Group("/")
		authenticated.Use(authMiddleware.MiddlewareFunc())
		{
			// Auth route (after google login)
			authenticated.GET("/auth/me", container.UserHandler.GetCurrentUser)

			// User routes
			userRoutes := authenticated.Group("/users")
			userRoutes.DELETE("/delete", container.UserHandler.Delete)
			userRoutes.PUT("/update", container.UserHandler.Update)

			// Vocabulary list routes (authenticated)
			listRoutes := authenticated.Group("/lists")
			listRoutes.POST("", container.VocabListHandler.CreateList)
			listRoutes.GET("", container.VocabListHandler.GetLists)
			listRoutes.GET("/:listId", container.VocabListHandler.GetList)
			listRoutes.PUT("/:listId", container.VocabListHandler.UpdateList)
			listRoutes.DELETE("/:listId", container.VocabListHandler.DeleteList)

			// Word management routes within lists (authenticated)
			listRoutes.POST("/:listId/words", container.VocabListHandler.AddWordToList)
			listRoutes.DELETE("/:listId/words", container.VocabListHandler.RemoveWordFromList)
			listRoutes.GET("/:listId/words", container.VocabListHandler.GetWordsInListWithData)
			listRoutes.PUT("/:listId/words/status", container.VocabListHandler.UpdateWordStatus)

			// Vocabulary request routes (authenticated)
			authenticated.POST("/vocabs/request", container.VocabRequestHandler.RequestVocab)

		}
	}
}

func initEnvs() {
	// In production/release mode, use environment variables passed to container
	if os.Getenv("GIN_MODE") == "release" {
		log.Println("Running in release mode, using system environment variables")
		return
	}

	// In development mode, try to load .env files
	err := godotenv.Load(".env")
	if err != nil {
		log.Println("No .env file found, using system environment variables:", err)
	} else {
		log.Println("Loaded .env file successfully")
	}
}
