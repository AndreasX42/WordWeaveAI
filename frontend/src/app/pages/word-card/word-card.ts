import {
  Component,
  inject,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
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
  WordRequestNotification,
} from '../../services/word-request.service';
import { MessageService } from '../../services/message.service';
import {
  VocabularyWord,
  ConjugationTable,
  NonPersonalForms,
  Mood,
  Tense,
  Synonym,
  Example,
  Pronunciation,
  Media,
} from '../../models/word.model';
import { getLanguageConfig, LanguageConfig } from './conjugation.config';
import { Configs } from '../../shared/config';
import { Subscription } from 'rxjs';
import { Location } from '@angular/common';

interface ProcessingStage {
  id: string;
  name: string;
  icon: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  category: 'sequential' | 'parallel' | 'final';
  order: number;
  description: string;
}

interface WordRequestData {
  sourceWord: string;
  sourceLanguage?: string;
  targetLanguage: string;
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
  route = inject(ActivatedRoute);
  router = inject(Router);
  cdr = inject(ChangeDetectorRef);
  private location = inject(Location);

  word: VocabularyWord | null = null;
  loading = true;
  error: string | null = null;
  langConfig: LanguageConfig = getLanguageConfig(null);

  // Validation error details for better UI display
  validationError: {
    issue?: string;
    detectedLanguage?: string;
    suggestions?: { word: string; language: string }[];
  } | null = null;
  private playSyllablesNext = false;
  private audio: HTMLAudioElement | null = null;
  private subscriptions = new Subscription();
  isRequestMode = false;

  // Progressive loading states for different sections
  loadingStates = {
    targetWord: true,
    syllables: true,
    pronunciation: true,
    definition: true, // Definition loading state
    synonyms: true,
    examples: true,
    media: true,
    conjugation: true,
    languageInfo: true, // Language flags
    sourcePos: true, // Source part of speech
    targetPos: true, // Target part of speech
  };

  // Progressive Processing Stages
  processingStages: ProcessingStage[] = [
    // Sequential Stages
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
    // Parallel Stages
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
    // Final Stage
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
    // Clear any previous validation errors
    this.validationError = null;

    // Get navigation state
    const navigation = this.router.lastSuccessfulNavigation;
    const routeState = navigation?.extras?.state;

    // Case 1: Word request state (from request dialog) - skeleton loading with WebSocket
    if (routeState && routeState['isRequest']) {
      this.handleWordRequest(routeState);
      return;
    }

    // Case 2: Full word object in state (from search) - fastest path
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
      this.setAllLoadingStates(false); // Word is fully loaded
      this.loading = false;
      return;
    }

    // Case 3: PK/SK in state for optimized fetch (fallback)
    if (routeState && routeState['pk'] && routeState['sk']) {
      this.loadWordByPkSk(routeState['pk'], routeState['sk']);
      return;
    }

    // Case 4: URL parameters - construct PK/SK and fetch
    this.handleUrlParameters();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  private handleWordRequest(routeState: Record<string, unknown>): void {
    const requestData = routeState['requestData'] as WordRequestData;
    if (!requestData) {
      this.error = 'Invalid request data';
      this.loading = false;
      return;
    }

    this.isRequestMode = true;

    // Create skeleton word object for immediate display
    this.createSkeletonWord(requestData);

    // Subscribe to WebSocket notifications to update the word
    this.subscriptions.add(
      this.wordRequestService.notifications$.subscribe((notification) => {
        this.handleWordRequestNotification(notification);
      })
    );
  }

