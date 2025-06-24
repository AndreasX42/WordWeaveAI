package repositories

import (
	"context"
	"encoding/base64"
	"errors"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/guregu/dynamo/v2"
)

// DynamoVocabListRepository implements vocabulary list operations using DynamoDB
type DynamoVocabListRepository struct {
	table dynamo.Table
}

// NewDynamoVocabListRepository creates a new DynamoDB vocabulary list repository
func NewDynamoVocabListRepository(table dynamo.Table) repositories.VocabListRepository {
	return &DynamoVocabListRepository{
		table: table,
	}
}

// VocabListRecord represents the DynamoDB storage format for vocabulary list metadata
type VocabListRecord struct {
	PK          string    `dynamo:"PK"` // USER#{userId}
	SK          string    `dynamo:"SK"` // LIST#{listId}#META
	ListID      string    `dynamo:"list_id"`
	UserID      string    `dynamo:"user_id"`
	Name        string    `dynamo:"name"`
	Description string    `dynamo:"description"`
	CreatedAt   time.Time `dynamo:"created_at"`
	UpdatedAt   time.Time `dynamo:"updated_at"`
	WordCount   int       `dynamo:"word_count"`
}

// VocabListWordRecord represents the DynamoDB storage format for words in lists
type VocabListWordRecord struct {
	PK        string     `dynamo:"PK"` // USER#{userId}
	SK        string     `dynamo:"SK"` // LIST#{listId}#WORD#{base64(vocabPK|vocabSK)}
	ListID    string     `dynamo:"list_id"`
	UserID    string     `dynamo:"user_id"`
	VocabPK   string     `dynamo:"vocab_pk"` // Reference to vocabulary table PK
	VocabSK   string     `dynamo:"vocab_sk"` // Reference to vocabulary table SK
	AddedAt   time.Time  `dynamo:"added_at"`
	LearnedAt *time.Time `dynamo:"learned_at,omitempty"`
	IsLearned bool       `dynamo:"is_learned"`
}

// Utility functions for vocabulary key encoding/decoding
func encodeVocabKeys(vocabPK, vocabSK string) string {
	combined := vocabPK + "|" + vocabSK
	return base64.URLEncoding.EncodeToString([]byte(combined))
}

func decodeVocabKeys(encoded string) (string, string, error) {
	decoded, err := base64.URLEncoding.DecodeString(encoded)
	if err != nil {
		return "", "", err
	}
	parts := strings.Split(string(decoded), "|")
	if len(parts) != 2 {
		return "", "", errors.New("invalid encoded vocabulary keys")
	}
	return parts[0], parts[1], nil
}

// CreateList creates a new vocabulary list
func (r *DynamoVocabListRepository) CreateList(ctx context.Context, list *entities.VocabList) error {
	record := r.toListRecord(list)
	return r.table.Put(record).
		If("attribute_not_exists(PK) AND attribute_not_exists(SK)").
		Run(ctx)
}

// GetListByID retrieves a vocabulary list by ID
func (r *DynamoVocabListRepository) GetListByID(ctx context.Context, userID, listID string) (*entities.VocabList, error) {
	var record VocabListRecord
	pk := "USER#" + userID
	sk := "LIST#" + listID + "#META"

	err := r.table.Get("PK", pk).Range("SK", dynamo.Equal, sk).One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("vocabulary list not found")
		}
		return nil, err
	}
	return r.toListEntity(record), nil
}

// GetListsByUserID retrieves all vocabulary lists for a user
func (r *DynamoVocabListRepository) GetListsByUserID(ctx context.Context, userID string) ([]*entities.VocabList, error) {
	var records []VocabListRecord
	pk := "USER#" + userID

	err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, "LIST#").Filter("ends_with(SK, ?)", "#META").All(ctx, &records)
	if err != nil {
		return nil, err
	}

	lists := make([]*entities.VocabList, len(records))
	for i, record := range records {
		lists[i] = r.toListEntity(record)
	}
	return lists, nil
}

// UpdateList updates a vocabulary list
func (r *DynamoVocabListRepository) UpdateList(ctx context.Context, list *entities.VocabList) error {
	list.UpdatedAt = time.Now()
	record := r.toListRecord(list)
	return r.table.Put(record).
		If("attribute_exists(PK) AND attribute_exists(SK)").
		Run(ctx)
}

// DeleteList deletes a vocabulary list and all its words using batch operations
func (r *DynamoVocabListRepository) DeleteList(ctx context.Context, userID, listID string) error {
	pk := "USER#" + userID

	// First, get all items for this list (metadata + words)
	var items []struct {
		PK string `dynamo:"PK"`
		SK string `dynamo:"SK"`
	}

	err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, "LIST#"+listID).All(ctx, &items)
	if err != nil {
		return err
	}

	if len(items) == 0 {
		return nil // Nothing to delete
	}

	// Delete items in parallel to avoid sequential bottleneck
	errChan := make(chan error, len(items))
	for _, item := range items {
		go func(pk, sk string) {
			err := r.table.Delete("PK", pk).Range("SK", sk).Run(ctx)
			errChan <- err
		}(item.PK, item.SK)
	}

	// Wait for all deletes to complete
	for i := 0; i < len(items); i++ {
		if err := <-errChan; err != nil {
			return err
		}
	}

	return nil
}

