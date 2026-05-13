package utils

import "strings"

const (
	DynamoKeySeparator = "#"

	VocabSourcePKPrefix     = "SRC#"
	VocabTargetSKPrefix     = "TGT#"
	VocabPartOfSpeechPrefix = "POS#"
	VocabLookupPrefix       = "LKP#"
	VocabSourceLangPrefix   = "SRC_LANG#"

	UserPKPrefix        = "USER#"
	ListMetaSKPrefix    = "META#"
	ListSKPrefix        = "LIST#"
	ListWordSKSegment   = "#WORD#"
	MediaSearchPKPrefix = "SEARCH#"

	CountPKPrefix      = "COUNT#"
	CountSK            = "COUNT"
	CountResourceVocab = "vocab"
	CountResourceLists = "lists"
	CountResourceUsers = "users"
)

type VocabPrimaryKeys struct {
	PK string
	SK string
}

type VocabDynamoKeys struct {
	PK      string
	SK      string
	LKP     string
	SrcLang string
}

func VocabPK(sourceLanguage, normalizedSourceWord string) string {
	return VocabSourcePKPrefix + sourceLanguage + DynamoKeySeparator + normalizedSourceWord
}

func VocabSK(targetLanguage, sourcePOS string) string {
	return VocabTargetSKPrefix + targetLanguage + DynamoKeySeparator + VocabPartOfSpeechPrefix + sourcePOS
}

func VocabSKPrefixForTarget(targetLanguage string) string {
	return VocabTargetSKPrefix + targetLanguage
}

func VocabLKP(targetLanguage, normalizedTargetWord string) string {
	return VocabLookupPrefix + targetLanguage + DynamoKeySeparator + normalizedTargetWord
}

func VocabSourceLangKey(sourceLanguage string) string {
	return VocabSourceLangPrefix + sourceLanguage
}

func VocabKeys(sourceLanguage, sourceWord, targetLanguage, targetWord, sourcePOS string) VocabDynamoKeys {
	return VocabDynamoKeys{
		PK:      VocabPK(sourceLanguage, NormalizeWord(sourceWord)),
		SK:      VocabSK(targetLanguage, sourcePOS),
		LKP:     VocabLKP(targetLanguage, NormalizeWord(targetWord)),
		SrcLang: VocabSourceLangKey(sourceLanguage),
	}
}

func VocabKeysFromParams(sourceLanguage, targetLanguage, word, pos string) VocabPrimaryKeys {
	return VocabPrimaryKeys{
		PK: VocabPK(sourceLanguage, NormalizeWord(word)),
		SK: VocabSK(targetLanguage, strings.ToLower(pos)),
	}
}

func UserPK(userID string) string {
	return UserPKPrefix + userID
}

func ListMetaSK(listID string) string {
	return ListMetaSKPrefix + listID
}

func ListWordSK(listID, encodedVocabKey string) string {
	return ListSKPrefix + listID + ListWordSKSegment + encodedVocabKey
}

func ListWordSKPrefixForList(listID string) string {
	return ListSKPrefix + listID + ListWordSKSegment
}

func ListSKPrefixForList(listID string) string {
	return ListSKPrefix + listID
}

func MediaSearchPK(normalizedSearchTerm string) string {
	return MediaSearchPKPrefix + normalizedSearchTerm
}

func CountPK(resource string) string {
	return CountPKPrefix + resource
}

func VocabCountPK() string {
	return CountPK(CountResourceVocab)
}

func ListCountPK() string {
	return CountPK(CountResourceLists)
}

func UserCountPK() string {
	return CountPK(CountResourceUsers)
}
