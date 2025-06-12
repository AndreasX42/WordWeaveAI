package integration

import (
	"github.com/AndreasX42/wordweave-go/domain/repositories"
	infraRepos "github.com/AndreasX42/wordweave-go/infrastructure/repositories"
	"github.com/guregu/dynamo/v2"
)

// NewTestDynamoUserRepository creates a new test repository with the test table
func NewTestDynamoUserRepository(db *dynamo.DB) repositories.UserRepository {
	// Create a table reference for testing
	table := db.Table(TestTableName)

	// Use the real repository implementation
	return infraRepos.NewDynamoUserRepository(table)
}
