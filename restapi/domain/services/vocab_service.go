package services

import (
	"context"
	"regexp"
	"strings"
	"sync"
	"time"
	"unicode"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"golang.org/x/text/unicode/norm"
)

// CacheEntry represents a cached search result
type CacheEntry struct {
	Results   []entities.VocabWord
	Timestamp time.Time
}

type VocabService struct {
	vocabRepo repositories.VocabRepository
	cache     map[string]CacheEntry
	cacheMu   sync.RWMutex
	cacheTTL  time.Duration
}

type SearchVocabularyRequest struct {
	Query      string
	Limit      int
	SourceLang string // optional
	TargetLang string // optional
}

var normalizeRgx = regexp.MustCompile(`[^a-z0-9]`)

func NewVocabService(vocabRepo repositories.VocabRepository) *VocabService {
	return &VocabService{
		vocabRepo: vocabRepo,
		cache:     make(map[string]CacheEntry),
		cacheTTL:  time.Minute * 10,
	}
}

func (s *VocabService) SearchVocabulary(ctx context.Context, req SearchVocabularyRequest) ([]entities.VocabWord, error) {
	// Set defaults
	if req.Limit == 0 || req.Limit > 10 {
		req.Limit = 5
	}

	// Normalize the query
	normalizedQuery := normalizeWord(req.Query)

	// Check cache
	s.cacheMu.RLock()
	cacheEntry, exists := s.cache[normalizedQuery]
	s.cacheMu.RUnlock()

	if exists && time.Since(cacheEntry.Timestamp) < s.cacheTTL {
		return cacheEntry.Results, nil
	}

	// Choose search strategy based on language specification
	if req.SourceLang != "" || req.TargetLang != "" {
		// Targeted search when languages are specified
		results, err := s.vocabRepo.SearchByWordWithLanguages(ctx, normalizedQuery, req.SourceLang, req.TargetLang, req.Limit)
		if err != nil {
			return nil, err
		}
		s.cacheMu.Lock()
		s.cache[normalizedQuery] = CacheEntry{Results: results, Timestamp: time.Now()}
		s.cacheMu.Unlock()
		return results, nil
	} else {
		// Comprehensive search across all supported languages
		supportedLanguages := []string{"en", "es", "de"}
		results, err := s.vocabRepo.SearchByNormalizedWord(ctx, normalizedQuery, supportedLanguages, req.Limit)
		if err != nil {
			return nil, err
		}
		s.cacheMu.Lock()
		s.cache[normalizedQuery] = CacheEntry{Results: results, Timestamp: time.Now()}
		s.cacheMu.Unlock()
		return results, nil
	}
}

// normalizeWord matches the Python normalize_word function exactly
func normalizeWord(word string) string {
	// Step 1: NFKC normalization and lowercase
	word = strings.ToLower(word)
	word = norm.NFKC.String(word)

	// Step 2: NFD normalization and remove combining marks
	word = norm.NFD.String(word)
	result := make([]rune, 0, len(word))
	for _, r := range word {
		if unicode.In(r, unicode.Mn) {
			continue // Skip combining marks (category Mn)
		}
		result = append(result, r)
	}
	word = string(result)

	// Step 3: Remove non-alphanumeric characters
	return normalizeRgx.ReplaceAllString(word, "")
}
