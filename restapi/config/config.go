package config

import (
	"context"
	"crypto/tls"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/handlers"
	infraRepos "github.com/AndreasX42/restapi/infrastructure/repositories"
	infraServices "github.com/AndreasX42/restapi/infrastructure/services"
	"github.com/AndreasX42/restapi/utils"
	jwt "github.com/appleboy/gin-jwt/v2"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ses"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/guregu/dynamo/v2"
)

// Container holds all dependencies
type Container struct {
	UserRepository       repositories.UserRepository
	VocabRepository      repositories.VocabRepository
	VocabListRepository  repositories.VocabListRepository
	VocabMediaRepository repositories.VocabMediaRepository
	EmailService         repositories.EmailService
	UserService          *services.UserService
	VocabService         *services.VocabService
	VocabListService     *services.VocabListService
	StatsService         *services.StatsService
	UserHandler          *handlers.UserHandler
	HealthHandler        *handlers.HealthHandler
	SearchHandler        *handlers.SearchHandler
	VocabListHandler     *handlers.VocabListHandler
	VocabRequestHandler  *handlers.VocabRequestHandler
	OAuthHandler         *handlers.OAuthHandler
	SentryHandler        *handlers.SentryHandler
	StatsHandler         *handlers.StatsHandler
	DynamoDB             *dynamo.DB
	SESClient            *ses.Client
	SQSClient            *sqs.Client
	GoogleOAuthConfig    *GoogleOAuthConfig
	SentryConfig         *SentryConfig
}

// NewContainer creates and wires all dependencies
func NewContainer() *Container {
	container := &Container{}

	// Initialize AWS services
	log.Println("Initializing AWS services")
	container.initAWS()

	// Initialize OAuth configuration
	log.Println("Initializing OAuth configuration")
	container.initOAuth()

	// Initialize Sentry configuration
	log.Println("Initializing Sentry configuration")
	container.initSentry()

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
	log.Println("Creating/checking database tables")
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

	// Optimize HTTP client for DynamoDB performance and ensure TLS for all AWS services
	cfg.HTTPClient = &http.Client{
		Timeout: 10 * time.Second,
		Transport: &http.Transport{
			MaxConnsPerHost:       50,                // Increase from default 100
			MaxIdleConns:          100,               // Increase from default 100
			MaxIdleConnsPerHost:   20,                // Increase from default 2
			IdleConnTimeout:       120 * time.Second, // Keep connections alive longer
			ResponseHeaderTimeout: 5 * time.Second,   // Wait max 5s for response headers
			ExpectContinueTimeout: 1 * time.Second,   // Wait 1s for "100 Continue" response
			DisableCompression:    true,              // DynamoDB responses are already compressed
			WriteBufferSize:       32 * 1024,         // 32KB write buffer
			ReadBufferSize:        32 * 1024,         // 32KB read buffer
			// TLS Configuration - Force TLS 1.2 minimum for all AWS services including SES
			TLSHandshakeTimeout: 3 * time.Second,
			ForceAttemptHTTP2:   true, // Use HTTP/2 when possible
			TLSClientConfig: &tls.Config{
				MinVersion:         tls.VersionTLS12, // Force minimum TLS 1.2
				InsecureSkipVerify: false,            // Always verify certificates
				ServerName:         "",               // Let Go auto-detect server name
			},
		},
	}

	// Initialize DynamoDB
	c.DynamoDB = dynamo.New(cfg)

	// Initialize SES with explicit TLS enforcement
	c.SESClient = ses.NewFromConfig(cfg)

	// Initialize SQS client
	c.SQSClient = sqs.NewFromConfig(cfg)

	log.Println("AWS services initialized")
}

func (c *Container) initOAuth() {
	c.GoogleOAuthConfig = NewGoogleOAuthConfig()
}

func (c *Container) initSentry() {
	c.SentryConfig = NewSentryConfig()
}

