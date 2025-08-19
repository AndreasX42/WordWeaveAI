package repositories

import (
	"context"

	"github.com/AndreasX42/restapi/domain/entities"
)

// ValidationResult holds the result of existence checks
type ValidationResult struct {
	EmailExists    bool
	UsernameExists bool
}

// UserRepository defines the contract for user data operations
type UserRepository interface {
	Create(ctx context.Context, user *entities.User) error
	GetByID(ctx context.Context, id string) (*entities.User, error)
	GetByEmail(ctx context.Context, email string) (*entities.User, error)
	GetByUsername(ctx context.Context, username string) (*entities.User, error)
	GetByGoogleID(ctx context.Context, googleID string) (*entities.User, error)
	Update(ctx context.Context, user *entities.User) error
	Delete(ctx context.Context, id string) error
	EmailExists(ctx context.Context, email string) (bool, error)
	UsernameExists(ctx context.Context, username string) (bool, error)
	BatchValidateExistence(ctx context.Context, email, username string) (*ValidationResult, error)

	// Count operations
	GetTotalUserCount(ctx context.Context) (int, error)
	InitializeUserCount(ctx context.Context) error
}

// EmailService defines the contract for email operations
type EmailService interface {
	SendConfirmationEmail(email, code string) error
	SendResetPasswordEmail(email, password string) error
}
