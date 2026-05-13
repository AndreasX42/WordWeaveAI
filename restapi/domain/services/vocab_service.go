package services

import (
	"context"
	"fmt"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/AndreasX42/restapi/utils"
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

func NewVocabService(vocabRepo repositories.VocabRepository, vocabMediaRepo repositories.VocabMediaRepository) *VocabService {
	return &VocabService{
		vocabRepo:      vocabRepo,
		vocabMediaRepo: vocabMediaRepo,
	}
}

func (s *VocabService) SearchVocabulary(ctx context.Context, req SearchVocabularyRequest) ([]*entities.VocabWord, error) {
	// Set defaults
	if req.Limit == 0 || req.Limit > 10 {
		req.Limit = 10
	}

	// Normalize the query
	normalizedQuery := s.NormalizeWord(req.Query)

	var results []*entities.VocabWord
	var err error

	// If language(s) are specified, use primary and sort keys
	if req.SourceLang != "" || req.TargetLang != "" {
		results, err = s.vocabRepo.SearchByWordWithLanguages(ctx, normalizedQuery, req.SourceLang, req.TargetLang, req.Limit)
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
	if err != nil {
		return nil, err
	}

	// filter for source and target languages
	if req.SourceLang != "" || req.TargetLang != "" {
		results = filterByLanguages(results, req.SourceLang, req.TargetLang)
	}

	return results, nil
}

func filterByLanguages(results []*entities.VocabWord, sourceLang string, targetLang string) []*entities.VocabWord {
	var filteredResults []*entities.VocabWord

	for _, result := range results {
		if result == nil {
			continue
		}
		sourceMatch := sourceLang == "" || result.SourceLanguage == sourceLang
		targetMatch := targetLang == "" || result.TargetLanguage == targetLang

		if sourceMatch && targetMatch {
			filteredResults = append(filteredResults, result)
		}
	}

	return filteredResults
}

// NormalizeWord returns the canonical lookup key form for vocabulary searches.
func (v *VocabService) NormalizeWord(word string) string {
	return utils.NormalizeWord(word)
}

// GetVocabularyByKeys fetches a single vocabulary word by its PK and SK, enriching with media if available
func (s *VocabService) GetVocabularyByKeys(ctx context.Context, pk, sk string) (*entities.VocabWord, error) {
	vocab, err := s.vocabRepo.GetByKeys(ctx, pk, sk)
	if err != nil {
		return nil, err
	}

	// Enrich with media if media_ref exists
	if vocab.MediaRef != "" {
		media, mediaErr := s.vocabMediaRepo.GetMediaByRef(ctx, vocab.MediaRef)
		if mediaErr != nil {
			fmt.Printf("Warning: Failed to fetch media for ref %s: %v\n", vocab.MediaRef, mediaErr)
		} else {
			vocab.Media = media
		}
	}

	return vocab, nil
}

func (s *VocabService) GetVocabularyWithOptionalMedia(ctx context.Context, pk, sk, mediaRef string) (*entities.VocabWord, error) {
	// Use channels for concurrent execution
	type result struct {
		vocab *entities.VocabWord
		media map[string]any
		err   error
	}

	vocabChan := make(chan result, 1)
	mediaChan := make(chan result, 1)
	// Fetch vocab word
	go func() {
		vocab, err := s.GetVocabularyByKeys(ctx, pk, sk)
		vocabChan <- result{vocab: vocab, err: err}
	}()

	// Fetch media
	if mediaRef != "" {
		go func() {
			media, err := s.GetMediaByRef(ctx, mediaRef)
			mediaChan <- result{media: media, err: err}
		}()
	} else {
		mediaChan <- result{media: nil, err: nil}
	}

	// Wait for both results
	vocabResult := <-vocabChan
	mediaResult := <-mediaChan

	// Check for vocab error
	if vocabResult.err != nil {
		return nil, vocabResult.err
	}

	// Add media to vocab word (ignore media errors)
	if mediaResult.err == nil && mediaResult.media != nil {
		vocabResult.vocab.Media = mediaResult.media
	}

	return vocabResult.vocab, nil
}

// GetVocabularyByParams fetches a vocabulary word from URL route parameters.
func (s *VocabService) GetVocabularyByParams(ctx context.Context, sourceLanguage, targetLanguage, word, pos string) (*entities.VocabWord, error) {
	keys := utils.VocabKeysFromParams(sourceLanguage, targetLanguage, word, pos)

	return s.GetVocabularyByKeys(ctx, keys.PK, keys.SK)
}

// GetMediaByRef fetches media data by media reference
func (s *VocabService) GetMediaByRef(ctx context.Context, mediaRef string) (map[string]any, error) {
	media, err := s.vocabMediaRepo.GetMediaByRef(ctx, mediaRef)
	if err != nil {
		return nil, err
	}

	return media, nil
}
