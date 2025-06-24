package entities

// Vocabulary word represents a vocabulary entity
type VocabWord struct {
	SourceWord       string
	SourceLanguage   string
	SourceDefinition string
	TargetWord       string
	TargetLanguage   string
	Examples         []map[string]string
	Synonyms         []string
	Media            map[string]interface{}
	PronunciationURL string
	EnglishWord      string
}

// VocabKey represents a vocabulary table key pair
type VocabKey struct {
	PK string
	SK string
}
