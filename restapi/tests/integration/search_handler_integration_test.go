package integration

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/handlers"
	"github.com/AndreasX42/restapi/middlewares"
	"github.com/AndreasX42/restapi/tests/mocks"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestSearchHandlerIntegration(t *testing.T) {
	// Setup environment for JWT
	os.Setenv("JWT_SECRET_KEY", "test-secret-key-for-search-integration-tests")
	os.Setenv("JWT_EXPIRATION_TIME", "60")

	t.Run("search handler endpoints integration", func(t *testing.T) {
		server := setupSearchIntegrationTestServer(t)

		// Test all search handler endpoints
		testGetVocabularyByPkSk(t, server)
		testGetVocabularyByParams(t, server)
		testGetMediaByRef(t, server)
		testSearchVocabulary(t, server)
		testSearchErrorHandling(t, server)
	})
}

func setupSearchIntegrationTestServer(t *testing.T) *gin.Engine {
	gin.SetMode(gin.TestMode)

	// Create mock repositories
	userRepo := mocks.NewMockUserRepository()
	vocabRepo := mocks.NewMockVocabRepository()
	mediaRepo := mocks.NewMockVocabMediaRepository()
	emailService := mocks.NewMockEmailService()

	// Add comprehensive test vocabulary data
	setupSearchTestVocabularyData(vocabRepo.(*mocks.MockVocabRepository), mediaRepo)

	// Create services
	userService := services.NewUserService(userRepo, emailService)
	vocabService := services.NewVocabService(vocabRepo, mediaRepo)

	// Create JWT middleware for testing
	authMiddleware, err := middlewares.JWTMiddleware(userService)
	if err != nil {
		t.Fatalf("Failed to setup JWT middleware: %v", err)
	}

	// Create handlers
	userHandler := handlers.NewUserHandler(userService, authMiddleware)
	searchHandler := handlers.NewSearchHandler(vocabService)

	// Setup router
	router := gin.New()

	// Public routes
	router.POST("/search", searchHandler.SearchVocabulary)
	router.GET("/vocab", searchHandler.GetVocabularyByPkSk)
	router.GET("/vocab/:sourceLanguage/:targetLanguage/:word/:pos", searchHandler.GetVocabularyByParams)
	router.GET("/media/:mediaRef", searchHandler.GetMediaByRef)

	// Auth routes
	router.POST("/users/register", userHandler.Register)
	router.POST("/users/confirm-email", userHandler.ConfirmEmail)
	router.POST("/auth/login", authMiddleware.LoginHandler)

	return router
}

