package mocks

import (
	"context"
	"fmt"
	"sync"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
)

// MockVocabListRepository implements repositories.VocabListRepository for testing
type MockVocabListRepository struct {
	lists       map[string]*entities.VocabList     // key: userID:listID
	words       map[string]*entities.VocabListWord // key: userID:listID:vocabPK:vocabSK
	listsByUser map[string][]*entities.VocabList   // key: userID
	mutex       sync.RWMutex

	// Count tracking
	listCount        int
	countInitialized bool
}

// NewMockVocabListRepository creates a new mock vocab list repository
func NewMockVocabListRepository() repositories.VocabListRepository {
	return &MockVocabListRepository{
		lists:       make(map[string]*entities.VocabList),
		words:       make(map[string]*entities.VocabListWord),
		listsByUser: make(map[string][]*entities.VocabList),
	}
}

func (m *MockVocabListRepository) getListKey(userID, listID string) string {
	return fmt.Sprintf("%s:%s", userID, listID)
}

func (m *MockVocabListRepository) getWordKey(userID, listID, vocabPK, vocabSK string) string {
	return fmt.Sprintf("%s:%s:%s:%s", userID, listID, vocabPK, vocabSK)
}

// List operations
func (m *MockVocabListRepository) CreateList(ctx context.Context, list *entities.VocabList) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	key := m.getListKey(list.UserID, list.ID)

	// Check if list already exists
	if _, exists := m.lists[key]; exists {
		return fmt.Errorf("list already exists")
	}

	// Store copy to avoid data races
	listCopy := *list
	m.lists[key] = &listCopy

	// Update user's lists
	m.listsByUser[list.UserID] = append(m.listsByUser[list.UserID], &listCopy)

	// Increment list count
	m.listCount++

	return nil
}

func (m *MockVocabListRepository) GetListByID(ctx context.Context, userID, listID string) (*entities.VocabList, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	key := m.getListKey(userID, listID)
	list, exists := m.lists[key]
	if !exists {
		return nil, fmt.Errorf("list not found")
	}

	// Return a copy to avoid data races
	listCopy := *list
	return &listCopy, nil
}

func (m *MockVocabListRepository) GetListsByUserID(ctx context.Context, userID string) ([]*entities.VocabList, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	lists, exists := m.listsByUser[userID]
	if !exists {
		return []*entities.VocabList{}, nil
	}

	// Return copies to avoid data races
	result := make([]*entities.VocabList, len(lists))
	for i, list := range lists {
		listCopy := *list
		result[i] = &listCopy
	}

	return result, nil
}

func (m *MockVocabListRepository) UpdateList(ctx context.Context, list *entities.VocabList) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	key := m.getListKey(list.UserID, list.ID)
	if _, exists := m.lists[key]; !exists {
		return fmt.Errorf("list not found")
	}

	// Store copy to avoid data races
	listCopy := *list
	m.lists[key] = &listCopy

	// Update in user's lists
	userLists := m.listsByUser[list.UserID]
	for i, userList := range userLists {
		if userList.ID == list.ID {
			m.listsByUser[list.UserID][i] = &listCopy
			break
		}
	}

	return nil
}

func (m *MockVocabListRepository) DeleteList(ctx context.Context, userID, listID string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	key := m.getListKey(userID, listID)
	if _, exists := m.lists[key]; !exists {
		return fmt.Errorf("list not found")
	}

	// Delete the list
	delete(m.lists, key)

	// Remove from user's lists
	userLists := m.listsByUser[userID]
	for i, list := range userLists {
		if list.ID == listID {
			m.listsByUser[userID] = append(userLists[:i], userLists[i+1:]...)
			break
		}
	}

	// Delete all words in the list
	keysToDelete := []string{}
	for wordKey, word := range m.words {
		if word.UserID == userID && word.ListID == listID {
			keysToDelete = append(keysToDelete, wordKey)
		}
	}
	for _, wordKey := range keysToDelete {
		delete(m.words, wordKey)
	}

	// Decrement list count
	if m.listCount > 0 {
		m.listCount--
	}

	return nil
}

