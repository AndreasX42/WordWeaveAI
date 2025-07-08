package handlers

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
)

type SearchHandler struct {
	vocabService *services.VocabService
}

type VocabularySearchResult struct {
	PK               string              `json:"pk" required:"true"`
	SK               string              `json:"sk" required:"true"`
	LKP              string              `json:"lkp" required:"true"`
	SrcLang          string              `json:"src_lang" required:"true"`
	SourceWord       string              `json:"source_word" required:"true"`
	SourceLanguage   string              `json:"source_language" required:"true"`
	SourcePos        string              `json:"source_pos" required:"true"`
	TargetWord       string              `json:"target_word" required:"true"`
	TargetLanguage   string              `json:"target_language" required:"true"`
	TargetPos        string              `json:"target_pos,omitempty"`
	Definition       []string            `json:"source_definition,omitempty"`
	Examples         []map[string]string `json:"examples,omitempty"`
	Synonyms         []map[string]string `json:"synonyms,omitempty"`
	Syllables        []string            `json:"target_syllables,omitempty"`
	PhoneticGuide    string              `json:"target_phonetic_guide,omitempty"`
	Media            map[string]any      `json:"media,omitempty"`
	Pronunciations   map[string]string   `json:"target_pronunciations,omitempty"`
	ConjugationTable string              `json:"conjugation_table,omitempty"`
	CreatedAt        string              `json:"created_at,omitempty"`
	CreatedBy        string              `json:"created_by,omitempty"`
}

type SearchRequest struct {
	Query      string `json:"query" binding:"required"`
	Limit      int    `json:"limit,omitempty"`
	SourceLang string `json:"source_lang,omitempty"`
	TargetLang string `json:"target_lang,omitempty"`
}

type SearchResponse struct {
	Results []VocabularySearchResult `json:"results"`
	Count   int                      `json:"count"`
	Query   string                   `json:"query"`
}

func NewSearchHandler(vocabService *services.VocabService) *SearchHandler {
	return &SearchHandler{
		vocabService: vocabService,
	}
}

// SearchVocabulary handles vocabulary search requests
func (h *SearchHandler) SearchVocabulary(c *gin.Context) {
	var req SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		h.handleValidationError(c, err)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Create service request
	serviceReq := services.SearchVocabularyRequest{
		Query:      req.Query,
		Limit:      req.Limit,
		SourceLang: req.SourceLang,
		TargetLang: req.TargetLang,
	}

	vocabularies, err := h.vocabService.SearchVocabulary(ctx, serviceReq)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"message": "Search failed",
			"details": gin.H{
				"error": err.Error(),
			},
		})
		return
	}

	// Convert domain entities to search results
	var results []VocabularySearchResult
	for _, vocab := range vocabularies {
		result := h.convertToSearchResult(vocab)
		results = append(results, result)
	}

	response := SearchResponse{
		Results: results,
		Count:   len(results),
		Query:   req.Query,
	}

	c.JSON(http.StatusOK, response)
}

func (h *SearchHandler) convertToSearchResult(vocab entities.VocabWord) VocabularySearchResult {
	return VocabularySearchResult{
		PK:               vocab.PK,
		SK:               vocab.SK,
		LKP:              vocab.LKP,
		SrcLang:          vocab.SrcLang,
		SourceWord:       vocab.SourceWord,
		SourceLanguage:   vocab.SourceLanguage,
		SourcePos:        vocab.SourcePos,
		TargetWord:       vocab.TargetWord,
		TargetLanguage:   vocab.TargetLanguage,
		TargetPos:        vocab.TargetPos,
		Definition:       vocab.SourceDefinition,
		Examples:         vocab.Examples,
		Synonyms:         vocab.Synonyms,
		Syllables:        vocab.Syllables,
		PhoneticGuide:    vocab.PhoneticGuide,
		Media:            vocab.Media,
		Pronunciations:   vocab.Pronunciations,
		ConjugationTable: vocab.ConjugationTable,
		CreatedAt:        vocab.CreatedAt,
		CreatedBy:        vocab.CreatedBy,
	}
}

func (h *SearchHandler) handleValidationError(c *gin.Context, err error) {
	if errs, ok := err.(validator.ValidationErrors); ok {
		errMessages := make([]string, 0)
		for _, e := range errs {
			errMessages = append(errMessages, fmt.Sprintf("Field %s failed on the '%s' rule", e.Field(), e.Tag()))
		}
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Validation failed",
			"details": gin.H{
				"errors": errMessages,
			},
		})
		return
	}
	c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid request body"})
}
