import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { WordService } from '../../services/word.service';
import {
  VocabularyWord,
  ConjugationTable,
  NonPersonalForms,
  Mood,
  Tense,
} from '../../models/word.model';
import { getLanguageConfig, LanguageConfig } from './conjugation.config';
import { Configs } from '../../shared/config';

@Component({
  selector: 'app-word-card',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatChipsModule,
    MatDividerModule,
    MatProgressSpinnerModule,
    TranslatePipe,
  ],
  templateUrl: './word-card.html',
  styleUrls: ['./word-card.scss'],
})
export class WordCard implements OnInit {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  route = inject(ActivatedRoute);
  router = inject(Router);

  word: VocabularyWord | null = null;
  loading = true;
  error: string | null = null;
  langConfig: LanguageConfig = getLanguageConfig(null);
  private playSyllablesNext = false;
  private audio: HTMLAudioElement | null = null;

  // Computed properties for performance optimization
  get indicativeTenses() {
    return this.getIndicativeTenses();
  }

  get subjunctiveTenses() {
    return this.getSubjunctiveTenses();
  }

  get hasTargetSyllables() {
    return !!(
      this.word?.target_syllables && this.word.target_syllables.length > 0
    );
  }

  get hasMedia() {
    return !!this.word?.media;
  }

  get hasSynonyms() {
    return !!(this.word?.synonyms && this.word.synonyms.length > 0);
  }

  get hasExamples() {
    return !!(this.word?.examples && this.word.examples.length > 0);
  }

  get hasConjugationTable() {
    return !!this.word?.conjugation_table;
  }

