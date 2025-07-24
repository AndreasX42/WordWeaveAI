package mocks

import (
	"context"
	"fmt"
	"sync"

	"github.com/aws/aws-sdk-go-v2/service/sqs"
)

// MockSQSClient implements SQSClientInterface for testing
type MockSQSClient struct {
	messages     []MockSQSMessage
	mutex        sync.RWMutex
	shouldError  bool
	errorMessage string
}

// MockSQSMessage represents a message sent to the mock SQS
type MockSQSMessage struct {
	QueueURL        string
	MessageBody     string
	DeduplicationID string
	MessageGroupID  string
}

// NewMockSQSClient creates a new mock SQS client
func NewMockSQSClient() *MockSQSClient {
	return &MockSQSClient{
		messages: make([]MockSQSMessage, 0),
	}
}

// SendMessage mocks the SQS SendMessage operation
func (m *MockSQSClient) SendMessage(ctx context.Context, params *sqs.SendMessageInput, optFns ...func(*sqs.Options)) (*sqs.SendMessageOutput, error) {
	m.mutex.Lock()
	defer m.mutex.Unlock()

	if m.shouldError {
		return nil, fmt.Errorf(m.errorMessage)
	}

	// Store the message
	message := MockSQSMessage{
		QueueURL:        *params.QueueUrl,
		MessageBody:     *params.MessageBody,
		DeduplicationID: *params.MessageDeduplicationId,
		MessageGroupID:  *params.MessageGroupId,
	}
	m.messages = append(m.messages, message)

	// Return successful response
	messageId := fmt.Sprintf("msg-%d", len(m.messages))
	return &sqs.SendMessageOutput{
		MessageId: &messageId,
	}, nil
}

// GetSentMessages returns all messages sent to the mock SQS
func (m *MockSQSClient) GetSentMessages() []MockSQSMessage {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	// Return a copy to avoid data races
	result := make([]MockSQSMessage, len(m.messages))
	copy(result, m.messages)
	return result
}

// Reset clears all sent messages
func (m *MockSQSClient) Reset() {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.messages = make([]MockSQSMessage, 0)
}

// SetError configures the mock to return an error on SendMessage
func (m *MockSQSClient) SetError(shouldError bool, errorMessage string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	m.shouldError = shouldError
	m.errorMessage = errorMessage
}

// GetMessageCount returns the number of messages sent
func (m *MockSQSClient) GetMessageCount() int {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	return len(m.messages)
}

// GetLastMessage returns the most recently sent message
func (m *MockSQSClient) GetLastMessage() *MockSQSMessage {
	m.mutex.RLock()
	defer m.mutex.RUnlock()

	if len(m.messages) == 0 {
		return nil
	}

	// Return a copy to avoid data races
	lastMsg := m.messages[len(m.messages)-1]
	return &lastMsg
}
