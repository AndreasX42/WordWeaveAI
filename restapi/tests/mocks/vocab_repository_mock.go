package mocks

import (
	"context"
	"fmt"
	"sync"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
)

// MockVocabRepository implements repositories.VocabRepository for testing
type MockVocabRepository struct {
	words map[string]*entities.VocabWord // key: PK|SK
	mutex sync.RWMutex

	// Count tracking (managed externally, but we track for testing)
	vocabCount int
}

// NewMockVocabRepository creates a new mock vocabulary repository
func NewMockVocabRepository() repositories.VocabRepository {
	return &MockVocabRepository{
		words: make(map[string]*entities.VocabWord),
	}
}

func (m *MockVocabRepository) getKey(pk, sk string) string {
	return pk + "|" + sk
}

// AddTestWord adds a word to the mock repository for testing
func (m *MockVocabRepository) AddTestWord(pk, sk string, word *entities.VocabWord) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	key := m.getKey(pk, sk)
	wordCopy := *word
	m.words[key] = &wordCopy
}

// SearchByNormalizedWord performs vocabulary search by normalized word
func (m *MockVocabRepository) SearchByNormalizedWord(ctx context.Context, normalizedQuery string, supportedLanguages []string, limit int) ([]entities.VocabWord, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	var results []entities.VocabWord

	for _, word := range m.words {
		if len(results) >= limit {
			break
		}

		// Simple matching logic for testing
		if word.SourceWord == normalizedQuery || word.TargetWord == normalizedQuery {
			wordCopy := *word
			results = append(results, wordCopy)
		}
	}

	return results, nil
}

// GetByKeys gets a single vocabulary entry by PK and SK
func (m *MockVocabRepository) GetByKeys(ctx context.Context, vocabPK, vocabSK string) (*entities.VocabWord, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	key := m.getKey(vocabPK, vocabSK)
	word, exists := m.words[key]
	if !exists {
		return nil, fmt.Errorf("vocabulary entry not found")
	}

	// Return copy to avoid data races
	wordCopy := *word
	return &wordCopy, nil
}

// GetByKeysBatch gets multiple vocabulary entries by their PK/SK pairs
func (m *MockVocabRepository) GetByKeysBatch(ctx context.Context, keys []entities.VocabKey) (map[string]*entities.VocabWord, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	result := make(map[string]*entities.VocabWord)

	for _, key := range keys {
		keyStr := m.getKey(key.PK, key.SK)
		if word, exists := m.words[keyStr]; exists {
			// Return copy to avoid data races
			wordCopy := *word
			result[keyStr] = &wordCopy
		}
	}

	return result, nil
}

// SearchByWordWithLanguages performs targeted vocabulary search when languages are specified
func (m *MockVocabRepository) SearchByWordWithLanguages(ctx context.Context, normalizedQuery, sourceLang, targetLang string, limit int) ([]entities.VocabWord, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	var results []entities.VocabWord

	for _, word := range m.words {
		if len(results) >= limit {
			break
		}

		// Check if word matches the search criteria
		sourceMatch := sourceLang == "" || word.SourceLanguage == sourceLang
		targetMatch := targetLang == "" || word.TargetLanguage == targetLang
		wordMatch := word.SourceWord == normalizedQuery || word.TargetWord == normalizedQuery

		if sourceMatch && targetMatch && wordMatch {
			wordCopy := *word
			results = append(results, wordCopy)
		}
	}

	return results, nil
}

// Count operations
func (m *MockVocabRepository) GetTotalVocabCount(ctx context.Context) (int, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return m.vocabCount, nil
}

func (m *MockVocabRepository) InitializeVocabCount(ctx context.Context) error {
	// For testing, we don't need to do anything special here
	// The count is already initialized to 0 when the mock is created
	return nil
}

// Test helper methods
func (m *MockVocabRepository) SetVocabCount(count int) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.vocabCount = count
}

func (m *MockVocabRepository) Reset() {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.words = make(map[string]*entities.VocabWord)
	m.vocabCount = 0
}

func (m *MockVocabRepository) GetWordCount() int {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return len(m.words)
}
