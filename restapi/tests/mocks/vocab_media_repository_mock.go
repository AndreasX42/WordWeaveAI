package mocks

import (
	"context"
	"fmt"
	"sync"
)

// MockVocabMediaRepository implements repositories.VocabMediaRepository for testing
type MockVocabMediaRepository struct {
	mediaData   map[string]map[string]any // key: mediaRef, value: media data
	mutex       sync.RWMutex
	shouldError bool
	errorMsg    string
}

// NewMockVocabMediaRepository creates a new mock media repository
func NewMockVocabMediaRepository() *MockVocabMediaRepository {
	return &MockVocabMediaRepository{
		mediaData: make(map[string]map[string]any),
	}
}

// GetMediaByRef implements the media repository interface
func (m *MockVocabMediaRepository) GetMediaByRef(ctx context.Context, mediaRef string) (map[string]any, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	if m.shouldError {
		return nil, fmt.Errorf(m.errorMsg)
	}

	media, exists := m.mediaData[mediaRef]
	if !exists {
		return nil, fmt.Errorf("media not found for ref: %s", mediaRef)
	}

	// Return a copy to avoid data races
	result := make(map[string]any)
	for k, v := range media {
		result[k] = v
	}

	return result, nil
}

// GetMediaBySearchTerms implements the media repository interface
func (m *MockVocabMediaRepository) GetMediaBySearchTerms(ctx context.Context, searchTerms []string) (map[string]any, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	if m.shouldError {
		return nil, fmt.Errorf(m.errorMsg)
	}

	// Simple implementation for testing - just return empty result
	return make(map[string]any), nil
}

// AddTestMedia adds media data for testing
func (m *MockVocabMediaRepository) AddTestMedia(mediaRef string, mediaData map[string]any) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Store a copy to avoid data races
	dataCopy := make(map[string]any)
	for k, v := range mediaData {
		dataCopy[k] = v
	}
	m.mediaData[mediaRef] = dataCopy
}

// SetError configures the mock to return an error
func (m *MockVocabMediaRepository) SetError(shouldError bool, errorMsg string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.shouldError = shouldError
	m.errorMsg = errorMsg
}

// Reset clears all media data
func (m *MockVocabMediaRepository) Reset() {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.mediaData = make(map[string]map[string]any)
	m.shouldError = false
	m.errorMsg = ""
}

// GetMediaCount returns the number of media entries
func (m *MockVocabMediaRepository) GetMediaCount() int {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return len(m.mediaData)
}
