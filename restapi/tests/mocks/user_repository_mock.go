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