func (c *Container) initRepositories() {
	// Create DynamoDB table references
	usersTable := c.DynamoDB.Table(utils.GetTableName(os.Getenv("DYNAMODB_USER_TABLE_NAME")))
	vocabTable := c.DynamoDB.Table(utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_TABLE_NAME")))
	vocabListTable := c.DynamoDB.Table(utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_LIST_TABLE_NAME")))
	vocabMediaTable := c.DynamoDB.Table(utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_MEDIA_TABLE_NAME")))

	// Initialize repositories
	c.UserRepository = infraRepos.NewDynamoUserRepository(usersTable)
	c.VocabRepository = infraRepos.NewDynamoVocabRepository(vocabTable)
	c.VocabListRepository = infraRepos.NewDynamoVocabListRepository(vocabListTable)
	c.VocabMediaRepository = infraRepos.NewDynamoVocabMediaRepository(vocabMediaTable)
}

func (c *Container) initServices() {
	c.EmailService = infraServices.NewSESEmailService(c.SESClient)
	c.UserService = services.NewUserService(c.UserRepository, c.EmailService)
	c.VocabService = services.NewVocabService(c.VocabRepository, c.VocabMediaRepository)
	c.VocabListService = services.NewVocabListService(c.VocabListRepository, c.VocabRepository)
	c.StatsService = services.NewStatsService(c.UserRepository, c.VocabListRepository, c.VocabRepository)
}

func (c *Container) initHandlers() {
	c.HealthHandler = handlers.NewHealthHandler(c.DynamoDB)
	c.SearchHandler = handlers.NewSearchHandler(c.VocabService)
	c.VocabListHandler = handlers.NewVocabListHandler(c.VocabListService)
	c.VocabRequestHandler = handlers.NewVocabRequestHandler(c.SQSClient, c.UserRepository)
	c.OAuthHandler = handlers.NewOAuthHandler(c.UserService, c.GoogleOAuthConfig.Config)
	c.SentryHandler = handlers.NewSentryHandler(c.SentryConfig.Client)
	c.StatsHandler = handlers.NewStatsHandler(c.StatsService)
	// UserHandler will be set later in main.go after JWT middleware is created
}

// SetUserHandler sets the user handler after JWT middleware is available
func (c *Container) SetUserHandler(authMiddleware *jwt.GinJWTMiddleware) {
	c.UserHandler = handlers.NewUserHandler(c.UserService, authMiddleware)
}

func (c *Container) createTables() {
	ctx := context.Background()

	// Create User table
	c.createUserTable(ctx)

	// Create Vocabulary table
	c.createVocabularyTable(ctx)

	// Create Vocabulary List table
	c.createVocabularyListTable(ctx)

	// Create Vocabulary Media table
	c.createVocabularyMediaTable(ctx)
}

func (c *Container) createUserTable(ctx context.Context) {
	tableName := utils.GetTableName(os.Getenv("DYNAMODB_USER_TABLE_NAME"))

	// Check if table exists first
	table := c.DynamoDB.Table(tableName)
	_, err := table.Describe().Run(ctx)
	if err == nil {
		log.Printf("Table %s already exists", tableName)
		return
	}

	// Create table with indexes including OAuth support
	err = c.DynamoDB.CreateTable(tableName, infraRepos.UserRecord{}).
		Provision(5, 5). // Read/Write capacity units
		ProvisionIndex("EmailIndex", 5, 5).
		ProvisionIndex("UsernameIndex", 5, 5).
		ProvisionIndex("GoogleIDIndex", 5, 5).
		Run(ctx)

	if err != nil {
		log.Fatalf("Failed to create table %s: %v", tableName, err)
	}

	// Wait for table to be active
	c.waitForTable(ctx, tableName)
	log.Printf("Table %s created successfully", tableName)
}

func (c *Container) createVocabularyTable(ctx context.Context) {
	tableName := utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_TABLE_NAME"))

	// Check if table exists first
	table := c.DynamoDB.Table(tableName)
	_, err := table.Describe().Run(ctx)
	if err == nil {
		log.Printf("Table %s already exists", tableName)
		return
	}

	// Create vocabulary table with indexes matching AWS CDK structure
	err = c.DynamoDB.CreateTable(tableName, infraRepos.VocabRecord{}).
		Provision(5, 5).                                 // Read/Write capacity units
		ProvisionIndex("ReverseLookupIndex", 5, 5).      // GSI-1: LKP + SRC_LANG for reverse lookup
		ProvisionIndex("EnglishMediaLookupIndex", 5, 5). // GSI-2: english_word for media reuse
		Run(ctx)

	if err != nil {
		log.Fatalf("Failed to create vocabulary table %s: %v", tableName, err)
	}

	// Wait for table to be active
	c.waitForTable(ctx, tableName)
	log.Printf("Vocabulary table %s created successfully", tableName)
}

func (c *Container) createVocabularyListTable(ctx context.Context) {
	tableName := utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_LIST_TABLE_NAME"))

	// Check if table exists first
	table := c.DynamoDB.Table(tableName)
	_, err := table.Describe().Run(ctx)
	if err == nil {
		log.Printf("Table %s already exists", tableName)
		return
	}

	// Create vocabulary list table
	err = c.DynamoDB.CreateTable(tableName, infraRepos.VocabListRecord{}).
		Provision(5, 5). // Read/Write capacity units
		Run(ctx)

	if err != nil {
		log.Fatalf("Failed to create vocabulary list table %s: %v", tableName, err)
	}

	// Wait for table to be active
	c.waitForTable(ctx, tableName)
	log.Printf("Vocabulary list table %s created successfully", tableName)
}

func (c *Container) createVocabularyMediaTable(ctx context.Context) {
	tableName := utils.GetTableName(os.Getenv("DYNAMODB_VOCAB_MEDIA_TABLE_NAME"))

	// Check if table exists first
	table := c.DynamoDB.Table(tableName)
	_, err := table.Describe().Run(ctx)
	if err == nil {
		log.Printf("Table %s already exists", tableName)
		return
	}

	// Create vocabulary media table with simple structure
	err = c.DynamoDB.CreateTable(tableName, infraRepos.VocabMediaRecord{}).
		Provision(5, 5). // Read/Write capacity units
		Run(ctx)

	if err != nil {
		log.Fatalf("Failed to create vocabulary media table %s: %v", tableName, err)
	}

	// Wait for table to be active
	c.waitForTable(ctx, tableName)
	log.Printf("Vocabulary media table %s created successfully", tableName)
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
