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
	vocabRepo      repositories.VocabRepository
	vocabMediaRepo repositories.VocabMediaRepository
}

type SearchVocabularyRequest struct {
	Query      string
	Limit      int
	SourceLang string // optional
	TargetLang string // optional
}

var normalizeRgx = regexp.MustCompile(`[^a-z0-9]`)

func NewVocabService(vocabRepo repositories.VocabRepository, vocabMediaRepo repositories.VocabMediaRepository) *VocabService {
	return &VocabService{
		vocabRepo:      vocabRepo,
		vocabMediaRepo: vocabMediaRepo,
	}
}

func (s *VocabService) SearchVocabulary(ctx context.Context, req SearchVocabularyRequest) ([]entities.VocabWord, error) {
	// Set defaults
	if req.Limit == 0 || req.Limit > 10 {
		req.Limit = 5
	}

	// Normalize the query
	normalizedQuery := s.NormalizeWord(req.Query)

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

	// filter for source and target languages
	if req.SourceLang != "" || req.TargetLang != "" {
		results = filterByLanguages(results, req.SourceLang, req.TargetLang)
	}

	return results, nil
}

func filterByLanguages(results []entities.VocabWord, sourceLang string, targetLang string) []entities.VocabWord {
	var filteredResults []entities.VocabWord

	for _, result := range results {
		sourceMatch := sourceLang == "" || result.SourceLanguage == sourceLang
		targetMatch := targetLang == "" || result.TargetLanguage == targetLang

		if sourceMatch && targetMatch {
			filteredResults = append(filteredResults, result)
		}
	}

	return filteredResults
}

// EnrichWithMedia fetches media data for vocab words that have media_ref (public method)
func (s *VocabService) EnrichWithMedia(ctx context.Context, results []entities.VocabWord) ([]entities.VocabWord, error) {
	return s.enrichWithMedia(ctx, results)
}

// enrichWithMedia fetches media data for vocab words that have media_ref (private method)
func (s *VocabService) enrichWithMedia(ctx context.Context, results []entities.VocabWord) ([]entities.VocabWord, error) {
	// Skip if no media repository (e.g., in tests)
	if s.vocabMediaRepo == nil {
		return results, nil
	}

	for i, result := range results {
		// Skip if no media_ref included
		if result.MediaRef == "" {
			continue
		}

		// Fetch media data using media_ref
		media, err := s.vocabMediaRepo.GetMediaByRef(ctx, result.MediaRef)
		if err != nil {
			// Log the error but don't fail the entire search
			fmt.Printf("Warning: Failed to fetch media for ref %s: %v\n", result.MediaRef, err)
			continue
		}

		if media != nil {
			// Update the result with media data
			results[i].Media = media
		}
	}

	return results, nil
}

// NormalizeWord matches the Python normalize_word function exactly
func (v *VocabService) NormalizeWord(word string) string {
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

// GetVocabularyByKeys fetches a single vocabulary word by its PK and SK, enriching with media if available
func (s *VocabService) GetVocabularyByKeys(ctx context.Context, pk, sk string) (*entities.VocabWord, error) {
	vocab, err := s.vocabRepo.GetByKeys(ctx, pk, sk)
	if err != nil {
		return nil, err
	}

	// Enrich with media if media_ref exists
	if vocab.MediaRef != "" && s.vocabMediaRepo != nil {
		media, mediaErr := s.vocabMediaRepo.GetMediaByRef(ctx, vocab.MediaRef)
		if mediaErr != nil {
			fmt.Printf("Warning: Failed to fetch media for ref %s: %v\n", vocab.MediaRef, mediaErr)
		} else {
			vocab.Media = media
		}
	}

	return vocab, nil
}

// GetVocabularyByKeysWithoutMedia fetches a single vocabulary word by its PK and SK, without enriching with media if available
func (s *VocabService) GetVocabularyByKeysWithoutMedia(ctx context.Context, pk, sk string) (*entities.VocabWord, error) {
	vocab, err := s.vocabRepo.GetByKeys(ctx, pk, sk)
	if err != nil {
		return nil, err
	}

	return vocab, nil
}

// GetMediaByRef fetches media data by media reference
func (s *VocabService) GetMediaByRef(ctx context.Context, mediaRef string) (map[string]any, error) {
	if s.vocabMediaRepo == nil {
		return nil, fmt.Errorf("media repository not available")
	}

	return s.vocabMediaRepo.GetMediaByRef(ctx, mediaRef)
}
