package unit

import (
	"context"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/tests/mocks"
)

func TestStatsService_GetSystemStats(t *testing.T) {
	ctx := context.Background()

	t.Run("successful stats retrieval with automatic initialization", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		statsService := services.NewStatsService(userRepo, listRepo, vocabRepo)

		// Set up some test data (without manual initialization)
		vocabRepo.SetVocabCount(50000)

		// Create some test entities
		user, _ := entities.NewUser("user1", "testuser", "test@example.com", "hash", "code")
		userRepo.Create(ctx, user)

		list := entities.NewVocabList(user.ID, "Test List", "A test list")
		listRepo.CreateList(ctx, list)

		// Execute - this should automatically initialize counts
		stats, err := statsService.GetAppStats(ctx)

		// Verify
		if err != nil {
			t.Errorf("GetSystemStats failed: %v", err)
		}

		if stats == nil {
			t.Fatal("Expected stats to not be nil")
		}

		if stats.TotalUsers != 1 {
			t.Errorf("Expected 1 user, got %d", stats.TotalUsers)
		}

		if stats.TotalLists != 1 {
			t.Errorf("Expected 1 list, got %d", stats.TotalLists)
		}

		if stats.TotalVocabWords != 50000 {
			t.Errorf("Expected 50000 vocab words, got %d", stats.TotalVocabWords)
		}

		if stats.LastUpdated.IsZero() {
			t.Error("Expected LastUpdated to be set")
		}
	})

	t.Run("caching behavior", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		statsService := services.NewStatsService(userRepo, listRepo, vocabRepo)

		// First call - should fetch fresh data
		stats1, err := statsService.GetAppStats(ctx)
		if err != nil {
			t.Errorf("First GetSystemStats failed: %v", err)
		}
		if stats1 == nil {
			t.Fatal("Expected stats1 to not be nil")
		}

		firstCallTime := stats1.LastUpdated

		// Create additional data
		user, _ := entities.NewUser("user2", "testuser2", "test2@example.com", "hash", "code")
		userRepo.Create(ctx, user)

		// Second call immediately - should return cached data
		stats2, err := statsService.GetAppStats(ctx)
		if err != nil {
			t.Errorf("Second GetSystemStats failed: %v", err)
		}
		if stats2 == nil {
			t.Fatal("Expected stats2 to not be nil")
		}

		// Should return cached data (same timestamp, doesn't reflect new user)
		if stats2.LastUpdated != firstCallTime {
			t.Error("Expected cached data with same timestamp")
		}
		if stats2.TotalUsers != stats1.TotalUsers {
			t.Error("Expected cached data to have same user count")
		}
	})

	t.Run("stats with empty system", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		statsService := services.NewStatsService(userRepo, listRepo, vocabRepo)

		// Execute - should automatically initialize and return zeros
		stats, err := statsService.GetAppStats(ctx)

		// Verify
		if err != nil {
			t.Errorf("GetSystemStats failed: %v", err)
		}

		if stats.TotalUsers != 0 {
			t.Errorf("Expected 0 users, got %d", stats.TotalUsers)
		}

		if stats.TotalLists != 0 {
			t.Errorf("Expected 0 lists, got %d", stats.TotalLists)
		}

		if stats.TotalVocabWords != 0 {
			t.Errorf("Expected 0 vocab words, got %d", stats.TotalVocabWords)
		}
	})
}

func TestStatsService_CacheBehavior(t *testing.T) {
	ctx := context.Background()

	t.Run("clear cache functionality", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)
		listRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)

		statsService := services.NewStatsService(userRepo, listRepo, vocabRepo)

		// First call to populate cache
		stats1, err := statsService.GetAppStats(ctx)
		if err != nil {
			t.Errorf("First GetSystemStats failed: %v", err)
		}

		// Clear cache
		statsService.ClearCache()

		// Create additional data
		user, _ := entities.NewUser("user1", "testuser", "test@example.com", "hash", "code")
		userRepo.Create(ctx, user)

		// Second call should fetch fresh data (not cached)
		stats2, err := statsService.GetAppStats(ctx)
		if err != nil {
			t.Errorf("Second GetSystemStats failed: %v", err)
		}

		// Should reflect new user
		if stats2.TotalUsers != stats1.TotalUsers+1 {
			t.Errorf("Expected user count to increase by 1, got %d -> %d", stats1.TotalUsers, stats2.TotalUsers)
		}

		// Should have newer timestamp
		if !stats2.LastUpdated.After(stats1.LastUpdated) {
			t.Error("Expected newer timestamp after cache clear")
		}
	})
}
