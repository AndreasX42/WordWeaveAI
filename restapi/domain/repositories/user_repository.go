package repositories

import (
	"context"

	"github.com/AndreasX42/restapi/domain/entities"
)

// UserRepository defines the contract for user data operations
type UserRepository interface {
	Create(ctx context.Context, user *entities.User) error
	GetByID(ctx context.Context, id string) (*entities.User, error)
	GetByEmail(ctx context.Context, email string) (*entities.User, error)
	GetByUsername(ctx context.Context, username string) (*entities.User, error)
	Update(ctx context.Context, user *entities.User) error
	Delete(ctx context.Context, id string) error
	EmailExists(ctx context.Context, email string) (bool, error)
	UsernameExists(ctx context.Context, username string) (bool, error)
}

// EmailService defines the contract for email operations
type EmailService interface {
	SendConfirmationEmail(email, code string) error
	SendResetPasswordEmail(email, password string) error
}
