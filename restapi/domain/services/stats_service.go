package services

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/utils"
	"golang.org/x/sync/errgroup"
)

// statsCacheTTL is overridable via STATS_CACHE_TTL_SECONDS (default 300 = 5 minutes).
var statsCacheTTL = 5 * time.Minute

func init() {
	secs := utils.EnvPositiveInt("STATS_CACHE_TTL_SECONDS", 300)
	statsCacheTTL = time.Duration(secs) * time.Second
}

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
		cachedResult := copySystemStats(s.cachedStats)
		s.mutex.RUnlock()
		return cachedResult, nil
	}
	s.mutex.RUnlock()

	// Need to fetch fresh data (write lock)
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// Double-check cache after acquiring write lock
	if s.cachedStats != nil && time.Now().Before(s.cacheExpiry) {
		return copySystemStats(s.cachedStats), nil
	}

	// Initialize counts if not done yet
	if !s.initialized {
		if err := s.initializeAllCountsInternal(ctx); err != nil {
			return nil, err
		}
		s.initialized = true
	}

	// Get fresh statistics in parallel
	var userCount, listCount, vocabCount int

	g, gCtx := errgroup.WithContext(ctx)

	// Get user count in parallel
	g.Go(func() error {
		count, err := s.userRepo.GetTotalUserCount(gCtx)
		if err != nil {
			return fmt.Errorf("user count: %w", err)
		}
		userCount = count
		return nil
	})

	// Get list count in parallel
	g.Go(func() error {
		count, err := s.vocabListRepo.GetTotalListCount(gCtx)
		if err != nil {
			return fmt.Errorf("list count: %w", err)
		}
		listCount = count
		return nil
	})

	// Get vocab count in parallel
	g.Go(func() error {
		count, err := s.vocabRepo.GetTotalVocabCount(gCtx)
		if err != nil {
			return fmt.Errorf("vocab count: %w", err)
		}
		vocabCount = count
		return nil
	})

	// Wait for all count operations to complete
	if err := g.Wait(); err != nil {
		return nil, err
	}

	// Create new stats
	stats := &SystemStats{
		TotalUsers:      userCount,
		TotalLists:      listCount,
		TotalVocabWords: vocabCount,
		LastUpdated:     time.Now(),
	}

	// Cache the result for a short period to avoid repeated aggregate reads.
	s.cachedStats = stats
	s.cacheExpiry = time.Now().Add(statsCacheTTL)

	// Return a copy to avoid external modifications
	return copySystemStats(stats), nil
}

func copySystemStats(stats *SystemStats) *SystemStats {
	result := *stats
	return &result
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
