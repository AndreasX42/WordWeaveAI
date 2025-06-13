package repositories

import (
	"context"
	"errors"
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
	UserID           string    `dynamo:"user_id,hash" index:"EmailIndex,range" index:"UsernameIndex,range"`
	Email            string    `dynamo:"email" index:"EmailIndex,hash"`
	Username         string    `dynamo:"username" index:"UsernameIndex,hash"`
	PasswordHash     string    `dynamo:"password_hash"`
	ConfirmationCode string    `dynamo:"confirmation_code"`
	ConfirmedEmail   bool      `dynamo:"confirmed_email"`
	IsActive         bool      `dynamo:"is_active"`
	IsAdmin          bool      `dynamo:"is_admin"`
	CreatedAt        time.Time `dynamo:"created_at"`
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
	}
}

func (r *DynamoUserRepository) Create(ctx context.Context, user *entities.User) error {
	record := r.toUserRecord(user)
	return r.table.Put(record).
		If("attribute_not_exists(user_id)").
		Run(ctx)
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

func (r *DynamoUserRepository) Update(ctx context.Context, user *entities.User) error {
	record := r.toUserRecord(user)
	return r.table.Put(record).
		If("attribute_exists(user_id)").
		Run(ctx)
}

func (r *DynamoUserRepository) Delete(ctx context.Context, id string) error {
	return r.table.Delete("user_id", id).
		If("attribute_exists(user_id)").
		Run(ctx)
}

func (r *DynamoUserRepository) EmailExists(ctx context.Context, email string) (bool, error) {
	count, err := r.table.Get("email", email).
		Index("EmailIndex").
		Count(ctx)
	if err != nil {
		return false, err
	}
	return count > 0, nil
}

func (r *DynamoUserRepository) UsernameExists(ctx context.Context, username string) (bool, error) {
	count, err := r.table.Get("username", username).
		Index("UsernameIndex").
		Count(ctx)
	if err != nil {
		return false, err
	}
	return count > 0, nil
}
