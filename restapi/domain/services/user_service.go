package services

import (
	"context"
	"errors"
	"log"
	"strings"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/utils"
	"github.com/google/uuid"
)

type UserService struct {
	userRepo     repositories.UserRepository
	emailService repositories.EmailService
}

func NewUserService(userRepo repositories.UserRepository, emailService repositories.EmailService) *UserService {
	return &UserService{
		userRepo:     userRepo,
		emailService: emailService,
	}
}

type RegisterUserRequest struct {
	Email    string
	Username string
	Password string
}

type LoginUserRequest struct {
	Email    string
	Password string
}

type ConfirmEmailRequest struct {
	Email string
	Code  string
}

type ResetPasswordRequest struct {
	Email string
}

type UpdateUserRequest struct {
	User     *entities.User
	Username string
	Password string
}

func (s *UserService) RegisterUser(ctx context.Context, req RegisterUserRequest) (*entities.User, error) {
	// Check if user already exists
	emailExists, err := s.userRepo.EmailExists(ctx, req.Email)
	if err != nil {
		return nil, err
	}
	if emailExists {
		return nil, errors.New("email already exists")
	}

	usernameExists, err := s.userRepo.UsernameExists(ctx, req.Username)
	if err != nil {
		return nil, err
	}
	if usernameExists {
		return nil, errors.New("username already exists")
	}

	// Generate user data
	userID := uuid.New().String()
	confirmationCode := utils.GenerateConfirmationCode()

	hashedPassword, err := utils.HashPassword(req.Password)
	if err != nil {
		return nil, errors.New("failed to hash password")
	}

	// Create user entity
	user, err := entities.NewUser(userID, req.Username, req.Email, hashedPassword, confirmationCode)
	if err != nil {
		return nil, err
	}

	// Save user
	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, err
	}

	// Send confirmation email asynchronously
	go func() {
		if err := s.emailService.SendConfirmationEmail(req.Email, confirmationCode); err != nil {
			log.Println("Error sending confirmation email:", err)
		}
	}()

	return user, nil
}

func (s *UserService) LoginUser(ctx context.Context, req LoginUserRequest) (*entities.User, error) {
	user, err := s.userRepo.GetByEmail(ctx, req.Email)
	if err != nil {
		return nil, errors.New("invalid credentials")
	}

	if !utils.ComparePasswords(user.PasswordHash, req.Password) {
		return nil, errors.New("invalid credentials")
	}

	if err := user.IsEligibleForLogin(); err != nil {
		return nil, err
	}

	return user, nil
}

func (s *UserService) ConfirmEmail(ctx context.Context, req ConfirmEmailRequest) error {
	user, err := s.userRepo.GetByEmail(ctx, req.Email)
	if err != nil {
		return err
	}

	if user.ConfirmedEmail {
		return errors.New("email already confirmed")
	}

	if err := user.ConfirmEmail(req.Code); err != nil {
		return err
	}

	return s.userRepo.Update(ctx, user)
}

func (s *UserService) ResetPassword(ctx context.Context, req ResetPasswordRequest) error {
	user, err := s.userRepo.GetByEmail(ctx, req.Email)
	if err != nil {
		log.Printf("Password reset attempted for non-existent email: %s", req.Email)
		return nil
	}

	newPassword := utils.GenerateRandomString(16)
	hashedPassword, err := utils.HashPassword(newPassword)
	if err != nil {
		return err
	}

	user.PasswordHash = hashedPassword
	if err := s.userRepo.Update(ctx, user); err != nil {
		return err
	}

	go func() {
		if err := s.emailService.SendResetPasswordEmail(req.Email, newPassword); err != nil {
			log.Println("Error sending reset password email:", err)
		}
	}()

	return nil
}

func (s *UserService) DeleteUser(ctx context.Context, userID string) error {
	err := s.userRepo.Delete(ctx, userID)
	if err != nil && strings.Contains(err.Error(), "user not found") {
		return nil
	}
	return err
}

func (s *UserService) GetUserByID(ctx context.Context, userID string) (*entities.User, error) {
	return s.userRepo.GetByID(ctx, userID)
}

func (s *UserService) UpdateUser(ctx context.Context, req UpdateUserRequest) error {
	user := req.User

	if req.Username != "" {
		user.Username = req.Username
	}

	if req.Password != "" {
		hashedPassword, err := utils.HashPassword(req.Password)
		if err != nil {
			return err
		}
		user.PasswordHash = hashedPassword
	}

	return s.userRepo.Update(ctx, user)
}
