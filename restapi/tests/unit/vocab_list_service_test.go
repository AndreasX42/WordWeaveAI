package unit

import (
	"context"
	"fmt"
	"testing"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/AndreasX42/restapi/tests/mocks"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupVocabListService() (*services.VocabListService, *mocks.MockVocabListRepository, *mocks.MockVocabRepository, *mocks.MockVocabMediaRepository) {
	mockVocabListRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
	mockVocabRepo := mocks.NewMockVocabRepository().(*mocks.MockVocabRepository)
	mockVocabMediaRepo := mocks.NewMockVocabMediaRepository()

	// Add some test vocabulary data
	mockVocabRepo.AddTestWord("SRC#en#hello", "TGT#es#hola", &entities.VocabWord{
		SourceWord:       "hello",
		SourceLanguage:   "en",
		SourceDefinition: []string{"A greeting expression"},
		TargetWord:       "hola",
		TargetLanguage:   "es",
		Examples:         []map[string]string{{"en": "Hello, how are you?", "es": "Hola, ¿cómo estás?"}},
		Synonyms:         []map[string]string{{"synonym": "hi", "explanation": "informal greeting"}, {"synonym": "greetings", "explanation": "formal greeting"}},
		EnglishWord:      "hello",
	})

	mockVocabRepo.AddTestWord("SRC#en#bye", "TGT#es#adios", &entities.VocabWord{
		SourceWord:       "bye",
		SourceLanguage:   "en",
		SourceDefinition: []string{"A farewell expression"},
		TargetWord:       "adios",
		TargetLanguage:   "es",
		Examples:         []map[string]string{{"en": "Bye, see you later!", "es": "Adiós, ¡nos vemos luego!"}},
		Synonyms:         []map[string]string{{"synonym": "goodbye", "explanation": "formal farewell"}, {"synonym": "farewell", "explanation": "formal departure"}},
		EnglishWord:      "bye",
	})

	mockVocabRepo.AddTestWord("SRC#en#thankyou", "TGT#es#gracias", &entities.VocabWord{
		SourceWord:       "thank you",
		SourceLanguage:   "en",
		SourceDefinition: []string{"An expression of gratitude"},
		TargetWord:       "gracias",
		TargetLanguage:   "es",
		Examples:         []map[string]string{{"en": "Thank you very much!", "es": "¡Muchas gracias!"}},
		Synonyms:         []map[string]string{{"synonym": "thanks", "explanation": "informal gratitude"}},
		EnglishWord:      "thank you",
	})

	service := services.NewVocabListService(mockVocabListRepo, mockVocabRepo, mockVocabMediaRepo)
	return service, mockVocabListRepo, mockVocabRepo, mockVocabMediaRepo
}

func TestVocabListService_CreateList(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	tests := []struct {
		name    string
		request services.CreateListRequest
		wantErr bool
	}{
		{
			name: "successful list creation",
			request: services.CreateListRequest{
				UserID:      "user123",
				Name:        "Spanish Basics",
				Description: "Basic Spanish vocabulary",
			},
			wantErr: false,
		},
		{
			name: "empty name",
			request: services.CreateListRequest{
				UserID:      "user123",
				Name:        "",
				Description: "No name provided",
			},
			wantErr: false, // Service doesn't validate empty names
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			list, err := service.CreateList(ctx, tt.request)

			if tt.wantErr {
				assert.Error(t, err)
				assert.Nil(t, list)
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, list)
				assert.Equal(t, tt.request.UserID, list.UserID)
				assert.Equal(t, tt.request.Name, list.Name)
				assert.Equal(t, tt.request.Description, list.Description)
				assert.NotEmpty(t, list.ID)
				assert.Equal(t, 0, list.WordCount)
			}
		})
	}
}

func TestVocabListService_GetListsByUser(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"

	// Create some test lists
	list1, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "List 1",
		Description: "First list",
	})
	list2, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "List 2",
		Description: "Second list",
	})

	// Create a list for a different user
	_, _ = service.CreateList(ctx, services.CreateListRequest{
		UserID:      "otheruser",
		Name:        "Other List",
		Description: "Should not appear",
	})

	lists, err := service.GetListsByUser(ctx, userID)

	assert.NoError(t, err)
	assert.Len(t, lists, 2)

	// Check that we got the right lists
	listIDs := []string{lists[0].ID, lists[1].ID}
	assert.Contains(t, listIDs, list1.ID)
	assert.Contains(t, listIDs, list2.ID)
}

