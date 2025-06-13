package unit

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/tests/mocks"
)

func TestUserService_RegisterUser(t *testing.T) {
	ctx := context.Background()

	t.Run("successful registration", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		req := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}

		// Execute
		user, err := userService.RegisterUser(ctx, req)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error, got %v", err)
		}

		if user == nil {
			t.Fatal("Expected user to be created")
		}

		if user.Email != req.Email {
			t.Errorf("Expected email %s, got %s", req.Email, user.Email)
		}

		if user.Username != req.Username {
			t.Errorf("Expected username %s, got %s", req.Username, user.Username)
		}

		if user.ConfirmedEmail {
			t.Error("Expected user email to not be confirmed initially")
		}

		if user.IsActive {
			t.Error("Expected user to not be active initially")
		}

		// Wait for async email sending to complete
		time.Sleep(100 * time.Millisecond)

		// Check if email was sent
		mockEmailService := emailService.(*mocks.MockEmailService)
		sentEmails := mockEmailService.GetSentEmails()
		if len(sentEmails) != 1 {
			t.Errorf("Expected 1 email to be sent, got %d", len(sentEmails))
		}

		if sentEmails[0].Email != req.Email {
			t.Errorf("Expected email to be sent to %s, got %s", req.Email, sentEmails[0].Email)
		}
	})

	t.Run("email already exists", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Pre-register a user
		firstReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser1",
			Password: "password123",
		}
		_, _ = userService.RegisterUser(ctx, firstReq)

		// Try to register another user with same email
		secondReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser2",
			Password: "password123",
		}

		// Execute
		user, err := userService.RegisterUser(ctx, secondReq)

		// Assert
		if err == nil {
			t.Fatal("Expected error for duplicate email")
		}

		if !strings.Contains(err.Error(), "email already exists") {
			t.Errorf("Expected 'email already exists' error, got %v", err)
		}

		if user != nil {
			t.Error("Expected user to be nil on error")
		}
	})

	t.Run("username already exists", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Pre-register a user
		firstReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		_, _ = userService.RegisterUser(ctx, firstReq)

		// Try to register another user with same username
		secondReq := services.RegisterUserRequest{
			Email:    "newtest@example.com",
			Username: "testuser",
			Password: "password123",
		}

		// Execute
		user, err := userService.RegisterUser(ctx, secondReq)

		// Assert
		if err == nil {
			t.Fatal("Expected error for duplicate username")
		}

		if !strings.Contains(err.Error(), "username already exists") {
			t.Errorf("Expected 'username already exists' error, got %v", err)
		}

		if user != nil {
			t.Error("Expected user to be nil on error")
		}
	})
}

func TestUserService_LoginUser(t *testing.T) {
	ctx := context.Background()

	t.Run("successful login", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register and confirm a user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		_, _ = userService.RegisterUser(ctx, registerReq)

		// Wait for async email
		time.Sleep(100 * time.Millisecond)

		// Get the confirmation code from mock email service
		mockEmailService := emailService.(*mocks.MockEmailService)
		sentEmails := mockEmailService.GetSentEmails()
		if len(sentEmails) == 0 {
			t.Fatal("Expected confirmation email to be sent")
		}
		confirmationCode := sentEmails[0].Code

		// Confirm email
		confirmReq := services.ConfirmEmailRequest{
			Email: "test@example.com",
			Code:  confirmationCode,
		}
		_ = userService.ConfirmEmail(ctx, confirmReq)

		// Now try to login
		loginReq := services.LoginUserRequest{
			Email:    "test@example.com",
			Password: "password123",
		}

		// Execute
		user, err := userService.LoginUser(ctx, loginReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error, got %v", err)
		}

		if user.Email != loginReq.Email {
			t.Errorf("Expected email %s, got %s", loginReq.Email, user.Email)
		}
	})

	t.Run("invalid credentials", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		loginReq := services.LoginUserRequest{
			Email:    "nonexistent@example.com",
			Password: "password123",
		}

		// Execute
		user, err := userService.LoginUser(ctx, loginReq)

		// Assert
		if err == nil {
			t.Fatal("Expected error for invalid credentials")
		}

		if !strings.Contains(err.Error(), "invalid credentials") {
			t.Errorf("Expected 'invalid credentials' error, got %v", err)
		}

		if user != nil {
			t.Error("Expected user to be nil on error")
		}
	})
}

