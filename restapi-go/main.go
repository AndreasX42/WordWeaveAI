package main

import (
	"log"

	"github.com/AndreasX42/wordweave-go/aws"
	"github.com/AndreasX42/wordweave-go/routes"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	initEnvs()
	aws.InitDB()
	aws.InitSES()

	server := gin.Default()
	routes.RegisterRoutes(server)
	server.Run(":8080")
}

func initEnvs() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
}
