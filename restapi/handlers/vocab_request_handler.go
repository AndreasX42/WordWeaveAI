package handlers

import (
	"net/http"
	"strings"

	"github.com/AndreasX42/restapi/domain/services"
	"github.com/gin-gonic/gin"
)

// VocabRequest represents the request structure from frontend
type VocabRequest struct {
	SourceWord     string `json:"source_word" binding:"required"`
	SourceLanguage string `json:"source_language"`
	TargetLanguage string `json:"target_language" binding:"required"`
}

type VocabRequestHandler struct {
	vocabRequestService *services.VocabRequestService
}

// NewVocabRequestHandler creates a new vocabulary request handler
func NewVocabRequestHandler(vocabRequestService *services.VocabRequestService) *VocabRequestHandler {
	return &VocabRequestHandler{
		vocabRequestService: vocabRequestService,
	}
}

// RequestVocab handles vocabulary requests and publishes to SQS FIFO queue
func (h *VocabRequestHandler) RequestVocab(c *gin.Context) {
	var request VocabRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid request format",
			"details": err.Error(),
		})
		return
	}

	// Extract user ID from JWT principal
	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "Authentication required",
		})
		return
	}

	// Clean and validate the source word
	request.SourceWord = strings.TrimSpace(request.SourceWord)
	if request.SourceWord == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Source word cannot be empty",
		})
		return
	}

	serviceRequest := services.VocabRequest{
		UserID:         user.ID,
		SourceWord:     request.SourceWord,
		SourceLanguage: request.SourceLanguage,
		TargetLanguage: request.TargetLanguage,
	}

	deduplicationID, err := h.vocabRequestService.RequestVocab(c.Request.Context(), serviceRequest)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}

	c.JSON(http.StatusAccepted, gin.H{
		"message":    "Vocabulary request submitted successfully",
		"request_id": deduplicationID,
		"status":     "pending",
	})
}
