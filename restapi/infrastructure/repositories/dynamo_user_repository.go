package repositories

import (
	"context"
	"errors"
	"strings"
	"time"

	"github.com/AndreasX42/restapi/domain/entities"
	"github.com/AndreasX42/restapi/domain/repositories"
	"github.com/guregu/dynamo/v2"
)

// DynamoUserRepository implements the UserRepository interface using DynamoDB
type DynamoUserRepository struct {
	table dynamo.Table
}

// UserRecord represents the DynamoDB storage format
type UserRecord struct {
	UserID           string    `dynamo:"user_id,hash"`
	Email            string    `dynamo:"email" index:"EmailIndex,hash"`
	Username         string    `dynamo:"username" index:"UsernameIndex,hash"`
	PasswordHash     string    `dynamo:"password_hash"`
	ConfirmationCode string    `dynamo:"confirmation_code"`
	ConfirmedEmail   bool      `dynamo:"confirmed_email"`
	IsActive         bool      `dynamo:"is_active"`
	IsAdmin          bool      `dynamo:"is_admin"`
	CreatedAt        time.Time `dynamo:"created_at"`
	// OAuth fields
	GoogleID     string `dynamo:"google_id" index:"GoogleIDIndex,hash"`
	IsOAuthUser  bool   `dynamo:"is_oauth_user"`
	ProfileImage string `dynamo:"profile_image"`
	RequestCount int    `dynamo:"request_count"`
}

// UserCountRecord represents the DynamoDB storage format for user counts
type UserCountRecord struct {
	UserID string `dynamo:"user_id,hash"` // COUNT#users
	Count  int    `dynamo:"count"`        // Total number of users
}

// NewDynamoUserRepository creates a new DynamoDB user repository
func NewDynamoUserRepository(table dynamo.Table) repositories.UserRepository {
	return &DynamoUserRepository{
		table: table,
	}
}

// toUserRecord converts domain entity to DynamoDB record
func (r *DynamoUserRepository) toUserRecord(user *entities.User) UserRecord {
	return UserRecord{
		UserID:           user.ID,
		Email:            user.Email,
		Username:         user.Username,
		PasswordHash:     user.PasswordHash,
		ConfirmationCode: user.ConfirmationCode,
		ConfirmedEmail:   user.ConfirmedEmail,
		IsActive:         user.IsActive,
		IsAdmin:          user.IsAdmin,
		CreatedAt:        user.CreatedAt,
		GoogleID:         user.GoogleID,
		IsOAuthUser:      user.IsOAuthUser,
		ProfileImage:     user.ProfileImage,
		RequestCount:     user.RequestCount,
	}
}

// toEntity converts DynamoDB record to domain entity
func (r *DynamoUserRepository) toEntity(record UserRecord) *entities.User {
	return &entities.User{
		ID:               record.UserID,
		Email:            record.Email,
		Username:         record.Username,
		PasswordHash:     record.PasswordHash,
		ConfirmationCode: record.ConfirmationCode,
		ConfirmedEmail:   record.ConfirmedEmail,
		IsActive:         record.IsActive,
		IsAdmin:          record.IsAdmin,
		CreatedAt:        record.CreatedAt,
		GoogleID:         record.GoogleID,
		IsOAuthUser:      record.IsOAuthUser,
		ProfileImage:     record.ProfileImage,
		RequestCount:     record.RequestCount,
	}
}

func (r *DynamoUserRepository) Create(ctx context.Context, user *entities.User) error {
	record := r.toUserRecord(user)

	// Create the user record first
	err := r.table.Put(record).
		If("attribute_not_exists(user_id)").
		Run(ctx)
	if err != nil {
		return err
	}

	// Atomically increment the user count
	return r.incrementUserCount(ctx, 1)
}

func (r *DynamoUserRepository) GetByID(ctx context.Context, id string) (*entities.User, error) {
	var record UserRecord
	err := r.table.Get("user_id", id).One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("user not found")
		}
		return nil, err
	}
	return r.toEntity(record), nil
}

func (r *DynamoUserRepository) GetByEmail(ctx context.Context, email string) (*entities.User, error) {
	var record UserRecord
	err := r.table.Get("email", email).
		Index("EmailIndex").
		One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("user not found")
		}
		return nil, err
	}
	return r.toEntity(record), nil
}

