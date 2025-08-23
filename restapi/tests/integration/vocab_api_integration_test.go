package integration

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/handlers"
	"github.com/AndreasX42/restapi/middlewares"
	"github.com/AndreasX42/restapi/tests/mocks"
	"github.com/gin-gonic/gin"
)

func TestVocabAPI_Integration(t *testing.T) {
	// Setup environment for JWT
	os.Setenv("JWT_SECRET_KEY", "test-secret-key-for-vocab-tests")
	os.Setenv("JWT_EXPIRATION_TIME", "60")

	t.Run("complete vocabulary workflow", func(t *testing.T) {
		server, userToken := setupVocabTestServer(t)

		// 1. Test vocabulary search (public endpoint)
		testVocabularySearch(t, server)

		// 2. Test vocabulary list management
		listID := testCreateVocabList(t, server, userToken)
		testGetVocabLists(t, server, userToken, 1)
		testGetVocabList(t, server, userToken, listID)
		testUpdateVocabList(t, server, userToken, listID)

		// 3. Test word management in lists
		testAddWordToList(t, server, userToken, listID)
		testGetWordsInList(t, server, userToken, listID, 1)
		testUpdateWordStatus(t, server, userToken, listID)
		testRemoveWordFromList(t, server, userToken, listID)

		// 4. Test list deletion
		testDeleteVocabList(t, server, userToken, listID)
		testGetVocabLists(t, server, userToken, 0)
	})

	t.Run("vocabulary search validation", func(t *testing.T) {
		server, _ := setupVocabTestServer(t)

		// Test empty query
		testSearchValidationError(t, server, map[string]any{}, "Field Query failed on the 'required' rule")

		// Test invalid request body
		testSearchInvalidBody(t, server)
	})

	t.Run("vocabulary list validation errors", func(t *testing.T) {
		server, userToken := setupVocabTestServer(t)

		// Test create list validation
		testCreateListValidationError(t, server, userToken, map[string]string{}, "Field Name failed on the 'required' rule")
		testCreateListValidationError(t, server, userToken, map[string]string{"name": ""}, "Field Name failed on the 'required' rule")
		testCreateListValidationError(t, server, userToken, map[string]string{"name": strings.Repeat("a", 201)}, "Field Name failed on the 'max' rule")
		testCreateListValidationError(t, server, userToken, map[string]string{"name": "test", "description": strings.Repeat("a", 501)}, "Field Description failed on the 'max' rule")

		// Test update list validation
		listID := testCreateVocabList(t, server, userToken)
		testUpdateListValidationError(t, server, userToken, listID, map[string]string{"name": strings.Repeat("a", 201)}, "Field Name failed on the 'max' rule")
	})

	t.Run("word management validation errors", func(t *testing.T) {
		server, userToken := setupVocabTestServer(t)
		listID := testCreateVocabList(t, server, userToken)

		// Test add word validation
		testAddWordValidationError(t, server, userToken, listID, map[string]string{}, "Field VocabPK failed on the 'required' rule")
		testAddWordValidationError(t, server, userToken, listID, map[string]string{"vocab_pk": "test"}, "Field VocabSK failed on the 'required' rule")

	})

	t.Run("unauthorized access", func(t *testing.T) {
		server, _ := setupVocabTestServer(t)

		// Test all protected endpoints without token
		testUnauthorizedAccess(t, server)

		// Test with invalid token
		testInvalidTokenAccess(t, server)
	})

	t.Run("not found errors", func(t *testing.T) {
		server, userToken := setupVocabTestServer(t)

		// Test get non-existent list
		testGetNonExistentList(t, server, userToken)

		// Test update non-existent list
		testUpdateNonExistentList(t, server, userToken)

		// Test delete non-existent list
		testDeleteNonExistentList(t, server, userToken)

		// Test operations on non-existent words
		listID := testCreateVocabList(t, server, userToken)
		testOperationsOnNonExistentWords(t, server, userToken, listID)
	})

	t.Run("duplicate operations", func(t *testing.T) {
		server, userToken := setupVocabTestServer(t)
		listID := testCreateVocabList(t, server, userToken)

		// Add word twice
		testAddWordToList(t, server, userToken, listID)
		testAddWordDuplicate(t, server, userToken, listID)
	})
}