func TestVocabListService_GetList(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Test List",
		Description: "Test description",
	})

	tests := []struct {
		name     string
		userID   string
		listID   string
		wantErr  bool
		expected *entities.VocabList
	}{
		{
			name:     "existing list",
			userID:   userID,
			listID:   list.ID,
			wantErr:  false,
			expected: list,
		},
		{
			name:    "non-existent list",
			userID:  userID,
			listID:  "nonexistent",
			wantErr: true,
		},
		{
			name:    "wrong user",
			userID:  "wronguser",
			listID:  list.ID,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := service.GetList(ctx, tt.userID, tt.listID)

			if tt.wantErr {
				assert.Error(t, err)
				assert.Nil(t, result)
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, result)
				assert.Equal(t, tt.expected.ID, result.ID)
				assert.Equal(t, tt.expected.Name, result.Name)
			}
		})
	}
}

func TestVocabListService_UpdateList(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Original Name",
		Description: "Original Description",
	})

	tests := []struct {
		name    string
		request services.UpdateListRequest
		wantErr bool
	}{
		{
			name: "successful update",
			request: services.UpdateListRequest{
				UserID:      userID,
				ListID:      list.ID,
				Name:        "Updated Name",
				Description: "Updated Description",
			},
			wantErr: false,
		},
		{
			name: "non-existent list",
			request: services.UpdateListRequest{
				UserID:      userID,
				ListID:      "nonexistent",
				Name:        "New Name",
				Description: "New Description",
			},
			wantErr: true,
		},
		{
			name: "wrong user",
			request: services.UpdateListRequest{
				UserID:      "wronguser",
				ListID:      list.ID,
				Name:        "Hacked Name",
				Description: "Hacked Description",
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := service.UpdateList(ctx, tt.request)

			if tt.wantErr {
				assert.Error(t, err)
				assert.Nil(t, result)
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, result)
				assert.Equal(t, tt.request.Name, result.Name)
				assert.Equal(t, tt.request.Description, result.Description)
			}
		})
	}
}

func TestVocabListService_DeleteList(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "To Delete",
		Description: "This will be deleted",
	})

	tests := []struct {
		name    string
		userID  string
		listID  string
		wantErr bool
	}{
		{
			name:    "successful deletion",
			userID:  userID,
			listID:  list.ID,
			wantErr: false,
		},
		{
			name:    "non-existent list",
			userID:  userID,
			listID:  "nonexistent",
			wantErr: true,
		},
		{
			name:    "wrong user",
			userID:  "wronguser",
			listID:  list.ID,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := service.DeleteList(ctx, tt.userID, tt.listID)

			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)

				// Verify the list is actually deleted
				_, err := service.GetList(ctx, tt.userID, tt.listID)
				assert.Error(t, err)
			}
		})
	}
}

func TestVocabListService_AddWordToList(t *testing.T) {
	ctx := context.Background()
	service, mockVocabListRepo, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Test List",
		Description: "For testing words",
	})

	tests := []struct {
		name    string
		request services.AddWordToListRequest
		wantErr bool
	}{
		{
			name: "successful word addition",
			request: services.AddWordToListRequest{
				UserID:  userID,
				ListID:  list.ID,
				VocabPK: "SRC#en#hello",
				VocabSK: "TGT#es#hola",
			},
			wantErr: false,
		},
		{
			name: "duplicate word",
			request: services.AddWordToListRequest{
				UserID:  userID,
				ListID:  list.ID,
				VocabPK: "SRC#en#hello", // Same as above
				VocabSK: "TGT#es#hola",  // Same as above
			},
			wantErr: true,
		},
		{
			name: "non-existent list",
			request: services.AddWordToListRequest{
				UserID:  userID,
				ListID:  "nonexistent",
				VocabPK: "SRC#en#bye",
				VocabSK: "TGT#es#adios",
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := service.AddWordToList(ctx, tt.request)

			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)

				// Verify the word was added
				exists, err := mockVocabListRepo.WordExistsInList(ctx, tt.request.UserID, tt.request.ListID, tt.request.VocabPK, tt.request.VocabSK)
				assert.NoError(t, err)
				assert.True(t, exists)
			}
		})
	}
}

