package repositories

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"sync"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/guregu/dynamo/v2"
	"golang.org/x/sync/errgroup"
)

// convertToString converts interface{} to string representation
func convertToString(v interface{}) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	// For complex types, convert to JSON string
	if bytes, err := json.Marshal(v); err == nil {
		return string(bytes)
	}
	return fmt.Sprintf("%v", v)
}

// DynamoVocabRepository implements vocabulary operations using DynamoDB
type DynamoVocabRepository struct {
	table dynamo.Table
}

// VocabRecord represents the DynamoDB storage format for vocabulary entries
type VocabRecord struct {
	PK               string              `dynamo:"PK,hash"`
	SK               string              `dynamo:"SK,range"`
	LKP              string              `dynamo:"LKP" index:"ReverseLookupIndex,hash"`
	SrcLang          string              `dynamo:"SRC_LANG" index:"ReverseLookupIndex,range"`
	ConjugationTable interface{}         `dynamo:"conjugation_table"`
	CreatedAt        string              `dynamo:"created_at"`
	CreatedBy        string              `dynamo:"created_by"`
	EnglishWord      string              `dynamo:"english_word" index:"EnglishMediaLookupIndex,hash"`
	Examples         []map[string]string `dynamo:"examples"`
	MediaRef         string              `dynamo:"media_ref"`
	Pronunciations   map[string]string   `dynamo:"pronunciations"`
	PhoneticGuide    string              `dynamo:"target_phonetic_guide"`
	SourceDefinition []string            `dynamo:"source_definition"`
	SourceLanguage   string              `dynamo:"source_language"`
	SourcePos        string              `dynamo:"source_pos"`
	SourceWord       string              `dynamo:"source_word"`
	SourceArticle    string              `dynamo:"source_article"`
	Syllables        []string            `dynamo:"target_syllables"`
	Synonyms         []map[string]string `dynamo:"synonyms"`
	TargetLanguage   string              `dynamo:"target_language"`
	TargetPos        string              `dynamo:"target_pos"`
	TargetWord       string              `dynamo:"target_word"`
	TargetArticle    string              `dynamo:"target_article"`
	SourceAddInfo    string              `dynamo:"source_additional_info"`
	TargetAddInfo    string              `dynamo:"target_additional_info"`
}

// NewDynamoVocabRepository creates a new DynamoDB vocabulary repository
func NewDynamoVocabRepository(table dynamo.Table) repositories.VocabRepository {
	return &DynamoVocabRepository{
		table: table,
	}
}

// toVocabRecord converts domain entity to DynamoDB record
func (r *DynamoVocabRepository) toVocabRecord(vocab *entities.VocabWord) VocabRecord {
	return VocabRecord{
		// DynamoDB-specific fields
		PK:      "SRC#" + vocab.SourceLanguage + "#" + strings.ToLower(vocab.SourceWord),
		SK:      "TGT#" + vocab.TargetLanguage + "#POS#" + vocab.SourcePos,
		LKP:     "LKP#" + vocab.TargetLanguage + "#" + strings.ToLower(vocab.TargetWord),
		SrcLang: "SRC_LANG#" + vocab.SourceLanguage,

		// Business fields
		SourceWord:       vocab.SourceWord,
		SourceLanguage:   vocab.SourceLanguage,
		SourceDefinition: vocab.SourceDefinition,
		SourceArticle:    vocab.SourceArticle,
		TargetWord:       vocab.TargetWord,
		TargetLanguage:   vocab.TargetLanguage,
		TargetArticle:    vocab.TargetArticle,
		Examples:         vocab.Examples,
		Synonyms:         vocab.Synonyms,
		MediaRef:         vocab.MediaRef,
		Pronunciations:   vocab.Pronunciations,
		PhoneticGuide:    vocab.PhoneticGuide,
		EnglishWord:      vocab.EnglishWord,
		ConjugationTable: vocab.ConjugationTable,
		CreatedAt:        vocab.CreatedAt,
		CreatedBy:        vocab.CreatedBy,
		SourcePos:        vocab.SourcePos,
		Syllables:        vocab.Syllables,
		TargetPos:        vocab.TargetPos,
		SourceAddInfo:    vocab.SourceAddInfo,
		TargetAddInfo:    vocab.TargetAddInfo,
	}
}

