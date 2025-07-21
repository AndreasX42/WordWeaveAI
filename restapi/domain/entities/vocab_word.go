package entities

// Vocabulary word represents a vocabulary entity matching the DynamoDB schema
type VocabWord struct {
	PK               string              `json:"pk"`
	SK               string              `json:"sk"`
	LKP              string              `json:"lkp"`
	SrcLang          string              `json:"src_lang"`
	SourceWord       string              `json:"source_word"`
	SourceLanguage   string              `json:"source_language"`
	SourceDefinition []string            `json:"source_definition"`
	SourceArticle    string              `json:"source_article"`
	TargetWord       string              `json:"target_word"`
	TargetLanguage   string              `json:"target_language"`
	TargetArticle    string              `json:"target_article"`
	Examples         []map[string]string `json:"examples"`
	Synonyms         []map[string]string `json:"synonyms"`
	Media            map[string]any      `json:"media"`
	MediaRef         string              `json:"media_ref"`
	Pronunciations   map[string]string   `json:"target_pronunciations"`
	PhoneticGuide    string              `json:"target_phonetic_guide"`
	EnglishWord      string              `json:"english_word"`
	ConjugationTable string              `json:"conjugation_table"`
	CreatedAt        string              `json:"created_at"`
	CreatedBy        string              `json:"created_by"`
	SourcePos        string              `json:"source_pos"`
	Syllables        []string            `json:"target_syllables"`
	TargetPos        string              `json:"target_pos"`
	SourceAddInfo    string              `json:"source_additional_info"`
	TargetAddInfo    string              `json:"target_additional_info"`
	TargetPluralForm string              `json:"target_plural_form"`
}

// VocabKey represents a vocabulary table key pair
type VocabKey struct {
	PK string
	SK string
}
