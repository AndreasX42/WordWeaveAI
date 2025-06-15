package utils

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"os"
)

func AwsString(s string) *string {
	return &s
}

func GetTableName(baseName string) string {
	if prefix := os.Getenv("DYNAMODB_TABLE_PREFIX"); prefix != "" {
		return prefix + "_" + baseName
	}
	return baseName
}

func GenerateConfirmationCode() string {
	n, _ := rand.Int(rand.Reader, big.NewInt(1000000))
	return fmt.Sprintf("%06d", n.Int64())
}

func GenerateRandomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyz" +
		"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" +
		"!@#$%^&*()-_=+[]{}<>?,./~`"

	result := make([]byte, length)
	for i := 0; i < length; i++ {
		idx, _ := rand.Int(rand.Reader, big.NewInt(int64(len(charset))))
		result[i] = charset[idx.Int64()]
	}
	return string(result)
}

func GetEnvWithDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
