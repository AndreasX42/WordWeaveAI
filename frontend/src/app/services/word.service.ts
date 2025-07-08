import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { VocabularyWord, SearchResponse } from '../models/word.model';
import { Configs } from '../shared/config';

@Injectable({
  providedIn: 'root',
})
export class WordService {
  private http = inject(HttpClient);
  private apiUrl = `${Configs.BASE_URL}/words`;

  getWord(
    sourceLanguage: string,
    targetLanguage: string,
    word: string
  ): Observable<VocabularyWord | null> {
    const url = `${
      this.apiUrl
    }/${sourceLanguage}/${targetLanguage}/${encodeURIComponent(word)}`;

    return this.http.get<VocabularyWord>(url).pipe(
      catchError((error) => {
        console.error('Error fetching word:', error);
        return of(null);
      })
    );
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

    return this.http.post<SearchResponse>(url, body).pipe(
      map((response) => {
        return response.results;
      }),
      catchError((error) => {
        console.error('Error searching words:', error);
        return of([]);
      })
    );
  }
}
