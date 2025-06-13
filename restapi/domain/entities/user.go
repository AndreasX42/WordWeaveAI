package entities

import (
	"errors"
	"time"
)

type User struct {
	ID               string
	Username         string
	Email            string
	PasswordHash     string
	ConfirmationCode string
	ConfirmedEmail   bool
	IsActive         bool
	IsAdmin          bool
	CreatedAt        time.Time
}

// NewUser creates a new user with validation
func NewUser(id, username, email, passwordHash, confirmationCode string) (*User, error) {
	if id == "" {
		return nil, errors.New("user ID cannot be empty")
	}
	if username == "" {
		return nil, errors.New("username cannot be empty")
	}
	if email == "" {
		return nil, errors.New("email cannot be empty")
	}
	if passwordHash == "" {
		return nil, errors.New("password hash cannot be empty")
	}

	return &User{
		ID:               id,
		Username:         username,
		Email:            email,
		PasswordHash:     passwordHash,
		ConfirmationCode: confirmationCode,
		ConfirmedEmail:   false,
		IsActive:         false,
		IsAdmin:          false,
		CreatedAt:        time.Now().UTC(),
	}, nil
}

// ConfirmEmail confirms the user's email with the provided code
func (u *User) ConfirmEmail(code string) error {
	if u.ConfirmationCode != code {
		return errors.New("invalid confirmation code")
	}

	u.ConfirmedEmail = true
	u.IsActive = true
	u.ConfirmationCode = ""

	return nil
}

// IsEligibleForLogin checks if user can login
func (u *User) IsEligibleForLogin() error {
	if !u.ConfirmedEmail {
		return errors.New("email not confirmed")
	}
	if !u.IsActive {
		return errors.New("user not active")
	}
	return nil
}
