import {
  Component,
  inject,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
  ElementRef,
  Renderer2,
  effect,
} from '@angular/core';
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
  WordRequestService,
  WordRequest,
  WordRequestNotification,
} from '../../services/word-request.service';
import { MessageService } from '../../services/message.service';
import { NotificationService } from '../../services/notification.service';
import {
  VocabularyWord,
  ConjugationTable,
  Synonym,
  Example,
  Pronunciation,
  Media,
} from '../../models/word.model';
import { ValidationErrorInfo } from '@/models/error.model';
import { getLanguageConfig, LanguageConfig } from './conjugation.config';
import { Configs } from '../../shared/config';
import { Subscription } from 'rxjs';
import { Location } from '@angular/common';
import { LoadingStateComponent } from './components/loading-state';
import { ErrorStateComponent } from './components/error-state';
import { ValidationErrorStateComponent } from './components/validation-error-state';
import { WordHeaderComponent } from './components/word-header';
import { WordMediaComponent } from './components/word-media';
import {
  ProcessingStagesComponent,
  ProcessingStage,
} from './components/processing-stages';
import { WordTabsComponent } from './components/word-tabs';
import { WordDetailsComponent } from './components/word-details';

interface WordRequestData {
  sourceWord: string;
  sourceLanguage?: string;
  targetLanguage: string;
  requestId?: string;
}

interface WordNotificationData {
  source_word?: string;
  source_article?: string | null;
  source_additional_info?: string;
  target_word?: string;
  target_article?: string | null;
  target_additional_info?: string;
  source_definition?: string[];
  source_language?: string;
  target_pos?: string;
  target_part_of_speech?: string;
  target_syllables?: string[];
  target_phonetic_guide?: string;
  target_plural_form?: string | null;
  synonyms?: Synonym[];
  examples?: Example[];
  conjugation_table?: ConjugationTable | string;
  conjugation?: ConjugationTable | string;
  conjugation_not_available?: boolean;
  conjugation_message?: string;
  target_pronunciations?: Pronunciation;
  pronunciations?: Pronunciation;
  media?: Media;
  source_pos?: string;
  source_part_of_speech?: string;
  completed_parallel_tasks?: string[];
  validation_quality_approved?: boolean;
  classification_quality_approved?: boolean;
  translation_quality_approved?: boolean;
  media_quality_approved?: boolean;
  examples_quality_approved?: boolean;
  synonyms_quality_approved?: boolean;
  syllables_quality_approved?: boolean;
  conjugation_quality_approved?: boolean;
  processing_complete?: boolean;
  overall_quality_score?: number;
  validation_issue?: string;
  validation_suggestions?: { word: string; language: string }[];
}

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
    LoadingStateComponent,
    ErrorStateComponent,
    ValidationErrorStateComponent,
    WordHeaderComponent,
    WordMediaComponent,
    ProcessingStagesComponent,
    WordTabsComponent,
    WordDetailsComponent,
  ],
  templateUrl: './word-card.html',
  styleUrls: ['./word-card.scss'],
})
export class WordCard implements OnInit, OnDestroy {
  themeService = inject(ThemeService);
  translationService = inject(TranslationService);
  wordService = inject(WordService);
  wordRequestService = inject(WordRequestService);
  messageService = inject(MessageService);
  notificationService = inject(NotificationService);
  route = inject(ActivatedRoute);
  router = inject(Router);
  cdr = inject(ChangeDetectorRef);
  private location = inject(Location);
  private elementRef = inject(ElementRef);
  private renderer = inject(Renderer2);

  word: VocabularyWord | null = null;
  loading = true;
  error: string | null = null;
  langConfig: LanguageConfig = getLanguageConfig(null);

  get hasValidPronunciation(): boolean {
    return (
      !!this.word?.target_pronunciations?.audio &&
      this.word.target_pronunciations.audio.endsWith('.mp3')
    );
  }

  validationError: ValidationErrorInfo | null = null;
  private playSyllablesNext = false;
  private audio: HTMLAudioElement | null = null;
  private subscriptions = new Subscription();
  isRequestMode = false;

  loadingStates = {
    targetWord: true,
    syllables: true,
    pronunciation: true,
    definition: true,
    synonyms: true,
    examples: true,
    media: true,
    conjugation: true,
    languageInfo: true,
    sourcePos: true,
    targetPos: true,
  };