// toEntity converts DynamoDB record to domain entity
func (r *DynamoVocabRepository) toEntity(record VocabRecord) *entities.VocabWord {
	return &entities.VocabWord{
		PK:               record.PK,
		SK:               record.SK,
		LKP:              record.LKP,
		SrcLang:          record.SrcLang,
		SourceWord:       record.SourceWord,
		SourceLanguage:   record.SourceLanguage,
		SourceDefinition: record.SourceDefinition,
		SourceArticle:    record.SourceArticle,
		TargetWord:       record.TargetWord,
		TargetLanguage:   record.TargetLanguage,
		TargetArticle:    record.TargetArticle,
		Examples:         record.Examples,
		Synonyms:         record.Synonyms,
		MediaRef:         record.MediaRef,
		Pronunciations:   record.Pronunciations,
		PhoneticGuide:    record.PhoneticGuide,
		EnglishWord:      record.EnglishWord,
		ConjugationTable: convertToString(record.ConjugationTable),
		CreatedAt:        record.CreatedAt,
		CreatedBy:        record.CreatedBy,
		SourcePos:        record.SourcePos,
		Syllables:        record.Syllables,
		TargetPos:        record.TargetPos,
		SourceAddInfo:    record.SourceAddInfo,
		TargetAddInfo:    record.TargetAddInfo,
	}
}

// SearchByNormalizedWord performs comprehensive vocabulary search using parallel access patterns
func (r *DynamoVocabRepository) SearchByNormalizedWord(ctx context.Context, normalizedQuery string, supportedLanguages []string, limit int) ([]entities.VocabWord, error) {
	resultMap := make(map[string]entities.VocabWord)
	var mu sync.Mutex

	// Use error group for parallel execution with context cancellation
	g, gCtx := errgroup.WithContext(ctx)

	// Strategy 1: Parallel direct PK queries
	for _, sourceLang := range supportedLanguages {
		sourceLang := sourceLang // capture loop variable
		g.Go(func() error {
			pk := "SRC#" + sourceLang + "#" + normalizedQuery
			var records []VocabRecord

			err := r.table.Get("PK", pk).Limit(limit).All(gCtx, &records)
			if err == nil {
				mu.Lock()
				for _, record := range records {
					if len(resultMap) >= limit {
						mu.Unlock()
						return nil
					}
					key := record.PK + record.SK
					if _, exists := resultMap[key]; !exists {
						entity := r.toEntity(record)
						resultMap[key] = *entity
					}
				}
				mu.Unlock()
			}
			return nil // Don't fail entire search if one query fails
		})
	}

	// Strategy 2: Parallel reverse lookup GSI queries
	for _, targetLang := range supportedLanguages {
		targetLang := targetLang // capture loop variable
		g.Go(func() error {
			lkpKey := "LKP#" + targetLang + "#" + normalizedQuery
			var records []VocabRecord

			err := r.table.Get("LKP", lkpKey).Index("ReverseLookupIndex").Limit(limit).All(gCtx, &records)
			if err == nil {
				mu.Lock()
				for _, record := range records {
					if len(resultMap) >= limit {
						mu.Unlock()
						return nil
					}
					key := record.PK + record.SK
					if _, exists := resultMap[key]; !exists {
						entity := r.toEntity(record)
						resultMap[key] = *entity
					}
				}
				mu.Unlock()
			}
			return nil // Don't fail entire search if one query fails
		})
	}

	// Strategy 3: English word GSI query (single query)
	g.Go(func() error {
		var records []VocabRecord
		err := r.table.Get("english_word", normalizedQuery).Index("EnglishMediaLookupIndex").Limit(limit).All(gCtx, &records)
		if err == nil {
			mu.Lock()
			for _, record := range records {
				if len(resultMap) >= limit {
					mu.Unlock()
					return nil
				}
				key := record.PK + record.SK
				if _, exists := resultMap[key]; !exists {
					entity := r.toEntity(record)
					resultMap[key] = *entity
				}
			}
			mu.Unlock()
		}
		return nil
	})

	// Wait for all parallel queries to complete
	_ = g.Wait() // Ignore errors as we want best-effort search

	// Strategy 4: Optimized batch scan with early termination
	if len(resultMap) == 0 {
		batchSize := 1000
		maxBatches := 10
		batchCount := 0

		// Use Scan with pagination for controlled batching
		var lastEvaluatedKey dynamo.PagingKey

		for batchCount < maxBatches && len(resultMap) < limit {
			currentBatchSize := batchSize

			scanOp := r.table.Scan().
				Filter("(contains(source_word, ?) OR contains(target_word, ?))", normalizedQuery, normalizedQuery).
				Limit(currentBatchSize)

			// Continue from where we left off
			if lastEvaluatedKey != nil {
				scanOp = scanOp.StartFrom(lastEvaluatedKey)
			}

			iter := scanOp.Iter()
			var record VocabRecord

			for iter.Next(ctx, &record) {
				if len(resultMap) >= limit {
					goto scanComplete // Early termination when we have enough results
				}

				key := record.PK + record.SK
				if _, exists := resultMap[key]; !exists {
					entity := r.toEntity(record)
					resultMap[key] = *entity
				}
			}

			batchCount++

			// Get the last evaluated key for pagination
			lastEvaluatedKey, _ = iter.LastEvaluatedKey(ctx)

			// Check if we've scanned all records (no more to scan)
			if lastEvaluatedKey == nil {
				break // No more records to scan
			}

			// If we have enough results, we can stop early
			if len(resultMap) > limit {
				break
			}
		}

	scanComplete:
		// Scan optimization complete
	}

	// Convert map to slice and apply final limit
	var allResults []entities.VocabWord
	for _, result := range resultMap {
		allResults = append(allResults, result)
		if len(allResults) >= limit {
			break
		}
	}

	return allResults, nil
}

