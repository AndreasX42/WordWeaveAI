package services

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"time"
	"unicode"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"golang.org/x/text/unicode/norm"
)

type VocabService struct {
	vocabRepo repositories.VocabRepository
}

type SearchVocabularyRequest struct {
	Query      string
	Limit      int
	SourceLang string // optional
	TargetLang string // optional
}

var normalizeRgx = regexp.MustCompile(`[^a-z0-9]`)

func NewVocabService(vocabRepo repositories.VocabRepository) *VocabService {
	return &VocabService{
		vocabRepo: vocabRepo,
	}
}

func (s *VocabService) SearchVocabulary(ctx context.Context, req SearchVocabularyRequest) ([]entities.VocabWord, error) {
	// Set defaults
	if req.Limit == 0 || req.Limit > 10 {
		req.Limit = 5
	}

	// Normalize the query
	normalizedQuery := normalizeWord(req.Query)

	fmt.Println("1 - normalizedQuery", normalizedQuery)

	var results []entities.VocabWord
	var err error

	fmt.Println("2 - start search")
	now := time.Now()

	// If language(s) are specified, use primary and sort keys
	if req.SourceLang != "" || req.TargetLang != "" {
		results, err = s.vocabRepo.SearchByWordWithLanguages(ctx, normalizedQuery, req.SourceLang, req.TargetLang, req.Limit)
		fmt.Println("3 - search time after lang search", time.Since(now))
		if err != nil {
			return nil, err
		}

		if len(results) > 0 {
			return results, nil
		}
	}

	// if no languages were specified, perform a comprehensive search across all supported languages.
	supportedLanguages := []string{"en", "es", "de"}
	results, err = s.vocabRepo.SearchByNormalizedWord(ctx, normalizedQuery, supportedLanguages, req.Limit)
	fmt.Println("4 - search time after comprehensive search", time.Since(now))
	if err != nil {
		return nil, err
	}
	fmt.Println("-1 - results", results)
	return results, nil
}

// normalizeWord matches the Python normalize_word function exactly
func normalizeWord(word string) string {
	// Step 1: NFKC normalization and lowercase
	word = strings.ToLower(word)
	word = norm.NFKC.String(word)

	// Step 2: NFD normalization and remove combining marks
	word = norm.NFD.String(word)
	result := make([]rune, 0, len(word))
	for _, r := range word {
		if unicode.In(r, unicode.Mn) {
			continue // Skip combining marks (category Mn)
		}
		result = append(result, r)
	}
	word = string(result)

	// Step 3: Remove non-alphanumeric characters
	return normalizeRgx.ReplaceAllString(word, "")
}