  processingStages: ProcessingStage[] = [
    {
      id: 'validation',
      name: 'wordCard.stages.validation',
      icon: 'check_circle',
      status: 'pending',
      category: 'sequential',
      order: 1,
      description: 'wordCard.stages.validationDesc',
    },
    {
      id: 'classification',
      name: 'wordCard.stages.classification',
      icon: 'category',
      status: 'pending',
      category: 'sequential',
      order: 2,
      description: 'wordCard.stages.classificationDesc',
    },
    {
      id: 'translation',
      name: 'wordCard.stages.translation',
      icon: 'translate',
      status: 'pending',
      category: 'sequential',
      order: 3,
      description: 'wordCard.stages.translationDesc',
    },
    {
      id: 'media',
      name: 'wordCard.stages.media',
      icon: 'image',
      status: 'pending',
      category: 'parallel',
      order: 4,
      description: 'wordCard.stages.mediaDesc',
    },
    {
      id: 'examples',
      name: 'wordCard.stages.examples',
      icon: 'format_quote',
      status: 'pending',
      category: 'parallel',
      order: 5,
      description: 'wordCard.stages.examplesDesc',
    },
    {
      id: 'synonyms',
      name: 'wordCard.stages.synonyms',
      icon: 'swap_horiz',
      status: 'pending',
      category: 'parallel',
      order: 6,
      description: 'wordCard.stages.synonymsDesc',
    },
    {
      id: 'syllables',
      name: 'wordCard.stages.syllables',
      icon: 'text_fields',
      status: 'pending',
      category: 'parallel',
      order: 7,
      description: 'wordCard.stages.syllablesDesc',
    },
    {
      id: 'pronunciation',
      name: 'wordCard.stages.pronunciation',
      icon: 'record_voice_over',
      status: 'pending',
      category: 'parallel',
      order: 8,
      description: 'wordCard.stages.pronunciationDesc',
    },
    {
      id: 'conjugation',
      name: 'wordCard.stages.conjugation',
      icon: 'rule',
      status: 'pending',
      category: 'parallel',
      order: 9,
      description: 'wordCard.stages.conjugationDesc',
    },
    {
      id: 'final_quality',
      name: 'wordCard.stages.finalQuality',
      icon: 'done_all',
      status: 'pending',
      category: 'final',
      order: 10,
      description: 'wordCard.stages.finalQualityDesc',
    },
  ];

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

  get hasFormasNoPersonales() {
    const conjugationTable = this.getConjugationTable();
    return !!conjugationTable?.[this.langConfig.nonPersonalForms.key];
  }

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

