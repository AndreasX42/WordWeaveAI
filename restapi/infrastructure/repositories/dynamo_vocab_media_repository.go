package repositories

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/utils"
	"github.com/guregu/dynamo/v2"
	"golang.org/x/sync/errgroup"
)

// DynamoVocabMediaRepository implements media operations using DynamoDB
type DynamoVocabMediaRepository struct {
	table dynamo.Table
}

// VocabMediaRecord represents the DynamoDB storage format for media entries
type VocabMediaRecord struct {
	PK            string `dynamo:"PK,hash"`
	Media         any    `dynamo:"media,omitempty"`
	SearchTerm    string `dynamo:"search_term,omitempty"`
	MediaRef      string `dynamo:"media_ref,omitempty"`
	UsageCount    int    `dynamo:"usage_count,omitempty"`
	LastUsed      string `dynamo:"last_used,omitempty"`
	CreatedAt     string `dynamo:"created_at,omitempty"`
	ItemType      string `dynamo:"item_type"`
	SchemaVersion int    `dynamo:"schema_version"`
}

// parseMedia parses both JSON string format and native map format to map[string]any
func parseMedia(mediaData any) map[string]any {
	if mediaData == nil {
		return map[string]any{}
	}

	// Handle JSON string format
	if mediaStr, ok := mediaData.(string); ok {
		var mediaMap map[string]any
		if err := json.Unmarshal([]byte(mediaStr), &mediaMap); err != nil {
			return map[string]any{}
		}
		return mediaMap
	}

	// Handle native map format
	if mediaMap, ok := mediaData.(map[string]any); ok {
		return mediaMap
	}

	return map[string]any{}
}

// NewDynamoVocabMediaRepository creates a new DynamoDB vocabulary media repository
func NewDynamoVocabMediaRepository(table dynamo.Table) repositories.VocabMediaRepository {
	return &DynamoVocabMediaRepository{
		table: table,
	}
}

// GetMediaByRef retrieves media data by media reference
func (r *DynamoVocabMediaRepository) GetMediaByRef(ctx context.Context, mediaRef string) (map[string]any, error) {
	var record VocabMediaRecord

	err := r.table.Get("PK", mediaRef).One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("media not found")
		}
		return nil, fmt.Errorf("failed to get media: %w", err)
	}

	return parseMedia(record.Media), nil
}

// GetMediaByRefsBatch retrieves media data for multiple media references.
func (r *DynamoVocabMediaRepository) GetMediaByRefsBatch(ctx context.Context, mediaRefs []string) (map[string]map[string]any, error) {
	if len(mediaRefs) == 0 {
		return make(map[string]map[string]any), nil
	}

	const batchGetLimit = 100
	dynamoKeys := make([]dynamo.Keyed, 0, len(mediaRefs))
	seen := make(map[string]struct{}, len(mediaRefs))
	for _, mediaRef := range mediaRefs {
		if mediaRef == "" {
			continue
		}
		if _, exists := seen[mediaRef]; exists {
			continue
		}
		seen[mediaRef] = struct{}{}
		dynamoKeys = append(dynamoKeys, dynamo.Keys{mediaRef})
	}

	if len(dynamoKeys) == 0 {
		return make(map[string]map[string]any), nil
	}

	result := make(map[string]map[string]any, len(dynamoKeys))
	var resultMu sync.Mutex
	group, groupCtx := errgroup.WithContext(ctx)
	group.SetLimit(4)

	for start := 0; start < len(dynamoKeys); start += batchGetLimit {
		end := start + batchGetLimit
		if end > len(dynamoKeys) {
			end = len(dynamoKeys)
		}

		keys := dynamoKeys[start:end]
		group.Go(func() error {
			var records []VocabMediaRecord
			err := r.table.Batch("PK").Get(keys...).All(groupCtx, &records)
			if err != nil {
				if errors.Is(err, dynamo.ErrNotFound) {
					return nil
				}
				return fmt.Errorf("failed to batch get media: %w", err)
			}

			resultMu.Lock()
			defer resultMu.Unlock()
			for _, record := range records {
				result[record.PK] = parseMedia(record.Media)
			}
			return nil
		})
	}

	if err := group.Wait(); err != nil {
		return nil, err
	}

	return result, nil
}

// GetMediaBySearchTerms finds media by searching through multiple search terms
func (r *DynamoVocabMediaRepository) GetMediaBySearchTerms(ctx context.Context, searchTerms []string) (map[string]any, error) {
	if len(searchTerms) == 0 {
		return nil, nil
	}

	bestMatchMediaRef := ""
	bestMatchSearchPk := ""
	bestScore := 0

	// Check each search term
	for _, term := range searchTerms {
		normalizedTerm := utils.NormalizeWord(term)
		pk := utils.MediaSearchPK(normalizedTerm)

		var record VocabMediaRecord
		err := r.table.Get("PK", pk).One(ctx, &record)
		if err != nil {
			continue
		}

		// Simple scoring based on usage count
		score := record.UsageCount
		if score > bestScore {
			bestScore = score
			bestMatchMediaRef = record.MediaRef
			bestMatchSearchPk = pk
		}
	}

	if bestMatchMediaRef == "" {
		return nil, errors.New("no media found")
	}

	// Fetch the actual media data
	media, err := r.GetMediaByRef(ctx, bestMatchMediaRef)
	if err != nil {
		return nil, err
	}

	// Update usage statistics for the matched term
	_ = r.table.Update("PK", bestMatchSearchPk).
		Set("last_used", time.Now().UTC().Format(time.RFC3339)).
		Add("usage_count", 1).
		Run(ctx)

	return media, nil
}
