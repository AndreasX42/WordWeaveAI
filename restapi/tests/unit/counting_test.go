package unit

import (
	"context"
	"fmt"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/tests/mocks"
)

func TestUserRepositoryCountOperations(t *testing.T) {
	ctx := context.Background()

	t.Run("initialize user count", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)

		// Execute
		err := userRepo.InitializeUserCount(ctx)

		// Verify
		if err != nil {
			t.Errorf("InitializeUserCount failed: %v", err)
		}

		count, err := userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("GetTotalUserCount failed: %v", err)
		}

		if count != 0 {
			t.Errorf("Expected initial count to be 0, got %d", count)
		}
	})

	t.Run("user count increments on creation", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		userRepo.InitializeUserCount(ctx)

		// Create first user
		user1, _ := entities.NewUser("user1", "testuser1", "test1@example.com", "hash1", "code1")
		err := userRepo.Create(ctx, user1)
		if err != nil {
			t.Errorf("Failed to create user1: %v", err)
		}

		count, err := userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("GetTotalUserCount failed: %v", err)
		}

		if count != 1 {
			t.Errorf("Expected count to be 1 after first user creation, got %d", count)
		}

		// Create second user
		user2, _ := entities.NewUser("user2", "testuser2", "test2@example.com", "hash2", "code2")
		err = userRepo.Create(ctx, user2)
		if err != nil {
			t.Errorf("Failed to create user2: %v", err)
		}

		count, err = userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("GetTotalUserCount failed: %v", err)
		}

		if count != 2 {
			t.Errorf("Expected count to be 2 after second user creation, got %d", count)
		}
	})

	t.Run("user count decrements on deletion", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		userRepo.InitializeUserCount(ctx)

		// Create two users
		user1, _ := entities.NewUser("user1", "testuser1", "test1@example.com", "hash1", "code1")
		user2, _ := entities.NewUser("user2", "testuser2", "test2@example.com", "hash2", "code2")

		userRepo.Create(ctx, user1)
		userRepo.Create(ctx, user2)

		// Verify we have 2 users
		count, _ := userRepo.GetTotalUserCount(ctx)
		if count != 2 {
			t.Errorf("Expected count to be 2 before deletion, got %d", count)
		}

		// Delete first user
		err := userRepo.Delete(ctx, user1.ID)
		if err != nil {
			t.Errorf("Failed to delete user1: %v", err)
		}

		count, err = userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("GetTotalUserCount failed: %v", err)
		}

		if count != 1 {
			t.Errorf("Expected count to be 1 after deletion, got %d", count)
		}

		// Delete second user
		err = userRepo.Delete(ctx, user2.ID)
		if err != nil {
			t.Errorf("Failed to delete user2: %v", err)
		}

		count, err = userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("GetTotalUserCount failed: %v", err)
		}

		if count != 0 {
			t.Errorf("Expected count to be 0 after deleting all users, got %d", count)
		}
	})

	t.Run("user count doesn't go negative", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		userRepo.InitializeUserCount(ctx)

		// Create a user
		user, _ := entities.NewUser("user1", "testuser1", "test1@example.com", "hash1", "code1")
		userRepo.Create(ctx, user)

		// Delete the user
		userRepo.Delete(ctx, user.ID)

		// Try to delete again (should not go negative)
		userRepo.Delete(ctx, user.ID) // This should fail but not affect count

		count, err := userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("GetTotalUserCount failed: %v", err)
		}

		if count < 0 {
			t.Errorf("Count should not be negative, got %d", count)
		}
	})
}

func TestVocabListRepositoryCountOperations(t *testing.T) {
	ctx := context.Background()

	t.Run("initialize list count", func(t *testing.T) {
		// Setup
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)

		// Execute
		err := listRepo.InitializeListCount(ctx)

		// Verify
		if err != nil {
			t.Errorf("InitializeListCount failed: %v", err)
		}

		count, err := listRepo.GetTotalListCount(ctx)
		if err != nil {
			t.Errorf("GetTotalListCount failed: %v", err)
		}

		if count != 0 {
			t.Errorf("Expected initial count to be 0, got %d", count)
		}
	})

	t.Run("list count increments on creation", func(t *testing.T) {
		// Setup
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		listRepo.InitializeListCount(ctx)

		// Create first list
		list1 := entities.NewVocabList("user1", "My First List", "Description 1")
		err := listRepo.CreateList(ctx, list1)
		if err != nil {
			t.Errorf("Failed to create list1: %v", err)
		}

		count, err := listRepo.GetTotalListCount(ctx)
		if err != nil {
			t.Errorf("GetTotalListCount failed: %v", err)
		}

		if count != 1 {
			t.Errorf("Expected count to be 1 after first list creation, got %d", count)
		}

		// Create second list
		list2 := entities.NewVocabList("user2", "My Second List", "Description 2")
		err = listRepo.CreateList(ctx, list2)
		if err != nil {
			t.Errorf("Failed to create list2: %v", err)
		}

		count, err = listRepo.GetTotalListCount(ctx)
		if err != nil {
			t.Errorf("GetTotalListCount failed: %v", err)
		}

		if count != 2 {
			t.Errorf("Expected count to be 2 after second list creation, got %d", count)
		}
	})

	t.Run("list count decrements on deletion", func(t *testing.T) {
		// Setup
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		listRepo.InitializeListCount(ctx)

		// Create two lists
		list1 := entities.NewVocabList("user1", "My First List", "Description 1")
		list2 := entities.NewVocabList("user2", "My Second List", "Description 2")

		listRepo.CreateList(ctx, list1)
		listRepo.CreateList(ctx, list2)

		// Verify we have 2 lists
		count, _ := listRepo.GetTotalListCount(ctx)
		if count != 2 {
			t.Errorf("Expected count to be 2 before deletion, got %d", count)
		}

		// Delete first list
		err := listRepo.DeleteList(ctx, list1.UserID, list1.ID)
		if err != nil {
			t.Errorf("Failed to delete list1: %v", err)
		}

		count, err = listRepo.GetTotalListCount(ctx)
		if err != nil {
			t.Errorf("GetTotalListCount failed: %v", err)
		}

		if count != 1 {
			t.Errorf("Expected count to be 1 after deletion, got %d", count)
		}
	})
}

