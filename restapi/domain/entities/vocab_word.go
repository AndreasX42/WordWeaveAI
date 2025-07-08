package entities

// Vocabulary word represents a vocabulary entity matching the DynamoDB schema
type VocabWord struct {
	PK               string
	SK               string
	LKP              string
	SrcLang          string
	SourceWord       string
	SourceLanguage   string
	SourceDefinition []string
	TargetWord       string
	TargetLanguage   string
	Examples         []map[string]string
	Synonyms         []map[string]string
	Media            map[string]interface{}
	PronunciationURL map[string]string
	EnglishWord      string
	ConjugationTable string
	CreatedAt        string
	CreatedBy        string
	SchemaVersion    int
	SearchQuery      []string
	SourcePos        string
	Syllables        []string
	TargetPos        string
}

// VocabKey represents a vocabulary table key pair
type VocabKey struct {
	PK string
	SK string
}