func setupVocabTestServer(t *testing.T) (*gin.Engine, string) {
	gin.SetMode(gin.TestMode)

	// Create mock repositories
	userRepo := mocks.NewMockUserRepository()
	vocabRepo := mocks.NewMockVocabRepository()
	vocabListRepo := mocks.NewMockVocabListRepository()
	vocabMediaRepo := mocks.NewMockVocabMediaRepository()
	emailService := mocks.NewMockEmailService()

	// Add test vocabulary data
	setupTestVocabularyData(vocabRepo.(*mocks.MockVocabRepository))

	// Create services
	userService := services.NewUserService(userRepo, emailService)
	// Create service with mock repository
	vocabService := services.NewVocabService(vocabRepo, nil) // Pass nil for media repository in tests
	vocabListService := services.NewVocabListService(vocabListRepo, vocabRepo, vocabMediaRepo)

	// Create JWT middleware for testing
	authMiddleware, err := middlewares.JWTMiddleware(userService)
	if err != nil {
		t.Fatalf("Failed to setup JWT middleware: %v", err)
	}

	// Create handlers
	userHandler := handlers.NewUserHandler(userService, authMiddleware)
	searchHandler := handlers.NewSearchHandler(vocabService)
	vocabListHandler := handlers.NewVocabListHandler(vocabListService)

	// Setup router
	router := gin.New()

	// Public routes
	router.POST("/search", searchHandler.SearchVocabulary)
	router.POST("/users/register", userHandler.Register)
	router.POST("/users/confirm-email", userHandler.ConfirmEmail)

	// JWT routes
	router.POST("/auth/login", authMiddleware.LoginHandler)

	// Authenticated routes
	authenticated := router.Group("/")
	authenticated.Use(authMiddleware.MiddlewareFunc())
	{
		// Vocabulary list routes
		vocabRoutes := authenticated.Group("/vocabs")
		{
			// List management
			vocabRoutes.POST("/", vocabListHandler.CreateList)
			vocabRoutes.GET("/", vocabListHandler.GetLists)
			vocabRoutes.GET("/:listId", vocabListHandler.GetList)
			vocabRoutes.PUT("/:listId", vocabListHandler.UpdateList)
			vocabRoutes.DELETE("/:listId", vocabListHandler.DeleteList)

			// Word management within lists
			vocabRoutes.POST("/:listId/words", vocabListHandler.AddWordToList)
			vocabRoutes.GET("/:listId/words", vocabListHandler.GetWordsInList)
			vocabRoutes.DELETE("/:listId/words", vocabListHandler.RemoveWordFromList)
			vocabRoutes.PUT("/:listId/words", vocabListHandler.UpdateWordStatus)
		}
	}

	// Create and confirm a test user, then get login token
	token := setupTestUserAndGetToken(t, router, userRepo)

	return router, token
}

func setupTestVocabularyData(vocabRepo *mocks.MockVocabRepository) {
	testWords := []*entities.VocabWord{
		{
			SourceWord:       "hello",
			SourceLanguage:   "en",
			SourceDefinition: []string{"A greeting"},
			TargetWord:       "hola",
			TargetLanguage:   "es",
			Examples: []map[string]string{
				{"source": "Hello world", "target": "Hola mundo"},
			},
			Synonyms:       []map[string]string{{"synonym": "hi", "explanation": "informal greeting"}, {"synonym": "greetings", "explanation": "formal greeting"}},
			Media:          map[string]any{"image": "hello.jpg"},
			Pronunciations: map[string]string{"audio": "hello.mp3"},
			EnglishWord:    "hello",
		},
		{
			SourceWord:       "goodbye",
			SourceLanguage:   "en",
			SourceDefinition: []string{"A farewell"},
			TargetWord:       "adiós",
			TargetLanguage:   "es",
			Examples: []map[string]string{
				{"source": "Goodbye friend", "target": "Adiós amigo"},
			},
			Synonyms:       []map[string]string{{"synonym": "bye", "explanation": "informal farewell"}, {"synonym": "farewell", "explanation": "formal departure"}},
			Media:          map[string]any{"image": "goodbye.jpg"},
			Pronunciations: map[string]string{"audio": "goodbye.mp3"},
			EnglishWord:    "goodbye",
		},
		{
			SourceWord:       "house",
			SourceLanguage:   "en",
			SourceDefinition: []string{"A building for living"},
			TargetWord:       "casa",
			TargetLanguage:   "es",
			Examples: []map[string]string{
				{"source": "My house", "target": "Mi casa"},
			},
			Synonyms:       []map[string]string{{"synonym": "home", "explanation": "place of residence"}, {"synonym": "dwelling", "explanation": "place to live"}},
			Media:          map[string]any{"image": "house.jpg"},
			Pronunciations: map[string]string{"audio": "house.mp3"},
			EnglishWord:    "house",
		},
	}

	for i, word := range testWords {
		pk := fmt.Sprintf("SRC#en#%s", word.SourceWord)
		sk := fmt.Sprintf("TGT#es#%d", i)
		vocabRepo.AddTestWord(pk, sk, word)
	}
}

