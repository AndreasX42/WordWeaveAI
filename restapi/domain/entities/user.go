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
	// OAuth fields
	GoogleID     string // Google OAuth ID
	IsOAuthUser  bool   // Whether user registered via OAuth
	ProfileImage string // Profile image URL from OAuth provider
	// Vocab stats
	RequestCount int
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
		IsOAuthUser:      false,
		RequestCount:     0,
	}, nil
}

// NewOAuthUser creates a new user via OAuth (Google)
func NewOAuthUser(id, username, email, googleID, profileImage string) (*User, error) {
	if id == "" {
		return nil, errors.New("user ID cannot be empty")
	}
	if username == "" {
		return nil, errors.New("username cannot be empty")
	}
	if email == "" {
		return nil, errors.New("email cannot be empty")
	}
	if googleID == "" {
		return nil, errors.New("google ID cannot be empty")
	}

	return &User{
		ID:               id,
		Username:         username,
		Email:            email,
		PasswordHash:     "", // OAuth users don't have passwords
		ConfirmationCode: "",
		ConfirmedEmail:   true, // OAuth emails are pre-verified
		IsActive:         true, // OAuth users are immediately active
		IsAdmin:          false,
		CreatedAt:        time.Now().UTC(),
		GoogleID:         googleID,
		IsOAuthUser:      true,
		ProfileImage:     profileImage,
		RequestCount:     0,
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
