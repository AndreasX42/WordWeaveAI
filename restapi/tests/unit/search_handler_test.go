package unit

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/handlers"
	"github.com/AndreasX42/restapi/tests/mocks"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupSearchHandler() (*handlers.SearchHandler, *mocks.MockVocabRepository, *mocks.MockVocabMediaRepository) {
	gin.SetMode(gin.TestMode)

	// Create mocks
	vocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)
	mediaRepo := mocks.NewMockVocabMediaRepository()

	// Add test vocabulary data
	vocabRepo.AddTestWord("SRC#en#hello", "TGT#es#POS#noun", &entities.VocabWord{
		PK:               "SRC#en#hello",
		SK:               "TGT#es#POS#noun",
		SourceWord:       "hello",
		SourceLanguage:   "en",
		SourcePos:        "noun",
		SourceDefinition: []string{"A greeting"},
		TargetWord:       "hola",
		TargetLanguage:   "es",
		Examples:         []map[string]string{{"source": "Hello world", "target": "Hola mundo"}},
		MediaRef:         "hello_media_ref",
		EnglishWord:      "hello",
	})

	vocabRepo.AddTestWord("SRC#en#house", "TGT#es#POS#noun", &entities.VocabWord{
		PK:               "SRC#en#house",
		SK:               "TGT#es#POS#noun",
		SourceWord:       "house",
		SourceLanguage:   "en",
		SourcePos:        "noun",
		SourceDefinition: []string{"A building for living"},
		TargetWord:       "casa",
		TargetLanguage:   "es",
		Examples:         []map[string]string{{"source": "My house", "target": "Mi casa"}},
		MediaRef:         "house_media_ref",
		EnglishWord:      "house",
	})

	// Add test media data
	mediaRepo.AddTestMedia("hello_media_ref", map[string]any{
		"image": "hello.jpg",
		"audio": "hello.mp3",
		"type":  "greeting",
	})

	mediaRepo.AddTestMedia("house_media_ref", map[string]any{
		"image": "house.jpg",
		"audio": "house.mp3",
		"type":  "noun",
	})

	// Create service and handler
	vocabService := services.NewVocabService(vocabRepo, mediaRepo)
	searchHandler := handlers.NewSearchHandler(vocabService)

	return searchHandler, vocabRepo, mediaRepo
}

func TestSearchHandler_GetVocabularyByPkSk(t *testing.T) {
	searchHandler, _, _ := setupSearchHandler()

	t.Run("successful PK/SK lookup without media", func(t *testing.T) {
		// Setup Gin context
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab", searchHandler.GetVocabularyByPkSk)

		// Make request
		req := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23hello&sk=TGT%23es%23POS%23noun", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "SRC#en#hello", response.PK)
		assert.Equal(t, "TGT#es#POS#noun", response.SK)
		assert.Equal(t, "hello", response.SourceWord)
		assert.Equal(t, "hola", response.TargetWord)
		assert.NotEmpty(t, response.Media) // Should have media data
	})

	t.Run("successful PK/SK lookup with media_ref parameter", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab", searchHandler.GetVocabularyByPkSk)

		// Make request with media_ref parameter
		req := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23hello&sk=TGT%23es%23POS%23noun&media_ref=hello_media_ref", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "SRC#en#hello", response.PK)
		assert.Equal(t, "TGT#es#POS#noun", response.SK)
		assert.Equal(t, "hello", response.SourceWord)
		assert.Equal(t, "hola", response.TargetWord)

		// Should have media data from both vocab and media service
		assert.NotEmpty(t, response.Media)
		assert.Equal(t, "hello.jpg", response.Media["image"])
		assert.Equal(t, "hello.mp3", response.Media["audio"])
	})

	t.Run("missing PK parameter", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab", searchHandler.GetVocabularyByPkSk)

		// Make request without PK
		req := httptest.NewRequest(http.MethodGet, "/vocab?sk=TGT%23es%23POS%23noun", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
		assert.Equal(t, http.StatusBadRequest, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "pk and sk are required", response["message"])
	})

	t.Run("missing SK parameter", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab", searchHandler.GetVocabularyByPkSk)

		// Make request without SK
		req := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23hello", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
		assert.Equal(t, http.StatusBadRequest, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "pk and sk are required", response["message"])
	})

	t.Run("vocabulary not found", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab", searchHandler.GetVocabularyByPkSk)

		// Make request for non-existent vocabulary
		req := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23nonexistent&sk=TGT%23es%23POS%23noun", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
		assert.Equal(t, http.StatusNotFound, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Vocabulary not found", response["message"])
		assert.Contains(t, response["details"].(map[string]any)["error"], "vocabulary entry not found")
	})

	t.Run("concurrent vocab and media fetch with media error", func(t *testing.T) {
		// This tests the concurrent fetching logic when media_ref is provided
		// but media service fails (should not fail the entire request)
		searchHandler, _, mediaRepo := setupSearchHandler()

		// Configure media repo to return error
		mediaRepo.SetError(true, "media service unavailable")

		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab", searchHandler.GetVocabularyByPkSk)

		// Make request with media_ref parameter
		req := httptest.NewRequest(http.MethodGet, "/vocab?pk=SRC%23en%23hello&sk=TGT%23es%23POS%23noun&media_ref=hello_media_ref", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Should still succeed even with media error (non-critical)
		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "hello", response.SourceWord)
		// Media should be empty since the media service call was mocked to fail
		assert.Empty(t, response.Media)
	})
}