func setupTestUserAndGetToken(t *testing.T, server *gin.Engine, userRepo repositories.UserRepository) string {
	// Register user
	registerReq := map[string]string{
		"email":    "vocabtest@example.com",
		"username": "vocabuser",
		"password": "password123",
	}

	reqBody, _ := json.Marshal(registerReq)
	request := httptest.NewRequest(http.MethodPost, "/users/register", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Failed to register user: %d - %s", recorder.Code, recorder.Body.String())
	}

	// Confirm email (get confirmation code from user repository)
	user, _ := userRepo.GetByEmail(request.Context(), "vocabtest@example.com")
	confirmReq := map[string]string{
		"email": "vocabtest@example.com",
		"code":  user.ConfirmationCode,
	}

	reqBody, _ = json.Marshal(confirmReq)
	request = httptest.NewRequest(http.MethodPost, "/users/confirm-email", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	recorder = httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Failed to confirm email: %d - %s", recorder.Code, recorder.Body.String())
	}

	// Login to get token
	loginReq := map[string]string{
		"email":    "vocabtest@example.com",
		"password": "password123",
	}

	reqBody, _ = json.Marshal(loginReq)
	request = httptest.NewRequest(http.MethodPost, "/auth/login", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	recorder = httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Failed to login: %d - %s", recorder.Code, recorder.Body.String())
	}

	var loginResponse map[string]any
	json.Unmarshal(recorder.Body.Bytes(), &loginResponse)
	return loginResponse["token"].(string)
}

// Vocabulary search tests
func testVocabularySearch(t *testing.T, server *gin.Engine) {
	searchReq := map[string]any{
		"query": "hello",
		"limit": 5,
	}

	reqBody, _ := json.Marshal(searchReq)
	request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse search response: %v", err)
	}

	results := response["results"].([]any)
	if len(results) == 0 {
		t.Error("Expected search results, got none")
	}

	count := int(response["count"].(float64))
	if count != len(results) {
		t.Errorf("Expected count %d to match results length %d", count, len(results))
	}

	query := response["query"].(string)
	if query != "hello" {
		t.Errorf("Expected query 'hello', got '%s'", query)
	}
}

func testSearchValidationError(t *testing.T, server *gin.Engine, req map[string]any, expectedError string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), expectedError) {
		t.Errorf("Expected error containing '%s', got: %s", expectedError, recorder.Body.String())
	}
}

