package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/handlers"
	"github.com/AndreasX42/restapi/middlewares"
	"github.com/AndreasX42/restapi/tests/mocks"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/gin-gonic/gin"
	"github.com/guregu/dynamo/v2"
)

var (
	dynamoClient *dynamo.DB
	awsClient    *dynamodb.Client
)

// TestMain sets up and tears down the test environment
func TestMain(m *testing.M) {
	// Setup environment variables for JWT
	os.Setenv("JWT_SECRET_KEY", "test-secret-key-for-integration-tests")
	os.Setenv("JWT_EXPIRATION_TIME", "60") // 60 minutes

	// Setup
	var err error
	dynamoClient, awsClient, err = SetupDynamoDBLocal()
	if err != nil {
		panic("Failed to setup DynamoDB Local: " + err.Error())
	}

	// Create test table
	if err := CreateTestTable(awsClient); err != nil {
		panic("Failed to create test table: " + err.Error())
	}

	// Run tests
	code := m.Run()

	// Cleanup
	if err := CleanupTestTable(awsClient); err != nil {
		panic("Failed to cleanup test table: " + err.Error())
	}

	os.Exit(code)
}

func TestUserAPI_DynamoDBIntegration(t *testing.T) {
	t.Run("complete user journey with real DynamoDB", func(t *testing.T) {
		// Setup test server with real DynamoDB and mock email service
		server := setupIntegrationTestServer(t)

		// Test data
		testEmail := "integration@example.com"
		testUsername := "integrationuser"
		testPassword := "password123"

		// 1. Register user
		registerReq := map[string]string{
			"email":    testEmail,
			"username": testUsername,
			"password": testPassword,
		}

		userID, confirmationCode := testRegisterUser(t, server, registerReq)
		t.Logf("Registered user with ID: %s", userID)

		// 2. Confirm email
		testConfirmEmail(t, server, testEmail, confirmationCode)
		t.Logf("Confirmed email for user: %s", testEmail)

		// 3. Login user
		token := testLoginUser(t, server, testEmail, testPassword)
		t.Logf("User logged in successfully")

		// 4. Delete user
		testDeleteUser(t, server, token)
		t.Logf("User deleted successfully")

		// 5. Verify user cannot login after deletion
		testLoginAfterDeletion(t, server, testEmail, testPassword)
		t.Logf("Verified user cannot login after deletion")
	})

	t.Run("register validation errors", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Test invalid email format
		invalidEmailReq := map[string]string{
			"email":    "invalid-email",
			"username": "testuser",
			"password": "password123",
		}
		testRegisterValidationError(t, server, invalidEmailReq, "Field Email failed on the 'email' rule")

		// Test username too short
		shortUsernameReq := map[string]string{
			"email":    "test@example.com",
			"username": "ab",
			"password": "password123",
		}
		testRegisterValidationError(t, server, shortUsernameReq, "Field Username failed on the 'min' rule")

		// Test password too short
		shortPasswordReq := map[string]string{
			"email":    "test@example.com",
			"username": "testuser",
			"password": "short",
		}
		testRegisterValidationError(t, server, shortPasswordReq, "Field Password failed on the 'min' rule")

		// Test missing required fields
		missingEmailReq := map[string]string{
			"username": "testuser",
			"password": "password123",
		}
		testRegisterValidationError(t, server, missingEmailReq, "Field Email failed on the 'required' rule")

		// Test multiple validation errors
		multipleErrorsReq := map[string]string{
			"email":    "invalid",
			"username": "ab",
			"password": "short",
		}
		testRegisterMultipleValidationErrors(t, server, multipleErrorsReq, []string{
			"Field Email failed on the 'email' rule",
			"Field Username failed on the 'min' rule",
			"Field Password failed on the 'min' rule",
		})
	})

	t.Run("login validation errors", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Test invalid email format
		invalidEmailReq := map[string]string{
			"email":    "invalid-email",
			"password": "password123",
		}
		testLoginValidationError(t, server, invalidEmailReq, "Field Email failed on the 'email' rule")

		// Test password too short
		shortPasswordReq := map[string]string{
			"email":    "test@example.com",
			"password": "short",
		}
		testLoginValidationError(t, server, shortPasswordReq, "Field Password failed on the 'min' rule")

		// Test missing required fields
		missingEmailReq := map[string]string{
			"password": "password123",
		}
		testLoginValidationError(t, server, missingEmailReq, "Field Email failed on the 'required' rule")
	})

	t.Run("confirm email validation errors", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Test invalid email format
		invalidEmailReq := map[string]string{
			"email": "invalid-email",
			"code":  "123456",
		}
		testConfirmEmailValidationError(t, server, invalidEmailReq, "Field Email failed on the 'email' rule")

		// Test code too short
		shortCodeReq := map[string]string{
			"email": "test@example.com",
			"code":  "12345",
		}
		testConfirmEmailValidationError(t, server, shortCodeReq, "Field Code failed on the 'min' rule")

		// Test missing required fields
		missingCodeReq := map[string]string{
			"email": "test@example.com",
		}
		testConfirmEmailValidationError(t, server, missingCodeReq, "Field Code failed on the 'required' rule")
	})

	t.Run("reset password validation errors", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Test invalid email format
		invalidEmailReq := map[string]string{
			"email": "invalid-email",
		}
		testResetPasswordValidationError(t, server, invalidEmailReq, "Field Email failed on the 'email' rule")

		// Test missing required field
		missingEmailReq := map[string]string{}
		testResetPasswordValidationError(t, server, missingEmailReq, "Field Email failed on the 'required' rule")
	})

	t.Run("database constraint validation", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register first user
		firstUserReq := map[string]string{
			"email":    "unique@example.com",
			"username": "uniqueuser",
			"password": "password123",
		}
		testRegisterUser(t, server, firstUserReq)

		// Try to register with same email - should fail
		sameEmailReq := map[string]string{
			"email":    "unique@example.com",
			"username": "differentuser",
			"password": "password123",
		}
		testRegisterUserError(t, server, sameEmailReq, http.StatusConflict, "email already exists")

		// Try to register with same username - should fail
		sameUsernameReq := map[string]string{
			"email":    "different@example.com",
			"username": "uniqueuser",
			"password": "password123",
		}
		testRegisterUserError(t, server, sameUsernameReq, http.StatusConflict, "username already exists")
	})

	t.Run("email confirmation workflow", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register user
		registerReq := map[string]string{
			"email":    "confirm@example.com",
			"username": "confirmuser",
			"password": "password123",
		}
		_, confirmationCode := testRegisterUser(t, server, registerReq)

		// Try to login before confirmation - should fail
		testLoginError(t, server, "confirm@example.com", "password123", http.StatusUnauthorized)

		// Confirm email
		testConfirmEmail(t, server, "confirm@example.com", confirmationCode)

		// Now login should work
		testLoginUser(t, server, "confirm@example.com", "password123")
	})

	t.Run("invalid confirmation code", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register user
		registerReq := map[string]string{
			"email":    "invalid@example.com",
			"username": "invaliduser",
			"password": "password123",
		}
		testRegisterUser(t, server, registerReq)

		// Try to confirm with wrong code
		testConfirmEmailError(t, server, "invalid@example.com", "wrongcode", http.StatusBadRequest)
	})

	t.Run("delete user", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register and confirm user
		registerReq := map[string]string{
			"email":    "delete@example.com",
			"username": "deleteuser",
			"password": "password123",
		}
		_, confirmationCode := testRegisterUser(t, server, registerReq)
		testConfirmEmail(t, server, "delete@example.com", confirmationCode)
		token := testLoginUser(t, server, "delete@example.com", "password123")

		// Delete user
		testDeleteUser(t, server, token)

	})

	t.Run("password reset workflow", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register and confirm user
		registerReq := map[string]string{
			"email":    "reset@example.com",
			"username": "resetuser",
			"password": "password123",
		}
		_, confirmationCode := testRegisterUser(t, server, registerReq)
		testConfirmEmail(t, server, "reset@example.com", confirmationCode)

		// Verify user can login with original password
		testLoginUser(t, server, "reset@example.com", "password123")

		// Reset password
		newPassword := testResetPassword(t, server, "reset@example.com")

		// Verify user cannot login with old password
		testLoginError(t, server, "reset@example.com", "password123", http.StatusUnauthorized)

		// Verify user can login with new password
		testLoginUser(t, server, "reset@example.com", newPassword)
	})

	t.Run("password reset for non-existent user - returns success for security", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Test password reset for non-existent email
		testResetPasswordSuccess(t, server, "nonexistent@example.com")
		t.Log("Password reset for non-existent user handled securely")
	})

	t.Run("password reset with invalid email", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Try to reset password with invalid email format
		testResetPasswordError(t, server, "invalid-email", http.StatusBadRequest)
	})

	t.Run("update user validation errors", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register and confirm user to get a valid token
		registerReq := map[string]string{
			"email":    "validation@example.com",
			"username": "validationuser",
			"password": "password123",
		}
		_, confirmationCode := testRegisterUser(t, server, registerReq)
		testConfirmEmail(t, server, "validation@example.com", confirmationCode)
		token := testLoginUser(t, server, "validation@example.com", "password123")

		// Test username too short
		shortUsernameReq := map[string]string{
			"username": "ab",
			"password": "password123",
		}
		testUpdateValidationError(t, server, "Bearer "+token, shortUsernameReq, "Field Username failed on the 'min' rule")

		// Test password too short
		shortPasswordReq := map[string]string{
			"username": "validuser",
			"password": "short",
		}
		testUpdateValidationError(t, server, "Bearer "+token, shortPasswordReq, "Field Password failed on the 'min' rule")

		// Test missing required fields
		missingUsernameReq := map[string]string{
			"password": "password123",
		}
		testUpdateValidationError(t, server, "Bearer "+token, missingUsernameReq, "Field Username failed on the 'required' rule")

		// Test multiple validation errors
		multipleErrorsReq := map[string]string{
			"username": "ab",
			"password": "short",
		}
		testUpdateMultipleValidationErrors(t, server, "Bearer "+token, multipleErrorsReq, []string{
			"Field Username failed on the 'min' rule",
			"Field Password failed on the 'min' rule",
		})
	})

	t.Run("update user functionality", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		// Register and confirm user
		registerReq := map[string]string{
			"email":    "update@example.com",
			"username": "oldusername",
			"password": "oldpassword123",
		}
		_, confirmationCode := testRegisterUser(t, server, registerReq)
		testConfirmEmail(t, server, "update@example.com", confirmationCode)
		token := testLoginUser(t, server, "update@example.com", "oldpassword123")

		// Test successful username and password update
		updateReq := map[string]string{
			"username": "newusername",
			"password": "newpassword123",
		}
		testUpdateUser(t, server, "Bearer "+token, updateReq)

		// Verify user can no longer login with old credentials
		testLoginError(t, server, "update@example.com", "oldpassword123", http.StatusUnauthorized)

		// Verify user can login with new password
		testLoginUser(t, server, "update@example.com", "newpassword123")
	})

	t.Run("update user unauthorized", func(t *testing.T) {
		server := setupIntegrationTestServer(t)

		updateReq := map[string]string{
			"username": "newusername",
			"password": "newpassword123",
		}

		// Test without token
		testUpdateUserError(t, server, "", updateReq, http.StatusUnauthorized)

		// Test with invalid token
		testUpdateUserError(t, server, "Bearer invalidtoken", updateReq, http.StatusUnauthorized)
	})
}

