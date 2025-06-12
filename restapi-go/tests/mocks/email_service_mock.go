package mocks

import (
	"fmt"
	"sync"

	"github.com/AndreasX42/wordweave-go/domain/repositories"
)

// MockEmailService implements repositories.EmailService for testing
type MockEmailService struct {
	sentEmails []SentEmail
	mutex      sync.RWMutex
}

type SentEmail struct {
	Email   string // For unit test compatibility
	Code    string // For unit test compatibility
	To      string // For integration test compatibility
	Subject string // For integration test compatibility
	Body    string // For integration test compatibility
}

// NewMockEmailService creates a new mock email service
func NewMockEmailService() repositories.EmailService {
	return &MockEmailService{
		sentEmails: make([]SentEmail, 0),
	}
}

func (m *MockEmailService) SendConfirmationEmail(email, code string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	sentEmail := SentEmail{
		Email:   email,                                              // For unit test compatibility
		Code:    code,                                               // For unit test compatibility
		To:      email,                                              // For integration test compatibility
		Subject: "Confirm Your Email Address",                       // For integration test compatibility
		Body:    fmt.Sprintf("Your confirmation code is: %s", code), // For integration test compatibility
	}

	m.sentEmails = append(m.sentEmails, sentEmail)
	return nil
}

func (m *MockEmailService) SendResetPasswordEmail(email, password string) error {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	sentEmail := SentEmail{
		Email:   email,                                                       // For unit test compatibility
		Code:    password,                                                    // For unit test compatibility (reusing Code field for password)
		To:      email,                                                       // For integration test compatibility
		Subject: "Password Reset",                                            // For integration test compatibility
		Body:    fmt.Sprintf("Your new temporary password is: %s", password), // For integration test compatibility
	}

	m.sentEmails = append(m.sentEmails, sentEmail)
	return nil
}

// Helper methods for testing
func (m *MockEmailService) GetSentEmails() []SentEmail {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	// Return a copy to avoid data races
	emails := make([]SentEmail, len(m.sentEmails))
	copy(emails, m.sentEmails)
	return emails
}

func (m *MockEmailService) Reset() {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	m.sentEmails = make([]SentEmail, 0)
}

func (m *MockEmailService) GetLastSentEmail() *SentEmail {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	if len(m.sentEmails) == 0 {
		return nil
	}

	// Return a copy of the last sent email
	lastEmail := m.sentEmails[len(m.sentEmails)-1]
	return &lastEmail
}
