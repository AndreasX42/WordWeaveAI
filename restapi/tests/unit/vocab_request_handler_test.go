package unit

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/handlers"
	"github.com/AndreasX42/restapi/tests/mocks"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupVocabRequestHandler() (*handlers.VocabRequestHandler, *mocks.MockSQSClient, *mocks.MockUserRepository, *gin.Engine) {
	gin.SetMode(gin.TestMode)

	// Setup environment variables
	os.Setenv("JWT_SECRET_KEY", "test-secret-key-for-vocab-request-tests")
	os.Setenv("JWT_EXPIRATION_TIME", "60")
	os.Setenv("SQS_VOCAB_REQUEST_QUEUE_URL", "https://sqs.test.amazonaws.com/123456789/vocab-requests.fifo")
	os.Setenv("MAX_VOCAB_REQUESTS_FREE_TIER", "10")

	// Create mocks
	sqsClient := mocks.NewMockSQSClient()
	userRepo := mocks.NewMockUserRepository().(*mocks.MockUserRepository)

	// Create handler
	vocabRequestHandler := handlers.NewVocabRequestHandler(sqsClient, userRepo)

	// Setup router
	router := gin.New()

	// Create a simple test middleware that extracts user ID from a test header
	testAuthMiddleware := func(c *gin.Context) {
		userID := c.GetHeader("Test-User-ID")
		if userID == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "Unauthorized"})
			c.Abort()
			return
		}

		// Get user from repository
		user, err := userRepo.GetByID(c.Request.Context(), userID)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "User not found"})
			c.Abort()
			return
		}

		// Set user as principal
		c.Set("principal", user)
		c.Next()
	}

	// Protected routes
	authenticated := router.Group("/")
	authenticated.Use(testAuthMiddleware)
	authenticated.POST("/vocab/request", vocabRequestHandler.RequestVocab)

	return vocabRequestHandler, sqsClient, userRepo, router
}

func createTestUserAndGetToken(t *testing.T, userRepo *mocks.MockUserRepository, router *gin.Engine, requestCount int) (string, *entities.User) {
	// Create test user
	testUser, err := entities.NewUser(
		"test-user-123",
		"testuser",
		"test@example.com",
		"hashedpassword",
		"",
	)
	require.NoError(t, err)

	// Mark as confirmed and active
	testUser.ConfirmedEmail = true
	testUser.IsActive = true
	testUser.RequestCount = requestCount

	// Add to mock repository
	userRepo.AddTestUser(testUser)

	// Return the user ID as a "token" for our test middleware
	return testUser.ID, testUser
}

func TestVocabRequestHandler_RequestVocab(t *testing.T) {
	_, sqsClient, userRepo, router := setupVocabRequestHandler()

	t.Run("successful vocab request", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		// Assertions
		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Vocabulary request submitted successfully", response["message"])
		assert.Equal(t, "pending", response["status"])
		assert.NotEmpty(t, response["request_id"])

		// Verify SQS message was sent
		messages := sqsClient.GetSentMessages()
		assert.Equal(t, 1, len(messages))

		if len(messages) > 0 {
			message := messages[0]
			assert.Equal(t, "https://sqs.test.amazonaws.com/123456789/vocab-requests.fifo", message.QueueURL)
			assert.Equal(t, "vocab-requests", message.MessageGroupID)
			assert.NotEmpty(t, message.DeduplicationID)

			// Verify message content
			var sqsMessage map[string]any
			err = json.Unmarshal([]byte(message.MessageBody), &sqsMessage)
			require.NoError(t, err)

			assert.Equal(t, "hello", sqsMessage["source_word"])
			assert.Equal(t, "en", sqsMessage["source_language"])
			assert.Equal(t, "es", sqsMessage["target_language"])
			assert.Equal(t, "test-user-123", sqsMessage["user_id"])
		}

		// Verify user request count was incremented
		updatedUser, err := userRepo.GetByID(context.Background(), "test-user-123")
		require.NoError(t, err)
		assert.Equal(t, 1, updatedUser.RequestCount)
	})

	t.Run("missing source_word", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusBadRequest, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Invalid request format", response["error"])
		assert.Contains(t, response["details"], "SourceWord")
	})

	t.Run("missing target_language", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusBadRequest, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Invalid request format", response["error"])
		assert.Contains(t, response["details"], "TargetLanguage")
	})

	t.Run("empty source_word after trimming", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "   ", // Only whitespace
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusBadRequest, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Source word cannot be empty", response["error"])
	})

	t.Run("unauthorized access", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		// No Test-User-ID header set

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusUnauthorized, recorder.Code)
	})

	t.Run("invalid JWT token", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", "nonexistent-user-id") // Invalid user ID

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusUnauthorized, recorder.Code)
	})

	t.Run("rate limit exceeded", func(t *testing.T) {
		// Create user with max requests already reached
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 10)

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusTooManyRequests, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Contains(t, response["details"], "You have reached the maximum number of 10 requests")
	})

	t.Run("SQS error handling", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		// Configure SQS to return error
		sqsClient.SetError(true, "SQS service unavailable")

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusInternalServerError, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Failed to submit word request", response["error"])

		// Reset SQS error state
		sqsClient.SetError(false, "")
	})

	t.Run("invalid JSON request", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer([]byte("invalid json")))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusBadRequest, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Invalid request format", response["error"])
	})

	t.Run("user repository error during update", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		// Configure user repo to return error on update
		userRepo.SetUpdateError(true, "database unavailable")

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusInternalServerError, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Failed to update user data", response["error"])

		// Reset error state
		userRepo.SetUpdateError(false, "")
	})

	t.Run("missing SQS queue URL environment variable", func(t *testing.T) {
		// Temporarily remove environment variable
		originalURL := os.Getenv("SQS_VOCAB_REQUEST_QUEUE_URL")
		os.Unsetenv("SQS_VOCAB_REQUEST_QUEUE_URL")

		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusInternalServerError, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Queue configuration error", response["error"])

		// Restore environment variable
		os.Setenv("SQS_VOCAB_REQUEST_QUEUE_URL", originalURL)
	})
}

