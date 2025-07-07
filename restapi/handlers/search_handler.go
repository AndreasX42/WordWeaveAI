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
	SourceWord       string                 `json:"source_word"`
	SourceLanguage   string                 `json:"source_language"`
	TargetWord       string                 `json:"target_word"`
	TargetLanguage   string                 `json:"target_language"`
	Definition       []string               `json:"source_definition,omitempty"`
	Examples         []map[string]string    `json:"examples,omitempty"`
	Synonyms         []map[string]string    `json:"synonyms,omitempty"`
	Media            map[string]interface{} `json:"media,omitempty"`
	PronunciationURL map[string]string      `json:"pronunciation_url,omitempty"`
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
		SourceWord:       vocab.SourceWord,
		SourceLanguage:   vocab.SourceLanguage,
		TargetWord:       vocab.TargetWord,
		TargetLanguage:   vocab.TargetLanguage,
		Definition:       vocab.SourceDefinition,
		Examples:         vocab.Examples,
		Synonyms:         vocab.Synonyms,
		Media:            vocab.Media,
		PronunciationURL: vocab.PronunciationURL,
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