func TestVocabRepositoryCountOperations(t *testing.T) {
	ctx := context.Background()

	t.Run("get vocab count returns zero initially", func(t *testing.T) {
		// Setup
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		// Execute
		count, err := vocabRepo.GetTotalVocabCount(ctx)

		// Verify
		if err != nil {
			t.Errorf("GetTotalVocabCount failed: %v", err)
		}

		if count != 0 {
			t.Errorf("Expected initial count to be 0, got %d", count)
		}
	})

	t.Run("vocab count can be initialized", func(t *testing.T) {
		// Setup
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		// Initialize count
		err := vocabRepo.InitializeVocabCount(ctx)
		if err != nil {
			t.Errorf("InitializeVocabCount failed: %v", err)
		}

		// Verify initial count is 0
		count, err := vocabRepo.GetTotalVocabCount(ctx)
		if err != nil {
			t.Errorf("GetTotalVocabCount failed: %v", err)
		}

		if count != 0 {
			t.Errorf("Expected initial count to be 0, got %d", count)
		}
	})

	t.Run("vocab count can be set externally", func(t *testing.T) {
		// Setup
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		// Set count externally (simulating external data import)
		vocabRepo.SetVocabCount(50000)

		// Verify
		count, err := vocabRepo.GetTotalVocabCount(ctx)
		if err != nil {
			t.Errorf("GetTotalVocabCount failed: %v", err)
		}

		if count != 50000 {
			t.Errorf("Expected count to be 50000, got %d", count)
		}
	})

	t.Run("vocab count can be updated incrementally", func(t *testing.T) {
		// Setup
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)
		vocabRepo.SetVocabCount(1000)

		// Update count
		vocabRepo.SetVocabCount(1100)

		// Verify
		count, err := vocabRepo.GetTotalVocabCount(ctx)
		if err != nil {
			t.Errorf("GetTotalVocabCount failed: %v", err)
		}

		if count != 1100 {
			t.Errorf("Expected count to be 1100, got %d", count)
		}
	})
}

func TestCountingIntegration(t *testing.T) {
	ctx := context.Background()

	t.Run("all repositories provide counts", func(t *testing.T) {
		// Setup all repositories
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		// Initialize counts
		userRepo.InitializeUserCount(ctx)
		listRepo.InitializeListCount(ctx)
		vocabRepo.InitializeVocabCount(ctx)
		vocabRepo.SetVocabCount(75000)

		// Create some test data
		user, _ := entities.NewUser("user1", "testuser", "test@example.com", "hash", "code")
		userRepo.Create(ctx, user)

		list := entities.NewVocabList(user.ID, "Test List", "A test vocabulary list")
		listRepo.CreateList(ctx, list)

		// Get all counts
		userCount, err := userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("Failed to get user count: %v", err)
		}

		listCount, err := listRepo.GetTotalListCount(ctx)
		if err != nil {
			t.Errorf("Failed to get list count: %v", err)
		}

		vocabCount, err := vocabRepo.GetTotalVocabCount(ctx)
		if err != nil {
			t.Errorf("Failed to get vocab count: %v", err)
		}

		// Verify all counts
		if userCount != 1 {
			t.Errorf("Expected 1 user, got %d", userCount)
		}

		if listCount != 1 {
			t.Errorf("Expected 1 list, got %d", listCount)
		}

		if vocabCount != 75000 {
			t.Errorf("Expected 75000 vocab words, got %d", vocabCount)
		}

		// Simulate system stats response
		stats := map[string]int{
			"total_users":       userCount,
			"total_lists":       listCount,
			"total_vocab_words": vocabCount,
		}

		expectedStats := map[string]int{
			"total_users":       1,
			"total_lists":       1,
			"total_vocab_words": 75000,
		}

		for key, expected := range expectedStats {
			if actual, exists := stats[key]; !exists || actual != expected {
				t.Errorf("Expected %s to be %d, got %d", key, expected, actual)
			}
		}
	})

	t.Run("count operations are thread-safe", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		userRepo.InitializeUserCount(ctx)

		// Create multiple users concurrently
		numUsers := 10
		userChan := make(chan error, numUsers)

		for i := 0; i < numUsers; i++ {
			go func(id int) {
				user, err := entities.NewUser(
					fmt.Sprintf("user%d", id),
					fmt.Sprintf("testuser%d", id),
					fmt.Sprintf("test%d@example.com", id),
					"hash",
					"code",
				)
				if err != nil {
					userChan <- err
					return
				}

				err = userRepo.Create(ctx, user)
				userChan <- err
			}(i)
		}

		// Wait for all goroutines to complete
		for i := 0; i < numUsers; i++ {
			if err := <-userChan; err != nil {
				t.Errorf("Failed to create user concurrently: %v", err)
			}
		}

		// Verify final count
		count, err := userRepo.GetTotalUserCount(ctx)
		if err != nil {
			t.Errorf("Failed to get final user count: %v", err)
		}

		if count != numUsers {
			t.Errorf("Expected final count to be %d, got %d", numUsers, count)
		}
	})
}