func TestVocabListService_GetWordsInList(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Test List",
		Description: "For testing words",
	})

	// Add some words
	_ = service.AddWordToList(ctx, services.AddWordToListRequest{
		UserID:  userID,
		ListID:  list.ID,
		VocabPK: "SRC#en#hello",
		VocabSK: "TGT#es#hola",
	})
	_ = service.AddWordToList(ctx, services.AddWordToListRequest{
		UserID:  userID,
		ListID:  list.ID,
		VocabPK: "SRC#en#bye",
		VocabSK: "TGT#es#adios",
	})

	tests := []struct {
		name          string
		userID        string
		listID        string
		wantErr       bool
		expectedCount int
	}{
		{
			name:          "get words from existing list",
			userID:        userID,
			listID:        list.ID,
			wantErr:       false,
			expectedCount: 2,
		},
		{
			name:          "non-existent list",
			userID:        userID,
			listID:        "nonexistent",
			wantErr:       true,
			expectedCount: 0,
		},
		{
			name:          "wrong user",
			userID:        "wronguser",
			listID:        list.ID,
			wantErr:       true,
			expectedCount: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			words, err := service.GetWordsInListWithData(ctx, tt.userID, tt.listID)

			if tt.wantErr {
				assert.Error(t, err)
				assert.Nil(t, words)
			} else {
				assert.NoError(t, err)
				assert.Len(t, words, tt.expectedCount)

				// Verify vocabulary data is included
				for _, word := range words {
					assert.NotNil(t, word.VocabWord, "Vocabulary data should be included")
					assert.NotEmpty(t, word.VocabWord.SourceWord)
					assert.NotEmpty(t, word.VocabWord.TargetWord)
				}
			}
		})
	}
}

func TestVocabListService_RemoveWordFromList(t *testing.T) {
	ctx := context.Background()
	service, mockVocabListRepo, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Test List",
		Description: "For testing words",
	})

	// Add a word to remove
	vocabPK := "SRC#en#hello"
	vocabSK := "TGT#es#hola"
	_ = service.AddWordToList(ctx, services.AddWordToListRequest{
		UserID:  userID,
		ListID:  list.ID,
		VocabPK: vocabPK,
		VocabSK: vocabSK,
	})

	tests := []struct {
		name    string
		userID  string
		listID  string
		vocabPK string
		vocabSK string
		wantErr bool
	}{
		{
			name:    "successful word removal",
			userID:  userID,
			listID:  list.ID,
			vocabPK: vocabPK,
			vocabSK: vocabSK,
			wantErr: false,
		},
		{
			name:    "non-existent word",
			userID:  userID,
			listID:  list.ID,
			vocabPK: "SRC#en#nonexistent",
			vocabSK: "TGT#es#noexiste",
			wantErr: true,
		},
		{
			name:    "non-existent list",
			userID:  userID,
			listID:  "nonexistent",
			vocabPK: vocabPK,
			vocabSK: vocabSK,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := service.RemoveWordFromList(ctx, tt.userID, tt.listID, tt.vocabPK, tt.vocabSK)

			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)

				// Verify the word was removed
				exists, err := mockVocabListRepo.WordExistsInList(ctx, tt.userID, tt.listID, tt.vocabPK, tt.vocabSK)
				assert.NoError(t, err)
				assert.False(t, exists)
			}
		})
	}
}