func TestSearchHandler_GetVocabularyByParams(t *testing.T) {
	searchHandler, _, _ := setupSearchHandler()

	t.Run("successful parameter-based lookup", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab/:sourceLanguage/:targetLanguage/:word/:pos", searchHandler.GetVocabularyByParams)

		// Make request
		req := httptest.NewRequest(http.MethodGet, "/vocab/en/es/hello/noun", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
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

	t.Run("vocabulary not found for parameters", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab/:sourceLanguage/:targetLanguage/:word/:pos", searchHandler.GetVocabularyByParams)

		// Make request for non-existent vocabulary
		req := httptest.NewRequest(http.MethodGet, "/vocab/en/es/nonexistent/noun", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Assertions
		assert.Equal(t, http.StatusNotFound, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "Vocabulary not found", response["message"])
	})

	t.Run("missing required parameters", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab/:sourceLanguage/:targetLanguage/:word/:pos", searchHandler.GetVocabularyByParams)

		// Test cases for missing parameters
		testCases := []struct {
			path           string
			description    string
			expectedStatus int
		}{
			{"/vocab///hello/noun", "missing source and target language", http.StatusBadRequest},
			{"/vocab/en//hello/noun", "missing target language", http.StatusBadRequest},
			{"/vocab/en/es//noun", "missing word", http.StatusBadRequest},
			{"/vocab/en/es/hello/", "missing pos", http.StatusMovedPermanently}, // This one gets a redirect
		}

		for _, tc := range testCases {
			t.Run(tc.description, func(t *testing.T) {
				req := httptest.NewRequest(http.MethodGet, tc.path, nil)
				recorder := httptest.NewRecorder()
				router.ServeHTTP(recorder, req)

				assert.Equal(t, tc.expectedStatus, recorder.Code)
			})
		}
	})

	t.Run("word normalization", func(t *testing.T) {
		// Test that words are properly normalized before lookup
		searchHandler, vocabRepo, _ := setupSearchHandler()

		// Add a word with special characters
		vocabRepo.AddTestWord("SRC#en#cafe", "TGT#es#POS#noun", &entities.VocabWord{
			PK:             "SRC#en#cafe",
			SK:             "TGT#es#POS#noun",
			SourceWord:     "café",
			SourceLanguage: "en",
			SourcePos:      "noun",
			TargetWord:     "café",
			TargetLanguage: "es",
			EnglishWord:    "café",
		})

		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.GET("/vocab/:sourceLanguage/:targetLanguage/:word/:pos", searchHandler.GetVocabularyByParams)

		// Make request with special characters (should be normalized)
		req := httptest.NewRequest(http.MethodGet, "/vocab/en/es/café/noun", nil)
		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		// Should find the word even with special characters
		assert.Equal(t, http.StatusOK, recorder.Code)

		var response entities.VocabWord
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		assert.Equal(t, "café", response.SourceWord)
	})
}

func TestSearchHandler_SearchVocabulary(t *testing.T) {
	// Test the existing search functionality to ensure we didn't break anything
	searchHandler, _, _ := setupSearchHandler()

	t.Run("successful search", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.POST("/search", searchHandler.SearchVocabulary)

		searchReq := map[string]any{
			"query": "hello",
			"limit": 5,
		}

		reqBody, _ := json.Marshal(searchReq)
		req := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
		req.Header.Set("Content-Type", "application/json")

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		results := response["results"].([]any)
		assert.GreaterOrEqual(t, len(results), 1)
		assert.Equal(t, "hello", response["query"])
	})

	t.Run("search with language filters", func(t *testing.T) {
		gin.SetMode(gin.TestMode)
		router := gin.New()
		router.POST("/search", searchHandler.SearchVocabulary)

		searchReq := map[string]any{
			"query":       "hello",
			"limit":       5,
			"source_lang": "en",
			"target_lang": "es",
		}

		reqBody, _ := json.Marshal(searchReq)
		req := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
		req.Header.Set("Content-Type", "application/json")

		recorder := httptest.NewRecorder()
		router.ServeHTTP(recorder, req)

		assert.Equal(t, http.StatusOK, recorder.Code)

		var response map[string]any
		err := json.Unmarshal(recorder.Body.Bytes(), &response)
		require.NoError(t, err)

		results := response["results"].([]any)
		if len(results) > 0 {
			result := results[0].(map[string]any)
			assert.Equal(t, "en", result["source_language"])
			assert.Equal(t, "es", result["target_language"])
		}
	})
}
