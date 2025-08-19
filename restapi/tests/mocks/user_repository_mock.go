package mocks

import (
	"context"
	"fmt"
	"sync"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
)

// MockUserRepository implements repositories.UserRepository for testing
type MockUserRepository struct {
	users         map[string]*entities.User
	usersByID     map[string]*entities.User
	emailIndex    map[string]string // email -> userID
	usernameIndex map[string]string // username -> userID
	googleIDIndex map[string]string // googleID -> userID
	mutex         sync.RWMutex

	// Count tracking
	userCount        int
	countInitialized bool

	// Test configuration
	shouldUpdateError bool
	updateErrorMsg    string
}

// NewMockUserRepository creates a new mock user repository
func NewMockUserRepository() repositories.UserRepository {
	return &MockUserRepository{
		users:         make(map[string]*entities.User),
		usersByID:     make(map[string]*entities.User),
		emailIndex:    make(map[string]string),
		usernameIndex: make(map[string]string),
		googleIDIndex: make(map[string]string),
	}
}

func (m *MockUserRepository) Create(ctx context.Context, user *entities.User) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Check if email already exists
	if _, exists := m.users[user.Email]; exists {
		return fmt.Errorf("email already exists")
	}

	// Check if username already exists
	for _, existingUser := range m.users {
		if existingUser.Username == user.Username {
			return fmt.Errorf("username already exists")
		}
	}

	// Store copies to avoid data races
	userCopy := *user
	m.users[user.Email] = &userCopy
	m.usersByID[user.ID] = &userCopy
	m.emailIndex[user.Email] = user.ID
	m.usernameIndex[user.Username] = user.ID
	if user.GoogleID != "" {
		m.googleIDIndex[user.GoogleID] = user.ID
	}

	// Increment user count
	m.userCount++

	return nil
}

func (m *MockUserRepository) GetByID(ctx context.Context, id string) (*entities.User, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	user, exists := m.usersByID[id]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}

	// Return a copy to avoid data races
	userCopy := *user
	return &userCopy, nil
}

func (m *MockUserRepository) GetByEmail(ctx context.Context, email string) (*entities.User, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	user, exists := m.users[email]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}

	// Return a copy to avoid data races
	userCopy := *user
	return &userCopy, nil
}

func (m *MockUserRepository) GetByUsername(ctx context.Context, username string) (*entities.User, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	for _, user := range m.users {
		if user.Username == username {
			// Return a copy to avoid data races
			userCopy := *user
			return &userCopy, nil
		}
	}

	return nil, fmt.Errorf("user not found")
}

func (m *MockUserRepository) GetByGoogleID(ctx context.Context, googleID string) (*entities.User, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	userID, exists := m.googleIDIndex[googleID]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}

	user, exists := m.usersByID[userID]
	if !exists {
		return nil, fmt.Errorf("user not found")
	}

	// Return a copy to avoid data races
	userCopy := *user
	return &userCopy, nil
}

func (m *MockUserRepository) Update(ctx context.Context, user *entities.User) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Check if we should return an error for testing
	if m.shouldUpdateError {
		return fmt.Errorf(m.updateErrorMsg)
	}

	existingUser, exists := m.usersByID[user.ID]
	if !exists {
		return fmt.Errorf("user not found")
	}

	// Remove old entries from indices
	delete(m.users, existingUser.Email)
	delete(m.emailIndex, existingUser.Email)
	delete(m.usernameIndex, existingUser.Username)
	if existingUser.GoogleID != "" {
		delete(m.googleIDIndex, existingUser.GoogleID)
	}

	// Store copies to avoid data races
	userCopy := *user

	// Add new entries to indices
	m.users[user.Email] = &userCopy
	m.usersByID[user.ID] = &userCopy
	m.emailIndex[user.Email] = user.ID
	m.usernameIndex[user.Username] = user.ID
	if user.GoogleID != "" {
		m.googleIDIndex[user.GoogleID] = user.ID
	}

	return nil
}

func (m *MockUserRepository) Delete(ctx context.Context, id string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	user, exists := m.usersByID[id]
	if !exists {
		return fmt.Errorf("user not found")
	}

	delete(m.users, user.Email)
	delete(m.usersByID, id)
	delete(m.emailIndex, user.Email)
	delete(m.usernameIndex, user.Username)
	if user.GoogleID != "" {
		delete(m.googleIDIndex, user.GoogleID)
	}

	// Decrement user count
	if m.userCount > 0 {
		m.userCount--
	}

	return nil
}

func (m *MockUserRepository) EmailExists(ctx context.Context, email string) (bool, error) {
	_, exists := m.emailIndex[email]
	return exists, nil
}

func (m *MockUserRepository) UsernameExists(ctx context.Context, username string) (bool, error) {
	_, exists := m.usernameIndex[username]
	return exists, nil
}

func (m *MockUserRepository) BatchValidateExistence(ctx context.Context, email, username string) (*repositories.ValidationResult, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	result := &repositories.ValidationResult{}

	if email != "" {
		_, exists := m.emailIndex[email]
		result.EmailExists = exists
	}

	if username != "" {
		_, exists := m.usernameIndex[username]
		result.UsernameExists = exists
	}

	return result, nil
}

// Count operations
func (m *MockUserRepository) GetTotalUserCount(ctx context.Context) (int, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return m.userCount, nil
}

func (m *MockUserRepository) InitializeUserCount(ctx context.Context) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if !m.countInitialized {
		// Don't reset the count if it already reflects real data
		// Only set to 0 if we haven't been tracking counts
		if m.userCount == 0 && len(m.users) > 0 {
			m.userCount = len(m.users)
		}
		m.countInitialized = true
	}
	return nil
}

// Test helper methods

// AddTestUser adds a user directly to the mock repository for testing
func (m *MockUserRepository) AddTestUser(user *entities.User) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	// Store copies to avoid data races
	userCopy := *user
	m.users[user.Email] = &userCopy
	m.usersByID[user.ID] = &userCopy
	m.emailIndex[user.Email] = user.ID
	m.usernameIndex[user.Username] = user.ID
	if user.GoogleID != "" {
		m.googleIDIndex[user.GoogleID] = user.ID
	}

	// Increment count for test user
	m.userCount++
}

// SetUpdateError configures the mock to return an error on Update calls
func (m *MockUserRepository) SetUpdateError(shouldError bool, errorMsg string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.shouldUpdateError = shouldError
	m.updateErrorMsg = errorMsg
}

// Reset clears all data and resets error states
func (m *MockUserRepository) Reset() {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	m.users = make(map[string]*entities.User)
	m.usersByID = make(map[string]*entities.User)
	m.emailIndex = make(map[string]string)
	m.usernameIndex = make(map[string]string)
	m.googleIDIndex = make(map[string]string)
	m.userCount = 0
	m.countInitialized = false
	m.shouldUpdateError = false
	m.updateErrorMsg = ""
}

// GetUserCount returns the number of users in the repository
func (m *MockUserRepository) GetUserCount() int {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return len(m.users)
}