func TestVocabListService_UpdateWordStatus(t *testing.T) {
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"
	list, _ := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Test List",
		Description: "For testing words",
	})

	// Add a word to update
	vocabPK := "SRC#en#hello"
	vocabSK := "TGT#es#hola"
	_ = service.AddWordToList(ctx, services.AddWordToListRequest{
		UserID:  userID,
		ListID:  list.ID,
		VocabPK: vocabPK,
		VocabSK: vocabSK,
	})

	tests := []struct {
		name    string
		request services.UpdateWordStatusRequest
		wantErr bool
	}{
		{
			name: "mark word as learned",
			request: services.UpdateWordStatusRequest{
				UserID:    userID,
				ListID:    list.ID,
				VocabPK:   vocabPK,
				VocabSK:   vocabSK,
				IsLearned: true,
			},
			wantErr: false,
		},
		{
			name: "mark word as not learned",
			request: services.UpdateWordStatusRequest{
				UserID:    userID,
				ListID:    list.ID,
				VocabPK:   vocabPK,
				VocabSK:   vocabSK,
				IsLearned: false,
			},
			wantErr: false,
		},
		{
			name: "non-existent word",
			request: services.UpdateWordStatusRequest{
				UserID:    userID,
				ListID:    list.ID,
				VocabPK:   "SRC#en#nonexistent",
				VocabSK:   "TGT#es#noexiste",
				IsLearned: true,
			},
			wantErr: true,
		},
		{
			name: "non-existent list",
			request: services.UpdateWordStatusRequest{
				UserID:    userID,
				ListID:    "nonexistent",
				VocabPK:   vocabPK,
				VocabSK:   vocabSK,
				IsLearned: true,
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := service.UpdateWordStatus(ctx, tt.request)

			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)

				// Verify the status was updated using GetWordsInListWithData
				words, err := service.GetWordsInListWithData(ctx, tt.request.UserID, tt.request.ListID)
				require.NoError(t, err)

				var updatedWord *services.VocabListWordWithData
				for _, word := range words {
					if word.VocabPK == tt.request.VocabPK && word.VocabSK == tt.request.VocabSK {
						updatedWord = word
						break
					}
				}

				require.NotNil(t, updatedWord)
				assert.Equal(t, tt.request.IsLearned, updatedWord.IsLearned)

				if tt.request.IsLearned {
					assert.NotNil(t, updatedWord.LearnedAt)
				} else {
					assert.Nil(t, updatedWord.LearnedAt)
				}
			}
		})
	}
}

func TestVocabListService_Integration(t *testing.T) {
	// Integration test that exercises multiple service methods together
	ctx := context.Background()
	service, _, _, _ := setupVocabListService()

	userID := "user123"

	// Create a list
	list, err := service.CreateList(ctx, services.CreateListRequest{
		UserID:      userID,
		Name:        "Integration Test List",
		Description: "Testing the full workflow",
	})
	require.NoError(t, err)
	require.NotNil(t, list)

	// Add multiple words
	words := []struct {
		vocabPK string
		vocabSK string
	}{
		{"SRC#en#hello", "TGT#es#hola"},
		{"SRC#en#bye", "TGT#es#adios"},
		{"SRC#en#thankyou", "TGT#es#gracias"},
	}

	for _, word := range words {
		err := service.AddWordToList(ctx, services.AddWordToListRequest{
			UserID:  userID,
			ListID:  list.ID,
			VocabPK: word.vocabPK,
			VocabSK: word.vocabSK,
		})
		require.NoError(t, err)
	}

	// Verify words were added with vocabulary data
	wordsInList, err := service.GetWordsInListWithData(ctx, userID, list.ID)
	require.NoError(t, err)
	assert.Len(t, wordsInList, 3)

	// Verify vocabulary data is included
	for _, word := range wordsInList {
		assert.NotNil(t, word.VocabWord, "Vocabulary data should be included")
		assert.NotEmpty(t, word.VocabWord.SourceWord)
		assert.NotEmpty(t, word.VocabWord.TargetWord)
		assert.NotEmpty(t, word.VocabWord.SourceLanguage)
		assert.NotEmpty(t, word.VocabWord.TargetLanguage)
	}

	// Mark one word as learned
	err = service.UpdateWordStatus(ctx, services.UpdateWordStatusRequest{
		UserID:    userID,
		ListID:    list.ID,
		VocabPK:   "SRC#en#hello",
		VocabSK:   "TGT#es#hola",
		IsLearned: true,
	})
	require.NoError(t, err)

	// Remove one word
	err = service.RemoveWordFromList(ctx, userID, list.ID, "SRC#en#bye", "TGT#es#adios")
	require.NoError(t, err)

	// Verify final state
	finalWords, err := service.GetWordsInListWithData(ctx, userID, list.ID)
	require.NoError(t, err)
	assert.Len(t, finalWords, 2)

	// Check that the hello word is learned and the thank you word is not
	learnedCount := 0
	for _, word := range finalWords {
		if word.IsLearned {
			learnedCount++
			assert.Equal(t, "SRC#en#hello", word.VocabPK)
			assert.Equal(t, "TGT#es#hola", word.VocabSK)
			assert.Equal(t, "hello", word.VocabWord.SourceWord)
			assert.Equal(t, "hola", word.VocabWord.TargetWord)
		}
	}
	assert.Equal(t, 1, learnedCount)

	// Update the list metadata
	updatedList, err := service.UpdateList(ctx, services.UpdateListRequest{
		UserID:      userID,
		ListID:      list.ID,
		Name:        "Updated List Name",
		Description: "Updated description",
	})
	require.NoError(t, err)
	assert.Equal(t, "Updated List Name", updatedList.Name)
	assert.Equal(t, "Updated description", updatedList.Description)

	// Delete the list
	err = service.DeleteList(ctx, userID, list.ID)
	require.NoError(t, err)

	// Verify list is deleted
	_, err = service.GetList(ctx, userID, list.ID)
	assert.Error(t, err)
}

