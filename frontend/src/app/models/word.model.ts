export interface VocabularyWord {
  pk: string;
  sk: string;

  // Source word information
  source_word: string;
  source_language: string;
  source_article?: string | null;
  source_pos: string;
  source_definition: string[];
  source_additional_info?: string | null;

  // Target word information
  target_word: string;
  target_language: string;
  target_pos: string;
  target_article?: string | null;
  target_syllables: string[];
  target_phonetic_guide: string;
  target_additional_info?: string | null;
  target_plural_form?: string | null;

  // Additional fields
  english_word?: string;
  synonyms: Synonym[];
  examples: Example[];
  conjugation_table?: ConjugationTable | string;
  target_pronunciations?: Pronunciation;
  media?: Media;
  media_ref?: string;

  // Reverse Lookup fields
  LKP?: string;
  SRC_LANG?: string;

  // Metadata
  created_at?: string;
  created_by: string;
  updated_at?: string;
}

export interface SearchResponse {
  results: VocabularyWord[];
  count: number;
  query: string;
}

export interface Synonym {
  synonym?: string;
  explanation?: string;
}

export interface Example {
  original: string;
  translation: string;
  context?: string;
}

export type NonPersonalForms = Record<string, string>;

export type Tense = Record<string, string>;

export type Mood = Record<string, Tense>;

export type ConjugationTable = Record<string, Mood | NonPersonalForms>;

export interface Pronunciation {
  audio: string;
  syllables?: string;
}

export interface MediaSource {
  large2x: string;
  large: string;
  medium: string;
}

export interface Media {
  alt: string;
  explanation: string;
  memory_tip: string;
  src: MediaSource;
  url: string;
}
