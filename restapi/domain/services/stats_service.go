package services

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/AndreasX42/restapi/domain/repositories"
	"golang.org/x/sync/errgroup"
)

// StatsService provides system statistics aggregation with caching
type StatsService struct {
	userRepo      repositories.UserRepository
	vocabListRepo repositories.VocabListRepository
	vocabRepo     repositories.VocabRepository

	// Cache fields
	cachedStats *SystemStats
	cacheExpiry time.Time
	mutex       sync.RWMutex
	initialized bool
}

// NewStatsService creates a new stats service with caching
func NewStatsService(userRepo repositories.UserRepository, vocabListRepo repositories.VocabListRepository, vocabRepo repositories.VocabRepository) *StatsService {
	return &StatsService{
		userRepo:      userRepo,
		vocabListRepo: vocabListRepo,
		vocabRepo:     vocabRepo,
		initialized:   false,
	}
}

// SystemStats represents the complete system statistics
type SystemStats struct {
	TotalUsers      int       `json:"total_users"`
	TotalLists      int       `json:"total_lists"`
	TotalVocabWords int       `json:"total_vocab_words"`
	LastUpdated     time.Time `json:"last_updated"`
}

// GetSystemStats retrieves comprehensive system statistics with automatic initialization and caching
func (s *StatsService) GetAppStats(ctx context.Context) (*SystemStats, error) {
	// Check cache first (read lock)
	s.mutex.RLock()
	if s.cachedStats != nil && time.Now().Before(s.cacheExpiry) {
		cachedResult := *s.cachedStats // Copy to avoid race conditions
		s.mutex.RUnlock()
		return &cachedResult, nil
	}
	s.mutex.RUnlock()

	// Need to fetch fresh data (write lock)
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// Double-check cache after acquiring write lock
	if s.cachedStats != nil && time.Now().Before(s.cacheExpiry) {
		cachedResult := *s.cachedStats
		return &cachedResult, nil
	}

	// Initialize counts if not done yet
	if !s.initialized {
		if err := s.initializeAllCountsInternal(ctx); err != nil {
			return nil, err
		}
		s.initialized = true
	}

	// Get fresh statistics in parallel
	userChan := make(chan int, 1)
	listChan := make(chan int, 1)
	vocabChan := make(chan int, 1)

	g, gCtx := errgroup.WithContext(ctx)

	// Get user count in parallel
	g.Go(func() error {
		count, err := s.userRepo.GetTotalUserCount(gCtx)
		if err != nil {
			return fmt.Errorf("user count: %w", err)
		}
		userChan <- count
		return nil
	})

	// Get list count in parallel
	g.Go(func() error {
		count, err := s.vocabListRepo.GetTotalListCount(gCtx)
		if err != nil {
			return fmt.Errorf("list count: %w", err)
		}
		listChan <- count
		return nil
	})

	// Get vocab count in parallel
	g.Go(func() error {
		count, err := s.vocabRepo.GetTotalVocabCount(gCtx)
		if err != nil {
			return fmt.Errorf("vocab count: %w", err)
		}
		vocabChan <- count
		return nil
	})

	// Wait for all count operations to complete
	if err := g.Wait(); err != nil {
		return nil, err
	}

	// Collect results from channels
	userCount := <-userChan
	listCount := <-listChan
	vocabCount := <-vocabChan

	// Create new stats
	stats := &SystemStats{
		TotalUsers:      userCount,
		TotalLists:      listCount,
		TotalVocabWords: vocabCount,
		LastUpdated:     time.Now(),
	}

	// Cache the result for 1 minute
	s.cachedStats = stats
	s.cacheExpiry = time.Now().Add(1 * time.Minute)

	// Return a copy to avoid external modifications
	result := *stats
	return &result, nil
}

// initializeAllCountsInternal initializes count records internally in parallel (private method)
func (s *StatsService) initializeAllCountsInternal(ctx context.Context) error {
	// Use errgroup for cleaner parallel execution with context cancellation
	g, gCtx := errgroup.WithContext(ctx)

	// Initialize user count in parallel
	g.Go(func() error {
		return s.userRepo.InitializeUserCount(gCtx)
	})

	// Initialize vocab list count in parallel
	g.Go(func() error {
		return s.vocabListRepo.InitializeListCount(gCtx)
	})

	// Initialize vocab count in parallel
	g.Go(func() error {
		return s.vocabRepo.InitializeVocabCount(gCtx)
	})

	// Wait for all goroutines to complete and return the first error (if any)
	return g.Wait()
}

// ClearCache clears the cached statistics (useful for testing or admin operations)
func (s *StatsService) ClearCache() {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	s.cachedStats = nil
	s.cacheExpiry = time.Time{}
}
