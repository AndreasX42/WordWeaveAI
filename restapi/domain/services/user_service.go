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
	Email    string
	Password string
}

type OAuthUserRequest struct {
	GoogleID     string
	Email        string
	Name         string
	Username     string
	ProfileImage string
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

func (s *UserService) ResendConfirmationCode(ctx context.Context, email string) error {
	user, err := s.userRepo.GetByEmail(ctx, email)
	if err != nil {
		return errors.New("user not found")
	}

	if user.ConfirmedEmail {
		return errors.New("email already confirmed")
	}

	// Generate new confirmation code
	newConfirmationCode := utils.GenerateConfirmationCode()
	user.ConfirmationCode = newConfirmationCode

	// Update user with new code
	if err := s.userRepo.Update(ctx, user); err != nil {
		return err
	}

	// Send confirmation email asynchronously
	go func() {
		if err := s.emailService.SendConfirmationEmail(email, newConfirmationCode); err != nil {
			log.Println("Error sending confirmation email:", err)
		}
	}()

	return nil
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

	// Validate username uniqueness if it's being changed
	if req.Username != "" && req.Username != user.Username {
		usernameExists, err := s.userRepo.UsernameExists(ctx, req.Username)
		if err != nil {
			return err
		}
		if usernameExists {
			return errors.New("username already exists")
		}
		user.Username = req.Username
	}

	// Validate email uniqueness if it's being changed
	if req.Email != "" && req.Email != user.Email {
		emailExists, err := s.userRepo.EmailExists(ctx, req.Email)
		if err != nil {
			return err
		}
		if emailExists {
			return errors.New("email already exists")
		}
		user.Email = req.Email
	}

	// Update password if provided
	if req.Password != "" {
		hashedPassword, err := utils.HashPassword(req.Password)
		if err != nil {
			return err
		}
		user.PasswordHash = hashedPassword
	}

	return s.userRepo.Update(ctx, user)
}

// CreateOrLoginOAuthUser handles OAuth user creation or login
func (s *UserService) CreateOrLoginOAuthUser(ctx context.Context, req OAuthUserRequest) (*entities.User, error) {
	// 1. Check if user exists by Google ID
	user, err := s.userRepo.GetByGoogleID(ctx, req.GoogleID)
	if err == nil {
		// User exists, return existing user
		return user, nil
	}

	// 2. Check if user exists by email (might be regular user converting to OAuth)
	existingUser, err := s.userRepo.GetByEmail(ctx, req.Email)
	if err == nil {
		// User exists with same email but no Google ID
		// Link the Google account to existing user
		existingUser.GoogleID = req.GoogleID
		existingUser.IsOAuthUser = true
		existingUser.ProfileImage = req.ProfileImage
		existingUser.ConfirmedEmail = true
		existingUser.IsActive = true

		if err := s.userRepo.Update(ctx, existingUser); err != nil {
			return nil, err
		}
		return existingUser, nil
	}

	// 3. Create new OAuth user
	userID := uuid.New().String()
	username := req.Username

	// TODO: Check if username is set
	// Ensure username is unique
	if username == "" {
		username = strings.Split(req.Email, "@")[0]
	}

	// Check if username exists and make it unique if needed
	usernameExists, err := s.userRepo.UsernameExists(ctx, username)
	if err != nil {
		return nil, err
	}
	if usernameExists {
		username = username + "_" + utils.GenerateRandomString(6)
	}

	user, err = entities.NewOAuthUser(userID, username, req.Email, req.GoogleID, req.ProfileImage)
	if err != nil {
		return nil, err
	}

	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, err
	}

	return user, nil
}
