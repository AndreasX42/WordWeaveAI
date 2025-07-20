package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/gin-gonic/gin"
)

// VocabRequest represents the request structure from frontend
type VocabRequest struct {
	SourceWord     string `json:"source_word" binding:"required"`
	SourceLanguage string `json:"source_language"`
	TargetLanguage string `json:"target_language" binding:"required"`
}

// VocabSQSMessage represents the message structure sent to SQS
type VocabSQSMessage struct {
	SourceWord     string `json:"source_word"`
	SourceLanguage string `json:"source_language"`
	TargetLanguage string `json:"target_language"`
	UserID         string `json:"user_id"`
}

// VocabRequestHandler handles vocabulary request operations
type VocabRequestHandler struct {
	sqsClient *sqs.Client
}

// NewVocabRequestHandler creates a new vocabulary request handler
func NewVocabRequestHandler(sqsClient *sqs.Client) *VocabRequestHandler {
	return &VocabRequestHandler{
		sqsClient: sqsClient,
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
	user, exists := c.Get("principal")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "Authentication required",
		})
		return
	}

	// Clean and validate the source word
	request.SourceWord = strings.TrimSpace(strings.ToLower(request.SourceWord))
	if request.SourceWord == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Source word cannot be empty",
		})
		return
	}

	// Create SQS message
	sqsMessage := VocabSQSMessage{
		SourceWord:     request.SourceWord,
		SourceLanguage: request.SourceLanguage,
		TargetLanguage: request.TargetLanguage,
		UserID:         user.(*entities.User).ID,
	}

	// Convert message to JSON
	messageBody, err := json.Marshal(sqsMessage)
	if err != nil {
		log.Printf("Error marshaling SQS message: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to process request",
		})
		return
	}

	// Generate deduplication ID: {srcword}-{srclang}-{tgtlang}
	// Sanitize for SQS requirements (alphanumeric and punctuation only)
	sanitizeForSQS := func(s string) string {
		// Replace spaces with underscores
		s = strings.ReplaceAll(s, " ", "_")
		// Remove any characters that are not alphanumeric, underscore, or hyphen
		reg := regexp.MustCompile(`[^a-zA-Z0-9_-]`)
		s = reg.ReplaceAllString(s, "")
		// Ensure it's not empty and within 128 character limit
		if len(s) == 0 {
			s = "default"
		}
		if len(s) > 100 { // Leave room for language codes and separators
			s = s[:100]
		}
		return s
	}

	deduplicationID := fmt.Sprintf("%s-%s-%s",
		sanitizeForSQS(request.SourceWord),
		sanitizeForSQS(request.SourceLanguage),
		sanitizeForSQS(request.TargetLanguage))

	// Log the request for monitoring
	log.Printf("Processing vocabulary request: %s (%s -> %s) for user %s",
		request.SourceWord, request.SourceLanguage, request.TargetLanguage, user.(*entities.User).ID)

	// Get SQS queue URL from environment
	queueURL := os.Getenv("SQS_VOCAB_REQUEST_QUEUE_URL")
	if queueURL == "" {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Queue configuration error",
		})
		return
	}

	// Send message to SQS FIFO queue
	_, err = h.sqsClient.SendMessage(context.Background(), &sqs.SendMessageInput{
		QueueUrl:               &queueURL,
		MessageBody:            aws.String(string(messageBody)),
		MessageDeduplicationId: aws.String(deduplicationID),
		MessageGroupId:         aws.String("word-requests"), // Trivial message group
	})

	if err != nil {
		log.Printf("Error sending message to SQS: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to submit word request",
		})
		return
	}

	log.Printf("Vocabulary request published to SQS: %s -> %s (User: %s)",
		request.SourceWord, request.TargetLanguage, user.(*entities.User).ID)

	c.JSON(http.StatusOK, gin.H{
		"message":    "Vocabulary request submitted successfully",
		"request_id": deduplicationID,
		"status":     "pending",
	})
}