func setupSearchTestVocabularyData(vocabRepo *mocks.MockVocabRepository, mediaRepo *mocks.MockVocabMediaRepository) {
	testWords := []*entities.VocabWord{
		{
			PK:               "SRC#en#hello",
			SK:               "TGT#es#POS#noun",
			SourceWord:       "hello",
			SourceLanguage:   "en",
			SourcePos:        "noun",
			SourceDefinition: []string{"A greeting"},
			TargetWord:       "hola",
			TargetLanguage:   "es",
			Examples:         []map[string]string{{"source": "Hello world", "target": "Hola mundo"}},
			Synonyms:         []map[string]string{{"synonym": "hi", "explanation": "informal greeting"}},
			MediaRef:         "hello_media_ref",
			EnglishWord:      "hello",
		},
		{
			PK:               "SRC#en#goodbye",
			SK:               "TGT#es#POS#interjection",
			SourceWord:       "goodbye",
			SourceLanguage:   "en",
			SourcePos:        "interjection",
			SourceDefinition: []string{"A farewell"},
			TargetWord:       "adiós",
			TargetLanguage:   "es",
			Examples:         []map[string]string{{"source": "Goodbye friend", "target": "Adiós amigo"}},
			Synonyms:         []map[string]string{{"synonym": "bye", "explanation": "informal farewell"}},
			MediaRef:         "goodbye_media_ref",
			EnglishWord:      "goodbye",
		},
		{
			PK:               "SRC#en#house",
			SK:               "TGT#es#POS#noun",
			SourceWord:       "house",
			SourceLanguage:   "en",
			SourcePos:        "noun",
			SourceDefinition: []string{"A building for living"},
			TargetWord:       "casa",
			TargetLanguage:   "es",
			Examples:         []map[string]string{{"source": "My house", "target": "Mi casa"}},
			Synonyms:         []map[string]string{{"synonym": "home", "explanation": "place of residence"}},
			MediaRef:         "house_media_ref",
			EnglishWord:      "house",
		},
		{
			// Word with special characters for normalization testing
			PK:               "SRC#fr#cafe",
			SK:               "TGT#en#POS#noun",
			SourceWord:       "café",
			SourceLanguage:   "fr",
			SourcePos:        "noun",
			SourceDefinition: []string{"A place that serves coffee"},
			TargetWord:       "café",
			TargetLanguage:   "en",
			Examples:         []map[string]string{{"source": "Un café parisien", "target": "A Parisian café"}},
			MediaRef:         "cafe_media_ref",
			EnglishWord:      "café",
		},
	}

	for _, word := range testWords {
		vocabRepo.AddTestWord(word.PK, word.SK, word)
	}

	// Add media data
	mediaRepo.AddTestMedia("hello_media_ref", map[string]any{
		"image":    "hello.jpg",
		"audio":    "hello.mp3",
		"type":     "greeting",
		"duration": "2.5s",
	})

	mediaRepo.AddTestMedia("goodbye_media_ref", map[string]any{
		"image":    "goodbye.jpg",
		"audio":    "goodbye.mp3",
		"type":     "farewell",
		"duration": "3.0s",
	})

	mediaRepo.AddTestMedia("house_media_ref", map[string]any{
		"image":       "house.jpg",
		"audio":       "house.mp3",
		"type":        "noun",
		"duration":    "1.8s",
		"description": "A typical suburban house",
	})

	mediaRepo.AddTestMedia("cafe_media_ref", map[string]any{
		"image":       "cafe.jpg",
		"audio":       "cafe.mp3",
		"type":        "place",
		"duration":    "2.2s",
		"description": "A cozy Parisian café",
	})
}

// Test GetVocabularyByPkSk endpoint
func testGetVocabularyByPkSk(t *testing.T, server *gin.Engine) {
	t.Run("GetVocabularyByPkSk successful lookup", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23hello&sk=TGT%23es%23POS%23noun", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "SRC#en#hello", response.PK)
		assert.Equal(t, "TGT#es#POS#noun", response.SK)
		assert.Equal(t, "hello", response.SourceWord)
		assert.Equal(t, "hola", response.TargetWord)
		assert.Equal(t, "en", response.SourceLanguage)
		assert.Equal(t, "es", response.TargetLanguage)
		assert.NotEmpty(t, response.Media)
	})

	t.Run("GetVocabularyByPkSk with media_ref parameter", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23house&sk=TGT%23es%23POS%23noun&media_ref=house_media_ref", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "house", response.SourceWord)
		assert.Equal(t, "casa", response.TargetWord)
		assert.NotEmpty(t, response.Media)
		assert.Equal(t, "house.jpg", response.Media["image"])
		assert.Equal(t, "1.8s", response.Media["duration"])
	})

	t.Run("GetVocabularyByPkSk missing parameters", func(t *testing.T) {
		testCases := []struct {
			url         string
			description string
		}{
			{"/vocab?sk=TGT%23es%23POS%23noun", "missing pk"},
			{"/vocab?pk=SRC%23en%23hello", "missing sk"},
			{"/vocab", "missing both parameters"},
		}

		for _, tc := range testCases {
			t.Run(tc.description, func(t *testing.T) {
				request := httptest.NewRequest(http.MethodGet, tc.url, nil)
				recorder := httptest.NewRecorder()
				server.ServeHTTP(recorder, request)

				assert.Equal(t, http.StatusBadRequest, recorder.Code)

				var response map[string]any
				err := json.Unmarshal(recorder.Body.Bytes(), &response)
				require.NoError(t, err)

				assert.Equal(t, "pk and sk are required", response["message"])
			})
		}
	})

	t.Run("GetVocabularyByPkSk not found", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23nonexistent&sk=TGT%23es%23POS%23noun", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusNotFound, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Vocabulary not found", response["message"])
		assert.Contains(t, response["details"], "error")
	})
}