var testEmailService *mocks.MockEmailService

func setupIntegrationTestServer(t *testing.T) *gin.Engine {
	// Use test mode for Gin
	gin.SetMode(gin.TestMode)

	// Create real DynamoDB repository and mock email service
	userRepo := NewTestDynamoUserRepository(dynamoClient)
	testEmailService = mocks.NewMockEmailService().(*mocks.MockEmailService)
	userService := services.NewUserService(userRepo, testEmailService)
	userHandler := handlers.NewUserHandler(userService)

	// Setup Gin router
	router := gin.New()

	// Public routes
	router.POST("/users/register", userHandler.Register)
	router.POST("/users/login", userHandler.Login)
	router.POST("/users/confirm-email", userHandler.ConfirmEmail)
	router.POST("/users/reset-password", userHandler.ResetPassword)

	// Authenticated routes
	authenticated := router.Group("/users")
	authenticated.Use(middlewares.Authentication(userService))
	authenticated.DELETE("/delete", userHandler.Delete)
	authenticated.PUT("/update", userHandler.Update)

	return router
}

func testRegisterUser(t *testing.T, server *gin.Engine, req map[string]string) (string, string) {
	// Reset email service before each test
	testEmailService.Reset()

	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/register", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	details := response["details"].(map[string]interface{})
	userID := details["user_id"].(string)

	// Give time for async email sending
	time.Sleep(100 * time.Millisecond)

	// Get the actual confirmation code from the mock email service
	sentEmails := testEmailService.GetSentEmails()
	if len(sentEmails) == 0 {
		t.Fatal("Expected confirmation email to be sent")
	}
	confirmationCode := sentEmails[0].Code

	return userID, confirmationCode
}

