package utils

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"os"
	"regexp"
	"strings"
	"unicode"

	"golang.org/x/text/unicode/norm"
)

var normalizeWordRgx = regexp.MustCompile(`[^a-z0-9]`)
var germanTransliterator = strings.NewReplacer(
	"ß", "ss",
	"ä", "ae",
	"ö", "oe",
	"ü", "ue",
)

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

// ParseCommaSeparatedList splits a comma-separated string into trimmed, non-empty entries.
// Returns a copy of fallback when the input is blank or yields no valid entries.
func ParseCommaSeparatedList(raw string, fallback []string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return fallbackCopy(fallback)
	}
	out := make([]string, 0)
	for _, part := range strings.Split(raw, ",") {
		if t := strings.TrimSpace(part); t != "" {
			out = append(out, t)
		}
	}
	if len(out) == 0 {
		return fallbackCopy(fallback)
	}
	return out
}

func fallbackCopy(src []string) []string {
	dst := make([]string, len(src))
	copy(dst, src)
	return dst
}

func NormalizeWord(word string) string {
	word = strings.ToLower(word)
	word = norm.NFKC.String(word)
	word = germanTransliterator.Replace(word)

	word = norm.NFD.String(word)
	result := make([]rune, 0, len(word))
	for _, r := range word {
		if unicode.In(r, unicode.Mn) {
			continue
		}
		result = append(result, r)
	}

	return normalizeWordRgx.ReplaceAllString(string(result), "")
}