func TestUserService_ConfirmEmail(t *testing.T) {
	ctx := context.Background()

	t.Run("successful email confirmation", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register a user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		_, _ = userService.RegisterUser(ctx, registerReq)

		// Wait for async email
		time.Sleep(100 * time.Millisecond)

		// Get the confirmation code from mock email service
		mockEmailService := emailService.(*mocks.MockEmailService)
		sentEmails := mockEmailService.GetSentEmails()
		if len(sentEmails) == 0 {
			t.Fatal("Expected confirmation email to be sent")
		}
		confirmationCode := sentEmails[0].Code

		// Confirm email
		confirmReq := services.ConfirmEmailRequest{
			Email: "test@example.com",
			Code:  confirmationCode,
		}

		// Execute
		err := userService.ConfirmEmail(ctx, confirmReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error, got %v", err)
		}

		// Verify user is now confirmed and active
		user, _ := userRepo.GetByEmail(ctx, "test@example.com")
		if !user.ConfirmedEmail {
			t.Error("Expected user email to be confirmed")
		}

		if !user.IsActive {
			t.Error("Expected user to be active")
		}

		if user.ConfirmationCode != "" {
			t.Error("Expected confirmation code to be cleared")
		}
	})

	t.Run("invalid confirmation code", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register a user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		_, _ = userService.RegisterUser(ctx, registerReq)

		// Use wrong confirmation code
		confirmReq := services.ConfirmEmailRequest{
			Email: "test@example.com",
			Code:  "000000",
		}

		// Execute
		err := userService.ConfirmEmail(ctx, confirmReq)

		// Assert
		if err == nil {
			t.Fatal("Expected error for invalid confirmation code")
		}

		if !strings.Contains(err.Error(), "invalid confirmation code") {
			t.Errorf("Expected 'invalid confirmation code' error, got %v", err)
		}
	})
}

func TestUserService_ResetPassword(t *testing.T) {
	ctx := context.Background()

	t.Run("successful password reset", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register and confirm user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Wait for registration email to be sent
		time.Sleep(100 * time.Millisecond)

		// Confirm email
		confirmReq := services.ConfirmEmailRequest{
			Email: user.Email,
			Code:  user.ConfirmationCode,
		}
		_ = userService.ConfirmEmail(ctx, confirmReq)

		// Get initial email count (should be 1 from registration)
		mockEmailService := emailService.(*mocks.MockEmailService)
		initialEmailCount := len(mockEmailService.GetSentEmails())

		resetReq := services.ResetPasswordRequest{
			Email: "test@example.com",
		}

		// Execute
		err := userService.ResetPassword(ctx, resetReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error, got %v", err)
		}

		// Wait for async email sending
		time.Sleep(100 * time.Millisecond)

		// Verify password reset email was sent (should be one more than initial)
		sentEmails := mockEmailService.GetSentEmails()
		expectedTotal := initialEmailCount + 1
		if len(sentEmails) != expectedTotal {
			t.Errorf("Expected %d emails to be sent, got %d", expectedTotal, len(sentEmails))
		}

		// Get the last sent email (password reset email)
		lastEmail := sentEmails[len(sentEmails)-1]
		if lastEmail.Subject != "Password Reset" {
			t.Errorf("Expected email subject 'Password Reset', got '%s'", lastEmail.Subject)
		}

		if lastEmail.Email != "test@example.com" {
			t.Errorf("Expected email to be sent to test@example.com, got %s", lastEmail.Email)
		}

		// Verify the new password is valid (should be 16 characters)
		newPassword := lastEmail.Code // Code field contains the password
		if len(newPassword) != 16 {
			t.Errorf("Expected new password to be 16 characters, got %d", len(newPassword))
		}

		// Verify user can login with new password
		loginReq := services.LoginUserRequest{
			Email:    "test@example.com",
			Password: newPassword,
		}
		loggedInUser, err := userService.LoginUser(ctx, loginReq)
		if err != nil {
			t.Fatalf("Expected to login with new password, got error: %v", err)
		}

		if loggedInUser.Email != "test@example.com" {
			t.Errorf("Expected logged in user email to be test@example.com, got %s", loggedInUser.Email)
		}
	})

	t.Run("user not found - returns success for security", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		resetReq := services.ResetPasswordRequest{
			Email: "nonexistent@example.com",
		}

		// Execute
		err := userService.ResetPassword(ctx, resetReq)

		// Assert - should return success to prevent email enumeration attacks
		if err != nil {
			t.Fatalf("Expected no error for security reasons, got %v", err)
		}

		// Wait for potential async email sending
		time.Sleep(100 * time.Millisecond)

		// Verify no email was sent for non-existent user
		mockEmailService := emailService.(*mocks.MockEmailService)
		sentEmails := mockEmailService.GetSentEmails()
		if len(sentEmails) != 0 {
			t.Errorf("Expected no emails to be sent for non-existent user, got %d", len(sentEmails))
		}
	})
}

