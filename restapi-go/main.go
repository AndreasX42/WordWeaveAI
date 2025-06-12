package main

import (
	"log"

	"github.com/AndreasX42/wordweave-go/config"
	"github.com/AndreasX42/wordweave-go/middlewares"
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

	// Register routes with dependency injection
	registerRoutes(server, container)

	// Start server
	server.Run(":8080")
}

func registerRoutes(server *gin.Engine, container *config.Container) {
	// Public routes
	server.POST("/users/register", container.UserHandler.Register)
	server.POST("/users/login", container.UserHandler.Login)
	server.POST("/users/confirm-email", container.UserHandler.ConfirmEmail)
	server.POST("/users/reset-password", container.UserHandler.ResetPassword)

	// Authenticated routes
	authenticated := server.Group("/users")
	authenticated.Use(middlewares.Authentication(container.UserService))
	authenticated.DELETE("/delete", container.UserHandler.Delete)
	authenticated.PUT("/update", container.UserHandler.Update)
}

func initEnvs() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
}
