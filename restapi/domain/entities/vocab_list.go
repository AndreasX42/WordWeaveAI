package entities

import (
	"time"

	"github.com/google/uuid"
)

// VocabList represents a user's vocabulary list
type VocabList struct {
	ID           string
	UserID       string
	Name         string
	Description  string
	CreatedAt    time.Time
	UpdatedAt    time.Time
	WordCount    int
	LearnedCount int
}

// VocabListWord represents a word in a user's vocabulary list
type VocabListWord struct {
	ListID    string
	UserID    string
	VocabPK   string
	VocabSK   string
	MediaRef  string
	AddedAt   time.Time
	LearnedAt *time.Time
	IsLearned bool
}

// NewVocabList creates a new vocab list
func NewVocabList(userID, name, description string) *VocabList {
	now := time.Now()
	return &VocabList{
		ID:          uuid.New().String(),
		UserID:      userID,
		Name:        name,
		Description: description,
		CreatedAt:   now,
		UpdatedAt:   now,
		WordCount:   0,
	}
}

// NewVocabListWord creates a new vocab list word entry
func NewVocabListWord(listID, userID, vocabPK, vocabSK, mediaRef string) *VocabListWord {
	return &VocabListWord{
		ListID:    listID,
		UserID:    userID,
		VocabPK:   vocabPK,
		VocabSK:   vocabSK,
		MediaRef:  mediaRef,
		AddedAt:   time.Now(),
		IsLearned: false,
	}
}

// MarkAsLearned marks a word as learned
func (w *VocabListWord) MarkAsLearned() {
	now := time.Now()
	w.LearnedAt = &now
	w.IsLearned = true
}

// MarkAsNotLearned marks a word as not learned
func (w *VocabListWord) MarkAsNotLearned() {
	w.LearnedAt = nil
	w.IsLearned = false
}
