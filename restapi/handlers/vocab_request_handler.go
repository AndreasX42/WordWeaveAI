package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/gin-gonic/gin"
)

// SQSAPI defines the interface for SQS client operations, allowing for mocking in tests.
type SQSAPI interface {
	SendMessage(ctx context.Context, params *sqs.SendMessageInput, optFns ...func(*sqs.Options)) (*sqs.SendMessageOutput, error)
}

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
	sqsClient      SQSAPI
	userRepository repositories.UserRepository
}

// NewVocabRequestHandler creates a new vocabulary request handler
func NewVocabRequestHandler(sqsClient SQSAPI, userRepository repositories.UserRepository) *VocabRequestHandler {
	return &VocabRequestHandler{
		sqsClient:      sqsClient,
		userRepository: userRepository,
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

	// Create SQS message
	sqsMessage := VocabSQSMessage{
		SourceWord:     request.SourceWord,
		SourceLanguage: request.SourceLanguage,
		TargetLanguage: request.TargetLanguage,
		UserID:         user.ID,
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
		maxLength := 50

		// Replace spaces with underscores
		s = strings.ReplaceAll(s, " ", "_")
		// Remove any characters that are not alphanumeric, underscore, or hyphen
		reg := regexp.MustCompile(`[^a-zA-Z0-9_-]`)
		s = reg.ReplaceAllString(s, "")
		// Ensure it's not empty and within 128 character limit
		if len(s) == 0 {
			s = "default"
		}
		if len(s) > maxLength { // Leave room for language codes and separators
			s = s[:maxLength]
		}
		return s
	}

	deduplicationID := fmt.Sprintf("%s-%s-%s",
		sanitizeForSQS(request.SourceWord),
		sanitizeForSQS(request.SourceLanguage),
		sanitizeForSQS(request.TargetLanguage))

	// Log the request for monitoring
	log.Printf("Processing vocabulary request: %s (%s -> %s) for user %s",
		request.SourceWord, request.SourceLanguage, request.TargetLanguage, user.ID)

	// Get SQS queue URL from environment
	queueURL := os.Getenv("SQS_VOCAB_REQUEST_QUEUE_URL")
	if queueURL == "" {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Queue configuration error",
		})
		return
	}

	// Check if the user has reached the maximum number of requests
	maxRequestsFreeTier, err := strconv.Atoi(os.Getenv("MAX_VOCAB_REQUESTS_FREE_TIER"))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to parse MAX_VOCAB_REQUESTS_FREE_TIER",
		})
		return
	}
	if user.RequestCount >= maxRequestsFreeTier {
		c.JSON(http.StatusTooManyRequests, gin.H{
			"details": fmt.Sprintf("You have reached the maximum number of %d requests", maxRequestsFreeTier),
		})
		return
	}

	// Send message to SQS FIFO queue
	_, err = h.sqsClient.SendMessage(context.Background(), &sqs.SendMessageInput{
		QueueUrl:               &queueURL,
		MessageBody:            aws.String(string(messageBody)),
		MessageDeduplicationId: aws.String(deduplicationID),
		MessageGroupId:         aws.String("vocab-requests"), // Trivial message group
	})

	if err != nil {
		log.Printf("Error sending message to SQS: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to submit word request",
		})
		return
	}

	// increment the request count for the user
	user.RequestCount++
	if err := h.userRepository.Update(c.Request.Context(), user); err != nil {
		log.Printf("Error updating user request count: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update user data",
		})
		return
	}

	log.Printf("Vocabulary request published to SQS: %s -> %s (User: %s)",
		request.SourceWord, request.TargetLanguage, user.ID)

	c.JSON(http.StatusOK, gin.H{
		"message":    "Vocabulary request submitted successfully",
		"request_id": deduplicationID,
		"status":     "pending",
	})
}