func TestVocabListService_CountingIntegration(t *testing.T) {
	ctx := context.Background()

	t.Run("list count updates through service operations", func(t *testing.T) {
		// Setup
		vocabListRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository()
		vocabMediaRepo := mocks.NewMockVocabMediaRepository()
		service := services.NewVocabListService(vocabListRepo, vocabRepo, vocabMediaRepo)

		// Initialize count
		err := vocabListRepo.InitializeListCount(ctx)
		require.NoError(t, err)

		// Verify initial count
		count, err := vocabListRepo.GetTotalListCount(ctx)
		require.NoError(t, err)
		assert.Equal(t, 0, count)

		// Create a list through the service
		userID := "user123"
		req := services.CreateListRequest{
			UserID:      userID,
			Name:        "Test List",
			Description: "A test list",
		}

		list, err := service.CreateList(ctx, req)
		require.NoError(t, err)

		// Verify count increased
		count, err = vocabListRepo.GetTotalListCount(ctx)
		require.NoError(t, err)
		assert.Equal(t, 1, count)

		// Delete the list through the service
		err = service.DeleteList(ctx, userID, list.ID)
		require.NoError(t, err)

		// Verify count decreased
		count, err = vocabListRepo.GetTotalListCount(ctx)
		require.NoError(t, err)
		assert.Equal(t, 0, count)
	})

	t.Run("count tracks multiple lists correctly", func(t *testing.T) {
		// Setup
		vocabListRepo := mocks.NewMockVocabListRepository().(*mocks.MockVocabListRepository)
		vocabRepo := mocks.NewMockVocabRepository()
		vocabMediaRepo := mocks.NewMockVocabMediaRepository()
		service := services.NewVocabListService(vocabListRepo, vocabRepo, vocabMediaRepo)

		vocabListRepo.InitializeListCount(ctx)

		userID := "user123"

		// Create multiple lists
		lists := make([]string, 3) // Store list IDs instead of response objects
		for i := 0; i < 3; i++ {
			req := services.CreateListRequest{
				UserID:      userID,
				Name:        fmt.Sprintf("Test List %d", i),
				Description: fmt.Sprintf("Test list number %d", i),
			}

			list, err := service.CreateList(ctx, req)
			require.NoError(t, err)
			lists[i] = list.ID
		}

		// Verify count is 3
		count, err := vocabListRepo.GetTotalListCount(ctx)
		require.NoError(t, err)
		assert.Equal(t, 3, count)

		// Delete one list
		err = service.DeleteList(ctx, userID, lists[0])
		require.NoError(t, err)

		// Verify count is 2
		count, err = vocabListRepo.GetTotalListCount(ctx)
		require.NoError(t, err)
		assert.Equal(t, 2, count)

		// Delete remaining lists
		for i := 1; i < 3; i++ {
			err = service.DeleteList(ctx, userID, lists[i])
			require.NoError(t, err)
		}

		// Verify count is 0
		count, err = vocabListRepo.GetTotalListCount(ctx)
		require.NoError(t, err)
		assert.Equal(t, 0, count)
	})
}