// AddWordToList adds a word to a vocabulary list and updates word count
func (r *DynamoVocabListRepository) AddWordToList(ctx context.Context, word *entities.VocabListWord) error {
	record := r.toWordRecord(word)

	// Add the word record
	err := r.table.Put(record).
		If("attribute_not_exists(PK) AND attribute_not_exists(SK)").
		Run(ctx)
	if err != nil {
		return err
	}

	// Atomically increment the word count in the list metadata
	listPK := "USER#" + word.UserID
	listSK := "LIST#" + word.ListID + "#META"

	err = r.table.Update("PK", listPK).Range("SK", listSK).
		Set("word_count = word_count + ?", 1).
		Set("updated_at = ?", time.Now()).
		Run(ctx)

	return err
}

// RemoveWordFromList removes a word from a vocabulary list and updates word count
func (r *DynamoVocabListRepository) RemoveWordFromList(ctx context.Context, userID, listID, vocabPK, vocabSK string) error {
	pk := "USER#" + userID
	encodedKey := encodeVocabKeys(vocabPK, vocabSK)
	sk := "LIST#" + listID + "#WORD#" + encodedKey

	// Remove the word record
	err := r.table.Delete("PK", pk).Range("SK", sk).
		If("attribute_exists(PK) AND attribute_exists(SK)").
		Run(ctx)
	if err != nil {
		return err
	}

	// Atomically decrement the word count in the list metadata
	listPK := "USER#" + userID
	listSK := "LIST#" + listID + "#META"

	err = r.table.Update("PK", listPK).Range("SK", listSK).
		Set("word_count = word_count - ?", 1).
		Set("updated_at = ?", time.Now()).
		If("word_count > ?", 0). // Prevent negative counts
		Run(ctx)

	return err
}

// GetWordsInList retrieves all words in a vocabulary list
func (r *DynamoVocabListRepository) GetWordsInList(ctx context.Context, userID, listID string) ([]*entities.VocabListWord, error) {
	var records []VocabListWordRecord
	pk := "USER#" + userID
	skPrefix := "LIST#" + listID + "#WORD#"

	err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, skPrefix).All(ctx, &records)
	if err != nil {
		return nil, err
	}

	words := make([]*entities.VocabListWord, len(records))
	for i, record := range records {
		words[i] = r.toWordEntity(record)
	}
	return words, nil
}

// UpdateWordInList updates a word in a vocabulary list
func (r *DynamoVocabListRepository) UpdateWordInList(ctx context.Context, word *entities.VocabListWord) error {
	record := r.toWordRecord(word)
	return r.table.Put(record).
		If("attribute_exists(PK) AND attribute_exists(SK)").
		Run(ctx)
}

// WordExistsInList checks if a word exists in a vocabulary list
func (r *DynamoVocabListRepository) WordExistsInList(ctx context.Context, userID, listID, vocabPK, vocabSK string) (bool, error) {
	pk := "USER#" + userID
	encodedKey := encodeVocabKeys(vocabPK, vocabSK)
	sk := "LIST#" + listID + "#WORD#" + encodedKey

	count, err := r.table.Get("PK", pk).Range("SK", dynamo.Equal, sk).Count(ctx)
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

// Helper methods for entity conversion
func (r *DynamoVocabListRepository) toListRecord(list *entities.VocabList) VocabListRecord {
	return VocabListRecord{
		PK:          "USER#" + list.UserID,
		SK:          "LIST#" + list.ID + "#META",
		ListID:      list.ID,
		UserID:      list.UserID,
		Name:        list.Name,
		Description: list.Description,
		CreatedAt:   list.CreatedAt,
		UpdatedAt:   list.UpdatedAt,
		WordCount:   list.WordCount,
	}
}

func (r *DynamoVocabListRepository) toListEntity(record VocabListRecord) *entities.VocabList {
	return &entities.VocabList{
		ID:          record.ListID,
		UserID:      record.UserID,
		Name:        record.Name,
		Description: record.Description,
		CreatedAt:   record.CreatedAt,
		UpdatedAt:   record.UpdatedAt,
		WordCount:   record.WordCount,
	}
}

func (r *DynamoVocabListRepository) toWordRecord(word *entities.VocabListWord) VocabListWordRecord {
	encodedKey := encodeVocabKeys(word.VocabPK, word.VocabSK)
	return VocabListWordRecord{
		PK:        "USER#" + word.UserID,
		SK:        "LIST#" + word.ListID + "#WORD#" + encodedKey,
		ListID:    word.ListID,
		UserID:    word.UserID,
		VocabPK:   word.VocabPK,
		VocabSK:   word.VocabSK,
		AddedAt:   word.AddedAt,
		LearnedAt: word.LearnedAt,
		IsLearned: word.IsLearned,
	}
}

func (r *DynamoVocabListRepository) toWordEntity(record VocabListWordRecord) *entities.VocabListWord {
	return &entities.VocabListWord{
		ListID:    record.ListID,
		UserID:    record.UserID,
		VocabPK:   record.VocabPK,
		VocabSK:   record.VocabSK,
		AddedAt:   record.AddedAt,
		LearnedAt: record.LearnedAt,
		IsLearned: record.IsLearned,
	}
}
