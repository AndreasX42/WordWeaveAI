export interface WordList {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  word_count?: number;
  learned_count?: number;
}

export interface WordListWord {
  vocab_pk: string;
  vocab_sk: string;
  added_at: string;
  learned_at?: string;
  is_learned: boolean;
  source_word?: string;
  source_language?: string;
  source_definition?: string[];
  target_word?: string;
  target_language?: string;
  examples?: Record<string, string>[];
  synonyms?: Record<string, string>[];
  media?: Record<string, unknown>;
  media_ref?: string;
  pronunciations?: Record<string, string>;
  phonetic_guide?: string;
  english_word?: string;
}

export interface CreateWordListRequest {
  name: string;
  description?: string;
}

export interface UpdateWordListRequest {
  name?: string;
  description?: string;
}

export interface AddWordToListRequest {
  vocab_pk: string;
  vocab_sk: string;
  media_ref?: string;
}

export interface UpdateWordStatusRequest {
  vocab_pk: string;
  vocab_sk: string;
  status: WordListWordStatus;
}

export interface RemoveWordFromListRequest {
  vocab_pk: string;
  vocab_sk: string;
}

export type WordListWordStatus = 'learning' | 'learned';

export interface WordListsResponse {
  data: WordList[];
  count: number;
  message?: string;
}

export interface WordListWordsResponse {
  data: WordListWord[];
  count: number;
  message?: string;
}
