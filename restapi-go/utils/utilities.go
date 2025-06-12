package utils

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"os"
	"regexp"
)

func AwsString(s string) *string {
	return &s
}

func GetTableName(baseName string) string {
	if prefix := os.Getenv("TABLE_PREFIX"); prefix != "" {
		return prefix + "_" + baseName
	}
	return baseName
}

func IsValidEmail(email string) bool {
	re := regexp.MustCompile(`^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`)
	return re.MatchString(email)
}

func GenerateConfirmationCode() string {
	n, _ := rand.Int(rand.Reader, big.NewInt(1000000))
	return fmt.Sprintf("%06d", n.Int64())
}

func GetEnvWithDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