func TestUserService_DeleteUser(t *testing.T) {
	ctx := context.Background()

	t.Run("successful user deletion", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register a user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Verify user exists before deletion
		existingUser, err := userRepo.GetByID(ctx, user.ID)
		if err != nil {
			t.Fatalf("Expected user to exist before deletion, got error: %v", err)
		}
		if existingUser.ID != user.ID {
			t.Errorf("Expected user ID %s, got %s", user.ID, existingUser.ID)
		}

		// Execute
		err = userService.DeleteUser(ctx, user.ID)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error during deletion, got %v", err)
		}

		// Verify user no longer exists
		_, err = userRepo.GetByID(ctx, user.ID)
		if err == nil {
			t.Error("Expected error when trying to get deleted user")
		}
		if !strings.Contains(err.Error(), "user not found") {
			t.Errorf("Expected 'user not found' error, got %v", err)
		}

		// Verify email index is also cleaned up
		emailExists, err := userRepo.EmailExists(ctx, user.Email)
		if err != nil {
			t.Fatalf("Error checking email existence: %v", err)
		}
		if emailExists {
			t.Error("Expected email to not exist after user deletion")
		}

		// Verify username index is also cleaned up
		usernameExists, err := userRepo.UsernameExists(ctx, user.Username)
		if err != nil {
			t.Fatalf("Error checking username existence: %v", err)
		}
		if usernameExists {
			t.Error("Expected username to not exist after user deletion")
		}
	})

	t.Run("delete non-existent user (idempotent)", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		nonExistentUserID := "non-existent-user-id"

		// Execute
		err := userService.DeleteUser(ctx, nonExistentUserID)

		// Assert - DELETE should be idempotent, no error for non-existent user
		if err != nil {
			t.Fatalf("Expected no error for idempotent delete operation, got %v", err)
		}
	})

	t.Run("delete user with empty ID (idempotent)", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Execute
		err := userService.DeleteUser(ctx, "")

		// Assert - DELETE should be idempotent, no error for empty ID
		if err != nil {
			t.Fatalf("Expected no error for idempotent delete operation, got %v", err)
		}
	})

	t.Run("delete same user twice (idempotent)", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register a user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Execute - delete user first time
		err := userService.DeleteUser(ctx, user.ID)
		if err != nil {
			t.Fatalf("Expected no error during first deletion, got %v", err)
		}

		// Execute - delete user second time (should be idempotent)
		err = userService.DeleteUser(ctx, user.ID)

		// Assert - second delete should also succeed (idempotent)
		if err != nil {
			t.Fatalf("Expected no error for idempotent second deletion, got %v", err)
		}
	})
}

