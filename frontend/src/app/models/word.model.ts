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

  // Additional fields
  english_word?: string;
  synonyms: Synonym[];
  examples: Example[];
  conjugation_table?: ConjugationTable;
  pronunciation_url: string;
  media: Media[];

  // Reverse Lookup fields
  LKP?: string;
  SRC_LANG?: string;

  // Metadata
  created_at: string;
  created_by: string;
}

export interface SearchResponse {
  results: VocabularyWord[];
  count: number;
  query: string;
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
