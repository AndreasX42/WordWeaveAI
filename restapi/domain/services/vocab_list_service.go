package services

import (
	"context"
	"errors"
	"sync"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
)

type VocabListService struct {
	vocabListRepo  repositories.VocabListRepository
	vocabRepo      repositories.VocabRepository
	vocabMediaRepo repositories.VocabMediaRepository
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
	UserID   string
	ListID   string
	VocabPK  string
	VocabSK  string
	MediaRef string
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
	VocabWord *entities.VocabWord
}

func NewVocabListService(vocabListRepo repositories.VocabListRepository, vocabRepo repositories.VocabRepository, vocabMediaRepo repositories.VocabMediaRepository) *VocabListService {
	return &VocabListService{
		vocabListRepo:  vocabListRepo,
		vocabRepo:      vocabRepo,
		vocabMediaRepo: vocabMediaRepo,
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
	lists, err := s.vocabListRepo.GetListsByUserID(ctx, userID)
	if err != nil {
		return nil, err
	}

	for _, list := range lists {
		learnedCount := 0
		words, err := s.vocabListRepo.GetWordsInList(ctx, userID, list.ID)
		if err != nil {
			continue
		}
		for _, word := range words {
			if word.IsLearned {
				learnedCount++
			}
		}
		list.LearnedCount = learnedCount
	}
	return lists, nil
}

func (s *VocabListService) GetList(ctx context.Context, userID, listID string) (*entities.VocabList, error) {
	return s.vocabListRepo.GetListByID(ctx, userID, listID)
}

func (s *VocabListService) UpdateList(ctx context.Context, req UpdateListRequest) (*entities.VocabList, error) {
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
	return s.vocabListRepo.DeleteList(ctx, userID, listID)
}

// Word management operations
func (s *VocabListService) AddWordToList(ctx context.Context, req AddWordToListRequest) error {
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
		req.MediaRef,
	)

	return s.vocabListRepo.AddWordToList(ctx, word)
}

func (s *VocabListService) RemoveWordFromList(ctx context.Context, userID, listID, vocabPK, vocabSK string) error {
	return s.vocabListRepo.RemoveWordFromList(ctx, userID, listID, vocabPK, vocabSK)
}

// GetWordsInList retrieves all words in a vocabulary list (basic version - just references)
func (s *VocabListService) GetWordsInList(ctx context.Context, userID, listID string) ([]*entities.VocabListWord, error) {
	return s.vocabListRepo.GetWordsInList(ctx, userID, listID)
}

// TODO: Probably not necessary return the full vocab data
// GetWordsInListWithData retrieves all words in a vocabulary list with full vocabulary data
func (s *VocabListService) GetWordsInListWithData(ctx context.Context, userID, listID string) ([]*VocabListWordWithData, error) {
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

	chanWords := make(chan *VocabListWordWithData, len(listWords))
	wg := sync.WaitGroup{}
	wg.Add(len(listWords))

	for _, word := range listWords {
		go func(word *entities.VocabListWord) {
			defer wg.Done()
			keyStr := word.VocabPK + "|" + word.VocabSK
			vocabWord := vocabData[keyStr]

			// If vocabulary word exists and has a MediaRef, fetch the media data
			if vocabWord != nil && vocabWord.MediaRef != "" {
				mediaData, err := s.vocabMediaRepo.GetMediaByRef(ctx, vocabWord.MediaRef)
				if err == nil {
					vocabWord.Media = mediaData
				}
			}

			wordWithData := &VocabListWordWithData{
				ListID:    word.ListID,
				UserID:    word.UserID,
				VocabPK:   word.VocabPK,
				VocabSK:   word.VocabSK,
				AddedAt:   word.AddedAt,
				LearnedAt: word.LearnedAt,
				IsLearned: word.IsLearned,
				VocabWord: vocabWord,
			}

			chanWords <- wordWithData
		}(word)
	}

	go func() {
		wg.Wait()
		close(chanWords)
	}()

	for word := range chanWords {
		result = append(result, word)
	}

	return result, nil
}

func (s *VocabListService) UpdateWordStatus(ctx context.Context, req UpdateWordStatusRequest) error {
	return s.vocabListRepo.UpdateWordInList(ctx, req.UserID, req.ListID, req.VocabPK, req.VocabSK, req.IsLearned)
}
