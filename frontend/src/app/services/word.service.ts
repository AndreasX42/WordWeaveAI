import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, shareReplay, timeout, catchError, map } from 'rxjs';
import { VocabularyWord, SearchResponse } from '../models/word.model';
import { Configs } from '../shared/config';

@Injectable({
  providedIn: 'root',
})
export class WordService {
  private http = inject(HttpClient);
  private apiUrl = `${Configs.BASE_URL}/words`;

  private static readonly CACHE_MS = 15000;

  // Cache maps store {obs, ts}
  private searchCache = new Map<
    string,
    { obs: Observable<VocabularyWord[]>; ts: number }
  >();
  private wordCache = new Map<
    string,
    { obs: Observable<VocabularyWord | null>; ts: number }
  >();

  getWord(
    sourceLanguage: string,
    targetLanguage: string,
    word: string,
    forceRefresh = false
  ): Observable<VocabularyWord | null> {
    const key = `${sourceLanguage}|${targetLanguage}|${word.toLowerCase()}`;

    const cached = this.wordCache.get(key);
    if (
      !forceRefresh &&
      cached &&
      Date.now() - cached.ts < WordService.CACHE_MS
    ) {
      return cached.obs;
    }

    const url = `${
      this.apiUrl
    }/${sourceLanguage}/${targetLanguage}/${encodeURIComponent(word)}`;

    const observable = this.http.get<VocabularyWord>(url).pipe(
      timeout(3000),
      catchError((error) => {
        console.error('Error fetching word:', error);
        return of(null);
      }),
      shareReplay({
        bufferSize: 1,
        refCount: false,
        windowTime: WordService.CACHE_MS,
      })
    );

    this.wordCache.set(key, { obs: observable, ts: Date.now() });
    return observable;
  }

  searchWords(
    query: string,
    sourceLanguage?: string,
    targetLanguage?: string
  ): Observable<VocabularyWord[]> {
    const url = `${Configs.BASE_URL}${Configs.SEARCH_URL}`;
    const body: any = {
      query: query,
      limit: 3,
    };

    if (sourceLanguage && sourceLanguage.trim() !== '') {
      body.source_lang = sourceLanguage;
    } else {
      body.source_lang = null;
    }

    if (targetLanguage && targetLanguage.trim() !== '') {
      body.target_lang = targetLanguage;
    } else {
      body.target_lang = null;
    }

    // Generate a cache key based on parameters
    const key = `${query}|${sourceLanguage ?? ''}|${targetLanguage ?? ''}`;

    const cachedSearch = this.searchCache.get(key);
    if (cachedSearch && Date.now() - cachedSearch.ts < WordService.CACHE_MS) {
      return cachedSearch.obs;
    }

    const observable = this.http.post<SearchResponse>(url, body).pipe(
      map((response) => {
        return response.results;
      }),
      catchError((error) => {
        console.error('Error searching words:', error);
        return of([]);
      }),
      shareReplay({
        bufferSize: 1,
        refCount: false,
        windowTime: WordService.CACHE_MS,
      })
    );

    this.searchCache.set(key, { obs: observable, ts: Date.now() });
    return observable;
  }

  // Optionally expose method to clear caches
  clearCaches() {
    this.searchCache.clear();
    this.wordCache.clear();
  }
}
