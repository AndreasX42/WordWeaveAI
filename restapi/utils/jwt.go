package utils

import (
	"errors"
	"os"
	"strconv"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

var secretKey = os.Getenv("JWT_SECRET_KEY")

func GenerateJWT(userId, username string) (string, error) {
	expirationMinutes, err := strconv.ParseInt(os.Getenv("JWT_EXPIRATION_TIME"), 10, 64)
	if err != nil {
		return "", errors.New("could not parse JWT_EXPIRATION_TIME")
	}

	expirationTime := time.Now().Add(time.Duration(expirationMinutes) * time.Minute).Unix()

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"user_id":  userId,
		"username": username,
		"exp":      expirationTime,
	})

	return token.SignedString([]byte(secretKey))
}

func VerifyJWT(token string) (string, error) {
	parsedToken, err := jwt.Parse(token, func(token *jwt.Token) (any, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return []byte(secretKey), nil
	})

	if err != nil {
		return "", errors.New("could not parse token")
	}

	if !parsedToken.Valid {
		return "", errors.New("invalid token")
	}

	claims, ok := parsedToken.Claims.(jwt.MapClaims)
	if !ok {
		return "", errors.New("could not get claims")
	}

	userId := claims["user_id"].(string)

	return userId, nil
}
