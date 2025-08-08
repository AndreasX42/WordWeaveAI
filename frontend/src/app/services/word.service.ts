import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, shareReplay, timeout, catchError, map } from 'rxjs';
import { VocabularyWord, SearchResponse } from '../models/word.model';
import { Configs } from '../shared/config';

interface SearchRequestBody {
  query: string;
  limit: number;
  source_lang?: string | null;
  target_lang?: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class WordService {
  private http = inject(HttpClient);
  private apiUrl = `${Configs.BASE_URL}${Configs.WORD_FETCH_URL}`;

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

  private getFromCacheOrFetch<T>(
    key: string,
    cache: Map<string, { obs: Observable<T>; ts: number }>,
    fetchFn: () => Observable<T>,
    forceRefresh = false
  ): Observable<T> {
    const cached = cache.get(key);
    if (
      !forceRefresh &&
      cached &&
      Date.now() - cached.ts < WordService.CACHE_MS
    ) {
      return cached.obs;
    }

    const observable = fetchFn().pipe(
      shareReplay({
        bufferSize: 1,
        refCount: false,
        windowTime: WordService.CACHE_MS,
      })
    );

    cache.set(key, { obs: observable, ts: Date.now() });
    return observable;
  }

  getWord(
    sourceLanguage: string,
    targetLanguage: string,
    word: string,
    forceRefresh = false
  ): Observable<VocabularyWord | null> {
    const key = `${sourceLanguage}|${targetLanguage}|${word.toLowerCase()}`;
    const url = `${
      this.apiUrl
    }/${sourceLanguage}/${targetLanguage}/${encodeURIComponent(word)}`;

    return this.getFromCacheOrFetch(
      key,
      this.wordCache,
      () =>
        this.http.get<VocabularyWord>(url).pipe(
          timeout(3000),
          catchError((error) => {
            console.error('Error fetching word:', error);
            return of(null);
          })
        ),
      forceRefresh
    );
  }

  searchWords(
    query: string,
    sourceLanguage?: string,
    targetLanguage?: string
  ): Observable<VocabularyWord[]> {
    const url = `${Configs.BASE_URL}${Configs.SEARCH_URL}`;
    const body: SearchRequestBody = {
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

    const fetchFn = () =>
      this.http.post<SearchResponse>(url, body).pipe(
        map((response) => response.results),
        catchError((error) => {
          console.error('Error searching words:', error);
          return of([]);
        })
      );

    return this.getFromCacheOrFetch(key, this.searchCache, fetchFn);
  }

  getWordByPkSk(
    pk: string,
    sk: string,
    forceRefresh = false
  ): Observable<VocabularyWord | null> {
    const key = `${pk}|${sk}`;
    const url = `${Configs.BASE_URL}${
      Configs.WORD_FETCH_URL
    }?pk=${encodeURIComponent(pk)}&sk=${encodeURIComponent(sk)}`;

    return this.getFromCacheOrFetch(
      key,
      this.wordCache,
      () =>
        this.http.get<VocabularyWord>(url).pipe(
          timeout(3000),
          catchError((error) => {
            console.error('Error fetching word by PK/SK:', error);
            return of(null);
          })
        ),
      forceRefresh
    );
  }

  getWordByPkSkWithMedia(
    pk: string,
    sk: string,
    mediaRef: string,
    forceRefresh = false
  ): Observable<VocabularyWord | null> {
    const key = `${pk}|${sk}|${mediaRef}`;
    const url = `${Configs.BASE_URL}${
      Configs.WORD_FETCH_URL
    }?pk=${encodeURIComponent(pk)}&sk=${encodeURIComponent(
      sk
    )}&media_ref=${encodeURIComponent(mediaRef)}`;

    return this.getFromCacheOrFetch(
      key,
      this.wordCache,
      () =>
        this.http.get<VocabularyWord>(url).pipe(
          timeout(3000),
          catchError((error) => {
            console.error('Error fetching word by PK/SK with media:', error);
            return of(null);
          })
        ),
      forceRefresh
    );
  }

  // Optionally expose method to clear caches
  clearCaches() {
    this.searchCache.clear();
    this.wordCache.clear();
  }
}