// Test GetVocabularyByParams endpoint
func testGetVocabularyByParams(t *testing.T, server *gin.Engine) {
	t.Run("GetVocabularyByParams successful lookup", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/vocab/en/es/hello/noun", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "hello", response.SourceWord)
		assert.Equal(t, "hola", response.TargetWord)
		assert.Equal(t, "en", response.SourceLanguage)
		assert.Equal(t, "es", response.TargetLanguage)
		assert.Equal(t, "noun", response.SourcePos)
	})

	t.Run("GetVocabularyByParams with normalization", func(t *testing.T) {
		// Test with special characters that should be normalized
		request := httptest.NewRequest(http.MethodGet, "/vocab/fr/en/café/noun", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "café", response.SourceWord)
		assert.Equal(t, "café", response.TargetWord)
		assert.Equal(t, "fr", response.SourceLanguage)
		assert.Equal(t, "en", response.TargetLanguage)
	})

	t.Run("GetVocabularyByParams missing parameters", func(t *testing.T) {
		testCases := []struct {
			url          string
			expectedCode int
			expectedMsg  string
		}{
			{"/vocab///hello/noun", http.StatusBadRequest, "sourceLanguage, targetLanguage, pos, and word are required"},
			{"/vocab/en//hello/noun", http.StatusBadRequest, "sourceLanguage, targetLanguage, pos, and word are required"},
			{"/vocab/en/es//noun", http.StatusBadRequest, "sourceLanguage, targetLanguage, pos, and word are required"},
			{"/vocab/en/es/hello/", http.StatusMovedPermanently, ""}, // Trailing slash causes redirect
		}

		for _, tc := range testCases {
			request := httptest.NewRequest(http.MethodGet, tc.url, nil)
			recorder := httptest.NewRecorder()
			server.ServeHTTP(recorder, request)

			assert.Equal(t, tc.expectedCode, recorder.Code)

			if tc.expectedMsg != "" {
				var response map[string]any
				err := json.Unmarshal(recorder.Body.Bytes(), &response)
				require.NoError(t, err)
				assert.Equal(t, tc.expectedMsg, response["message"])
			}
		}
	})

	t.Run("GetVocabularyByParams not found", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/vocab/en/es/nonexistent/noun", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusNotFound, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Vocabulary not found", response["message"])
	})
}

// Test GetMediaByRef endpoint
func testGetMediaByRef(t *testing.T, server *gin.Engine) {
	t.Run("GetMediaByRef successful retrieval", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/media/hello_media_ref", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "hello.jpg", response["image"])
		assert.Equal(t, "hello.mp3", response["audio"])
		assert.Equal(t, "greeting", response["type"])
		assert.Equal(t, "2.5s", response["duration"])
	})

	t.Run("GetMediaByRef different media types", func(t *testing.T) {
		mediaRefs := []struct {
			ref          string
			expectedType string
		}{
			{"house_media_ref", "noun"},
			{"cafe_media_ref", "place"},
			{"goodbye_media_ref", "farewell"},
		}

		for _, media := range mediaRefs {
			request := httptest.NewRequest(http.MethodGet, "/media/"+media.ref, nil)
			recorder := httptest.NewRecorder()
			server.ServeHTTP(recorder, request)

			assert.Equal(t, http.StatusOK, recorder.Code)

			var response map[string]any
			err := json.Unmarshal(recorder.Body.Bytes(), &response)
			require.NoError(t, err)

			assert.Equal(t, media.expectedType, response["type"])
			assert.NotEmpty(t, response["image"])
			assert.NotEmpty(t, response["audio"])
		}
	})

	t.Run("GetMediaByRef not found", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodGet, "/media/nonexistent_media_ref", nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusNotFound, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Media not found", response["message"])
		assert.Contains(t, response["details"], "error")
	})
}