func testSearchInvalidBody(t *testing.T, server *gin.Engine) {
	request := httptest.NewRequest(http.MethodPost, "/search", bytes.NewBuffer([]byte("invalid json")))
	request.Header.Set("Content-Type", "application/json")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

// Vocabulary list management tests
func testCreateVocabList(t *testing.T, server *gin.Engine, token string) string {
	createReq := map[string]string{
		"name":        "My Test List",
		"description": "A test vocabulary list",
	}

	reqBody, _ := json.Marshal(createReq)
	request := httptest.NewRequest(http.MethodPost, "/vocabs/", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusCreated {
		t.Fatalf("Expected status 201, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse create list response: %v", err)
	}

	if response["message"] != "List created successfully" {
		t.Errorf("Expected success message, got: %v", response["message"])
	}

	data := response["data"].(map[string]any)
	listID := data["id"].(string)
	if listID == "" {
		t.Error("Expected list ID in response")
	}

	if data["name"] != createReq["name"] {
		t.Errorf("Expected name '%s', got '%v'", createReq["name"], data["name"])
	}

	if data["description"] != createReq["description"] {
		t.Errorf("Expected description '%s', got '%v'", createReq["description"], data["description"])
	}

	return listID
}

func testGetVocabLists(t *testing.T, server *gin.Engine, token string, expectedCount int) {
	request := httptest.NewRequest(http.MethodGet, "/vocabs/", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse get lists response: %v", err)
	}

	count := int(response["count"].(float64))
	if count != expectedCount {
		t.Errorf("Expected %d lists, got %d", expectedCount, count)
	}

	data := response["data"].([]any)
	if len(data) != expectedCount {
		t.Errorf("Expected %d lists in data, got %d", expectedCount, len(data))
	}
}

func testGetVocabList(t *testing.T, server *gin.Engine, token, listID string) {
	request := httptest.NewRequest(http.MethodGet, "/vocabs/"+listID, nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse get list response: %v", err)
	}

	data := response["data"].(map[string]any)
	if data["id"] != listID {
		t.Errorf("Expected list ID '%s', got '%v'", listID, data["id"])
	}
}

func testUpdateVocabList(t *testing.T, server *gin.Engine, token, listID string) {
	updateReq := map[string]string{
		"name":        "Updated Test List",
		"description": "An updated test vocabulary list",
	}

	reqBody, _ := json.Marshal(updateReq)
	request := httptest.NewRequest(http.MethodPut, "/vocabs/"+listID, bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse update list response: %v", err)
	}

	data := response["data"].(map[string]any)
	if data["name"] != updateReq["name"] {
		t.Errorf("Expected updated name '%s', got '%v'", updateReq["name"], data["name"])
	}
}

func testDeleteVocabList(t *testing.T, server *gin.Engine, token, listID string) {
	request := httptest.NewRequest(http.MethodDelete, "/vocabs/"+listID, nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse delete list response: %v", err)
	}

	if response["message"] != "List deleted successfully" {
		t.Errorf("Expected success message, got: %v", response["message"])
	}
}

// Word management tests
func testAddWordToList(t *testing.T, server *gin.Engine, token, listID string) {
	addWordReq := map[string]string{
		"vocab_pk": "SRC#en#hello",
		"vocab_sk": "TGT#es#0",
	}

	reqBody, _ := json.Marshal(addWordReq)
	request := httptest.NewRequest(http.MethodPost, "/vocabs/"+listID+"/words", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusCreated {
		t.Fatalf("Expected status 201, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse add word response: %v", err)
	}

	if response["message"] != "Word added to list successfully" {
		t.Errorf("Expected success message, got: %v", response["message"])
	}
}

func testGetWordsInList(t *testing.T, server *gin.Engine, token, listID string, expectedCount int) {
	request := httptest.NewRequest(http.MethodGet, "/vocabs/"+listID+"/words", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse get words response: %v", err)
	}

	count := int(response["count"].(float64))
	if count != expectedCount {
		t.Errorf("Expected %d words, got %d", expectedCount, count)
	}

	data := response["data"].([]any)
	if len(data) != expectedCount {
		t.Errorf("Expected %d words in data, got %d", expectedCount, len(data))
	}

	// Check word data structure
	if expectedCount > 0 {
		word := data[0].(map[string]any)
		if word["vocab_pk"] == nil {
			t.Error("Expected vocab_pk in word data")
		}
		if word["vocab_sk"] == nil {
			t.Error("Expected vocab_sk in word data")
		}
		if word["is_learned"] == nil {
			t.Error("Expected is_learned in word data")
		}
	}
}

func testUpdateWordStatus(t *testing.T, server *gin.Engine, token, listID string) {
	updateReq := map[string]bool{
		"is_learned": true,
	}

	reqBody, _ := json.Marshal(updateReq)
	request := httptest.NewRequest(http.MethodPut, "/vocabs/"+listID+"/words?vocab_pk=SRC%23en%23hello&vocab_sk=TGT%23es%230", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse update word status response: %v", err)
	}

	if response["message"] != "Word status updated successfully" {
		t.Errorf("Expected success message, got: %v", response["message"])
	}
}

func testRemoveWordFromList(t *testing.T, server *gin.Engine, token, listID string) {
	request := httptest.NewRequest(http.MethodDelete, "/vocabs/"+listID+"/words?vocab_pk=SRC%23en%23hello&vocab_sk=TGT%23es%230", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("Expected status 200, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	var response map[string]any
	err := json.Unmarshal(recorder.Body.Bytes(), &response)
	if err != nil {
		t.Fatalf("Failed to parse remove word response: %v", err)
	}

	if response["message"] != "Word removed from list successfully" {
		t.Errorf("Expected success message, got: %v", response["message"])
	}
}

// Validation error tests
func testCreateListValidationError(t *testing.T, server *gin.Engine, token string, req map[string]string, expectedError string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/vocabs/", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), expectedError) {
		t.Errorf("Expected error containing '%s', got: %s", expectedError, recorder.Body.String())
	}
}

func testUpdateListValidationError(t *testing.T, server *gin.Engine, token, listID string, req map[string]string, expectedError string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPut, "/vocabs/"+listID, bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), expectedError) {
		t.Errorf("Expected error containing '%s', got: %s", expectedError, recorder.Body.String())
	}
}

func testAddWordValidationError(t *testing.T, server *gin.Engine, token, listID string, req map[string]string, expectedError string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPost, "/vocabs/"+listID+"/words", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), expectedError) {
		t.Errorf("Expected error containing '%s', got: %s", expectedError, recorder.Body.String())
	}
}