func testRegisterUserError(t *testing.T, server *gin.Engine, req map[string]string, expectedStatus int, expectedErrorSubstring string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/register", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != expectedStatus {
		t.Fatalf("Expected status %d, got %d. Body: %s", expectedStatus, recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), expectedErrorSubstring) {
		t.Errorf("Expected error containing '%s', got: %s", expectedErrorSubstring, recorder.Body.String())
	}
}

func testConfirmEmail(t *testing.T, server *gin.Engine, email, code string) {
	req := map[string]string{
		"email": email,
		"code":  code,
	}

	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/confirm-email", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testConfirmEmailError(t *testing.T, server *gin.Engine, email, code string, expectedStatus int) {
	req := map[string]string{
		"email": email,
		"code":  code,
	}

	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/confirm-email", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != expectedStatus {
		t.Fatalf("Expected status %d, got %d. Body: %s", expectedStatus, recorder.Code, recorder.Body.String())
	}
}

func testLoginUser(t *testing.T, server *gin.Engine, email, password string) string {
	req := map[string]string{
		"email":    email,
		"password": password,
	}

	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/login", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse login response: %v", err)
	}

	details := response["details"].(map[string]interface{})
	return details["token"].(string)
}

func testLoginError(t *testing.T, server *gin.Engine, email, password string, expectedStatus int) {
	req := map[string]string{
		"email":    email,
		"password": password,
	}

	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/login", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != expectedStatus {
		t.Fatalf("Expected status %d, got %d. Body: %s", expectedStatus, recorder.Code, recorder.Body.String())
	}
}

