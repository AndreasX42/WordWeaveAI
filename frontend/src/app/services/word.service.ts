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

  // Mock data for development - Real Spanish conjugation data
  getMockWord(): VocabularyWord {
    const conjugationData = {
      formas_no_personales: {
        infinitivo: 'vivir',
        participio: 'vivido',
        gerundio: 'viviendo',
      },
      indicativo: {
        presente: {
          yo: 'vivo',
          tu: 'vives',
          el_ella_usted: 'vive',
          nosotros_nosotras: 'vivimos',
          vosotros_vosotras: 'vivís',
          ellos_ellas_ustedes: 'viven',
        },
        preterito_perfecto_simple: {
          yo: 'viví',
          tu: 'viviste',
          el_ella_usted: 'vivió',
          nosotros_nosotras: 'vivimos',
          vosotros_vosotras: 'vivisteis',
          ellos_ellas_ustedes: 'vivieron',
        },
        preterito_imperfecto: {
          yo: 'vivía',
          tu: 'vivías',
          el_ella_usted: 'vivía',
          nosotros_nosotras: 'vivíamos',
          vosotros_vosotras: 'vivíais',
          ellos_ellas_ustedes: 'vivían',
        },
        preterito_perfecto_compuesto: {
          yo: 'he vivido',
          tu: 'has vivido',
          el_ella_usted: 'ha vivido',
          nosotros_nosotras: 'hemos vivido',
          vosotros_vosotras: 'habéis vivido',
          ellos_ellas_ustedes: 'han vivido',
        },
        preterito_pluscuamperfecto: {
          yo: 'había vivido',
          tu: 'habías vivido',
          el_ella_usted: 'había vivido',
          nosotros_nosotras: 'habíamos vivido',
          vosotros_vosotras: 'habíais vivido',
          ellos_ellas_ustedes: 'habían vivido',
        },
        futuro: {
          yo: 'viviré',
          tu: 'vivirás',
          el_ella_usted: 'vivirá',
          nosotros_nosotras: 'viviremos',
          vosotros_vosotras: 'viviréis',
          ellos_ellas_ustedes: 'vivirán',
        },
        futuro_perfecto: {
          yo: 'habré vivido',
          tu: 'habrás vivido',
          el_ella_usted: 'habrá vivido',
          nosotros_nosotras: 'habremos vivido',
          vosotros_vosotras: 'habréis vivido',
          ellos_ellas_ustedes: 'habrán vivido',
        },
        condicional: {
          yo: 'viviría',
          tu: 'vivirías',
          el_ella_usted: 'viviría',
          nosotros_nosotras: 'viviríamos',
          vosotros_vosotras: 'viviríais',
          ellos_ellas_ustedes: 'vivirían',
        },
        condicional_perfecto: {
          yo: 'habría vivido',
          tu: 'habrías vivido',
          el_ella_usted: 'habría vivido',
          nosotros_nosotras: 'habríamos vivido',
          vosotros_vosotras: 'habríais vivido',
          ellos_ellas_ustedes: 'habrían vivido',
        },
      },
      subjuntivo: {
        presente: {
          yo: 'viva',
          tu: 'vivas',
          el_ella_usted: 'viva',
          nosotros_nosotras: 'vivamos',
          vosotros_vosotras: 'viváis',
          ellos_ellas_ustedes: 'vivan',
        },
        preterito_imperfecto: {
          yo: 'viviera',
          tu: 'vivieras',
          el_ella_usted: 'viviera',
          nosotros_nosotras: 'viviéramos',
          vosotros_vosotras: 'vivierais',
          ellos_ellas_ustedes: 'vivieran',
        },
        preterito_perfecto_compuesto: {
          yo: 'haya vivido',
          tu: 'hayas vivido',
          el_ella_usted: 'haya vivido',
          nosotros_nosotras: 'hayamos vivido',
          vosotros_vosotras: 'hayáis vivido',
          ellos_ellas_ustedes: 'hayan vivido',
        },
        preterito_pluscuamperfecto: {
          yo: 'hubiera vivido',
          tu: 'hubieras vivido',
          el_ella_usted: 'hubiera vivido',
          nosotros_nosotras: 'hubiéramos vivido',
          vosotros_vosotras: 'hubierais vivido',
          ellos_ellas_ustedes: 'hubieran vivido',
        },
        futuro: {
          yo: 'viviere',
          tu: 'vivieres',
          el_ella_usted: 'viviere',
          nosotros_nosotras: 'viviéremos',
          vosotros_vosotras: 'viviereis',
          ellos_ellas_ustedes: 'vivieren',
        },
      },
    };

    return {
      pk: '1',
      sk: '1',
      source_word: 'live',
      source_language: 'en',
      target_language: 'es',
      source_definition: ['to remain alive', 'to reside or dwell'],
      source_pos: 'verb',
      source_article: null,
      source_additional_info: null,
      target_word: 'vivir',
      target_pos: 'verb',
      target_article: null,
      target_syllables: ['vi', 'vir'],
      target_phonetic_guide: 'biˈβiɾ',
      target_additional_info:
        "Commonly used verb meaning 'to live' in the sense of residing or being alive.",
      english_word: 'live',
      synonyms: [
        {
          synonym: 'habitar',
          explanation: 'Significa ocupar o residir en un lugar determinado.',
        },
        {
          synonym: 'existir',
          explanation:
            'Se refiere a estar vivo o tener vida en un sentido general.',
        },
        {
          synonym: 'residir',
          explanation: 'Indica establecerse o vivir habitualmente en un lugar.',
        },
      ],
      examples: [
        {
          original: 'I live in a small town near the mountains.',
          translation: 'Yo vivo en un pequeño pueblo cerca de las montañas.',
          context: "Describing one's place of residence.",
        },
        {
          original: 'Many people want to live a happy and fulfilling life.',
          translation: 'Muchas personas quieren vivir una vida feliz y plena.',
          context: 'Talking about the desire for a good quality of life.',
        },
        {
          original: 'She decided to live abroad to experience a new culture.',
          translation:
            'Ella decidió vivir en el extranjero para experimentar una nueva cultura.',
          context: 'Explaining a decision to move to another country.',
        },
        {
          original: 'We should live in the moment and enjoy every day.',
          translation: 'Debemos vivir el momento y disfrutar cada día.',
          context: 'Encouraging mindfulness and appreciation of life.',
        },
      ],
      conjugation_table: conjugationData,
      pronunciation_url: '/api/audio/vivir.mp3',
      media: [
        {
          type: 'image',
          url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400',
          caption: 'Living life to the fullest',
        },
      ],
      created_at: new Date().toISOString(),
      created_by: 'AI Agent',
    };
  }
}
