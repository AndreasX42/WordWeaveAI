package repositories

import (
	"context"
	"encoding/base64"
	"errors"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/utils"
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
	PK           string    `dynamo:"PK,hash"`  // USER#{userId}
	SK           string    `dynamo:"SK,range"` // META#{listId}
	ListID       string    `dynamo:"list_id"`
	UserID       string    `dynamo:"user_id"`
	Name         string    `dynamo:"name"`
	Description  string    `dynamo:"description"`
	CreatedAt    time.Time `dynamo:"created_at"`
	UpdatedAt    time.Time `dynamo:"updated_at"`
	WordCount    int       `dynamo:"word_count"`
	LearnedCount int       `dynamo:"learned_count"`
}

// VocabListWordRecord represents the DynamoDB storage format for words in lists
type VocabListWordRecord struct {
	PK        string     `dynamo:"PK,hash"`  // USER#{userId}
	SK        string     `dynamo:"SK,range"` // LIST#{listId}#WORD#{base64(vocabPK|vocabSK)}
	ListID    string     `dynamo:"list_id"`
	UserID    string     `dynamo:"user_id"`
	VocabPK   string     `dynamo:"vocab_pk"` // Reference to vocabulary table PK
	VocabSK   string     `dynamo:"vocab_sk"` // Reference to vocabulary table SK
	MediaRef  string     `dynamo:"media_ref"`
	AddedAt   time.Time  `dynamo:"added_at"`
	LearnedAt *time.Time `dynamo:"learned_at,omitempty"`
	IsLearned bool       `dynamo:"is_learned"`
}

// VocabListCountRecord represents the DynamoDB storage format for vocabulary list counts
type VocabListCountRecord struct {
	PK    string `dynamo:"PK,hash"`  // COUNT#lists
	SK    string `dynamo:"SK,range"` // COUNT
	Count int    `dynamo:"count"`    // Total number of vocab lists
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

// CreateList creates a new vocabulary list and increments the count
func (r *DynamoVocabListRepository) CreateList(ctx context.Context, list *entities.VocabList) error {
	record := r.toListRecord(list)

	// Create the list record first
	err := r.table.Put(record).
		If("attribute_not_exists(PK) AND attribute_not_exists(SK)").
		Run(ctx)
	if err != nil {
		return err
	}

	// Atomically increment the list count
	return r.incrementListCount(ctx, 1)
}

// GetListByID retrieves a vocabulary list by ID
func (r *DynamoVocabListRepository) GetListByID(ctx context.Context, userID, listID string) (*entities.VocabList, error) {
	var record VocabListRecord
	pk := utils.UserPK(userID)
	sk := utils.ListMetaSK(listID)

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
	var allRecords []VocabListRecord
	pk := utils.UserPK(userID)
	skPrefix := utils.ListMetaSKPrefix

	// Get all list metadata records for this user.
	err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, skPrefix).All(ctx, &allRecords)
	if err != nil {
		return nil, err
	}

	lists := make([]*entities.VocabList, len(allRecords))
	for i, record := range allRecords {
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
	pk := utils.UserPK(userID)
	skMetaPrefix := utils.ListMetaSK(listID)
	skListPrefix := utils.ListSKPrefixForList(listID)

	// First, check if the list exists and get all items
	var listItems []struct {
		PK string `dynamo:"PK"`
		SK string `dynamo:"SK"`
	}

	var metaItems struct {
		PK string `dynamo:"PK"`
		SK string `dynamo:"SK"`
	}

	err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, skMetaPrefix).One(ctx, &metaItems)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil
		}
		return err
	}

	err = r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, skListPrefix).All(ctx, &listItems)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil
		}
		return err
	}

	// Delete items in parallel
	errChan := make(chan error, len(listItems))
	for _, item := range listItems {
		go func(pk, sk string) {
			err := r.table.Delete("PK", pk).Range("SK", sk).Run(ctx)
			if err != nil && !errors.Is(err, dynamo.ErrNotFound) {
				errChan <- err
			} else {
				errChan <- nil
			}
		}(item.PK, item.SK)
	}

	// Wait for all deletes to complete
	for i := 0; i < len(listItems); i++ {
		if err := <-errChan; err != nil {
			return err
		}
	}

	// Finally delete the list metadata record
	if metaItems.PK != "" {
		if err = r.table.Delete("PK", metaItems.PK).Range("SK", metaItems.SK).Run(ctx); err != nil {
			if !errors.Is(err, dynamo.ErrNotFound) {
				return err
			}
		}
		return r.incrementListCount(ctx, -1)
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
	listPK := utils.UserPK(word.UserID)
	listSK := utils.ListMetaSK(word.ListID)

	err = r.table.Update("PK", listPK).Range("SK", listSK).
		Add("word_count", 1).
		Set("updated_at", time.Now()).
		Run(ctx)

	return err
}