func TestUserService_UpdateUser(t *testing.T) {
	ctx := context.Background()

	t.Run("successful username update", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register and confirm user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "oldusername",
			Password: "password123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Confirm email to activate user
		confirmReq := services.ConfirmEmailRequest{
			Email: user.Email,
			Code:  user.ConfirmationCode,
		}
		_ = userService.ConfirmEmail(ctx, confirmReq)

		// Get updated user after confirmation
		user, _ = userService.GetUserByID(ctx, user.ID)
		originalPasswordHash := user.PasswordHash

		// Execute username update
		updateReq := services.UpdateUserRequest{
			User:     user,
			Username: "newusername",
			Password: "",
		}
		err := userService.UpdateUser(ctx, updateReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error during username update, got %v", err)
		}

		// Verify username was updated
		if user.Username != "newusername" {
			t.Errorf("Expected username to be 'newusername', got '%s'", user.Username)
		}

		// Verify password hash was not changed
		if user.PasswordHash != originalPasswordHash {
			t.Error("Expected password hash to remain unchanged when only updating username")
		}

		// Verify user can be retrieved with new username
		updatedUser, err := userRepo.GetByID(ctx, user.ID)
		if err != nil {
			t.Fatalf("Expected to retrieve updated user, got error: %v", err)
		}
		if updatedUser.Username != "newusername" {
			t.Errorf("Expected retrieved user username to be 'newusername', got '%s'", updatedUser.Username)
		}
	})

	t.Run("successful password update", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register and confirm user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "oldpassword123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Confirm email to activate user
		confirmReq := services.ConfirmEmailRequest{
			Email: user.Email,
			Code:  user.ConfirmationCode,
		}
		_ = userService.ConfirmEmail(ctx, confirmReq)

		// Get updated user after confirmation
		user, _ = userService.GetUserByID(ctx, user.ID)
		originalUsername := user.Username
		originalPasswordHash := user.PasswordHash

		// Execute password update
		updateReq := services.UpdateUserRequest{
			User:     user,
			Username: "",
			Password: "newpassword123",
		}
		err := userService.UpdateUser(ctx, updateReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error during password update, got %v", err)
		}

		// Verify username was not changed
		if user.Username != originalUsername {
			t.Errorf("Expected username to remain '%s', got '%s'", originalUsername, user.Username)
		}

		// Verify password hash was changed
		if user.PasswordHash == originalPasswordHash {
			t.Error("Expected password hash to be changed when updating password")
		}

		// Verify user can login with new password
		loginReq := services.LoginUserRequest{
			Email:    "test@example.com",
			Password: "newpassword123",
		}
		loggedInUser, err := userService.LoginUser(ctx, loginReq)
		if err != nil {
			t.Fatalf("Expected to login with new password, got error: %v", err)
		}
		if loggedInUser.Email != "test@example.com" {
			t.Errorf("Expected logged in user email to be test@example.com, got %s", loggedInUser.Email)
		}

		// Verify user cannot login with old password
		oldLoginReq := services.LoginUserRequest{
			Email:    "test@example.com",
			Password: "oldpassword123",
		}
		_, err = userService.LoginUser(ctx, oldLoginReq)
		if err == nil {
			t.Error("Expected error when trying to login with old password")
		}
	})

	t.Run("successful username and password update", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register and confirm user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "oldusername",
			Password: "oldpassword123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Confirm email to activate user
		confirmReq := services.ConfirmEmailRequest{
			Email: user.Email,
			Code:  user.ConfirmationCode,
		}
		_ = userService.ConfirmEmail(ctx, confirmReq)

		// Get updated user after confirmation
		user, _ = userService.GetUserByID(ctx, user.ID)
		originalPasswordHash := user.PasswordHash

		// Execute both username and password update
		updateReq := services.UpdateUserRequest{
			User:     user,
			Username: "newusername",
			Password: "newpassword123",
		}
		err := userService.UpdateUser(ctx, updateReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error during update, got %v", err)
		}

		// Verify username was updated
		if user.Username != "newusername" {
			t.Errorf("Expected username to be 'newusername', got '%s'", user.Username)
		}

		// Verify password hash was changed
		if user.PasswordHash == originalPasswordHash {
			t.Error("Expected password hash to be changed when updating password")
		}

		// Verify user can login with new credentials
		loginReq := services.LoginUserRequest{
			Email:    "test@example.com",
			Password: "newpassword123",
		}
		loggedInUser, err := userService.LoginUser(ctx, loginReq)
		if err != nil {
			t.Fatalf("Expected to login with new password, got error: %v", err)
		}
		if loggedInUser.Username != "newusername" {
			t.Errorf("Expected logged in user username to be 'newusername', got %s", loggedInUser.Username)
		}
	})

	t.Run("update with empty values (no changes)", func(t *testing.T) {
		// Setup
		userRepo := mocks.NewMockUserRepository()
		emailService := mocks.NewMockEmailService()
		userService := services.NewUserService(userRepo, emailService)

		// Register and confirm user first
		registerReq := services.RegisterUserRequest{
			Email:    "test@example.com",
			Username: "testuser",
			Password: "password123",
		}
		user, _ := userService.RegisterUser(ctx, registerReq)

		// Confirm email to activate user
		confirmReq := services.ConfirmEmailRequest{
			Email: user.Email,
			Code:  user.ConfirmationCode,
		}
		_ = userService.ConfirmEmail(ctx, confirmReq)

		// Get updated user after confirmation
		user, _ = userService.GetUserByID(ctx, user.ID)
		originalUsername := user.Username
		originalPasswordHash := user.PasswordHash

		// Execute update with empty values
		updateReq := services.UpdateUserRequest{
			User:     user,
			Username: "",
			Password: "",
		}
		err := userService.UpdateUser(ctx, updateReq)

		// Assert
		if err != nil {
			t.Fatalf("Expected no error during update with empty values, got %v", err)
		}

		// Verify username was not changed
		if user.Username != originalUsername {
			t.Errorf("Expected username to remain '%s', got '%s'", originalUsername, user.Username)
		}

		// Verify password hash was not changed
		if user.PasswordHash != originalPasswordHash {
			t.Error("Expected password hash to remain unchanged when updating with empty password")
		}
	})
}