  get hasIndicativo() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.moods.indicative];
  }

  get hasSubjuntivo() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.moods.subjunctive];
  }

  get hasFormasNoPersonales() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.nonPersonalForms.key];
  }

  // Helper method to get properly parsed conjugation table
  getConjugationTable(): ConjugationTable | null {
    if (!this.word?.conjugation_table) return null;

    if (typeof this.word.conjugation_table === 'object') {
      return this.word.conjugation_table as ConjugationTable;
    }

    if (typeof this.word.conjugation_table === 'string') {
      try {
        return JSON.parse(this.word.conjugation_table) as ConjugationTable;
      } catch (error) {
        console.error('Error parsing conjugation table JSON:', error);
        return null;
      }
    }

    return null;
  }

  // Helper methods to get correct mood names for each language
  getIndicativeMoodName(): string {
    return this.langConfig.moods.indicative;
  }

  getSubjunctiveMoodName(): string {
    return this.langConfig.moods.subjunctive;
  }

  getNonPersonalFormsKey(): string {
    return this.langConfig.nonPersonalForms.key;
  }

  // Get non-personal forms data dynamically based on language
  getNonPersonalForms(): NonPersonalForms | null {
    const key = this.getNonPersonalFormsKey();
    const conjugationTable = this.getConjugationTable();
    return (conjugationTable?.[key] as NonPersonalForms) || null;
  }

  // Get specific non-personal form values
  getInfinitive(): string {
    const forms = this.getNonPersonalForms();
    const infinitiveKey = this.langConfig.nonPersonalForms.infinitive;
    return forms?.[infinitiveKey] || '';
  }

  getParticiple(): string {
    const forms = this.getNonPersonalForms();
    const participleKey = this.langConfig.nonPersonalForms.participle;
    return forms?.[participleKey] || '';
  }

  getGerund(): string {
    const forms = this.getNonPersonalForms();
    const gerundKey = this.langConfig.nonPersonalForms.gerund;
    return forms?.[gerundKey] || '';
  }

  getLabel(key: string): string {
    if (key in this.langConfig.labels) {
      const labelKey = key as keyof LanguageConfig['labels'];
      const labelValue = this.langConfig.labels[labelKey];
      if (typeof labelValue === 'string') {
        return labelValue;
      }
    }
    if (key in this.langConfig.labels.tenses) {
      return this.langConfig.labels.tenses[key];
    }
    return key;
  }

  ngOnInit() {
    // Get navigation state
    const navigation = this.router.lastSuccessfulNavigation;
    const routeState = navigation?.extras?.state;

    // Case 1: Full word object in state (from search) - fastest path
    if (routeState && routeState['word']) {
      const wordFromState = routeState['word'] as VocabularyWord;

      // If word has media_ref but no media, fetch complete word + media in one call
      if (wordFromState.media_ref && !wordFromState.media) {
        this.loadWordByPkSkWithMedia(
          wordFromState.pk,
          wordFromState.sk,
          wordFromState.media_ref
        );
        return;
      }

      // Use word immediately if it already has media or no media_ref
      this.word = wordFromState;
      this.langConfig = getLanguageConfig(this.word);
      this.loading = false;
      return;
    }

    // Case 2: PK/SK in state for optimized fetch (fallback)
    if (routeState && routeState['pk'] && routeState['sk']) {
      this.loadWordByPkSk(routeState['pk'], routeState['sk']);
      return;
    }

    // Extract parameters from route
    const sourceLanguage = this.route.snapshot.paramMap.get('sourceLanguage');
    const targetLanguage = this.route.snapshot.paramMap.get('targetLanguage');
    const word = this.route.snapshot.paramMap.get('word');
    const pos = this.route.snapshot.paramMap.get('pos');

    if (sourceLanguage && targetLanguage && word) {
      // With POS - construct PK/SK and fetch directly
      const pk = `SRC#${sourceLanguage}#${word.toLowerCase().trim()}`;
      let sk = `TGT#${targetLanguage}`;
      if (pos) {
        sk += `#POS#${pos.toLowerCase().trim()}`;
      }
      this.loadWordByPkSk(pk, sk);
    } else {
      this.error =
        'Invalid parameters: missing source language, target language, or word';
      this.loading = false;
    }
  }

  loadWordByPkSk(pk: string, sk: string) {
    this.loading = true;
    this.error = null;
    this.wordService.getWordByPkSk(pk, sk).subscribe({
      next: (data) => {
        if (data) {
          this.word = data;
          this.langConfig = getLanguageConfig(this.word);
        } else {
          this.error = this.translationService.translate('wordCard.notFound');
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('API Error:', err);
        this.error = this.translationService.translate('wordCard.error');
        this.loading = false;
      },
    });
  }

  loadWordByPkSkWithMedia(pk: string, sk: string, mediaRef: string) {
    this.loading = true;
    this.error = null;

    this.wordService.getWordByPkSkWithMedia(pk, sk, mediaRef).subscribe({
      next: (data) => {
        if (data) {
          this.word = data;
          this.langConfig = getLanguageConfig(this.word);
        } else {
          this.error = this.translationService.translate('wordCard.notFound');
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('API Error:', err);
        this.error = this.translationService.translate('wordCard.loadError');
        this.loading = false;
      },
    });
  }

  playCombinedAudio() {
    if (this.audio && !this.audio.paused) {
      this.audio.pause();
    }

    if (!this.word?.target_pronunciations) {
      return;
    }

    let urlToPlay = this.playSyllablesNext
      ? this.getS3Url(this.word.target_pronunciations.syllables)
      : this.getS3Url(this.word.target_pronunciations.audio);

    // Fallback to main pronunciation if syllables URL is next but not available
    if (!urlToPlay && this.playSyllablesNext) {
      urlToPlay = this.getS3Url(this.word.target_pronunciations.audio);
    }

    if (urlToPlay) {
      this.audio = new Audio(urlToPlay);
      this.audio.play().catch((err) => {
        console.error('Error playing audio:', err);
      });

      // Toggle for the next click, only if syllable audio exists.
      if (this.word.target_pronunciations.syllables) {
        this.playSyllablesNext = !this.playSyllablesNext;
      } else {
        this.playSyllablesNext = false;
      }
    }
  }

  getPartOfSpeechLabel(pos: string): string {
    return this.translationService.translate(`wordCard.pos.${pos}`) || pos;
  }

  getIndicativeTenses(): string[] {
    const conjugationTable = this.getConjugationTable();
    const indicativeMoodName = this.getIndicativeMoodName();
    const moodData = conjugationTable?.[indicativeMoodName];
    return moodData ? Object.keys(moodData) : [];
  }

  getSubjunctiveTenses(): string[] {
    const conjugationTable = this.getConjugationTable();
    const subjunctiveMoodName = this.getSubjunctiveMoodName();
    const moodData = conjugationTable?.[subjunctiveMoodName];
    return moodData ? Object.keys(moodData) : [];
  }

  getConjugationPronouns(mood: string): string[] {
    const conjugationTable = this.getConjugationTable();
    const moodData = conjugationTable?.[mood] as Mood;
    if (!moodData) return [];

    // Get pronouns from the first available tense
    const firstTense = Object.values(moodData)[0] as Tense;
    return firstTense ? Object.keys(firstTense) : [];
  }

  getPronounLabel(pronoun: string): string {
    return this.langConfig.labels.pronouns[pronoun] || pronoun;
  }

  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString(
      this.translationService.getCurrentLanguage()().code,
      {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }
    );
  }

  goBack() {
    this.router.navigate(['/search']);
  }

  isArray(value: unknown): value is unknown[] {
    return Array.isArray(value);
  }

  asArray(value: string | string[]): string[] {
    return value as string[];
  }

  getTense(mood: string, tense: string): Record<string, string> | null {
    const conjugationTable = this.getConjugationTable();
    const moodData = conjugationTable?.[mood] as Mood;
    return moodData?.[tense] || null;
  }

  getLanguageFlag(langCode: string | undefined): string {
    if (!langCode) return '';

    const flagMap: Record<string, string> = {
      en: '🇬🇧',
      es: '🇪🇸',
      de: '🇩🇪',
    };

    return flagMap[langCode.toLowerCase()] || langCode.toUpperCase();
  }

  getConjugationValue(mood: string, tense: string, pronoun: string): string {
    const tenseData = this.getTense(mood, tense);
    return tenseData?.[pronoun] || '';
  }

  // New helper methods for restructured conjugation tables
  getGroupedTenses(mood: string): string[][] {
    const tenses =
      mood === this.getIndicativeMoodName()
        ? this.getIndicativeTenses()
        : this.getSubjunctiveTenses();

    // Group tenses into chunks of 3
    const grouped: string[][] = [];
    for (let i = 0; i < tenses.length; i += 3) {
      grouped.push(tenses.slice(i, i + 3));
    }
    return grouped;
  }

  getConjugationValueForTense(
    mood: string,
    tense: string,
    pronoun: string
  ): string {
    const conjugationTable = this.getConjugationTable();
    const moodData = conjugationTable?.[mood] as Mood;
    const tenseData = moodData?.[tense] as Tense;
    return tenseData?.[pronoun] || '';
  }

  getS3Url(key: string | undefined): string {
    if (!key) return '';

    // If key is already a full URL, return it as is
    if (key.startsWith('http://') || key.startsWith('https://')) {
      return key;
    }

    // If key starts with a slash, remove it to avoid double slashes
    const cleanKey = key.startsWith('/') ? key.slice(1) : key;

    return `${Configs.S3_BASE_URL}${cleanKey}`;
  }
}
