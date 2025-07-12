package repositories

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/guregu/dynamo/v2"
)

// DynamoVocabMediaRepository implements media operations using DynamoDB
type DynamoVocabMediaRepository struct {
	table dynamo.Table
}

// VocabMediaRecord represents the DynamoDB storage format for media entries
type VocabMediaRecord struct {
	PK            string         `dynamo:"PK,hash"`
	Media         map[string]any `dynamo:"media,omitempty"`
	SearchTerm    string         `dynamo:"search_term,omitempty"`
	MediaRef      string         `dynamo:"media_ref,omitempty"`
	UsageCount    int            `dynamo:"usage_count,omitempty"`
	LastUsed      string         `dynamo:"last_used,omitempty"`
	CreatedAt     string         `dynamo:"created_at,omitempty"`
	ItemType      string         `dynamo:"item_type"`
	SchemaVersion int            `dynamo:"schema_version"`
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

	return record.Media, nil
}

// GetMediaBySearchTerms finds media by searching through multiple search terms
func (r *DynamoVocabMediaRepository) GetMediaBySearchTerms(ctx context.Context, searchTerms []string) (map[string]any, error) {
	if len(searchTerms) == 0 {
		return nil, nil
	}

	bestMatch := ""
	bestScore := 0

	// Check each search term
	for _, term := range searchTerms {
		normalizedTerm := strings.ToLower(term)
		pk := "SEARCH#" + normalizedTerm

		var record VocabMediaRecord
		err := r.table.Get("PK", pk).One(ctx, &record)
		if err != nil {
			continue // Skip if not found
		}

		// Simple scoring based on usage count
		score := record.UsageCount
		if score > bestScore {
			bestScore = score
			bestMatch = record.MediaRef
		}
	}

	if bestMatch == "" {
		return nil, nil
	}

	// Fetch the actual media data
	media, err := r.GetMediaByRef(ctx, bestMatch)
	if err != nil {
		return nil, err
	}

	// Update usage statistics for the matched term
	for _, term := range searchTerms {
		normalizedTerm := strings.ToLower(term)
		pk := "SEARCH#" + normalizedTerm

		var record VocabMediaRecord
		err := r.table.Get("PK", pk).One(ctx, &record)
		if err == nil && record.MediaRef == bestMatch {
			// Update usage count
			_ = r.table.Update("PK", pk).
				Set("last_used", time.Now().UTC().Format(time.RFC3339)).
				Add("usage_count", 1).
				Run(ctx)
			break
		}
	}

	return media, nil
}
