package repositories

import (
	"context"

	"github.com/AndreasX42/restapi/domain/entities"
)

// VocabRepository defines the contract for vocabulary data operations
type VocabRepository interface {
	SearchByNormalizedWord(ctx context.Context, normalizedQuery string, supportedLanguages []string, limit int) ([]entities.VocabWord, error)
	SearchByWordWithLanguages(ctx context.Context, normalizedQuery, sourceLang, targetLang string, limit int) ([]entities.VocabWord, error)
	GetByKeys(ctx context.Context, vocabPK, vocabSK string) (*entities.VocabWord, error)
	GetByKeysBatch(ctx context.Context, keys []entities.VocabKey) (map[string]*entities.VocabWord, error)
}
