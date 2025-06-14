package integration

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"
	"github.com/guregu/dynamo/v2"
)

const (
	DynamoDBLocalEndpoint = "http://localhost:8081"
	TestTableName         = "users-test"
)

// SetupDynamoDBLocal creates a DynamoDB client configured for local testing
func SetupDynamoDBLocal() (*dynamo.DB, *dynamodb.Client, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion("us-east-1"),
		config.WithEndpointResolverWithOptions(aws.EndpointResolverWithOptionsFunc(
			func(service, region string, options ...interface{}) (aws.Endpoint, error) {
				return aws.Endpoint{URL: DynamoDBLocalEndpoint}, nil
			})),
		config.WithCredentialsProvider(credentials.StaticCredentialsProvider{
			Value: aws.Credentials{
				AccessKeyID:     "dummy",
				SecretAccessKey: "dummy",
			},
		}),
	)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	// Create AWS SDK client for table management
	awsClient := dynamodb.NewFromConfig(cfg)

	// Wait for DynamoDB Local to be ready
	if err := waitForDynamoDB(awsClient); err != nil {
		return nil, nil, fmt.Errorf("DynamoDB Local not ready: %w", err)
	}

	// Create guregu/dynamo client for repository usage
	dynamoClient := dynamo.New(cfg)

	return dynamoClient, awsClient, nil
}

// CreateTestTable creates the users table for testing
func CreateTestTable(client *dynamodb.Client) error {
	// Delete table if it exists
	_, err := client.DeleteTable(context.TODO(), &dynamodb.DeleteTableInput{
		TableName: aws.String(TestTableName),
	})
	if err != nil {
		// Ignore error if table doesn't exist
		log.Printf("Table deletion error (expected if table doesn't exist): %v", err)
	}

	// Wait a bit for deletion to complete
	time.Sleep(1 * time.Second)

	// Create the table with the correct schema for our UserRecord
	_, err = client.CreateTable(context.TODO(), &dynamodb.CreateTableInput{
		TableName: aws.String(TestTableName),
		KeySchema: []types.KeySchemaElement{
			{
				AttributeName: aws.String("user_id"),
				KeyType:       types.KeyTypeHash,
			},
		},
		AttributeDefinitions: []types.AttributeDefinition{
			{
				AttributeName: aws.String("user_id"),
				AttributeType: types.ScalarAttributeTypeS,
			},
			{
				AttributeName: aws.String("email"),
				AttributeType: types.ScalarAttributeTypeS,
			},
			{
				AttributeName: aws.String("username"),
				AttributeType: types.ScalarAttributeTypeS,
			},
		},
		GlobalSecondaryIndexes: []types.GlobalSecondaryIndex{
			{
				IndexName: aws.String("EmailIndex"),
				KeySchema: []types.KeySchemaElement{
					{
						AttributeName: aws.String("email"),
						KeyType:       types.KeyTypeHash,
					},
				},
				Projection: &types.Projection{
					ProjectionType: types.ProjectionTypeAll,
				},
				ProvisionedThroughput: &types.ProvisionedThroughput{
					ReadCapacityUnits:  aws.Int64(5),
					WriteCapacityUnits: aws.Int64(5),
				},
			},
			{
				IndexName: aws.String("UsernameIndex"),
				KeySchema: []types.KeySchemaElement{
					{
						AttributeName: aws.String("username"),
						KeyType:       types.KeyTypeHash,
					},
				},
				Projection: &types.Projection{
					ProjectionType: types.ProjectionTypeAll,
				},
				ProvisionedThroughput: &types.ProvisionedThroughput{
					ReadCapacityUnits:  aws.Int64(5),
					WriteCapacityUnits: aws.Int64(5),
				},
			},
		},
		ProvisionedThroughput: &types.ProvisionedThroughput{
			ReadCapacityUnits:  aws.Int64(5),
			WriteCapacityUnits: aws.Int64(5),
		},
	})

	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	// Wait for table to be active
	return waitForTableActive(client, TestTableName)
}

// CleanupTestTable deletes the test table
func CleanupTestTable(client *dynamodb.Client) error {
	_, err := client.DeleteTable(context.TODO(), &dynamodb.DeleteTableInput{
		TableName: aws.String(TestTableName),
	})
	return err
}

func waitForDynamoDB(client *dynamodb.Client) error {
	maxRetries := 30
	for i := 0; i < maxRetries; i++ {
		_, err := client.ListTables(context.TODO(), &dynamodb.ListTablesInput{})
		if err == nil {
			return nil
		}
		log.Printf("Waiting for DynamoDB Local... attempt %d/%d", i+1, maxRetries)
		time.Sleep(1 * time.Second)
	}
	return fmt.Errorf("DynamoDB Local not ready after %d attempts", maxRetries)
}

func waitForTableActive(client *dynamodb.Client, tableName string) error {
	maxRetries := 30
	for i := 0; i < maxRetries; i++ {
		resp, err := client.DescribeTable(context.TODO(), &dynamodb.DescribeTableInput{
			TableName: aws.String(tableName),
		})
		if err != nil {
			return fmt.Errorf("failed to describe table: %w", err)
		}

		if resp.Table.TableStatus == types.TableStatusActive {
			// Also wait for GSIs to be active
			allGSIsActive := true
			for _, gsi := range resp.Table.GlobalSecondaryIndexes {
				if gsi.IndexStatus != types.IndexStatusActive {
					allGSIsActive = false
					break
				}
			}
			if allGSIsActive {
				return nil
			}
		}

		log.Printf("Waiting for table to be active... attempt %d/%d", i+1, maxRetries)
		time.Sleep(1 * time.Second)
	}
	return fmt.Errorf("table not active after %d attempts", maxRetries)
}