  private createSkeletonWord(requestData: WordRequestData): void {
    // Create a skeleton word object that will be filled by WebSocket updates
    this.word = {
      pk: `SRC#${requestData.sourceLanguage || 'auto'}#${
        requestData.sourceWord
      }`,
      sk: `TGT#${requestData.targetLanguage}`,
      source_word: requestData.sourceWord,
      source_language: requestData.sourceLanguage || '',
      source_pos: 'pending', // Temporary POS
      source_definition: [],
      target_word: '', // Will be filled by WebSocket
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

    // Reset progressive loading states for request mode
    this.loadingStates = {
      targetWord: true,
      syllables: true,
      pronunciation: true,
      definition: true, // Definition loading state
      synonyms: true,
      examples: true,
      media: true,
      conjugation: true,
      languageInfo: true, // Reset on new request
      sourcePos: true,
      targetPos: true,
    };

    // Initialize processing stages and activate the first stage
    this.initializeProcessingStages();

    this.langConfig = getLanguageConfig(this.word);
    this.loading = true; // Keep loading state for skeleton
    console.log(
      '🎯 Skeleton word created for:',
      requestData.sourceWord,
      '→',
      requestData.targetLanguage
    );
    console.log(
      '📊 Progressive loading states initialized:',
      this.loadingStates
    );
  }

  private handleWordRequestNotification(
    notification: WordRequestNotification
  ): void {
    // Console log all WebSocket notifications as requested
    console.log('🔔 Word Request WebSocket Notification:', notification);

    if (!this.isRequestMode || !this.word) return;

    switch (notification.status) {
      case 'processing':
        console.log('⏳ Processing notification:', notification);
        if (notification.word_data) {
          console.log(
            '📝 Updating word with partial data:',
            notification.word_data
          );
          this.updateWordFromNotification(notification.word_data);
          this.updateStageFromWebSocketData(notification.word_data);
        }
        break;
      case 'completed':
        console.log('✅ Word creation completed:', notification);
        if (notification.word_data) {
          console.log('📋 Final word data received:', notification.word_data);
          this.updateWordFromNotification(notification.word_data, true); // Mark as final update
          this.updateStageFromWebSocketData(notification.word_data);
          this.setAllStagesCompleted(); // Ensure all visible stages are marked completed
        }
        this.loading = false; // Turn off loading only on completion
        break;
      case 'redirect':
        console.log('🔄 Word already exists - redirecting:', notification);
        if (notification.word_data) {
          this.handleWordExistsRedirect(notification.word_data);
        }
        break;
      case 'failed':
        console.log('❌ Word creation failed:', notification);
        this.error = notification.message || 'Failed to create word';
        this.loading = false;
        break;
      case 'invalid':
        console.log('⚠️ Word validation failed:', notification);

        // Set validation error details for UI display
        if (notification.word_data) {
          this.validationError = {
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
          // Set a simple error message since detailed info is in validationError
          this.error = 'Word validation failed';
          console.log(
            '🔍 Validation details set for UI display:',
            this.validationError
          );
        } else {
          // Fallback if no detailed validation data
          this.error =
            notification.error ||
            notification.message ||
            'Word validation failed';
        }
        this.loading = false;
        break;
      default:
        console.log(
          '❓ Unknown notification status:',
          notification.status,
          notification
        );
    }
  }

  private handleWordExistsRedirect(
    wordData: WordNotificationData & {
      word_exists?: boolean;
      pk?: string;
      sk?: string;
      media_ref?: string;
    }
  ): void {
    console.log('🚀 Handling word exists redirect with data:', wordData);

    if (!wordData.word_exists) {
      console.error('❌ Invalid redirect data - word_exists not true');
      return;
    }

    const pk = wordData.pk;
    const sk = wordData.sk;
    const mediaRef = wordData.media_ref;

    if (!pk || !sk) {
      console.error('❌ Missing essential redirect data:', {
        pk,
        sk,
        mediaRef,
      });
      this.error = 'Invalid redirect data received';
      this.loading = false;
      return;
    }

    console.log('📱 Loading existing word using efficient redirect');

    // Show snackbar message
    this.messageService.showInfoMessage(
      this.translationService.translate('wordCard.wordAlreadyExists'),
      4000
    );

    // Exit request mode and load the existing word
    this.isRequestMode = false;

    // Use efficient media loading if available, otherwise regular loading
    if (mediaRef) {
      console.log('🎯 Using efficient API call with media reference');
      this.loadWordByPkSkWithMedia(pk, sk, mediaRef);
    } else {
      console.log('📄 Using standard API call without media reference');
      this.loadWordByPkSk(pk, sk);
    }

    // The loadWordByPkSk methods will handle URL updating based on the loaded word data
  }

  private updateWordFromNotification(
    data: WordNotificationData,
    isFinal = false
  ): void {
    if (!this.word) return;

    console.log('🔄 Updating word from notification data:', data);

    // Update word properties with incoming data
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
      console.log('📖 Definition data received - resolving definition loading');
    }
    if (Object.prototype.hasOwnProperty.call(data, 'source_language')) {
      this.word.source_language = data.source_language || '';
      this.loadingStates.languageInfo = false; // Language info is now available
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
    // Handle case where conjugation is not available (e.g., not a verb)
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
      console.log('💼 Conjugation not available for non-verb:', data);
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

    // Update source definition if available
    if (Object.prototype.hasOwnProperty.call(data, 'source_definition')) {
      this.word.source_definition = data.source_definition || [];
    }

    // Update part of speech information
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

    // Check for completed parallel tasks to update loading states
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

    // On the final update, ensure all loading states are false
    if (isFinal) {
      this.setAllLoadingStates(false);
    }

    // Update language config and trigger change detection
    this.langConfig = getLanguageConfig(this.word);
    this.cdr.detectChanges();
  }

  private updateStageFromWebSocketData(data: WordNotificationData): void {
    console.log('🔄 Updating stages from WebSocket data:', data);

    // Sequential stages - based on quality approvals or data presence
    if (data.validation_quality_approved) {
      this.updateStageStatus('validation', true);
    }

    // Classification stage completion also resolves definition loading
    if (data.classification_quality_approved) {
      this.updateStageStatus('classification', true);
      // Definition is obtained during classification, so resolve definition loading
      this.loadingStates.definition = false;
      console.log(
        '📖 Definition loading resolved after classification completion'
      );
    }

    if (data.translation_quality_approved) {
      this.updateStageStatus('translation', true);
    }

    // Parallel stages - activate them when translation is done
    if (data.translation_quality_approved) {
      this.activateParallelStages();
    }

    // Update parallel stages based on quality approvals
    this.updateStageStatus('media', data.media_quality_approved);
    this.updateStageStatus('examples', data.examples_quality_approved);
    this.updateStageStatus('synonyms', data.synonyms_quality_approved);
    this.updateStageStatus('syllables', data.syllables_quality_approved);
    this.updateStageStatus('conjugation', data.conjugation_quality_approved);

    // Pronunciation doesn't have quality gate - check for pronunciations data
    if (data.pronunciations || data.target_pronunciations) {
      this.updateStageStatus('pronunciation', true);
    }

    // Final quality check
    if (data.processing_complete || data.overall_quality_score) {
      this.updateStageStatus('final_quality', true);
    }

    // Check for completed_parallel_tasks array for more granular updates
    if (
      data.completed_parallel_tasks &&
      Array.isArray(data.completed_parallel_tasks)
    ) {
      data.completed_parallel_tasks.forEach((taskName: string) => {
        this.updateStageStatus(taskName, true);
      });
    }

    console.log(
      '📊 Updated stages:',
      this.processingStages.map((s) => ({ id: s.id, status: s.status }))
    );
  }

  private updateStageStatus(
    stageId: string,
    approved: boolean | undefined
  ): void {
    if (approved === true) {
      const stage = this.processingStages.find((s) => s.id === stageId);
      if (stage && stage.status !== 'completed') {
        stage.status = 'completed';
        console.log(`✅ Stage '${stageId}' marked as completed`);
        // Activate next sequential stage if this was a sequential stage
        this.activateNextSequentialStage(stageId);
      }
    }
  }

  private activateNextSequentialStage(completedStageId: string): void {
    const completedStage = this.processingStages.find(
      (s) => s.id === completedStageId
    );
    if (!completedStage || completedStage.category !== 'sequential') return;

    // Find the next sequential stage
    const nextSequentialStage = this.processingStages.find(
      (s) => s.category === 'sequential' && s.order === completedStage.order + 1
    );

    if (nextSequentialStage && nextSequentialStage.status === 'pending') {
      nextSequentialStage.status = 'active';
      console.log(`🔄 Stage '${nextSequentialStage.id}' activated`);
    } else if (completedStage.order === 3) {
      // After translation (order 3), activate all parallel stages
      this.activateParallelStages();
    }
  }

  private activateParallelStages(): void {
    this.processingStages.forEach((stage) => {
      if (stage.category === 'parallel' && stage.status === 'pending') {
        stage.status = 'active';
        console.log(`🔄 Parallel stage '${stage.id}' activated`);
      }
    });
  }

  private initializeProcessingStages(): void {
    this.processingStages.forEach((stage) => {
      stage.status = 'pending';
    });
    // Activate the first stage (validation) when starting
    const firstStage = this.processingStages.find((s) => s.order === 1);
    if (firstStage) {
      firstStage.status = 'active';
      console.log(`🔄 First stage '${firstStage.id}' activated`);
    }
  }

  private setAllStagesCompleted(): void {
    this.processingStages.forEach((stage) => {
      stage.status = 'completed';
    });
  }

  getVisibleStages(): ProcessingStage[] {
    return this.processingStages.filter((stage) => {
      // Always show conjugation stage initially, only hide after explicit determination
      if (stage.id === 'conjugation') {
        // In request mode, always show until we know for sure it's not a verb
        if (this.isRequestMode) {
          return true;
        }
        // In non-request mode, hide if we definitively know it's not a verb
        return this.word?.target_pos === 'verb' || this.hasConjugationTable;
      }
      // Hide synonyms for POS that don't have synonyms (only after POS is determined)
      if (
        stage.id === 'synonyms' &&
        this.word?.target_pos &&
        !this.isRequestMode &&
        !this.shouldHaveSynonyms(this.word.target_pos)
      ) {
        return false;
      }
      return true;
    });
  }

  private shouldHaveSynonyms(pos: string): boolean {
    const posWithSynonyms = [
      'noun',
      'feminine noun',
      'masculine noun',
      'neuter noun',
      'verb',
      'adjective',
      'adverb',
      'interjection',
      'conjunction',
    ];
    return posWithSynonyms.includes(pos.toLowerCase());
  }

  shouldShowConjugationTab(): boolean {
    // In request mode, always show until we know for sure it's not a verb
    if (this.isRequestMode && this.loadingStates.conjugation) {
      return true;
    }

    // Show if we have conjugation data or if it's a verb
    if (this.hasConjugationTable || this.word?.target_pos === 'verb') {
      return true;
    }

    // In request mode but not loading, show if we haven't determined it's not a verb yet
    if (this.isRequestMode && !this.word?.target_pos) {
      return true;
    }

    // Otherwise, hide the tab
    return false;
  }

  private handleUrlParameters(): void {
    // Extract parameters from route
    const sourceLanguage = this.route.snapshot.paramMap.get('sourceLanguage');
    const targetLanguage = this.route.snapshot.paramMap.get('targetLanguage');
    const word = this.route.snapshot.paramMap.get('word');
    const pos = this.route.snapshot.paramMap.get('pos');

    if (sourceLanguage && targetLanguage && word) {
      // Decode the word parameter to handle special characters like ß
      const decodedWord = decodeURIComponent(word).toLowerCase().trim();

      // With POS - construct PK/SK and fetch directly
      const pk = `SRC#${sourceLanguage}#${decodedWord}`;
      let sk = `TGT#${targetLanguage}`;
      if (pos && pos !== 'pending') {
        sk += `#POS#${pos.toLowerCase().trim()}`;
      }

      this.loadWordByPkSk(pk, sk);
    } else {
      this.error =
        'Invalid parameters: missing source language, target language, or word';
      this.loading = false;
    }
  }

  // Fix URL when it shows "pending" instead of correct POS after DDB hit
  private fixPendingUrlIfNeeded(word: VocabularyWord): void {
    const currentUrl = this.location.path();
    if (currentUrl.includes('/pending/')) {
      // Extract POS from SK: "TGT#es#POS#noun" -> "noun"
      const skParts = word.sk.split('#');
      const posIndex = skParts.findIndex((part) => part === 'POS');
      if (posIndex !== -1 && posIndex + 1 < skParts.length) {
        const correctPos = skParts[posIndex + 1];
        const newUrl = currentUrl.replace('/pending/', `/${correctPos}/`);
        this.location.replaceState(newUrl);
        console.log('🔄 URL updated from pending to correct POS:', correctPos);
      }
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
          this.setAllLoadingStates(false); // Word is fully loaded
          this.fixPendingUrlIfNeeded(data); // Fix URL if it shows "pending"
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
          this.setAllLoadingStates(false);
          this.fixPendingUrlIfNeeded(data); // Fix URL if it shows "pending"
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
    // Clear validation error details when going back
    this.validationError = null;
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
