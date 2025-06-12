package aws

import (
	"context"
	"log"
	"os"
	"time"

	"github.com/AndreasX42/wordweave-go/utils"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/guregu/dynamo/v2"
)

var (
	DB         *dynamo.DB
	UsersTable dynamo.Table
)

// InitDB initializes the database connection using the dynamo library
func InitDB() {
	cfg, err := config.LoadDefaultConfig(context.TODO(), func(o *config.LoadOptions) error {
		// Set region from environment or default
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

	// Initialize dynamo client
	DB = dynamo.New(cfg)

	// Initialize table references (cached)
	initTableReferences()

	// Create tables if they don't exist
	createTables()
}

// initTableReferences creates cached table references
func initTableReferences() {
	UsersTable = DB.Table(utils.GetTableName("users"))
}

// createTables creates all necessary tables
func createTables() {
	ctx := context.Background()

	// Create users table
	createUsersTable(ctx)
}

// createUsersTable creates the users table with proper indexes
func createUsersTable(ctx context.Context) {
	tableName := utils.GetTableName("users")

	// Check if table exists first
	table := DB.Table(tableName)
	_, err := table.Describe().Run(ctx)
	if err == nil {
		log.Printf("Table %s already exists", tableName)
		return
	}

	// Create table with indexes
	err = DB.CreateTable(tableName, UserRecord{}).
		Provision(5, 5). // Read/Write capacity units - adjust as needed
		ProvisionIndex("EmailIndex", 5, 5).
		ProvisionIndex("UsernameIndex", 5, 5).
		Run(ctx)

	if err != nil {
		log.Fatalf("Failed to create table %s: %v", tableName, err)
	}

	// Wait for table to be active
	waitForTable(ctx, tableName)
	log.Printf("Table %s created successfully", tableName)
}

// waitForTable waits for a table to become active
func waitForTable(ctx context.Context, tableName string) {
	table := DB.Table(tableName)

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

// UserRecord represents the DynamoDB user record structure
type UserRecord struct {
	UserID           string    `dynamo:"user_id,hash" index:"EmailIndex,range" index:"UsernameIndex,range"`
	Email            string    `dynamo:"email" index:"EmailIndex,hash"`
	Username         string    `dynamo:"username" index:"UsernameIndex,hash"`
	PasswordHash     string    `dynamo:"password_hash"`
	ConfirmationCode string    `dynamo:"confirmation_code"`
	ConfirmedEmail   bool      `dynamo:"confirmed_email"`
	IsActive         bool      `dynamo:"is_active"`
	IsAdmin          bool      `dynamo:"is_admin"`
	CreatedAt        time.Time `dynamo:"created_at"`
}
