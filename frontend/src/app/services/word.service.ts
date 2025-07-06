import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { VocabularyWord } from '../models/word.model';
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
    sourceLanguage: string,
    targetLanguage: string,
    query: string
  ): Observable<VocabularyWord[]> {
    const url = `${this.apiUrl}/search`;
    const params = {
      source_lang: sourceLanguage,
      target_lang: targetLanguage,
      q: query,
    };

    return this.http.get<VocabularyWord[]>(url, { params }).pipe(
      catchError((error) => {
        console.error('Error searching words:', error);
        return of([]);
      })
    );
  }

  // Mock data for development
  getMockWord(): VocabularyWord {
    const conjugationData = {
      formas_no_personales: {
        infinitivo: 'defraudar',
        participio: 'defraudado',
        gerundio: 'defraudando',
      },
      indicativo: {
        presente: {
          yo: 'defraudo',
          tu: 'defraudas',
          el_ella_usted: 'defrauda',
          nosotros_nosotras: 'defraudamos',
          vosotros_vosotras: 'defraudáis',
          ellos_ellas_ustedes: 'defraudan',
        },
        preterito_perfecto_simple: {
          yo: 'defraudé',
          tu: 'defraudaste',
          el_ella_usted: 'defraudó',
          nosotros_nosotras: 'defraudamos',
          vosotros_vosotras: 'defraudasteis',
          ellos_ellas_ustedes: 'defraudaron',
        },
        preterito_imperfecto: {
          yo: 'defraudaba',
          tu: 'defraudabas',
          el_ella_usted: 'defraudaba',
          nosotros_nosotras: 'defraudábamos',
          vosotros_vosotras: 'defraudabais',
          ellos_ellas_ustedes: 'defraudaban',
        },
        futuro: {
          yo: 'defraudaré',
          tu: 'defraudarás',
          el_ella_usted: 'defraudará',
          nosotros_nosotras: 'defraudaremos',
          vosotros_vosotras: 'defraudaréis',
          ellos_ellas_ustedes: 'defraudarán',
        },
      },
      subjuntivo: {
        presente: {
          yo: 'defraude',
          tu: 'defraudes',
          el_ella_usted: 'defraude',
          nosotros_nosotras: 'defraudemos',
          vosotros_vosotras: 'defraudéis',
          ellos_ellas_ustedes: 'defrauden',
        },
      },
    };

    return {
      source_word: 'defraud',
      target_language: 'es',
      validation_passed: true,
      source_language: 'en',
      source_definition: [
        'to illegally obtain money from someone by deception',
        'to cheat or trick someone to gain something',
      ],
      source_part_of_speech: 'verb',
      source_article: null,
      source_additional_info: null,
      target_word: 'defraudar',
      target_part_of_speech: 'verb',
      target_article: null,
      target_syllables: ['de', 'frau', 'dar'],
      target_phonetic_guide: 'deˈfɾau̯dar',
      target_additional_info: 'Commonly used in legal and financial contexts.',
      english_word: 'to defraud',
      search_query: ['fraud', 'deception', 'scam'],
      synonyms: [
        {
          synonym: 'engañar',
          explanation:
            'Indica hacer que alguien crea algo falso, con la intención de obtener un beneficio.',
        },
        {
          synonym: 'estafar',
          explanation:
            'Se refiere a obtener dinero u otros bienes mediante engaños o trampas.',
        },
        {
          synonym: 'timar',
          explanation:
            'Significa engañar a alguien para quitarle dinero o bienes, generalmente con astucia.',
        },
      ],
      examples: [
        {
          original:
            'The company was found guilty of attempting to defraud its investors by falsifying financial statements.',
          translation:
            'La empresa fue declarada culpable de intentar defraudar a sus inversores falsificando los estados financieros.',
          context: 'Legal context involving financial fraud.',
        },
        {
          original:
            'He tried to defraud the government by submitting fake tax returns, but was caught by the authorities.',
          translation:
            'Intentó defraudar al gobierno presentando declaraciones de impuestos falsas, pero fue atrapado por las autoridades.',
          context: 'Criminal act related to tax evasion.',
        },
        {
          original:
            'Many people fall victim to scams designed to defraud them of their savings through deceptive schemes.',
          translation:
            'Muchas personas son víctimas de estafas diseñadas para defraudarlas de sus ahorros mediante esquemas engañosos.',
          context: 'General warning about fraudulent schemes.',
        },
        {
          original:
            'The charity was accused of defrauding donors by misusing the funds collected for relief efforts.',
          translation:
            'La organización benéfica fue acusada de defraudar a los donantes al malversar los fondos recaudados para esfuerzos de ayuda.',
          context: 'Misuse of charitable donations.',
        },
      ],
      conjugation_table: conjugationData,
      pronunciation_url: '/api/audio/defraudar.mp3',
      media: [
        {
          type: 'image',
          url: 'https://images.unsplash.com/photo-1633158829585-23ba8f7c8caf?w=400',
          caption: 'Concept of fraud and deception',
        },
      ],
      created_at: new Date().toISOString(),
      created_by: 'AI Agent',
    };
  }
}
