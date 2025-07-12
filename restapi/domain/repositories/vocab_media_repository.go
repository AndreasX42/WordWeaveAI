package repositories

import (
	"context"
)

// VocabMediaRepository defines the contract for vocabulary media data operations
type VocabMediaRepository interface {
	GetMediaByRef(ctx context.Context, mediaRef string) (map[string]any, error)
	GetMediaBySearchTerms(ctx context.Context, searchTerms []string) (map[string]any, error)
}