// Word operations
func (m *MockVocabListRepository) AddWordToList(ctx context.Context, word *entities.VocabListWord) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Check if list exists
	listKey := m.getListKey(word.UserID, word.ListID)
	list, exists := m.lists[listKey]
	if !exists {
		return fmt.Errorf("list not found")
	}

	wordKey := m.getWordKey(word.UserID, word.ListID, word.VocabPK, word.VocabSK)

	// Check if word already exists
	if _, exists := m.words[wordKey]; exists {
		return fmt.Errorf("word already exists in list")
	}

	// Store copy to avoid data races
	wordCopy := *word
	m.words[wordKey] = &wordCopy

	// Update word count in list
	list.WordCount++
	m.lists[listKey] = list

	// Update in user's lists
	userLists := m.listsByUser[word.UserID]
	for i, userList := range userLists {
		if userList.ID == word.ListID {
			m.listsByUser[word.UserID][i].WordCount++
			break
		}
	}

	return nil
}

func (m *MockVocabListRepository) RemoveWordFromList(ctx context.Context, userID, listID, vocabPK, vocabSK string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Check if list exists
	listKey := m.getListKey(userID, listID)
	list, exists := m.lists[listKey]
	if !exists {
		return fmt.Errorf("list not found")
	}

	wordKey := m.getWordKey(userID, listID, vocabPK, vocabSK)
	if _, exists := m.words[wordKey]; !exists {
		return fmt.Errorf("word not found in list")
	}

	// Delete the word
	delete(m.words, wordKey)

	// Update word count in list
	list.WordCount--
	m.lists[listKey] = list

	// Update in user's lists
	userLists := m.listsByUser[userID]
	for i, userList := range userLists {
		if userList.ID == listID {
			m.listsByUser[userID][i].WordCount--
			break
		}
	}

	return nil
}

func (m *MockVocabListRepository) GetWordsInList(ctx context.Context, userID, listID string) ([]*entities.VocabListWord, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	// Check if list exists
	listKey := m.getListKey(userID, listID)
	if _, exists := m.lists[listKey]; !exists {
		return nil, fmt.Errorf("list not found")
	}

	// Find all words for this list
	var words []*entities.VocabListWord
	for _, word := range m.words {
		if word.UserID == userID && word.ListID == listID {
			// Return copy to avoid data races
			wordCopy := *word
			words = append(words, &wordCopy)
		}
	}

	return words, nil
}

func (m *MockVocabListRepository) UpdateWordInList(ctx context.Context, word *entities.VocabListWord) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	wordKey := m.getWordKey(word.UserID, word.ListID, word.VocabPK, word.VocabSK)
	if _, exists := m.words[wordKey]; !exists {
		return fmt.Errorf("word not found in list")
	}

	// Store copy to avoid data races
	wordCopy := *word
	m.words[wordKey] = &wordCopy

	return nil
}

func (m *MockVocabListRepository) WordExistsInList(ctx context.Context, userID, listID, vocabPK, vocabSK string) (bool, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	wordKey := m.getWordKey(userID, listID, vocabPK, vocabSK)
	_, exists := m.words[wordKey]
	return exists, nil
}

// Count operations
func (m *MockVocabListRepository) GetTotalListCount(ctx context.Context) (int, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return m.listCount, nil
}

func (m *MockVocabListRepository) InitializeListCount(ctx context.Context) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if !m.countInitialized {
		// Don't reset the count if it already reflects real data
		// Only set to 0 if we haven't been tracking counts
		if m.listCount == 0 && len(m.lists) > 0 {
			m.listCount = len(m.lists)
		}
		m.countInitialized = true
	}
	return nil
}

// Test helper methods
func (m *MockVocabListRepository) Reset() {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	m.lists = make(map[string]*entities.VocabList)
	m.words = make(map[string]*entities.VocabListWord)
	m.listsByUser = make(map[string][]*entities.VocabList)
	m.listCount = 0
	m.countInitialized = false
}

func (m *MockVocabListRepository) GetListCount() int {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return m.listCount
}