// RemoveWordFromList removes a word from a vocabulary list and updates word count
func (r *DynamoVocabListRepository) RemoveWordFromList(ctx context.Context, userID, listID, vocabPK, vocabSK string) error {
	pk := utils.UserPK(userID)
	encodedKey := encodeVocabKeys(vocabPK, vocabSK)
	sk := utils.ListWordSK(listID, encodedKey)

	// Remove the word record
	err := r.table.Delete("PK", pk).Range("SK", sk).
		If("attribute_exists(PK) AND attribute_exists(SK)").
		Run(ctx)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) ||
			strings.Contains(err.Error(), "ConditionalCheckFailedException") {
			return nil
		}
		return err
	}

	// Atomically decrement the word count in the list metadata
	listPK := utils.UserPK(userID)
	listSK := utils.ListMetaSK(listID)

	err = r.table.Update("PK", listPK).Range("SK", listSK).
		Add("word_count", -1).
		Set("updated_at", time.Now()).
		If("word_count > ?", 0).
		Run(ctx)

	return err
}

// GetWordsInList retrieves all words in a vocabulary list
func (r *DynamoVocabListRepository) GetWordsInList(ctx context.Context, userID, listID string) ([]*entities.VocabListWord, error) {
	var records []VocabListWordRecord
	pk := utils.UserPK(userID)
	skPrefix := utils.ListWordSKPrefixForList(listID)

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
func (r *DynamoVocabListRepository) UpdateWordInList(ctx context.Context, userID, listID, vocabPK, vocabSK string, isLearned bool) error {
	pk := utils.UserPK(userID)
	encodedKey := encodeVocabKeys(vocabPK, vocabSK)
	sk := utils.ListWordSK(listID, encodedKey)

	var wordRecord VocabListWordRecord
	err := r.table.Get("PK", pk).Range("SK", dynamo.Equal, sk).One(ctx, &wordRecord)
	if err != nil {
		return err
	}

	wasLearned := wordRecord.IsLearned
	learnedCountDelta := 0
	if !wasLearned && isLearned {
		learnedCountDelta = 1
	} else if wasLearned && !isLearned {
		learnedCountDelta = -1
	}

	wordRecord.IsLearned = isLearned
	if isLearned {
		now := time.Now()
		wordRecord.LearnedAt = &now
	} else {
		wordRecord.LearnedAt = nil
	}

	err = r.table.Put(wordRecord).
		If("attribute_exists(PK) AND attribute_exists(SK)").
		Run(ctx)
	if err != nil {
		return err
	}

	if learnedCountDelta == 0 {
		return nil
	}

	listPK := utils.UserPK(userID)
	listSK := utils.ListMetaSK(listID)
	update := r.table.Update("PK", listPK).Range("SK", listSK).
		Add("learned_count", learnedCountDelta).
		Set("updated_at", time.Now())
	if learnedCountDelta < 0 {
		update = update.If("learned_count > ?", 0)
	}
	return update.Run(ctx)
}

// WordExistsInList checks if a word exists in a vocabulary list
func (r *DynamoVocabListRepository) WordExistsInList(ctx context.Context, userID, listID, vocabPK, vocabSK string) (bool, error) {
	pk := utils.UserPK(userID)
	encodedKey := encodeVocabKeys(vocabPK, vocabSK)
	sk := utils.ListWordSK(listID, encodedKey)

	var item struct {
		PK string `dynamo:"PK"`
		SK string `dynamo:"SK"`
	}

	err := r.table.Get("PK", pk).
		Range("SK", dynamo.Equal, sk).
		Project("PK", "SK").
		One(ctx, &item)
	if errors.Is(err, dynamo.ErrNotFound) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return true, nil
}

// Helper methods for entity conversion
func (r *DynamoVocabListRepository) toListRecord(list *entities.VocabList) VocabListRecord {
	return VocabListRecord{
		PK:           utils.UserPK(list.UserID),
		SK:           utils.ListMetaSK(list.ID),
		ListID:       list.ID,
		UserID:       list.UserID,
		Name:         list.Name,
		Description:  list.Description,
		CreatedAt:    list.CreatedAt,
		UpdatedAt:    list.UpdatedAt,
		WordCount:    list.WordCount,
		LearnedCount: list.LearnedCount,
	}
}

func (r *DynamoVocabListRepository) toListEntity(record VocabListRecord) *entities.VocabList {
	return &entities.VocabList{
		ID:           record.ListID,
		UserID:       record.UserID,
		Name:         record.Name,
		Description:  record.Description,
		CreatedAt:    record.CreatedAt,
		UpdatedAt:    record.UpdatedAt,
		WordCount:    record.WordCount,
		LearnedCount: record.LearnedCount,
	}
}

func (r *DynamoVocabListRepository) toWordRecord(word *entities.VocabListWord) VocabListWordRecord {
	encodedKey := encodeVocabKeys(word.VocabPK, word.VocabSK)
	return VocabListWordRecord{
		PK:        utils.UserPK(word.UserID),
		SK:        utils.ListWordSK(word.ListID, encodedKey),
		ListID:    word.ListID,
		UserID:    word.UserID,
		VocabPK:   word.VocabPK,
		VocabSK:   word.VocabSK,
		MediaRef:  word.MediaRef,
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
		MediaRef:  record.MediaRef,
		AddedAt:   record.AddedAt,
		LearnedAt: record.LearnedAt,
		IsLearned: record.IsLearned,
	}
}

// incrementListCount atomically increments or decrements the total list count
func (r *DynamoVocabListRepository) incrementListCount(ctx context.Context, delta int) error {
	countPK := utils.ListCountPK()
	countSK := utils.CountSK

	return r.table.Update("PK", countPK).Range("SK", countSK).
		Add("count", delta).
		Run(ctx)
}

// GetTotalListCount retrieves the total number of vocabulary lists across all users
func (r *DynamoVocabListRepository) GetTotalListCount(ctx context.Context) (int, error) {
	var record VocabListCountRecord
	countPK := utils.ListCountPK()
	countSK := utils.CountSK

	err := r.table.Get("PK", countPK).Range("SK", dynamo.Equal, countSK).One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			// If count record doesn't exist, return 0
			return 0, nil
		}
		return 0, err
	}

	return record.Count, nil
}

// InitializeListCount initializes the count record if it doesn't exist
func (r *DynamoVocabListRepository) InitializeListCount(ctx context.Context) error {
	countRecord := VocabListCountRecord{
		PK:    utils.ListCountPK(),
		SK:    utils.CountSK,
		Count: 0,
	}

	err := r.table.Put(countRecord).
		If("attribute_not_exists(PK) AND attribute_not_exists(SK)").
		Run(ctx)

	// If the conditional check failed, it means the record already exists
	// This is fine for initialization - we want it to be idempotent
	if err != nil && strings.Contains(err.Error(), "ConditionalCheckFailedException") {
		return nil
	}

	return err
}
