package services

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"regexp"
	"strings"

	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
)

type VocabRequestService struct {
	sqsClient           SQSAPI
	userRepository      repositories.UserRepository
	queueURL            string
	maxRequestsFreeTier int
}

// SQSAPI defines the interface for SQS client operations, allowing for mocking in tests.
type SQSAPI interface {
	SendMessage(ctx context.Context, params *sqs.SendMessageInput, optFns ...func(*sqs.Options)) (*sqs.SendMessageOutput, error)
}

// VocabSQSMessage represents the message structure sent to SQS
type VocabSQSMessage struct {
	SourceWord     string `json:"source_word"`
	SourceLanguage string `json:"source_language"`
	TargetLanguage string `json:"target_language"`
	UserID         string `json:"user_id"`
}

type VocabRequest struct {
	UserID         string
	SourceWord     string
	SourceLanguage string
	TargetLanguage string
}

var sqsDeduplicationIDPattern = regexp.MustCompile(`[^a-zA-Z0-9_-]`)

func NewVocabRequestService(sqsClient SQSAPI, userRepository repositories.UserRepository, queueURL string, maxRequestsFreeTier int) *VocabRequestService {
	return &VocabRequestService{
		sqsClient:           sqsClient,
		userRepository:      userRepository,
		queueURL:            queueURL,
		maxRequestsFreeTier: maxRequestsFreeTier,
	}
}

func (s *VocabRequestService) RequestVocab(ctx context.Context, request VocabRequest) (string, error) {

	// Create SQS message
	sqsMessage := VocabSQSMessage{
		SourceWord:     request.SourceWord,
		SourceLanguage: request.SourceLanguage,
		TargetLanguage: request.TargetLanguage,
		UserID:         request.UserID,
	}

	// Convert message to JSON
	messageBody, err := json.Marshal(sqsMessage)
	if err != nil {
		return "", fmt.Errorf("failed to marshal SQS message: %w", err)
	}

	deduplicationID := fmt.Sprintf("%s-%s-%s",
		sanitizeForSQS(request.SourceWord),
		sanitizeForSQS(request.SourceLanguage),
		sanitizeForSQS(request.TargetLanguage))

	// Log the request for monitoring
	log.Printf("Processing vocabulary request: %s (%s -> %s) for user %s",
		request.SourceWord, request.SourceLanguage, request.TargetLanguage, request.UserID)

	reserved, err := s.userRepository.IncrementRequestCountIfBelowLimit(ctx, request.UserID, s.maxRequestsFreeTier)
	if err != nil {
		return "", fmt.Errorf("failed to update user data: %w", err)
	}

	if !reserved {
		return "", fmt.Errorf("you have reached the maximum number of %d requests", s.maxRequestsFreeTier)
	}

	// Send message to SQS FIFO queue
	_, err = s.sqsClient.SendMessage(ctx, &sqs.SendMessageInput{
		QueueUrl:               &s.queueURL,
		MessageBody:            aws.String(string(messageBody)),
		MessageDeduplicationId: aws.String(deduplicationID),
		MessageGroupId:         aws.String("vocab-requests"),
	})

	if err != nil {
		log.Printf("Error sending message to SQS: %v", err)
		if releaseErr := s.userRepository.DecrementRequestCount(ctx, request.UserID); releaseErr != nil {
		}
		return "", fmt.Errorf("failed to submit word request: %w", err)
	}

	return deduplicationID, nil
}

func sanitizeForSQS(s string) string {
	maxLength := 50

	// Replace spaces with underscores
	s = strings.ReplaceAll(s, " ", "_")
	// Remove any characters that are not alphanumeric, underscore, or hyphen
	s = sqsDeduplicationIDPattern.ReplaceAllString(s, "")
	// Ensure it's not empty and within 128 character limit
	if len(s) == 0 {
		s = "default"
	}
	if len(s) > maxLength { // Leave room for language codes and separators
		s = s[:maxLength]
	}
	return s
}
