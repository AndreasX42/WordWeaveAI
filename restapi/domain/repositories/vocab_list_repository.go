package repositories

import (
	"context"

	"github.com/AndreasX42/restapi/domain/entities"
)

// VocabListRepository defines the contract for vocabulary list data operations
type VocabListRepository interface {
	// List operations
	CreateList(ctx context.Context, list *entities.VocabList) error
	GetListByID(ctx context.Context, userID, listID string) (*entities.VocabList, error)
	GetListsByUserID(ctx context.Context, userID string) ([]*entities.VocabList, error)
	UpdateList(ctx context.Context, list *entities.VocabList) error
	DeleteList(ctx context.Context, userID, listID string) error

	// Word operations
	AddWordToList(ctx context.Context, word *entities.VocabListWord) error
	RemoveWordFromList(ctx context.Context, userID, listID, vocabPK, vocabSK string) error
	GetWordsInList(ctx context.Context, userID, listID string) ([]*entities.VocabListWord, error)
	UpdateWordInList(ctx context.Context, word *entities.VocabListWord) error
	WordExistsInList(ctx context.Context, userID, listID, vocabPK, vocabSK string) (bool, error)

	// Count operations
	GetTotalListCount(ctx context.Context) (int, error)
	InitializeListCount(ctx context.Context) error
}