func testDeleteUser(t *testing.T, server *gin.Engine, token string) {
	request := httptest.NewRequest(http.MethodDelete, "/users/delete", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusNoContent {
		t.Fatalf("Expected status 204, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testLoginAfterDeletion(t *testing.T, server *gin.Engine, email, password string) {
	req := map[string]string{
		"email":    email,
		"password": password,
	}

	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/login", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("Expected login to fail after deletion, got status %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testResetPassword(t *testing.T, server *gin.Engine, email string) string {
	// Clear previous emails
	testEmailService.Reset()

	resetReq := map[string]string{
		"email": email,
	}

	reqBody, _ := json.Marshal(resetReq)
	request := httptest.NewRequest(http.MethodPost, "/users/reset-password", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status %d for password reset, got %d. Response: %s", http.StatusOK, recorder.Code, recorder.Body.String())
	}

	// Wait for async email sending
	time.Sleep(100 * time.Millisecond)

	// Get the new password from the sent email
	sentEmails := testEmailService.GetSentEmails()
	if len(sentEmails) != 1 {
		t.Fatalf("Expected 1 password reset email to be sent, got %d", len(sentEmails))
	}

	if sentEmails[0].Subject != "Password Reset" {
		t.Errorf("Expected email subject 'Password Reset', got '%s'", sentEmails[0].Subject)
	}

	if sentEmails[0].To != email {
		t.Errorf("Expected email to be sent to %s, got %s", email, sentEmails[0].To)
	}

	// Return the new password (stored in Code field)
	newPassword := sentEmails[0].Code
	if len(newPassword) != 16 {
		t.Errorf("Expected new password to be 16 characters, got %d", len(newPassword))
	}

	return newPassword
}

func testResetPasswordSuccess(t *testing.T, server *gin.Engine, email string) {
	// Clear previous emails
	testEmailService.Reset()

	resetReq := map[string]string{
		"email": email,
	}

	reqBody, _ := json.Marshal(resetReq)
	request := httptest.NewRequest(http.MethodPost, "/users/reset-password", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status %d for password reset, got %d. Response: %s", http.StatusOK, recorder.Code, recorder.Body.String())
	}

	// Wait for potential async email sending
	time.Sleep(100 * time.Millisecond)

	// For non-existent users, no email should be sent
	sentEmails := testEmailService.GetSentEmails()
	if len(sentEmails) != 0 {
		t.Errorf("Expected no emails to be sent for non-existent user, got %d", len(sentEmails))
	}
}

func testResetPasswordError(t *testing.T, server *gin.Engine, email string, expectedStatus int) {
	resetReq := map[string]string{
		"email": email,
	}

	reqBody, _ := json.Marshal(resetReq)
	request := httptest.NewRequest(http.MethodPost, "/users/reset-password", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != expectedStatus {
		t.Fatalf("Expected status %d for password reset, got %d. Response: %s", expectedStatus, recorder.Code, recorder.Body.String())
	}
}

// New validation test helper functions
func testRegisterValidationError(t *testing.T, server *gin.Engine, req map[string]string, expectedErrorMessage string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/register", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	// Check for structured validation error response
	if response["message"] != "Validation failed" {
		t.Errorf("Expected message 'Validation failed', got '%v'", response["message"])
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	errorFound := false
	for _, err := range errors {
		if strings.Contains(err.(string), expectedErrorMessage) {
			errorFound = true
			break
		}
	}

	if !errorFound {
		t.Errorf("Expected error message containing '%s', got errors: %v", expectedErrorMessage, errors)
	}
}

func testRegisterMultipleValidationErrors(t *testing.T, server *gin.Engine, req map[string]string, expectedErrors []string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/register", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	if len(errors) != len(expectedErrors) {
		t.Errorf("Expected %d errors, got %d: %v", len(expectedErrors), len(errors), errors)
	}

	for _, expectedError := range expectedErrors {
		errorFound := false
		for _, actualError := range errors {
			if strings.Contains(actualError.(string), expectedError) {
				errorFound = true
				break
			}
		}
		if !errorFound {
			t.Errorf("Expected error containing '%s' not found in errors: %v", expectedError, errors)
		}
	}
}

func testLoginValidationError(t *testing.T, server *gin.Engine, req map[string]string, expectedErrorMessage string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/login", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	// Check for structured validation error response
	if response["message"] != "Validation failed" {
		t.Errorf("Expected message 'Validation failed', got '%v'", response["message"])
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	errorFound := false
	for _, err := range errors {
		if strings.Contains(err.(string), expectedErrorMessage) {
			errorFound = true
			break
		}
	}

	if !errorFound {
		t.Errorf("Expected error message containing '%s', got errors: %v", expectedErrorMessage, errors)
	}
}

func testConfirmEmailValidationError(t *testing.T, server *gin.Engine, req map[string]string, expectedErrorMessage string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/confirm-email", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	// Check for structured validation error response
	if response["message"] != "Validation failed" {
		t.Errorf("Expected message 'Validation failed', got '%v'", response["message"])
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	errorFound := false
	for _, err := range errors {
		if strings.Contains(err.(string), expectedErrorMessage) {
			errorFound = true
			break
		}
	}

	if !errorFound {
		t.Errorf("Expected error message containing '%s', got errors: %v", expectedErrorMessage, errors)
	}
}

func testResetPasswordValidationError(t *testing.T, server *gin.Engine, req map[string]string, expectedErrorMessage string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/users/reset-password", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	// Check for structured validation error response
	if response["message"] != "Validation failed" {
		t.Errorf("Expected message 'Validation failed', got '%v'", response["message"])
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	errorFound := false
	for _, err := range errors {
		if strings.Contains(err.(string), expectedErrorMessage) {
			errorFound = true
			break
		}
	}

	if !errorFound {
		t.Errorf("Expected error message containing '%s', got errors: %v", expectedErrorMessage, errors)
	}
}

func testUpdateValidationError(t *testing.T, server *gin.Engine, token string, req map[string]string, expectedErrorMessage string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPut, "/users/update", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	// Check for structured validation error response
	if response["message"] != "Validation failed" {
		t.Errorf("Expected message 'Validation failed', got '%v'", response["message"])
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	errorFound := false
	for _, err := range errors {
		if strings.Contains(err.(string), expectedErrorMessage) {
			errorFound = true
			break
		}
	}

	if !errorFound {
		t.Errorf("Expected error message containing '%s', got errors: %v", expectedErrorMessage, errors)
	}
}

func testUpdateMultipleValidationErrors(t *testing.T, server *gin.Engine, token string, req map[string]string, expectedErrors []string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPut, "/users/update", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status %d, got %d. Body: %s", http.StatusBadRequest, recorder.Code, recorder.Body.String())
	}

	var response map[string]interface{}
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse response: %v", err)
	}

	details, ok := response["details"].(map[string]interface{})
	if !ok {
		t.Fatal("Expected 'details' field in response")
	}

	errors, ok := details["errors"].([]interface{})
	if !ok {
		t.Fatal("Expected 'errors' array in details")
	}

	if len(errors) != len(expectedErrors) {
		t.Errorf("Expected %d errors, got %d: %v", len(expectedErrors), len(errors), errors)
	}

	for _, expectedError := range expectedErrors {
		errorFound := false
		for _, actualError := range errors {
			if strings.Contains(actualError.(string), expectedError) {
				errorFound = true
				break
			}
		}
		if !errorFound {
			t.Errorf("Expected error containing '%s' not found in errors: %v", expectedError, errors)
		}
	}
}

func testUpdateUser(t *testing.T, server *gin.Engine, token string, req map[string]string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPut, "/users/update", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testUpdateUserError(t *testing.T, server *gin.Engine, token string, req map[string]string, expectedStatus int) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPut, "/users/update", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != expectedStatus {
		t.Fatalf("Expected status %d, got %d. Body: %s", expectedStatus, recorder.Code, recorder.Body.String())
	}
}
