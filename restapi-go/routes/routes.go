package routes

import (
	"github.com/AndreasX42/wordweave-go/middlewares"
	"github.com/gin-gonic/gin"
)

func RegisterRoutes(server *gin.Engine) {
	// server.GET("/events", getEvents)
	// server.GET("/events/:id", getEvent)

	// authenticated := server.Group("/")
	// authenticated.Use(middlewares.Authentication)
	// authenticated.POST("/events", createEvent)
	// authenticated.PUT("/events/:id", updateEvent)
	// authenticated.DELETE("/events/:id", deleteEvent)

	authenticated := server.Group("/users")
	authenticated.Use(middlewares.Authentication)
	authenticated.DELETE("/delete", delete)

	server.POST("/users/login", login)
	server.POST("/users/confirm-email", confirmEmail)
	server.POST("/users/register", register)
}
