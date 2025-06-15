package config

import (
	"context"
	"log"
	"os"
	"time"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/handlers"
	infraRepos "github.com/AndreasX42/restapi/infrastructure/repositories"
	infraServices "github.com/AndreasX42/restapi/infrastructure/services"
	"github.com/AndreasX42/restapi/utils"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ses"
	"github.com/guregu/dynamo/v2"
)

// Container holds all dependencies
type Container struct {
	UserRepository repositories.UserRepository
	EmailService   repositories.EmailService
	UserService    *services.UserService
	UserHandler    *handlers.UserHandler
	HealthHandler  *handlers.HealthHandler
	DynamoDB       *dynamo.DB
	SESClient      *ses.Client
}

// NewContainer creates and wires all dependencies
func NewContainer() *Container {
	container := &Container{}

	// Initialize AWS services
	log.Println("Initializing AWS services")
	container.initAWS()

	// Initialize repositories
	log.Println("Initializing repositories")
	container.initRepositories()

	// Initialize services
	log.Println("Initializing services")
	container.initServices()

	// Initialize handlers
	log.Println("Initializing handlers")
	container.initHandlers()

	// Create database tables
	log.Println("Creating database tables")
	container.createTables()

	log.Println("Container initialized successfully")
	return container
}

func (c *Container) initAWS() {
	cfg, err := config.LoadDefaultConfig(context.TODO(), func(o *config.LoadOptions) error {
		if region := os.Getenv("AWS_REGION"); region != "" {
			o.Region = region
		} else {
			o.Region = "us-east-1"
		}
		return nil
	})
	if err != nil {
		log.Fatal("AWS config load failed:", err)
	}

	// Initialize DynamoDB
	c.DynamoDB = dynamo.New(cfg)

	// Initialize SES
	c.SESClient = ses.NewFromConfig(cfg)
}

func (c *Container) initRepositories() {
	// Create DynamoDB table reference
	usersTable := c.DynamoDB.Table(utils.GetTableName(os.Getenv("DYNAMODB_USER_TABLE_NAME")))

	// Initialize repositories
	c.UserRepository = infraRepos.NewDynamoUserRepository(usersTable)
}

func (c *Container) initServices() {
	c.EmailService = infraServices.NewSESEmailService(c.SESClient)
	c.UserService = services.NewUserService(c.UserRepository, c.EmailService)
}

func (c *Container) initHandlers() {
	c.UserHandler = handlers.NewUserHandler(c.UserService)
	c.HealthHandler = handlers.NewHealthHandler(c.DynamoDB)
}

func (c *Container) createTables() {
	ctx := context.Background()
	tableName := utils.GetTableName(os.Getenv("DYNAMODB_USER_TABLE_NAME"))

	// Check if table exists first
	table := c.DynamoDB.Table(tableName)
	_, err := table.Describe().Run(ctx)
	if err == nil {
		log.Printf("Table %s already exists", tableName)
		return
	}

	// Create table with indexes
	err = c.DynamoDB.CreateTable(tableName, infraRepos.UserRecord{}).
		Provision(5, 5). // Read/Write capacity units
		ProvisionIndex("EmailIndex", 5, 5).
		ProvisionIndex("UsernameIndex", 5, 5).
		Run(ctx)

	if err != nil {
		log.Fatalf("Failed to create table %s: %v", tableName, err)
	}

	// Wait for table to be active
	c.waitForTable(ctx, tableName)
	log.Printf("Table %s created successfully", tableName)
}

// waitForTable waits for a table to become active
func (c *Container) waitForTable(ctx context.Context, tableName string) {
	table := c.DynamoDB.Table(tableName)

	for i := 0; i < 60; i++ { // Wait up to 60 seconds
		desc, err := table.Describe().Run(ctx)
		if err != nil {
			log.Printf("Error checking table status: %v", err)
			time.Sleep(1 * time.Second)
			continue
		}

		if desc.Status == "ACTIVE" {
			return
		}

		log.Printf("Waiting for table %s to become active (status: %s)", tableName, desc.Status)
		time.Sleep(1 * time.Second)
	}

	log.Fatalf("Table %s did not become active within timeout", tableName)
}
