package main

import (
	"log"
	"os"

	"github.com/AndreasX42/restapi/config"
	"github.com/AndreasX42/restapi/middlewares"
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

	// Register routes with dependency injection
	registerRoutes(server, container)

	// Start server
	server.Run(":8080")
}

func registerRoutes(server *gin.Engine, container *config.Container) {
	// Initialize JWT middleware
	authMiddleware, err := middlewares.JWTMiddleware(container.UserService)
	if err != nil {
		log.Fatal("JWT Error: " + err.Error())
	}

	// Health check routes
	server.GET("/health", container.HealthHandler.HealthCheck)

	// Public routes
	server.POST("/users/register", container.UserHandler.Register)
	server.POST("/users/confirm-email", container.UserHandler.ConfirmEmail)
	server.POST("/users/reset-password", container.UserHandler.ResetPassword)

	// JWT routes
	server.POST("/auth/login", authMiddleware.LoginHandler)
	server.POST("/auth/logout", authMiddleware.LogoutHandler)
	server.POST("/auth/refresh", authMiddleware.RefreshHandler)

	// Authenticated routes
	authenticated := server.Group("/users")
	authenticated.Use(authMiddleware.MiddlewareFunc())
	authenticated.DELETE("/delete", container.UserHandler.Delete)
	authenticated.PUT("/update", container.UserHandler.Update)
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