func testUpdateWordStatusValidationError(t *testing.T, server *gin.Engine, token, listID string, req map[string]any, expectedError string) {
	reqBody, _ := json.Marshal(req)
	request := httptest.NewRequest(http.MethodPut, "/vocabs/"+listID+"/words?vocab_pk=test&vocab_sk=test", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), expectedError) {
		t.Errorf("Expected error containing '%s', got: %s", expectedError, recorder.Body.String())
	}
}

// Authorization tests
func testUnauthorizedAccess(t *testing.T, server *gin.Engine) {
	endpoints := []struct {
		method string
		path   string
	}{
		{http.MethodPost, "/vocabs/"},
		{http.MethodGet, "/vocabs/"},
		{http.MethodGet, "/vocabs/test123"},
		{http.MethodPut, "/vocabs/test123"},
		{http.MethodDelete, "/vocabs/test123"},
		{http.MethodPost, "/vocabs/test123/words"},
		{http.MethodGet, "/vocabs/test123/words"},
		{http.MethodDelete, "/vocabs/test123/words"},
		{http.MethodPut, "/vocabs/test123/words"},
	}

	for _, endpoint := range endpoints {
		request := httptest.NewRequest(endpoint.method, endpoint.path, nil)
		recorder := httptest.NewRecorder()
		server.ServeHTTP(recorder, request)

		if recorder.Code != http.StatusUnauthorized {
			t.Errorf("Expected status 401 for %s %s, got %d", endpoint.method, endpoint.path, recorder.Code)
		}
	}
}

func testInvalidTokenAccess(t *testing.T, server *gin.Engine) {
	request := httptest.NewRequest(http.MethodGet, "/vocabs/", nil)
	request.Header.Set("Authorization", "Bearer invalid-token")

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401 for invalid token, got %d", recorder.Code)
	}
}

// Not found tests
func testGetNonExistentList(t *testing.T, server *gin.Engine, token string) {
	request := httptest.NewRequest(http.MethodGet, "/vocabs/nonexistent", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testUpdateNonExistentList(t *testing.T, server *gin.Engine, token string) {
	updateReq := map[string]string{"name": "test"}
	reqBody, _ := json.Marshal(updateReq)

	request := httptest.NewRequest(http.MethodPut, "/vocabs/nonexistent", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testDeleteNonExistentList(t *testing.T, server *gin.Engine, token string) {
	request := httptest.NewRequest(http.MethodDelete, "/vocabs/nonexistent", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}
}

func testOperationsOnNonExistentWords(t *testing.T, server *gin.Engine, token, listID string) {
	// Test get words in non-existent list
	request := httptest.NewRequest(http.MethodGet, "/vocabs/nonexistent/words", nil)
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusNotFound {
		t.Errorf("Expected status 404 for get words in non-existent list, got %d", recorder.Code)
	}

	// Test add word to non-existent list
	addReq := map[string]string{"vocab_pk": "test", "vocab_sk": "test"}
	reqBody, _ := json.Marshal(addReq)

	request = httptest.NewRequest(http.MethodPost, "/vocabs/nonexistent/words", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder = httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for add word to non-existent list, got %d", recorder.Code)
	}
}

// Duplicate operation tests
func testAddWordDuplicate(t *testing.T, server *gin.Engine, token, listID string) {
	addWordReq := map[string]string{
		"vocab_pk": "SRC#en#hello",
		"vocab_sk": "TGT#es#0",
	}

	reqBody, _ := json.Marshal(addWordReq)
	request := httptest.NewRequest(http.MethodPost, "/vocabs/"+listID+"/words", bytes.NewBuffer(reqBody))
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)

	recorder := httptest.NewRecorder()
	server.ServeHTTP(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for duplicate word, got %d. Body: %s", recorder.Code, recorder.Body.String())
	}

	if !strings.Contains(recorder.Body.String(), "already exists") {
		t.Errorf("Expected error about word already existing, got: %s", recorder.Body.String())
	}
}
