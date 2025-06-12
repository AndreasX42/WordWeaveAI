package models

import (
	"context"
	"errors"
	"time"

	"github.com/AndreasX42/wordweave-go/aws"
	"github.com/AndreasX42/wordweave-go/utils"
	"github.com/guregu/dynamo/v2"
)

type User struct {
	Id               string    `dynamo:"user_id"`
	Username         string    `dynamo:"username"`
	Email            string    `dynamo:"email"`
	Password         string    `dynamo:"password_hash"`
	ConfirmationCode string    `dynamo:"confirmation_code"`
	ConfirmedEmail   bool      `dynamo:"confirmed_email" default:"false"`
	IsActive         bool      `dynamo:"is_active" default:"false"`
	IsAdmin          bool      `dynamo:"is_admin" default:"false"`
	CreatedAt        time.Time `dynamo:"created_at"`
}

// CreateUser creates a new user in the database
func CreateUser(ctx context.Context, userId, email, username, passwordHash, confirmationCode string) error {
	user := User{
		Id:               userId,
		Email:            email,
		Username:         username,
		Password:         passwordHash,
		ConfirmationCode: confirmationCode,
		CreatedAt:        time.Now().UTC(),
	}

	return aws.UsersTable.Put(user).
		If("attribute_not_exists(user_id)"). // Only create if user doesn't exist
		Run(ctx)
}

func CheckEmailExists(ctx context.Context, email string) (bool, error) {
	count, err := aws.UsersTable.Get("email", email).
		Index("EmailIndex").
		Count(ctx)

	if err != nil {
		return false, err
	}

	return count > 0, nil
}

func CheckUsernameExists(ctx context.Context, username string) (bool, error) {
	count, err := aws.UsersTable.Get("username", username).
		Index("UsernameIndex").
		Count(ctx)

	if err != nil {
		return false, err
	}

	return count > 0, nil
}

func CheckUsernameOrEmailExists(ctx context.Context, username, email string) (bool, error) {
	emailExists, err := CheckEmailExists(ctx, email)
	if err != nil {
		return false, err
	}
	if emailExists {
		return true, nil
	}

	usernameExists, err := CheckUsernameExists(ctx, username)
	if err != nil {
		return false, err
	}

	return usernameExists, nil
}

func GetUserByEmail(ctx context.Context, email string) (User, error) {
	var user User
	err := aws.UsersTable.Get("email", email).
		Index("EmailIndex").
		One(ctx, &user)

	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return User{}, errors.New("user not found")
		}
		return User{}, err
	}

	return user, nil
}

func GetUserByUsername(ctx context.Context, username string) (User, error) {
	var user User
	err := aws.UsersTable.Get("username", username).
		Index("UsernameIndex").
		One(ctx, &user)

	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return User{}, errors.New("user not found")
		}
		return User{}, err
	}

	return user, nil
}

func GetUserById(ctx context.Context, id string) (User, error) {
	var user User
	err := aws.UsersTable.Get("user_id", id).One(ctx, &user)

	if err != nil {
		if errors.Is(err, dynamo.ErrNotFound) {
			return User{}, errors.New("user not found")
		}
		return User{}, err
	}

	return user, nil
}

func ValidateCredentials(ctx context.Context, email, password string) (User, error) {
	user, err := GetUserByEmail(ctx, email)
	if err != nil {
		return User{}, err
	}

	if !utils.ComparePasswords(user.Password, password) {
		return User{}, errors.New("invalid credentials")
	}

	return user, nil
}

func DeleteUser(ctx context.Context, id string) error {

	return aws.UsersTable.Delete("user_id", id).
		If("attribute_exists(user_id)").
		Run(ctx)
}

func UpdateUser(ctx context.Context, user User) error {
	return aws.UsersTable.Put(user).
		If("attribute_exists(user_id)").
		Run(ctx)
}