  ngOnInit() {
    this.validationError = null;

    const currentPath = this.location.path();

    if (currentPath === '/words/request') {
      this.handleRequestRoute();
      return;
    }

    if (currentPath === '/words/error') {
      this.handleErrorRoute();
      return;
    }

    const navigation = this.router.lastSuccessfulNavigation;
    const routeState = navigation?.extras?.state;

    if (routeState && routeState['isRequest']) {
      this.navigateToRequestRoute(routeState);
      return;
    }

    if (routeState && routeState['word']) {
      const wordFromState = routeState['word'] as VocabularyWord;

      if (wordFromState.media_ref && !wordFromState.media) {
        this.loadWordByPkSkWithMedia(
          wordFromState.pk,
          wordFromState.sk,
          wordFromState.media_ref
        );
        return;
      }

      this.word = wordFromState;
      this.langConfig = getLanguageConfig(this.word);
      this.setAllLoadingStates(false);
      this.loading = false;
      return;
    }

    if (routeState && routeState['pk'] && routeState['sk']) {
      this.loadWordByPkSk(routeState['pk'], routeState['sk']);
      return;
    }

    this.handleUrlParameters();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  constructor() {
    effect(() => {
      if (this.themeService.isDarkMode()) {
        this.renderer.addClass(this.elementRef.nativeElement, 'dark-theme');
      } else {
        this.renderer.removeClass(this.elementRef.nativeElement, 'dark-theme');
      }
    });
  }

  private navigateToRequestRoute(routeState: Record<string, unknown>): void {
    this.router.navigate(['/words/request'], {
      state: routeState,
      replaceUrl: true,
    });
  }

  private handleRequestRoute(): void {
    const navigation = this.router.lastSuccessfulNavigation;
    const routeState = navigation?.extras?.state;

    if (routeState && routeState['isRequest']) {
      this.handleWordRequest(routeState);
    } else {
      this.router.navigate(['/search']);
    }
  }

  private handleErrorRoute(): void {
    const navigation = this.router.lastSuccessfulNavigation;
    const routeState = navigation?.extras?.state;

    this.loading = false;

    if (routeState && routeState['error']) {
      this.error = routeState['error'] as string;
    } else if (routeState && routeState['validationError']) {
      this.validationError = routeState[
        'validationError'
      ] as ValidationErrorInfo;
      this.error = 'Word validation failed';
    } else {
      this.error = 'An error occurred while processing your request';
    }
  }

  private handleWordRequest(routeState: Record<string, unknown>): void {
    const requestData = routeState['requestData'] as WordRequestData;
    if (!requestData) {
      this.error = 'Invalid request data';
      this.loading = false;
      return;
    }

    this.isRequestMode = true;

    this.createSkeletonWord(requestData);

    this.subscriptions.add(
      this.wordRequestService.notifications$.subscribe((notification) => {
        this.handleWordRequestNotification(notification);
      })
    );

    if (requestData.requestId && requestData.requestId !== 'new') {
      this.wordRequestService.reconnectToRequest(
        requestData.sourceWord,
        requestData.sourceLanguage || 'auto',
        requestData.targetLanguage,
        requestData.requestId
      );
    } else {
      const request: WordRequest = {
        source_word: requestData.sourceWord,
        source_language: requestData.sourceLanguage,
        target_language: requestData.targetLanguage,
      };

      this.wordRequestService.submitWordRequest(request).subscribe({
        next: () => {
          // empty
        },
        error: () => {
          this.navigateToErrorUrl({
            error: 'Failed to submit word request. Please try again.',
          });
        },
      });
    }
  }

  private navigateToWordUrl(): void {
    if (!this.word) return;

    const sourceLanguage = this.getLanguageCode(
      this.word.source_language || 'en'
    );
    const targetLanguage = this.getLanguageCode(
      this.word.target_language || 'es'
    );
    const sourceWord = encodeURIComponent(this.word.source_word);
    const rawPos = this.word.source_pos || 'pending';
    const normalizedPos = this.normalizePOS(rawPos);

    const wordUrl = `/words/${sourceLanguage}/${targetLanguage}/${normalizedPos}/${sourceWord}`;

    this.router.navigate([wordUrl], { replaceUrl: true });
  }

  private navigateToErrorUrl(errorData: {
    error?: string;
    validationError?: ValidationErrorInfo;
  }): void {
    this.router.navigate(['/words/error'], {
      state: errorData,
      replaceUrl: true,
    });
  }

  private createSkeletonWord(requestData: WordRequestData): void {
    this.word = {
      pk: `SRC#${requestData.sourceLanguage || 'auto'}#${
        requestData.sourceWord
      }`,
      sk: `TGT#${requestData.targetLanguage}`,
      source_word: requestData.sourceWord,
      source_language: requestData.sourceLanguage || '',
      source_pos: 'pending',
      source_definition: [],
      target_word: '',
      target_language: requestData.targetLanguage,
      target_pos: '',
      target_syllables: [],
      target_phonetic_guide: '',
      target_pronunciations: undefined,
      synonyms: [],
      examples: [],
      conjugation_table: undefined,
      media_ref: undefined,
      media: undefined,
      created_by: 'user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    this.loadingStates = {
      targetWord: true,
      syllables: true,
      pronunciation: true,
      definition: true,
      synonyms: true,
      examples: true,
      media: true,
      conjugation: true,
      languageInfo: true,
      sourcePos: true,
      targetPos: true,
    };

    this.initializeProcessingStages();

    this.langConfig = getLanguageConfig(this.word);
    this.loading = true;
  }

  private handleWordRequestNotification(
    notification: WordRequestNotification
  ): void {
    if (!this.isRequestMode || !this.word) return;

    const isRedirectNotification =
      notification.status === 'redirect' ||
      (notification.word_data &&
        notification.word_data['word_exists'] === true);

    if (isRedirectNotification && notification.word_data) {
      this.handleWordExistsRedirect(notification.word_data);
      return;
    }

    switch (notification.status) {
      case 'processing':
        if (notification.word_data) {
          this.updateWordFromNotification(notification.word_data);
          this.updateStageFromWebSocketData(notification.word_data);
        }
        break;
      case 'completed':
        if (notification.word_data) {
          this.updateWordFromNotification(notification.word_data, true);
          this.updateStageFromWebSocketData(notification.word_data);
          this.setAllStagesCompleted();

          this.navigateToWordUrl();
        }
        this.loading = false;
        break;
      case 'redirect':
        if (notification.word_data) {
          this.handleWordExistsRedirect(notification.word_data);
        }
        break;
      case 'failed':
        this.navigateToErrorUrl({
          error: notification.message || 'Failed to create word',
        });
        break;
      case 'invalid':
        if (notification.word_data) {
          const validationError = {
            issue: notification.word_data['validation_issue'] as
              | string
              | undefined,
            detectedLanguage: notification.word_data['source_language'] as
              | string
              | undefined,
            suggestions:
              (notification.word_data['validation_suggestions'] as {
                word: string;
                language: string;
              }[]) || [],
          };
          this.navigateToErrorUrl({ validationError });
        } else {
          const error =
            notification.error ||
            notification.message ||
            'Word validation failed';
          this.navigateToErrorUrl({ error });
        }
        break;
      default:
    }
  }

  private handleWordExistsRedirect(
    wordData: WordNotificationData & {
      word_exists?: boolean;
      pk?: string;
      sk?: string;
      media_ref?: string;
      existing_item?: {
        PK: string;
        SK: string;
        media_ref?: string;
      };
    }
  ): void {
    if (!wordData.word_exists) {
      return;
    }

    const dataAsRecord = wordData as Record<string, unknown>;
    let pk = (dataAsRecord['PK'] as string) || '';
    let sk = (dataAsRecord['SK'] as string) || '';
    let mediaRef = (wordData.media_ref as string) || '';

    if ((!pk || !sk) && wordData.existing_item) {
      const existingItem = wordData.existing_item as Record<string, unknown>;
      pk = pk || (existingItem['PK'] as string) || '';
      sk = sk || (existingItem['SK'] as string) || '';
      mediaRef = mediaRef || (existingItem['media_ref'] as string) || '';
    }

    if (!pk || !sk) {
      this.error = 'Word exists but redirect data is incomplete';
      this.loading = false;
      return;
    }

    this.updateHeaderNotificationToRedirect(pk, sk, mediaRef);

    this.messageService.showInfoMessage(
      this.translationService.translate('wordCard.wordAlreadyExists'),
      4000
    );

    this.isRequestMode = false;

    if (mediaRef) {
      this.loadWordByPkSkWithMedia(pk, sk, mediaRef, true);
    } else {
      this.loadWordByPkSk(pk, sk, true);
    }
  }

  private updateHeaderNotificationToRedirect(
    pk: string,
    sk: string,
    mediaRef: string
  ): void {
    if (!this.word) return;

    const sourceLanguage = this.word.source_language || 'en';
    const targetLanguage = this.word.target_language || 'es';
    const sourceWord = this.word.source_word;

    const cleanedWord = sourceWord.replace(/\s+/g, '_').toLowerCase();
    const srcLang = this.getLanguageCode(sourceLanguage);
    const tgtLang = this.getLanguageCode(targetLanguage);
    const notificationId = `word-request-${cleanedWord}-${srcLang}-${tgtLang}`;

    const link = this.generateWordLink(pk, sk, sourceWord);

    this.notificationService.addOrUpdateNotification(
      {
        id: notificationId,
        title: 'Found',
        message: `"${sourceWord}" already exists in our database`,
        status: 'redirect',
        sourceWord,
        targetLanguage: targetLanguage as string,
        requestId: notificationId,
        link,
        pk,
        sk,
        mediaRef,
      },
      true
    );
  }

  private getLanguageCode(language: string): string {
    const langMap: Record<string, string> = {
      English: 'en',
      Spanish: 'es',
      German: 'de',
      en: 'en',
      es: 'es',
      de: 'de',
    };
    return langMap[language] || language.toLowerCase().slice(0, 2);
  }

  private generateWordLink(pk: string, sk: string, sourceWord: string): string {
    const pkParts = pk.split('#');
    const skParts = sk.split('#');

    if (pkParts.length >= 3 && skParts.length >= 2) {
      const sourceLang = pkParts[1];
      const targetLang = skParts[1];

      let pos = 'pending';
      const posIndex = skParts.findIndex((part) => part === 'POS');
      if (posIndex !== -1 && posIndex + 1 < skParts.length) {
        pos = skParts[posIndex + 1];
      }

      const encodedWord = encodeURIComponent(sourceWord);
      return `/words/${sourceLang}/${targetLang}/${pos}/${encodedWord}`;
    }

    return '';
  }

  private updateWordFromNotification(
    data: WordNotificationData,
    isFinal = false
  ): void {
    if (!this.word) return;

    if (Object.prototype.hasOwnProperty.call(data, 'source_word')) {
      this.word.source_word = data.source_word || '';
    }
    if (Object.prototype.hasOwnProperty.call(data, 'source_article')) {
      this.word.source_article = data.source_article;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'source_additional_info')) {
      this.word.source_additional_info = data.source_additional_info;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'target_word')) {
      this.word.target_word = data.target_word || '';
      this.loadingStates.targetWord = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'target_article')) {
      this.word.target_article = data.target_article;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'target_additional_info')) {
      this.word.target_additional_info = data.target_additional_info;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'source_definition')) {
      this.word.source_definition = data.source_definition || [];
      this.loadingStates.definition = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'source_language')) {
      this.word.source_language = data.source_language || '';
      this.loadingStates.languageInfo = false;
    }
    if (
      Object.prototype.hasOwnProperty.call(data, 'target_pos') ||
      Object.prototype.hasOwnProperty.call(data, 'target_part_of_speech')
    ) {
      this.word.target_pos =
        data.target_pos || data.target_part_of_speech || '';
      this.loadingStates.targetPos = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'target_syllables')) {
      this.word.target_syllables = data.target_syllables || [];
      this.loadingStates.syllables = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'target_phonetic_guide')) {
      this.word.target_phonetic_guide = data.target_phonetic_guide || '';
      this.loadingStates.pronunciation = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'target_plural_form')) {
      this.word.target_plural_form = data.target_plural_form;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'synonyms')) {
      this.word.synonyms = data.synonyms || [];
      this.loadingStates.synonyms = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'examples')) {
      this.word.examples = data.examples || [];
      this.loadingStates.examples = false;
    }
    if (
      Object.prototype.hasOwnProperty.call(data, 'conjugation_table') ||
      Object.prototype.hasOwnProperty.call(data, 'conjugation')
    ) {
      this.word.conjugation_table = data.conjugation_table || data.conjugation;
      this.loadingStates.conjugation = false;
    }
    if (
      Object.prototype.hasOwnProperty.call(data, 'conjugation_not_available') ||
      (Object.prototype.hasOwnProperty.call(data, 'conjugation_message') &&
        typeof data.conjugation_message === 'string' &&
        data.conjugation_message.includes('not a verb')) ||
      (Object.prototype.hasOwnProperty.call(data, 'conjugation') &&
        typeof data.conjugation === 'string' &&
        (data.conjugation.includes('not a verb') ||
          data.conjugation.includes('no conjugation table')))
    ) {
      this.loadingStates.conjugation = false;
    }
    if (
      Object.prototype.hasOwnProperty.call(data, 'target_pronunciations') ||
      Object.prototype.hasOwnProperty.call(data, 'pronunciations')
    ) {
      this.word.target_pronunciations =
        data.target_pronunciations || data.pronunciations;
      this.loadingStates.pronunciation = false;
    }
    if (Object.prototype.hasOwnProperty.call(data, 'media')) {
      this.word.media = data.media;
      this.loadingStates.media = false;
    }

    if (Object.prototype.hasOwnProperty.call(data, 'source_definition')) {
      this.word.source_definition = data.source_definition || [];
    }

    if (
      Object.prototype.hasOwnProperty.call(data, 'source_part_of_speech') ||
      Object.prototype.hasOwnProperty.call(data, 'source_pos')
    ) {
      this.word.source_pos =
        data.source_part_of_speech || data.source_pos || '';
      this.loadingStates.sourcePos = false;
    }
    if (
      Object.prototype.hasOwnProperty.call(data, 'target_part_of_speech') ||
      Object.prototype.hasOwnProperty.call(data, 'target_pos')
    ) {
      this.word.target_pos =
        data.target_part_of_speech || data.target_pos || '';
      this.loadingStates.targetPos = false;
    }

    if (
      Object.prototype.hasOwnProperty.call(data, 'completed_parallel_tasks') &&
      Array.isArray(data.completed_parallel_tasks)
    ) {
      const completedTasks = data.completed_parallel_tasks;

      if (completedTasks.includes('examples')) {
        this.loadingStates.examples = false;
      }
      if (completedTasks.includes('synonyms')) {
        this.loadingStates.synonyms = false;
      }
      if (completedTasks.includes('pronunciation')) {
        this.loadingStates.pronunciation = false;
      }
      if (completedTasks.includes('media')) {
        this.loadingStates.media = false;
      }
      if (completedTasks.includes('conjugation')) {
        this.loadingStates.conjugation = false;
      }
    }

    if (isFinal) {
      this.setAllLoadingStates(false);
    }

    this.langConfig = getLanguageConfig(this.word);
    this.cdr.detectChanges();
  }

  private updateStageFromWebSocketData(data: WordNotificationData): void {
    if (data.validation_quality_approved) {
      this.updateStageStatus('validation', true);
    }

    if (data.classification_quality_approved) {
      this.updateStageStatus('classification', true);
      this.loadingStates.definition = false;
    }

    if (data.translation_quality_approved) {
      this.updateStageStatus('translation', true);
    }

    if (data.translation_quality_approved) {
      this.activateParallelStages();
    }

    this.updateStageStatus('media', data.media_quality_approved);
    this.updateStageStatus('examples', data.examples_quality_approved);
    this.updateStageStatus('synonyms', data.synonyms_quality_approved);
    this.updateStageStatus('syllables', data.syllables_quality_approved);
    this.updateStageStatus('conjugation', data.conjugation_quality_approved);

    if (data.pronunciations || data.target_pronunciations) {
      this.updateStageStatus('pronunciation', true);
    }

    if (data.processing_complete || data.overall_quality_score) {
      this.updateStageStatus('final_quality', true);
    }

    if (
      data.completed_parallel_tasks &&
      Array.isArray(data.completed_parallel_tasks)
    ) {
      data.completed_parallel_tasks.forEach((taskName: string) => {
        this.updateStageStatus(taskName, true);
      });
    }
  }

  private updateStageStatus(
    stageId: string,
    approved: boolean | undefined
  ): void {
    if (approved === true) {
      const stage = this.processingStages.find((s) => s.id === stageId);
      if (stage && stage.status !== 'completed') {
        stage.status = 'completed';
        this.activateNextSequentialStage(stageId);
      }
    }
  }

  private activateNextSequentialStage(completedStageId: string): void {
    const completedStage = this.processingStages.find(
      (s) => s.id === completedStageId
    );
    if (!completedStage || completedStage.category !== 'sequential') return;

    const nextSequentialStage = this.processingStages.find(
      (s) => s.category === 'sequential' && s.order === completedStage.order + 1
    );

    if (nextSequentialStage && nextSequentialStage.status === 'pending') {
      nextSequentialStage.status = 'active';
    } else if (completedStage.order === 3) {
      this.activateParallelStages();
    }
  }

  private activateParallelStages(): void {
    this.processingStages.forEach((stage) => {
      if (stage.category === 'parallel' && stage.status === 'pending') {
        stage.status = 'active';
      }
    });
  }

  private initializeProcessingStages(): void {
    this.processingStages.forEach((stage) => {
      stage.status = 'pending';
    });
    const firstStage = this.processingStages.find((s) => s.order === 1);
    if (firstStage) {
      firstStage.status = 'active';
    }
  }

  private setAllStagesCompleted(): void {
    this.processingStages.forEach((stage) => {
      stage.status = 'completed';
    });
  }

  private handleUrlParameters(): void {
    const sourceLanguage = this.route.snapshot.paramMap.get('sourceLanguage');
    const targetLanguage = this.route.snapshot.paramMap.get('targetLanguage');
    const word = this.route.snapshot.paramMap.get('word');
    const pos = this.route.snapshot.paramMap.get('pos');

    if (sourceLanguage && targetLanguage && word) {
      const decodedWord = decodeURIComponent(word).toLowerCase().trim();

      const pk = `SRC#${sourceLanguage}#${decodedWord}`;
      let sk = `TGT#${targetLanguage}`;
      if (pos && pos !== 'pending') {
        const normalizedPos = this.normalizePOS(pos.trim());
        sk += `#POS#${normalizedPos}`;
      }

      this.loadWordByPkSk(pk, sk);
    } else {
      this.error =
        'Invalid parameters: missing source language, target language, or word';
      this.loading = false;
    }
  }

  loadWordByPkSk(pk: string, sk: string, isRedirect = false) {
    this.loading = true;
    this.error = null;
    this.wordService.getWordByPkSk(pk, sk).subscribe({
      next: (data) => {
        if (data) {
          this.word = data;
          this.langConfig = getLanguageConfig(this.word);
          this.setAllLoadingStates(false);

          if (isRedirect) {
            this.navigateToWordUrl();
          }
        } else {
          this.error = this.translationService.translate('wordCard.notFound');
        }
        this.loading = false;
      },
      error: () => {
        this.error = this.translationService.translate('wordCard.error');
        this.loading = false;
      },
    });
  }

  loadWordByPkSkWithMedia(
    pk: string,
    sk: string,
    mediaRef: string,
    isRedirect = false
  ) {
    this.loading = true;
    this.error = null;

    this.wordService.getWordByPkSkWithMedia(pk, sk, mediaRef).subscribe({
      next: (data) => {
        if (data) {
          this.word = data;
          this.langConfig = getLanguageConfig(this.word);
          this.setAllLoadingStates(false);

          if (isRedirect) {
            this.navigateToWordUrl();
          }
        } else {
          this.error = this.translationService.translate('wordCard.notFound');
        }
        this.loading = false;
      },
      error: () => {
        this.error = this.translationService.translate('wordCard.loadError');
        this.loading = false;
      },
    });
  }

  private setAllLoadingStates(state: boolean): void {
    Object.keys(this.loadingStates).forEach((key) => {
      const k = key as keyof typeof this.loadingStates;
      this.loadingStates[k] = state;
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

    if (!urlToPlay && this.playSyllablesNext) {
      urlToPlay = this.getS3Url(this.word.target_pronunciations.audio);
    }

    if (urlToPlay) {
      this.audio = new Audio(urlToPlay);
      this.audio.play().catch(() => {
        // empty
      });

      if (
        this.word.target_pronunciations.syllables &&
        this.word.target_pronunciations.syllables.endsWith('.mp3')
      ) {
        this.playSyllablesNext = !this.playSyllablesNext;
      } else {
        this.playSyllablesNext = false;
      }
    }
  }

  getPartOfSpeechLabel(pos: string): string {
    return this.translationService.translate(`wordCard.pos.${pos}`) || pos;
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
    this.validationError = null;
    this.router.navigate(['/search']);
  }

  searchSuggestion(suggestion: { word: string; language: string }): void {
    let targetLanguage = this.word?.target_language;

    if (!targetLanguage) {
      const navigation = this.router.lastSuccessfulNavigation;
      const routeState = navigation?.extras?.state;

      if (routeState && routeState['requestData']) {
        const requestData = routeState['requestData'] as WordRequestData;
        targetLanguage = requestData.targetLanguage;
      }

      if (!targetLanguage) {
        targetLanguage = 'es';
      }
    }

    const sourceLanguageCode = this.getLanguageCode(suggestion.language);
    const targetLanguageCode = this.getLanguageCode(targetLanguage);

    this.router.navigate(['/search'], {
      queryParams: {
        query: suggestion.word,
        source: sourceLanguageCode,
        target: targetLanguageCode,
        autosearch: 'true',
      },
    });
  }

  isArray(value: unknown): value is unknown[] {
    return Array.isArray(value);
  }

  getLanguageFlag(langCode: string | undefined): string {
    if (!langCode) return '';

    const lang = langCode.toLowerCase();

    const flagMap: Record<string, string> = {
      en: '🇬🇧',
      english: '🇬🇧',
      es: '🇪🇸',
      spanish: '🇪🇸',
      de: '🇩🇪',
      german: '🇩🇪',
    };

    return flagMap[lang] || langCode.toUpperCase();
  }

  getS3Url(key: string | undefined): string {
    if (!key || key === '<nil>') return '';

    if (key.startsWith('http://') || key.startsWith('https://')) {
      return key;
    }

    const cleanKey = key.startsWith('/') ? key.slice(1) : key;

    return `${Configs.S3_BASE_URL}${cleanKey}`;
  }

  private normalizePOS(pos: string): string {
    if (!pos) return 'pending';
    const posLower = pos.toLowerCase();
    return posLower.includes('noun') ? 'noun' : posLower;
  }

  getDisplayCreatedBy(createdBy: string | undefined): string {
    if (!createdBy) return '';
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (uuidRegex.test(createdBy)) {
      return createdBy.split('-')[0];
    }
    return createdBy;
  }
}
