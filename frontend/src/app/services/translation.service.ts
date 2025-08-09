import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, tap, catchError } from 'rxjs';

export interface Language {
  code: string;
  name: string;
  flag: string;
}

@Injectable({
  providedIn: 'root',
})
export class TranslationService {
  private http = inject(HttpClient);

  private readonly LANGUAGE_STORAGE_KEY = 'language';

  // Available languages
  readonly languages: Language[] = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  ];

  // Current language signal
  private currentLanguageSignal = signal<Language>(this.languages[0]); // English default

  // Translation cache
  private translationCache = new Map<string, Record<string, unknown>>();

  // Loading states
  private loadingStates = new Map<
    string,
    Observable<Record<string, unknown>>
  >();

  // Signal to trigger updates when translations are loaded
  private translationsLoadedSignal = signal<number>(0);

  constructor() {
    // Load saved language preference
    const savedLanguage = localStorage.getItem(this.LANGUAGE_STORAGE_KEY);
    if (savedLanguage) {
      const language = this.languages.find((l) => l.code === savedLanguage);
      if (language) {
        this.currentLanguageSignal.set(language);
      }
    }

    // Load initial translations
    this.loadTranslations(this.currentLanguageSignal().code).subscribe({
      next: () => {
        this.translationsLoadedSignal.update((val) => val + 1);
      },
    });
  }

  // Get current language signal
  getCurrentLanguage() {
    return this.currentLanguageSignal.asReadonly();
  }

  // Change language
  changeLanguage(languageCode: string): void {
    const language = this.languages.find((l) => l.code === languageCode);
    if (language) {
      this.currentLanguageSignal.set(language);
      localStorage.setItem(this.LANGUAGE_STORAGE_KEY, languageCode);
      this.loadTranslations(languageCode).subscribe({
        next: () => {
          this.translationsLoadedSignal.update((val) => val + 1);
        },
      });
    }
  }

  // Load translations for a specific language (lazy loading)
  private loadTranslations(
    languageCode: string
  ): Observable<Record<string, unknown>> {
    // Return cached translations if available
    if (this.translationCache.has(languageCode)) {
      return of(this.translationCache.get(languageCode)!);
    }

    // Return ongoing request if already loading
    if (this.loadingStates.has(languageCode)) {
      return this.loadingStates.get(languageCode)!;
    }

    // Start loading translations
    const loadingObservable = this.http
      .get<Record<string, unknown>>(`/assets/i18n/${languageCode}.json`)
      .pipe(
        tap((translations) => {
          this.translationCache.set(languageCode, translations);
          this.loadingStates.delete(languageCode);
        }),
        catchError((error) => {
          // Use console.warn instead of console.error to avoid triggering global error handler
          console.warn(
            `Failed to load translations for ${languageCode}:`,
            error
          );
          this.loadingStates.delete(languageCode);
          // Fallback to English if available, otherwise return empty object
          if (languageCode !== 'en' && this.translationCache.has('en')) {
            return of(this.translationCache.get('en')!);
          }
          return of({});
        })
      );

    this.loadingStates.set(languageCode, loadingObservable);
    return loadingObservable;
  }

  // Get translation for a key
  translate(key: string, params?: Record<string, string>): string {
    // Access the signal to ensure reactivity
    this.translationsLoadedSignal();

    const currentLang = this.currentLanguageSignal().code;
    const translations = this.translationCache.get(currentLang) || {};

    let translation = this.getNestedTranslation(translations, key) || key;

    // Replace parameters if provided
    if (params) {
      Object.keys(params).forEach((paramKey) => {
        translation = translation.replace(`{{${paramKey}}}`, params[paramKey]);
      });
    }

    return translation;
  }

  // Centralized helpers for language metadata
  getLanguageFlag(code: string | undefined): string {
    if (!code) return '';
    const normalized = this.getLanguageCode(code);
    const found = this.languages.find((l) => l.code === normalized);
    return found ? found.flag : '🏳️';
  }

  getLanguageName(code: string | undefined): string {
    if (!code) return '';
    const normalized = this.getLanguageCode(code);
    const found = this.languages.find((l) => l.code === normalized);
    return found ? found.name : normalized;
  }

  // Normalize input (code or localized name) to a language code
  getLanguageCode(input: string): string {
    if (!input) return '';
    const val = input.trim().toLowerCase();

    // Handle auto-detect aliases up-front
    if (val === 'auto' || val === 'auto-detect' || val === 'autodetect') {
      return 'auto';
    }

    // Known aliases/synonyms across locales and common abbreviations
    const aliasMap: Record<string, string> = {
      en: 'en',
      eng: 'en',
      english: 'en',
      es: 'es',
      spa: 'es',
      spanish: 'es',
      espanol: 'es',
      español: 'es',
      castilian: 'es',
      castillano: 'es',
      sp: 'es',
      de: 'de',
      ger: 'de',
      german: 'de',
      deutsch: 'de',
      ge: 'de',
    };
    if (aliasMap[val]) return aliasMap[val];

    // Exact code match
    const byCode = this.languages.find((l) => l.code === val);
    if (byCode) return byCode.code;
    // Localized name match
    const byName = this.languages.find((l) => l.name.toLowerCase() === val);
    if (byName) return byName.code;

    // Fallback: keep two-letter code if it is a valid one from our list, otherwise default to input
    const two = val.slice(0, 2);
    if (this.languages.some((l) => l.code === two)) return two;
    return val;
  }

  // Get nested translation from object
  private getNestedTranslation(
    obj: Record<string, unknown>,
    key: string
  ): string | null {
    return key.split('.').reduce((o, i) => {
      if (o && typeof o === 'object' && i in o) {
        return (o as Record<string, unknown>)[i];
      }
      return undefined;
    }, obj as unknown) as string | null;
  }

  // Preload translations for better performance
  preloadTranslations(
    languageCode: string
  ): Observable<Record<string, unknown>> {
    return this.loadTranslations(languageCode);
  }

  // Get all available translation keys for a language (useful for debugging)
  getAvailableKeys(languageCode: string): string[] {
    const translations = this.translationCache.get(languageCode);
    if (!translations) {
      return [];
    }
    return this.flattenKeys(translations);
  }

  // Helper method to flatten nested keys
  private flattenKeys(obj: Record<string, unknown>, prefix = ''): string[] {
    const keys: string[] = [];

    Object.keys(obj).forEach((key) => {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      const value = obj[key];

      if (
        typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value)
      ) {
        keys.push(
          ...this.flattenKeys(value as Record<string, unknown>, fullKey)
        );
      } else {
        keys.push(fullKey);
      }
    });

    return keys;
  }

  // Check if translations are loaded for a language
  isLanguageLoaded(languageCode: string): boolean {
    return this.translationCache.has(languageCode);
  }

  // Clear translation cache (useful for testing or memory management)
  clearCache(): void {
    this.translationCache.clear();
    this.loadingStates.clear();
  }
}
