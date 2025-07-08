package repositories

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"sync"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/guregu/dynamo/v2"
	"golang.org/x/sync/errgroup"
)

// DynamoVocabRepository implements vocabulary operations using DynamoDB
type DynamoVocabRepository struct {
	table dynamo.Table
}

// VocabRecord represents the DynamoDB storage format for vocabulary entries
type VocabRecord struct {
	PK               string                 `dynamo:"PK,hash"`
	SK               string                 `dynamo:"SK,range"`
	LKP              string                 `dynamo:"LKP" index:"ReverseLookupIndex,hash"`
	SrcLang          string                 `dynamo:"SRC_LANG" index:"ReverseLookupIndex,range"`
	ConjugationTable string                 `dynamo:"conjugation_table"`
	CreatedAt        string                 `dynamo:"created_at"`
	CreatedBy        string                 `dynamo:"created_by"`
	EnglishWord      string                 `dynamo:"english_word" index:"EnglishMediaLookupIndex,hash"`
	Examples         []map[string]string    `dynamo:"examples"`
	Media            map[string]interface{} `dynamo:"media"`
	PronunciationURL map[string]string      `dynamo:"pronunciation_url"`
	SchemaVersion    int                    `dynamo:"schema_version"`
	SearchQuery      []string               `dynamo:"search_query"`
	SourceDefinition []string               `dynamo:"source_definition"`
	SourceLanguage   string                 `dynamo:"source_language"`
	SourcePos        string                 `dynamo:"source_pos"`
	SourceWord       string                 `dynamo:"source_word"`
	Syllables        []string               `dynamo:"syllables"`
	Synonyms         []map[string]string    `dynamo:"synonyms"`
	TargetLanguage   string                 `dynamo:"target_language"`
	TargetPos        string                 `dynamo:"target_pos"`
	TargetWord       string                 `dynamo:"target_word"`
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
		TargetWord:       vocab.TargetWord,
		TargetLanguage:   vocab.TargetLanguage,
		Examples:         vocab.Examples,
		Synonyms:         vocab.Synonyms,
		Media:            vocab.Media,
		PronunciationURL: vocab.PronunciationURL,
		EnglishWord:      vocab.EnglishWord,
		ConjugationTable: vocab.ConjugationTable,
		CreatedAt:        vocab.CreatedAt,
		CreatedBy:        vocab.CreatedBy,
		SchemaVersion:    vocab.SchemaVersion,
		SearchQuery:      vocab.SearchQuery,
		SourcePos:        vocab.SourcePos,
		Syllables:        vocab.Syllables,
		TargetPos:        vocab.TargetPos,
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
		TargetWord:       record.TargetWord,
		TargetLanguage:   record.TargetLanguage,
		Examples:         record.Examples,
		Synonyms:         record.Synonyms,
		Media:            record.Media,
		PronunciationURL: record.PronunciationURL,
		EnglishWord:      record.EnglishWord,
		ConjugationTable: record.ConjugationTable,
		CreatedAt:        record.CreatedAt,
		CreatedBy:        record.CreatedBy,
		SourcePos:        record.SourcePos,
		Syllables:        record.Syllables,
		TargetPos:        record.TargetPos,
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

	// Strategy 4: Fallback scan only if we have very few results
	if len(resultMap) < limit/2 {
		var records []VocabRecord
		err := r.table.Scan().
			Filter("contains(source_word, ?) OR contains(target_word, ?)", normalizedQuery, normalizedQuery).
			Limit(limit).All(ctx, &records)

		if err == nil {
			for _, record := range records {
				if len(resultMap) >= limit {
					break
				}
				key := record.PK + record.SK
				if _, exists := resultMap[key]; !exists {
					entity := r.toEntity(record)
					resultMap[key] = *entity
				}
			}
		}
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

	// Direct PK query if source language is specified
	if sourceLang != "" {
		pk := "SRC#" + sourceLang + "#" + normalizedQuery
		fmt.Println("3.1 - pk", pk)
		var records []VocabRecord

		// If target language is also specified, query with SK prefix
		if targetLang != "" {
			skPrefix := "TGT#" + targetLang
			fmt.Println("3.2 - skPrefix", skPrefix)
			err := r.table.Get("PK", pk).Range("SK", dynamo.BeginsWith, skPrefix).Limit(limit).All(ctx, &records)
			fmt.Println("3.3 - records count:", len(records))
			fmt.Println("3.4 - err", err)
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
	} else if targetLang != "" {
		// Handle case where only target language is specified
		// Use reverse lookup index to find words that translate to the target language
		lkpKey := "LKP#" + targetLang + "#" + normalizedQuery
		fmt.Println("3.5 - lkpKey", lkpKey)
		var records []VocabRecord

		// Query the ReverseLookupIndex where LKP matches (hash key)
		// This will return all records with this LKP regardless of SRC_LANG (range key)
		err := r.table.Get("LKP", lkpKey).Index("ReverseLookupIndex").Limit(limit).All(ctx, &records)
		fmt.Println("3.6 - records count:", len(records))
		fmt.Println("3.7 - err", err)

		if err == nil {
			for _, record := range records {
				key := record.PK + record.SK
				if _, exists := resultMap[key]; !exists {
					entity := r.toEntity(record)
					resultMap[key] = *entity
					fmt.Println("3.8 - added record with PK:", record.PK, "SK:", record.SK, "LKP:", record.LKP)
				}
			}
		} else {
			fmt.Println("3.9 - reverse lookup error:", err)
		}
	}

	// Convert map to slice
	for _, result := range resultMap {
		allResults = append(allResults, result)
		if len(allResults) >= limit {
			break
		}
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

// GetByKeysWithPOS gets a vocabulary entry by source word, target language, and specific POS
func (r *DynamoVocabRepository) GetByKeysWithPOS(ctx context.Context, sourceWord, sourceLang, targetLang, pos string) (*entities.VocabWord, error) {
	pk := "SRC#" + sourceLang + "#" + strings.ToLower(sourceWord)
	sk := "TGT#" + targetLang + "#POS#" + pos

	return r.GetByKeys(ctx, pk, sk)
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