// Test SearchVocabulary endpoint (enhanced version of existing tests)
func testSearchVocabulary(t *testing.T, server *gin.Engine) {
	t.Run("SearchVocabulary basic search", func(t *testing.T) {
		searchReq := map[string]any{
			"query": "hello",
			"limit": 5,
		}

		reqBody, _ := json.Marshal(searchReq)
		request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")

		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		results := response["results"].([]any)
		assert.GreaterOrEqual(t, len(results), 1)
		assert.Equal(t, "hello", response["query"])

		// Check result structure
		if len(results) > 0 {
			result := results[0].(map[string]any)
			assert.NotEmpty(t, result["pk"])
			assert.NotEmpty(t, result["sk"])
			assert.NotEmpty(t, result["source_word"])
			assert.NotEmpty(t, result["target_word"])
		}
	})

	t.Run("SearchVocabulary with language filters", func(t *testing.T) {
		searchReq := map[string]any{
			"query":       "hello",
			"limit":       5,
			"source_lang": "en",
			"target_lang": "es",
		}

		reqBody, _ := json.Marshal(searchReq)
		request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")

		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		results := response["results"].([]any)
		// Verify language filtering worked
		for _, resultInterface := range results {
			result := resultInterface.(map[string]any)
			assert.Equal(t, "en", result["source_language"])
			assert.Equal(t, "es", result["target_language"])
		}
	})

	t.Run("SearchVocabulary validation errors", func(t *testing.T) {
		testCases := []struct {
			request     map[string]any
			description string
		}{
			{map[string]any{}, "empty query"},
			{map[string]any{"query": ""}, "empty query string"},
		}

		for _, tc := range testCases {
			t.Run(tc.description, func(t *testing.T) {
				reqBody, _ := json.Marshal(tc.request)
				request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
				request.Header.Set("Content-Type", "application/json")

				recorder := httptest.NewRecorder()
				server.ServeHTTP(recorder, request)

				assert.Equal(t, http.StatusBadRequest, recorder.Code)
			})
		}
	})
}

// Test error handling scenarios
func testSearchErrorHandling(t *testing.T, server *gin.Engine) {
	t.Run("invalid JSON request", func(t *testing.T) {
		request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer([]byte("invalid json")))
		request.Header.Set("Content-Type", "application/json")

		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusBadRequest, recorder.Code)
	})

	t.Run("missing content type", func(t *testing.T) {
		searchReq := map[string]any{
			"query": "hello",
		}

		reqBody, _ := json.Marshal(searchReq)
		request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
		// Intentionally not setting Content-Type header

		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		// Should still work but might behave differently
		// This tests the robustness of the endpoint
	})

	t.Run("service timeout simulation", func(t *testing.T) {
		// This would typically test timeout scenarios
		// For now, we'll test with a complex query that exercises the search logic
		searchReq := map[string]any{
			"query":       "nonexistent_word_that_should_return_empty",
			"limit":       10,
			"source_lang": "xx",
			"target_lang": "yy",
		}

		reqBody, _ := json.Marshal(searchReq)
		request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
		request.Header.Set("Content-Type", "application/json")

		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		// Check if results field exists and is not nil
		resultsInterface, exists := response["results"]
		if !exists || resultsInterface == nil {
			// If results is nil or doesn't exist, that's fine for empty results
			assert.Equal(t, 0, int(response["count"].(float64)))
			return
		}

		results := resultsInterface.([]any)
		assert.Equal(t, 0, len(results)) // Should return empty results
		assert.Equal(t, 0, int(response["count"].(float64)))
	})
}
