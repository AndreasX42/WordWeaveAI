package handlers

import (
	"net/http"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/services"
	"github.com/gin-gonic/gin"
)

type VocabListHandler struct {
	vocabListService *services.VocabListService
}

func NewVocabListHandler(vocabListService *services.VocabListService) *VocabListHandler {
	return &VocabListHandler{
		vocabListService: vocabListService,
	}
}

// Request types
type CreateVocabListRequest struct {
	Name        string `json:"name" binding:"required,min=1,max=200"`
	Description string `json:"description" binding:"omitempty,max=500"`
}

type UpdateVocabListRequest struct {
	Name        string `json:"name" binding:"omitempty,min=1,max=200"`
	Description string `json:"description" binding:"omitempty,max=500"`
}

type AddWordRequest struct {
	VocabPK  string `json:"vocab_pk" binding:"required"`
	VocabSK  string `json:"vocab_sk" binding:"required"`
	MediaRef string `json:"media_ref" binding:"omitempty"`
}

type UpdateWordStatusRequest struct {
	IsLearned bool `json:"is_learned"`
}

// Response types
type VocabListResponse struct {
	ID           string    `json:"id"`
	Name         string    `json:"name"`
	Description  string    `json:"description"`
	WordCount    int       `json:"word_count"`
	LearnedCount int       `json:"learned_count"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type VocabListWordResponse struct {
	VocabPK   string     `json:"vocab_pk"`
	VocabSK   string     `json:"vocab_sk"`
	MediaRef  string     `json:"media_ref"`
	AddedAt   time.Time  `json:"added_at"`
	LearnedAt *time.Time `json:"learned_at,omitempty"`
	IsLearned bool       `json:"is_learned"`
}

// Enhanced response type that includes vocabulary data
type VocabListWordWithDataResponse struct {
	// Learning metadata
	VocabPK   string     `json:"vocab_pk"`
	VocabSK   string     `json:"vocab_sk"`
	AddedAt   time.Time  `json:"added_at"`
	LearnedAt *time.Time `json:"learned_at,omitempty"`
	IsLearned bool       `json:"is_learned"`

	// Vocabulary data (if available)
	SourceWord       *string             `json:"source_word,omitempty"`
	SourceLanguage   *string             `json:"source_language,omitempty"`
	SourceDefinition *[]string           `json:"source_definition,omitempty"`
	TargetWord       *string             `json:"target_word,omitempty"`
	TargetLanguage   *string             `json:"target_language,omitempty"`
	Examples         []map[string]string `json:"examples,omitempty"`
	Synonyms         []map[string]string `json:"synonyms,omitempty"`
	Media            map[string]any      `json:"media,omitempty"`
	MediaRef         *string             `json:"media_ref,omitempty"`
	Pronunciations   map[string]string   `json:"pronunciations,omitempty"`
	PhoneticGuide    *string             `json:"phonetic_guide,omitempty"`
	EnglishWord      *string             `json:"english_word,omitempty"`
}

// CreateList creates a new vocabulary list
func (h *VocabListHandler) CreateList(c *gin.Context) {
	var req CreateVocabListRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	serviceReq := services.CreateListRequest{
		UserID:      user.ID,
		Name:        req.Name,
		Description: req.Description,
	}

	list, err := h.vocabListService.CreateList(c.Request.Context(), serviceReq)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Failed to create list",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"message": "List created successfully",
		"data":    h.toListResponse(list),
	})
}

// GetLists retrieves all vocabulary lists for the authenticated user
func (h *VocabListHandler) GetLists(c *gin.Context) {
	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	lists, err := h.vocabListService.GetListsByUser(c.Request.Context(), user.ID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"message": "Failed to retrieve lists",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	responses := make([]VocabListResponse, len(lists))
	for i, list := range lists {
		responses[i] = h.toListResponse(list)
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Lists retrieved successfully",
		"data":    responses,
		"count":   len(responses),
	})
}

// GetList retrieves a specific vocabulary list
func (h *VocabListHandler) GetList(c *gin.Context) {
	listID := c.Param("listId")
	if listID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID is required"})
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	list, err := h.vocabListService.GetList(c.Request.Context(), user.ID, listID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"message": "List not found",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "List retrieved successfully",
		"data":    h.toListResponse(list),
	})
}

// UpdateList updates a vocabulary list
func (h *VocabListHandler) UpdateList(c *gin.Context) {
	listID := c.Param("listId")
	if listID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID is required"})
		return
	}

	var req UpdateVocabListRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	serviceReq := services.UpdateListRequest{
		UserID:      user.ID,
		ListID:      listID,
		Name:        req.Name,
		Description: req.Description,
	}

	list, err := h.vocabListService.UpdateList(c.Request.Context(), serviceReq)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Failed to update list",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "List updated successfully",
		"data":    h.toListResponse(list),
	})
}

// DeleteList deletes a vocabulary list
func (h *VocabListHandler) DeleteList(c *gin.Context) {
	listID := c.Param("listId")
	if listID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID is required"})
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	err = h.vocabListService.DeleteList(c.Request.Context(), user.ID, listID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Failed to delete list",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "List deleted successfully",
	})
}

// AddWordToList adds a word to a vocabulary list
func (h *VocabListHandler) AddWordToList(c *gin.Context) {
	listID := c.Param("listId")
	if listID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID is required"})
		return
	}

	var req AddWordRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	serviceReq := services.AddWordToListRequest{
		UserID:   user.ID,
		ListID:   listID,
		VocabPK:  req.VocabPK,
		VocabSK:  req.VocabSK,
		MediaRef: req.MediaRef,
	}

	err = h.vocabListService.AddWordToList(c.Request.Context(), serviceReq)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Failed to add word to list",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"message": "Word added to list successfully",
	})
}

// RemoveWordFromList removes a word from a vocabulary list
func (h *VocabListHandler) RemoveWordFromList(c *gin.Context) {
	listID := c.Param("listId")
	vocabPK := c.Query("vocab_pk")
	vocabSK := c.Query("vocab_sk")

	if listID == "" || vocabPK == "" || vocabSK == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID, vocab_pk, and vocab_sk are required"})
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	err = h.vocabListService.RemoveWordFromList(c.Request.Context(), user.ID, listID, vocabPK, vocabSK)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Failed to remove word from list",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Word removed from list successfully",
	})
}

// TODO: Probably not necessary return the full vocab data
// GetWordsInList retrieves all words in a vocabulary list
func (h *VocabListHandler) GetWordsInListWithData(c *gin.Context) {
	listID := c.Param("listId")
	if listID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID is required"})
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	words, err := h.vocabListService.GetWordsInListWithData(c.Request.Context(), user.ID, listID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"message": "Failed to retrieve words",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	responses := make([]VocabListWordWithDataResponse, len(words))
	for i, word := range words {
		responses[i] = h.toWordWithDataResponse(word)
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Words retrieved successfully",
		"data":    responses,
		"count":   len(responses),
	})
}

// GetWordsInList retrieves all words in a vocabulary list
func (h *VocabListHandler) GetWordsInList(c *gin.Context) {
	listID := c.Param("listId")
	if listID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID is required"})
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	words, err := h.vocabListService.GetWordsInList(c.Request.Context(), user.ID, listID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"message": "Failed to retrieve words",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	responses := make([]VocabListWordResponse, len(words))
	for i, word := range words {
		responses[i] = h.toWordResponse(word)
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Words retrieved successfully",
		"data":    responses,
		"count":   len(responses),
	})
}

// UpdateWordStatus updates the learned status of a word in a list
func (h *VocabListHandler) UpdateWordStatus(c *gin.Context) {
	listID := c.Param("listId")
	vocabPK := c.Query("vocab_pk")
	vocabSK := c.Query("vocab_sk")

	if listID == "" || vocabPK == "" || vocabSK == "" {
		c.JSON(http.StatusBadRequest, gin.H{"message": "List ID, vocab_pk, and vocab_sk are required"})
		return
	}

	var req UpdateWordStatusRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		HandleValidationError(c, err)
		return
	}

	user, err := GetPrincipal(c)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"message": "Unauthorized"})
		return
	}

	serviceReq := services.UpdateWordStatusRequest{
		UserID:    user.ID,
		ListID:    listID,
		VocabPK:   vocabPK,
		VocabSK:   vocabSK,
		IsLearned: req.IsLearned,
	}

	err = h.vocabListService.UpdateWordStatus(c.Request.Context(), serviceReq)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"message": "Failed to update word status",
			"details": gin.H{"error": err.Error()},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "Word status updated successfully",
	})
}

// Helper methods
func (h *VocabListHandler) toListResponse(list *entities.VocabList) VocabListResponse {
	return VocabListResponse{
		ID:           list.ID,
		Name:         list.Name,
		Description:  list.Description,
		WordCount:    list.WordCount,
		LearnedCount: list.LearnedCount,
		CreatedAt:    list.CreatedAt,
		UpdatedAt:    list.UpdatedAt,
	}
}

func (h *VocabListHandler) toWordResponse(word *entities.VocabListWord) VocabListWordResponse {
	return VocabListWordResponse{
		VocabPK:   word.VocabPK,
		VocabSK:   word.VocabSK,
		MediaRef:  word.MediaRef,
		AddedAt:   word.AddedAt,
		LearnedAt: word.LearnedAt,
		IsLearned: word.IsLearned,
	}
}

func (h *VocabListHandler) toWordWithDataResponse(word *services.VocabListWordWithData) VocabListWordWithDataResponse {
	response := VocabListWordWithDataResponse{
		VocabPK:   word.VocabPK,
		VocabSK:   word.VocabSK,
		AddedAt:   word.AddedAt,
		LearnedAt: word.LearnedAt,
		IsLearned: word.IsLearned,
	}

	// Add vocabulary data if available
	if word.VocabWord != nil {
		response.SourceWord = &word.VocabWord.SourceWord
		response.SourceLanguage = &word.VocabWord.SourceLanguage
		response.SourceDefinition = &word.VocabWord.SourceDefinition
		response.TargetWord = &word.VocabWord.TargetWord
		response.TargetLanguage = &word.VocabWord.TargetLanguage
		response.Examples = word.VocabWord.Examples
		response.Synonyms = word.VocabWord.Synonyms
		response.Media = word.VocabWord.Media
		response.MediaRef = &word.VocabWord.MediaRef
		response.Pronunciations = word.VocabWord.Pronunciations
		response.PhoneticGuide = &word.VocabWord.PhoneticGuide
		response.EnglishWord = &word.VocabWord.EnglishWord
	}

	return response
}