// SearchByWordWithLanguages performs targeted search when languages are specified
func (r *DynamoVocabRepository) SearchByWordWithLanguages(ctx context.Context, normalizedQuery, sourceLang, targetLang string, limit int) ([]entities.VocabWord, error) {
	var allResults []entities.VocabWord
	resultMap := make(map[string]entities.VocabWord)

	// Strategy 1: Direct PK query if source language is specified
	if sourceLang != "" {
		pk := "SRC#" + sourceLang + "#" + normalizedQuery
		var records []VocabRecord

		// If target language is also specified, query with SK prefix
		if targetLang != "" {
			skPrefix := "TGT#" + targetLang
			err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, skPrefix).Limit(limit).All(ctx, &records)
			if err == nil {
				for _, record := range records {
					key := record.PK + record.SK
					if _, exists := resultMap[key]; !exists {
						entity := r.toEntity(record)
						resultMap[key] = *entity
					}
				}
			}
		} else {
			// Get all target language translations for this source word
			err := r.table.Get("PK", pk).Limit(limit).All(ctx, &records)
			if err == nil {
				for _, record := range records {
					key := record.PK + record.SK
					if _, exists := resultMap[key]; !exists {
						entity := r.toEntity(record)
						resultMap[key] = *entity
					}
				}
			}
		}
	}

	// Strategy 2: Reverse lookup if target language is specified AND no results found yet
	if targetLang != "" && len(resultMap) == 0 {
		lkpKey := "LKP#" + targetLang + "#" + normalizedQuery
		var records []VocabRecord

		// Query the ReverseLookupIndex where LKP matches (hash key)
		err := r.table.Get("LKP", lkpKey).Index("ReverseLookupIndex").Limit(limit).All(ctx, &records)

		if err != nil {
			fmt.Printf("Error querying ReverseLookupIndex: %v\n", err)
		} else {
			for _, record := range records {
				key := record.PK + record.SK
				if _, exists := resultMap[key]; !exists {
					entity := r.toEntity(record)
					resultMap[key] = *entity
				}
			}
		}
	}

	// Convert map to slice
	for _, result := range resultMap {
		allResults = append(allResults, result)
	}

	return allResults, nil
}

// GetByKeys gets a single vocabulary entry by PK and SK
func (r *DynamoVocabRepository) GetByKeys(ctx context.Context, vocabPK, vocabSK string) (*entities.VocabWord, error) {
	var record VocabRecord

	err := r.table.Get("PK", vocabPK).Range("SK", dynamo.Equal, vocabSK).One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("vocabulary entry not found")
		}
		return nil, err
	}

	return r.toEntity(record), nil
}

// GetByKeysBatch gets multiple vocabulary entries by their PK/SK pairs
func (r *DynamoVocabRepository) GetByKeysBatch(ctx context.Context, keys []entities.VocabKey) (map[string]*entities.VocabWord, error) {
	if len(keys) == 0 {
		return make(map[string]*entities.VocabWord), nil
	}

	result := make(map[string]*entities.VocabWord)

	// Convert VocabKey to dynamo.Keys for batch get
	var dynamoKeys []dynamo.Keyed
	for _, key := range keys {
		dynamoKeys = append(dynamoKeys, dynamo.Keys{key.PK, key.SK})
	}

	// Use guregu/dynamo's built-in batch get functionality
	var records []VocabRecord
	err := r.table.Batch("PK", "SK").Get(dynamoKeys...).All(ctx, &records)
	if err != nil {
		return nil, fmt.Errorf("failed to batch get vocabulary entries: %w", err)
	}

	// Convert records to entities and build result map
	for _, record := range records {
		vocab := r.toEntity(record)
		keyStr := fmt.Sprintf("%s|%s", record.PK, record.SK)
		result[keyStr] = vocab
	}

	return result, nil
}