func (r *DynamoUserRepository) GetByUsername(ctx context.Context, username string) (*entities.User, error) {
	var record UserRecord
	err := r.table.Get("username", username).
		Index("UsernameIndex").
		One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("user not found")
		}
		return nil, err
	}
	return r.toEntity(record), nil
}

func (r *DynamoUserRepository) GetByGoogleID(ctx context.Context, googleID string) (*entities.User, error) {
	var record UserRecord
	err := r.table.Get("google_id", googleID).
		Index("GoogleIDIndex").
		One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return nil, errors.New("user not found")
		}
		return nil, err
	}
	return r.toEntity(record), nil
}

func (r *DynamoUserRepository) Update(ctx context.Context, user *entities.User) error {
	record := r.toUserRecord(user)
	return r.table.Put(record).
		If("attribute_exists(user_id)").
		Run(ctx)
}

func (r *DynamoUserRepository) Delete(ctx context.Context, id string) error {
	// Delete the user record
	err := r.table.Delete("user_id", id).
		If("attribute_exists(user_id)").
		Run(ctx)
	if err != nil {
		return err
	}

	// Atomically decrement the user count
	return r.incrementUserCount(ctx, -1)
}

func (r *DynamoUserRepository) EmailExists(ctx context.Context, email string) (bool, error) {
	var record UserRecord
	err := r.table.Get("email", email).
		Index("EmailIndex").
		Limit(1).
		One(ctx, &record)

	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (r *DynamoUserRepository) UsernameExists(ctx context.Context, username string) (bool, error) {
	var record UserRecord
	err := r.table.Get("username", username).
		Index("UsernameIndex").
		Limit(1).
		One(ctx, &record)

	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (r *DynamoUserRepository) BatchValidateExistence(ctx context.Context, email, username string) (*repositories.ValidationResult, error) {
	result := &repositories.ValidationResult{}

	// Use channels to handle concurrent queries
	type checkResult struct {
		exists bool
		err    error
	}

	emailChan := make(chan checkResult, 1)
	usernameChan := make(chan checkResult, 1)

	// Concurrent email existence check
	if email != "" {
		go func() {
			exists, err := r.EmailExists(ctx, email)
			emailChan <- checkResult{exists: exists, err: err}
		}()
	} else {
		emailChan <- checkResult{exists: false, err: nil}
	}

	// Concurrent username existence check
	if username != "" {
		go func() {
			exists, err := r.UsernameExists(ctx, username)
			usernameChan <- checkResult{exists: exists, err: err}
		}()
	} else {
		usernameChan <- checkResult{exists: false, err: nil}
	}

	// Wait for both results
	emailResult := <-emailChan
	usernameResult := <-usernameChan

	// Check for errors
	if emailResult.err != nil {
		return nil, emailResult.err
	}
	if usernameResult.err != nil {
		return nil, usernameResult.err
	}

	result.EmailExists = emailResult.exists
	result.UsernameExists = usernameResult.exists

	return result, nil
}

// incrementUserCount atomically increments or decrements the total user count
func (r *DynamoUserRepository) incrementUserCount(ctx context.Context, delta int) error {
	countUserID := "COUNT#users"

	return r.table.Update("user_id", countUserID).
		Add("count", delta).
		Run(ctx)
}

// GetTotalUserCount retrieves the total number of users
func (r *DynamoUserRepository) GetTotalUserCount(ctx context.Context) (int, error) {
	var record UserCountRecord
	countUserID := "COUNT#users"

	err := r.table.Get("user_id", countUserID).One(ctx, &record)
	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			// If count record doesn't exist, return 0
			return 0, nil
		}
		return 0, err
	}

	return record.Count, nil
}

// InitializeUserCount initializes the user count record if it doesn't exist
func (r *DynamoUserRepository) InitializeUserCount(ctx context.Context) error {
	countRecord := UserCountRecord{
		UserID: "COUNT#users",
		Count:  0,
	}

	err := r.table.Put(countRecord).
		If("attribute_not_exists(user_id)").
		Run(ctx)

	// If the conditional check failed, it means the record already exists
	if err != nil && strings.Contains(err.Error(), "ConditionalCheckFailedException") {
		return nil
	}

	return err
}
