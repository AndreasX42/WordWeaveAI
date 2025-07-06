export interface VocabularyWord {
  PK?: string;
  SK?: string;

  // Source word information
  source_word: string;
  source_language: string;
  source_article?: string | null;
  source_part_of_speech?: string;
  source_definition?: string | string[];
  source_additional_info?: string | null;

  // Target word information
  target_word: string;
  target_language: string;
  target_part_of_speech?: string;
  target_article?: string | null;
  target_syllables?: string[];
  target_phonetic_guide?: string;
  target_additional_info?: string | null;

  // Additional fields
  english_word?: string;
  search_query?: string | string[];
  synonyms?: Synonym[];
  examples?: Example[];
  conjugation?: string; // JSON string of conjugation table
  conjugation_table?: ConjugationTable; // Parsed conjugation
  pronunciation_url?: string;
  pronunciations?: string;
  media?: Media[];

  // Validation
  validation_passed?: boolean;

  // Lookup fields
  LKP?: string;
  SRC_LANG?: string;

  // Metadata
  schema_version?: number;
  created_at?: string;
  created_by?: string;
}

export interface Synonym {
  synonym: string;
  explanation: string;
}

export interface Example {
  original: string;
  translation: string;
  context?: string;
}

export interface ConjugationTable {
  formas_no_personales?: {
    infinitivo?: string;
    participio?: string;
    gerundio?: string;
  };
  indicativo?: {
    [tense: string]: {
      [pronoun: string]: string;
    };
  };
  subjuntivo?: {
    [tense: string]: {
      [pronoun: string]: string;
    };
  };
  [mode: string]: any;
}

export interface Media {
  type: 'image' | 'video';
  url: string;
  caption?: string;
}
