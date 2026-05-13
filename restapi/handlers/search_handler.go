package handlers

import (
	"context"
	"net/http"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/gin-gonic/gin"
)

type SearchHandler struct {
	vocabService *services.VocabService
}

type VocabularySearchResult struct {
	PK             string `json:"pk" required:"true"`
	SK             string `json:"sk" required:"true"`
	SourceWord     string `json:"source_word" required:"true"`
	SourceLanguage string `json:"source_language" required:"true"`
	SourcePos      string `json:"source_pos" required:"true"`
	TargetWord     string `json:"target_word" required:"true"`
	TargetLanguage string `json:"target_language" required:"true"`
	MediaRef       string `json:"media_ref" optional:"true"`
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
		HandleValidationError(c, err)
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), SearchRequestTimeout)
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
		if vocab == nil {
			continue
		}
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

// GetVocabularyByPkSk handles direct PK/SK lookup (fast path)
func (h *SearchHandler) GetVocabularyByPkSk(c *gin.Context) {
	pk := c.Query("pk")
	sk := c.Query("sk")
	mediaRef := c.Query("media_ref")

	if pk == "" || sk == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "pk and sk are required"})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), DefaultRequestTimeout)
	defer cancel()

	vocab, err := h.vocabService.GetVocabularyWithOptionalMedia(ctx, pk, sk, mediaRef)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"message": "Vocabulary not found",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, vocab)
}

// GetVocabularyByParams handles fetching vocabulary words by source_language, target_language, and source_word
func (h *SearchHandler) GetVocabularyByParams(c *gin.Context) {
	sourceLanguage := c.Param("sourceLanguage")
	targetLanguage := c.Param("targetLanguage")
	word := c.Param("word")
	pos := c.Param("pos")

	if sourceLanguage == "" || targetLanguage == "" || word == "" || pos == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "sourceLanguage, targetLanguage, pos, and word are required"})
		return
	}

	ctx, cancel := context.WithTimeout(c.Request.Context(), DefaultRequestTimeout)
	defer cancel()

	vocab, err := h.vocabService.GetVocabularyByParams(ctx, sourceLanguage, targetLanguage, word, pos)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"message": "Vocabulary not found",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, vocab)
}

func (h *SearchHandler) convertToSearchResult(vocab *entities.VocabWord) VocabularySearchResult {
	return VocabularySearchResult{
		PK:             vocab.PK,
		SK:             vocab.SK,
		SourceWord:     vocab.SourceWord,
		SourceLanguage: vocab.SourceLanguage,
		SourcePos:      vocab.SourcePos,
		TargetWord:     vocab.TargetWord,
		TargetLanguage: vocab.TargetLanguage,
		MediaRef:       vocab.MediaRef,
	}
}
