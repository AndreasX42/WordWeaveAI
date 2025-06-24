package services

import (
	"context"
	"errors"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
)

type VocabListService struct {
	vocabListRepo repositories.VocabListRepository
	vocabRepo     repositories.VocabRepository
}

// Request/Response types
type CreateListRequest struct {
	UserID      string
	Name        string
	Description string
}

type UpdateListRequest struct {
	UserID      string
	ListID      string
	Name        string
	Description string
}

type AddWordToListRequest struct {
	UserID  string
	ListID  string
	VocabPK string
	VocabSK string
}

type UpdateWordStatusRequest struct {
	UserID    string
	ListID    string
	VocabPK   string
	VocabSK   string
	IsLearned bool
}

// Enhanced response type that includes vocabulary data
type VocabListWordWithData struct {
	// Learning metadata from vocab list
	ListID    string
	UserID    string
	VocabPK   string
	VocabSK   string
	AddedAt   time.Time
	LearnedAt *time.Time
	IsLearned bool

	// Vocabulary data from vocab table
	VocabWord *entities.VocabWord
}

func NewVocabListService(vocabListRepo repositories.VocabListRepository, vocabRepo repositories.VocabRepository) *VocabListService {
	return &VocabListService{
		vocabListRepo: vocabListRepo,
		vocabRepo:     vocabRepo,
	}
}

// List management operations
func (s *VocabListService) CreateList(ctx context.Context, req CreateListRequest) (*entities.VocabList, error) {
	list := entities.NewVocabList(req.UserID, req.Name, req.Description)
	err := s.vocabListRepo.CreateList(ctx, list)
	if err != nil {
		return nil, err
	}

	return list, nil
}

func (s *VocabListService) GetListsByUser(ctx context.Context, userID string) ([]*entities.VocabList, error) {
	return s.vocabListRepo.GetListsByUserID(ctx, userID)
}

func (s *VocabListService) GetList(ctx context.Context, userID, listID string) (*entities.VocabList, error) {
	return s.vocabListRepo.GetListByID(ctx, userID, listID)
}

func (s *VocabListService) UpdateList(ctx context.Context, req UpdateListRequest) (*entities.VocabList, error) {
	// First get the existing list to ensure it belongs to the user
	list, err := s.vocabListRepo.GetListByID(ctx, req.UserID, req.ListID)
	if err != nil {
		return nil, err
	}

	// Update the fields
	if req.Name != "" {
		list.Name = req.Name
	}
	if req.Description != "" {
		list.Description = req.Description
	}

	err = s.vocabListRepo.UpdateList(ctx, list)
	if err != nil {
		return nil, err
	}

	return list, nil
}

func (s *VocabListService) DeleteList(ctx context.Context, userID, listID string) error {
	// Verify list exists and belongs to user
	_, err := s.vocabListRepo.GetListByID(ctx, userID, listID)
	if err != nil {
		return err
	}

	return s.vocabListRepo.DeleteList(ctx, userID, listID)
}

// Word management operations
func (s *VocabListService) AddWordToList(ctx context.Context, req AddWordToListRequest) error {
	// Verify list exists and belongs to user
	_, err := s.vocabListRepo.GetListByID(ctx, req.UserID, req.ListID)
	if err != nil {
		return err
	}

	// Check if word already exists in the list
	exists, err := s.vocabListRepo.WordExistsInList(ctx, req.UserID, req.ListID, req.VocabPK, req.VocabSK)
	if err != nil {
		return err
	}
	if exists {
		return errors.New("word already exists in this list")
	}

	// Create the word entry
	word := entities.NewVocabListWord(
		req.ListID,
		req.UserID,
		req.VocabPK,
		req.VocabSK,
	)

	return s.vocabListRepo.AddWordToList(ctx, word)
}

func (s *VocabListService) RemoveWordFromList(ctx context.Context, userID, listID, vocabPK, vocabSK string) error {
	// Verify list exists and belongs to user
	_, err := s.vocabListRepo.GetListByID(ctx, userID, listID)
	if err != nil {
		return err
	}

	return s.vocabListRepo.RemoveWordFromList(ctx, userID, listID, vocabPK, vocabSK)
}

// GetWordsInList retrieves all words in a vocabulary list (basic version - just references)
func (s *VocabListService) GetWordsInList(ctx context.Context, userID, listID string) ([]*entities.VocabListWord, error) {
	// Verify list exists and belongs to user
	_, err := s.vocabListRepo.GetListByID(ctx, userID, listID)
	if err != nil {
		return nil, err
	}

	return s.vocabListRepo.GetWordsInList(ctx, userID, listID)
}

// GetWordsInListWithData retrieves all words in a vocabulary list with full vocabulary data
func (s *VocabListService) GetWordsInListWithData(ctx context.Context, userID, listID string) ([]*VocabListWordWithData, error) {
	// Verify list exists and belongs to user
	_, err := s.vocabListRepo.GetListByID(ctx, userID, listID)
	if err != nil {
		return nil, err
	}

	// Get the word references from the list
	listWords, err := s.vocabListRepo.GetWordsInList(ctx, userID, listID)
	if err != nil {
		return nil, err
	}

	if len(listWords) == 0 {
		return []*VocabListWordWithData{}, nil
	}

	// Prepare vocabulary keys for batch lookup
	vocabKeys := make([]entities.VocabKey, len(listWords))
	for i, word := range listWords {
		vocabKeys[i] = entities.VocabKey{
			PK: word.VocabPK,
			SK: word.VocabSK,
		}
	}

	// Batch fetch vocabulary data
	vocabData, err := s.vocabRepo.GetByKeysBatch(ctx, vocabKeys)
	if err != nil {
		return nil, err
	}

	// Combine list metadata with vocabulary data
	result := make([]*VocabListWordWithData, 0, len(listWords))
	for _, listWord := range listWords {
		keyStr := listWord.VocabPK + "|" + listWord.VocabSK
		vocabWord := vocabData[keyStr]

		// Create combined response (even if vocabulary data is missing)
		wordWithData := &VocabListWordWithData{
			ListID:    listWord.ListID,
			UserID:    listWord.UserID,
			VocabPK:   listWord.VocabPK,
			VocabSK:   listWord.VocabSK,
			AddedAt:   listWord.AddedAt,
			LearnedAt: listWord.LearnedAt,
			IsLearned: listWord.IsLearned,
			VocabWord: vocabWord,
		}

		result = append(result, wordWithData)
	}

	return result, nil
}

func (s *VocabListService) UpdateWordStatus(ctx context.Context, req UpdateWordStatusRequest) error {
	// Verify list exists and belongs to user
	_, err := s.vocabListRepo.GetListByID(ctx, req.UserID, req.ListID)
	if err != nil {
		return err
	}

	// Get the word to update
	words, err := s.vocabListRepo.GetWordsInList(ctx, req.UserID, req.ListID)
	if err != nil {
		return err
	}

	var wordToUpdate *entities.VocabListWord
	for _, word := range words {
		if word.VocabPK == req.VocabPK && word.VocabSK == req.VocabSK {
			wordToUpdate = word
			break
		}
	}

	if wordToUpdate == nil {
		return errors.New("word not found in list")
	}

	// Update the learned status
	if req.IsLearned {
		wordToUpdate.MarkAsLearned()
	} else {
		wordToUpdate.MarkAsNotLearned()
	}

	return s.vocabListRepo.UpdateWordInList(ctx, wordToUpdate)
}