func TestVocabRequestHandler_DeduplicationID(t *testing.T) {
	_, sqsClient, userRepo, router := setupVocabRequestHandler()

	t.Run("deduplication ID generation", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "hello world", // Contains space
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		// Verify message was sent with proper deduplication ID
		messages := sqsClient.GetSentMessages()
		assert.Equal(t, 1, len(messages))

		if len(messages) > 0 {
			message := messages[0]

			// Deduplication ID should be: hello_world-en-es (spaces replaced with underscores)
			assert.Equal(t, "hello_world-en-es", message.DeduplicationID)
		}
	})

	t.Run("deduplication ID sanitization", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "café & naïve", // Special characters
			"source_language": "fr",
			"target_language": "en",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		// Verify message was sent with sanitized deduplication ID
		messages := sqsClient.GetSentMessages()
		assert.Equal(t, 1, len(messages))

		if len(messages) > 0 {
			message := messages[0]

			// Should only contain alphanumeric, underscore, and hyphen characters
			dedupID := message.DeduplicationID
			assert.Regexp(t, "^[a-zA-Z0-9_-]+$", dedupID)
			assert.Equal(t, "caf__nave-fr-en", dedupID) // Double underscore because multiple special chars get replaced
		}
	})

	t.Run("very long source word truncation", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		// Create a very long source word
		longWord := strings.Repeat("abcde", 20) // 100 characters

		vocabRequest := map[string]string{
			"source_word":     longWord,
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		// Verify message was sent with truncated deduplication ID
		messages := sqsClient.GetSentMessages()
		assert.Equal(t, 1, len(messages))

		if len(messages) > 0 {
			message := messages[0]

			// Should be truncated to 50 chars for the word part, plus language codes
			assert.True(t, len(message.DeduplicationID) <= 50+3+3+2) // word(50) + lang1(3) + lang2(3) + separators(2)
		}
	})

	t.Run("empty source word deduplication", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "", // This should fail validation before reaching dedup logic
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		// Should fail validation before reaching SQS
		assert.Equal(t, http.StatusBadRequest, recorder.Code)
	})
}

func TestVocabRequestHandler_RateLimiting(t *testing.T) {
	_, sqsClient, userRepo, router := setupVocabRequestHandler()

	t.Run("at rate limit boundary", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		// Create user with 9 requests (just under the limit)
		token, _ := createTestUserAndGetToken(t, userRepo, router, 9)

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		// Should succeed (9 + 1 = 10, which is exactly the limit)
		assert.Equal(t, http.StatusOK, recorder.Code)

		// Verify user request count was incremented
		updatedUser, err := userRepo.GetByID(context.Background(), "test-user-123")
		require.NoError(t, err)
		assert.Equal(t, 10, updatedUser.RequestCount)
	})

	t.Run("malformed MAX_VOCAB_REQUESTS_FREE_TIER", func(t *testing.T) {
		sqsClient.Reset() // Clear previous messages
		// Save original value
		originalMaxRequests := os.Getenv("MAX_VOCAB_REQUESTS_FREE_TIER")

		// Set invalid value
		os.Setenv("MAX_VOCAB_REQUESTS_FREE_TIER", "invalid")

		token, _ := createTestUserAndGetToken(t, userRepo, router, 0)

		vocabRequest := map[string]string{
			"source_word":     "hello",
			"source_language": "en",
			"target_language": "es",
		}

		reqBody, _ := json.Marshal(vocabRequest)
		request := httptest.NewRequest(http.MethodPost, "/vocab/request", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("Test-User-ID", token) // Use Test-User-ID instead of Authorization

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusInternalServerError, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Failed to parse MAX_VOCAB_REQUESTS_FREE_TIER", response["error"])

		// Restore environment variable
		os.Setenv("MAX_VOCAB_REQUESTS_FREE_TIER", originalMaxRequests)
	})
}
