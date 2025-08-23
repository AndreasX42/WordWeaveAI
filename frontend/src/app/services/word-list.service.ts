import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import {
  WordList,
  WordListsResponse,
  WordListWordsResponse,
  CreateWordListRequest,
  UpdateWordListRequest,
  AddWordToListRequest,
  UpdateWordStatusRequest,
  RemoveWordFromListRequest,
  WordListWordStatus,
  WordListWord,
} from '../models/word-list.model';
import { Configs } from '../shared/config';

@Injectable({
  providedIn: 'root',
})
export class WordListService {
  private http = inject(HttpClient);
  private apiUrl = `${Configs.BASE_URL}/lists`;

  /**
   * Get all vocabulary lists for the authenticated user
   */
  getLists(): Observable<WordListsResponse> {
    return this.http.get<WordListsResponse>(this.apiUrl);
  }

  /**
   * Get a specific vocabulary list by ID
   */
  getList(listId: string): Observable<WordList> {
    return this.http.get<WordList>(`${this.apiUrl}/${listId}`);
  }

  /**
   * Create a new vocabulary list
   */
  createList(request: CreateWordListRequest): Observable<WordList> {
    return this.http.post<WordList>(this.apiUrl, request);
  }

  /**
   * Update an existing vocabulary list
   */
  updateList(
    listId: string,
    request: UpdateWordListRequest
  ): Observable<WordList> {
    return this.http.put<WordList>(`${this.apiUrl}/${listId}`, request);
  }

  /**
   * Delete a vocabulary list
   */
  deleteList(listId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${listId}`);
  }

  /**
   * Get all words in a specific vocabulary list
   */
  getWordsInList(listId: string): Observable<WordListWordsResponse> {
    return this.http
      .get<{ data: unknown[]; count: number; message?: string }>(
        `${this.apiUrl}/${listId}/words`
      )
      .pipe(
        map((response) => ({
          data: response.data.map((word: unknown) =>
            this.transformWordFromBackend(word)
          ),
          count: response.count,
          message: response.message,
        }))
      );
  }

  /**
   * Add a word to a vocabulary list
   */
  addWordToList(
    listId: string,
    request: AddWordToListRequest
  ): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/${listId}/words`, request);
  }

  /**
   * Remove a word from a vocabulary list
   */
  removeWordFromList(
    listId: string,
    request: RemoveWordFromListRequest
  ): Observable<void> {
    // Backend expects vocab_pk and vocab_sk as query parameters
    const params = {
      vocab_pk: request.vocab_pk,
      vocab_sk: request.vocab_sk,
    };
    return this.http.delete<void>(`${this.apiUrl}/${listId}/words`, {
      params,
    });
  }

  /**
   * Update the status of a word in a vocabulary list
   */
  updateWordStatus(
    listId: string,
    request: UpdateWordStatusRequest
  ): Observable<void> {
    // Backend expects vocab_pk and vocab_sk as query parameters
    // and is_learned boolean in body
    const params = {
      vocab_pk: request.vocab_pk,
      vocab_sk: request.vocab_sk,
    };
    const body = {
      is_learned: this.mapStatusToIsLearned(request.status),
    };
    return this.http.put<void>(`${this.apiUrl}/${listId}/words/status`, body, {
      params,
    });
  }

  /**
   * Maps frontend status enum to backend boolean
   */
  private mapStatusToIsLearned(status: WordListWordStatus): boolean {
    return status === 'learned';
  }

  /**
   * Transform backend word response to frontend format
   */
  private transformWordFromBackend(word: unknown): WordListWord {
    const wordData = word as Record<string, unknown>;
    return {
      vocab_pk: wordData['vocab_pk'] as string,
      vocab_sk: wordData['vocab_sk'] as string,
      added_at: wordData['added_at'] as string,
      learned_at: wordData['learned_at'] as string | undefined,
      is_learned: wordData['is_learned'] as boolean,
      source_word: wordData['source_word'] as string | undefined,
      source_language: wordData['source_language'] as string | undefined,
      source_definition: wordData['source_definition'] as string[] | undefined,
      target_word: wordData['target_word'] as string | undefined,
      target_language: wordData['target_language'] as string | undefined,
      examples: wordData['examples'] as Record<string, string>[] | undefined,
      synonyms: wordData['synonyms'] as Record<string, string>[] | undefined,
      media: wordData['media'] as Record<string, unknown> | undefined,
      media_ref: wordData['media_ref'] as string | undefined,
      pronunciations: wordData['pronunciations'] as
        | Record<string, string>
        | undefined,
      phonetic_guide: wordData['phonetic_guide'] as string | undefined,
      english_word: wordData['english_word'] as string | undefined,
    };
  }
}
