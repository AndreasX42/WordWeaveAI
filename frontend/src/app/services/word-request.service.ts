import { Injectable, inject, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject, BehaviorSubject, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { Configs } from '../shared/config';
import { NotificationService } from './notification.service';

export interface WordRequest {
  source_word: string;
  source_language?: string;
  target_language: string;
  user_id?: string;
  request_id?: string;
  created_at?: string;
}

export interface WordRequestResponse {
  request_id: string;
  message: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface WordRequestNotification {
  request_id: string;
  status:
    | 'pending'
    | 'processing'
    | 'completed'
    | 'failed'
    | 'redirect'
    | 'invalid';
  message: string;
  word_data?: Record<string, unknown>;
  error?: string;
}

interface WebSocketMessage {
  type?: string;
  data?: Record<string, unknown>;
  request_id?: string;
  vocab_word?: string;
  source_word?: string;
  step?: string;
  chunk?: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
  validation_result?: Record<string, unknown>;
  word_data?: Record<string, unknown>;
  message?: string;
}

@Injectable({
  providedIn: 'root',
})
export class WordRequestService implements OnDestroy {
  private http = inject(HttpClient);
  private router = inject(Router);
  private notificationService = inject(NotificationService);
  private apiUrl = `${Configs.BASE_URL}${Configs.WORD_REQUESTS_URL}`;

  // WebSocket connection
  private ws: WebSocket | null = null;
  private wsUrl = Configs.WEBSOCKET_URL;

  // Subjects for notifications
  private notificationSubject = new Subject<WordRequestNotification>();
  private connectionStatusSubject = new BehaviorSubject<boolean>(false);

  // Public observables
  public notifications$ = this.notificationSubject.asObservable();
  public connectionStatus$ = this.connectionStatusSubject.asObservable();

  // Track current route to determine if user is on word-card page
  private currentRoute = '';
  private currentRequestData: {
    sourceWord: string;
    sourceLanguage?: string;
    targetLanguage: string;
    requestId: string;
  } | null = null;

  constructor() {
    this.initializeWebSocket();

    // Track route changes
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.currentRoute = event.urlAfterRedirects;
      });
  }

  ngOnDestroy(): void {
    this.closeWebSocket();
  }

  /**
   * Submit a word request to the backend
   */
  submitWordRequest(request: WordRequest): Observable<WordRequestResponse> {
    // Validate required fields
    if (!request.source_word?.trim()) {
      return throwError(() => new Error('Source word is required'));
    }

    if (!request.target_language?.trim()) {
      return throwError(() => new Error('Target language is required'));
    }

    // Clean and format the source word
    const cleanedWord = this.cleanWord(request.source_word);

    const requestData: WordRequest = {
      ...request,
      source_word: cleanedWord,
    };

    return this.http.post<WordRequestResponse>(this.apiUrl, requestData).pipe(
      tap((response) => {
        console.log('Word request submitted:', response);

        // Store current request data for notifications
        this.currentRequestData = {
          sourceWord: cleanedWord,
          sourceLanguage: request.source_language,
          targetLanguage: request.target_language,
          requestId: response.request_id,
        };

        // Connect to WebSocket for this specific request
        this.connectWebSocket(
          request.user_id || 'anonymous',
          cleanedWord,
          request.target_language
        );
      }),
      catchError((error) => {
        console.error('Error submitting word request:', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Clean and format a word for submission
   * Removes extra whitespace but preserves original case
   */
  private cleanWord(word: string): string {
    return word.trim();
  }

  /**
   * Initialize WebSocket connection (optimized - no auto-connect)
   */
  private initializeWebSocket(): void {
    this.connectionStatusSubject.next(false);
  }

  /**
   * Connect to WebSocket with specific parameters (optimized)
   */
  private connectWebSocket(
    userId: string,
    sourceWord: string,
    targetLanguage: string
  ): void {
    // Close existing connection if any
    this.closeWebSocket();

    try {
      const urlWithParams = `${this.wsUrl}?user_id=${encodeURIComponent(
        userId
      )}&source_word=${encodeURIComponent(
        sourceWord
      )}&target_language=${encodeURIComponent(targetLanguage)}`;

      console.log('Connecting to WebSocket:', urlWithParams);
      this.ws = new WebSocket(urlWithParams);

      this.ws.onopen = () => {
        console.log('WebSocket connected for word requests');
        this.connectionStatusSubject.next(true);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.connectionStatusSubject.next(false);
        this.ws = null;
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionStatusSubject.next(false);
      };
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
      this.connectionStatusSubject.next(false);
    }
  }

  /**
   * Handle WebSocket messages based on the test client format
   */
  private handleWebSocketMessage(message: WebSocketMessage): void {
    const messageType = message.type || 'unknown';
    const data = message.data || {};

    // Create notification object
    const notification: WordRequestNotification = {
      request_id: message.request_id || message.vocab_word || 'unknown',
      status: 'pending',
      message: '',
    };

    // Check if user is currently on word-card page
    const isOnWordCardPage = this.currentRoute.includes('/words/');
    const sourceWord =
      message.source_word ||
      (data['source_word'] as string) ||
      this.currentRequestData?.sourceWord ||
      'word';

    switch (messageType) {
      case 'subscription_confirmed':
        notification.status = 'pending';
        notification.message = `Subscription confirmed for: ${sourceWord}`;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'pending',
          isOnWordCardPage
        );
        break;

      case 'processing_started':
        notification.status = 'processing';
        notification.message = `Processing started for: ${sourceWord}`;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'processing',
          isOnWordCardPage
        );
        break;

      case 'chunk_update':
        notification.status = 'processing';
        notification.message = `Processing update received`;
        notification.word_data = data['chunk'] as Record<string, unknown>;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'processing',
          isOnWordCardPage
        );
        break;

      case 'step_update':
        notification.status = 'processing';
        notification.message = `Step: ${message.step || 'Processing'}`;
        notification.word_data = data['result'] as Record<string, unknown>;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'processing',
          isOnWordCardPage
        );
        break;

      case 'processing_completed':
        notification.status = 'completed';
        notification.message = `Processing completed for: ${sourceWord}`;
        notification.word_data = data['result'] as Record<string, unknown>;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'completed',
          isOnWordCardPage,
          data
        );
        break;

      case 'processing_failed':
        notification.status = 'failed';
        notification.message = `Processing failed for: ${sourceWord}`;
        notification.error = data['error'] as string;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'failed',
          isOnWordCardPage
        );
        break;

      case 'validation_failed':
        notification.status = 'invalid';
        notification.message = `Validation failed for: ${sourceWord}`;
        notification.error =
          ((data['validation_result'] as Record<string, unknown>)?.[
            'validation_issue'
          ] as string) || 'Validation failed';
        notification.word_data = data['validation_result'] as Record<
          string,
          unknown
        >;
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'failed',
          isOnWordCardPage
        );
        break;

      case 'word_exists_redirect':
        // DDB cache hit - word already exists in database
        console.log('🔄 Received DDB hit redirect:', { data, sourceWord });
        notification.status = 'redirect';
        notification.message = `Word already exists: ${sourceWord} - redirecting to existing entry`;
        // Backend sends: { exists: true, existing_item: { PK, SK, media_ref, ... } }
        notification.word_data = (data['word_data'] || data) as Record<
          string,
          unknown
        >;
        console.log('📋 Redirect notification data:', notification.word_data);
        this.handleNotificationRouting(
          notification,
          sourceWord,
          'redirect',
          isOnWordCardPage,
          notification.word_data
        );
        break;

      case 'connection_close':
        notification.status = 'completed';
        notification.message =
          (data['message'] as string) || 'Processing complete';
        // Close WebSocket after receiving close message
        setTimeout(() => this.closeWebSocket(), 1000);
        break;

      default:
        notification.message = `Received: ${messageType}`;
        break;
    }

    // Always emit to the notification subject for word-card component
    this.notificationSubject.next(notification);
  }

  /**
   * Route notifications based on user location
   */
  private handleNotificationRouting(
    notification: WordRequestNotification,
    sourceWord: string,
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'redirect',
    isOnWordCardPage: boolean,
    wordData?: Record<string, unknown>
  ): void {
    // Send to header notifications regardless of location
    // TODO: Revert to only when not on word-card page after testing
    if (this.currentRequestData) {
      // Normalize the source word for consistent notification IDs (case-insensitive)
      const normalizedSourceWord =
        this.currentRequestData.sourceWord.toLowerCase();
      const normalizedTargetLang =
        this.currentRequestData.targetLanguage.toLowerCase();
      const notificationId = `word-request-${normalizedSourceWord}-${this.getLanguageCode(
        this.currentRequestData.sourceLanguage || 'en'
      )}-${this.getLanguageCode(normalizedTargetLang)}`;

      console.log('🔍 Notification routing:', {
        notificationId,
        currentStatus: status,
        sourceWord,
        requestId: this.currentRequestData.requestId,
        normalizedSourceWord,
        originalSourceWord: this.currentRequestData.sourceWord,
        timestamp: new Date().toISOString(),
      });

      let title = '';
      let message = '';
      let link = '';
      let pk = '';
      let sk = '';
      let mediaRef = '';

      // Extract language codes for short messages
      const srcLang = this.getLanguageCode(
        this.currentRequestData.sourceLanguage || 'en'
      );
      const tgtLang = this.getLanguageCode(
        this.currentRequestData.targetLanguage
      );

      switch (status) {
        case 'pending':
          title = 'Word Request';
          message = `Requested ${srcLang}→${tgtLang} "${sourceWord}"`;
          break;
        case 'processing':
          title = 'Processing';
          message = `Processing ${srcLang}→${tgtLang} "${sourceWord}"`;
          break;
        case 'completed':
        case 'redirect':
          title = status === 'redirect' ? 'Found' : 'Finished';
          message =
            status === 'redirect'
              ? `"${sourceWord}" already exists in our database`
              : `Finished ${srcLang}→${tgtLang} "${sourceWord}"`;
          // Generate link and extract PK/SK/media_ref
          if (wordData) {
            const linkData = this.extractWordLinkData(wordData);
            link = linkData.link;
            pk = linkData.pk;
            sk = linkData.sk;
            mediaRef = linkData.mediaRef;
            console.log('🔗 Generated redirect link:', {
              link,
              pk,
              sk,
              mediaRef,
            });
          }
          break;
        case 'failed':
          title = 'Failed';
          message = `Failed ${srcLang}→${tgtLang} "${sourceWord}"`;
          break;
      }

      // Force override for redirect notifications to ensure they're not overridden by processing
      const forceOverride = status === 'redirect';

      this.notificationService.addOrUpdateNotification(
        {
          id: notificationId,
          title,
          message,
          status,
          sourceWord,
          targetLanguage: this.currentRequestData.targetLanguage,
          requestId: this.currentRequestData.requestId,
          link,
          // Store PK/SK/media_ref for quick word loading
          ...(pk && { pk }),
          ...(sk && { sk }),
          ...(mediaRef && { mediaRef }),
        },
        forceOverride
      );
    }
  }

  /**
   * Normalize POS for database compatibility (feminine/masculine/neuter noun -> noun)
   */
  private normalizePOS(pos: string): string {
    if (!pos) return 'pending';
    const posLower = pos.toLowerCase();
    return posLower.includes('noun') ? 'noun' : posLower;
  }

  /**
   * Normalize word for URL compatibility (umlauts and special characters to base characters)
   */
  private normalizeWord(word: string): string {
    if (!word) return '';

    // Convert to lowercase first
    let normalized = word.toLowerCase();

    // Normalize German umlauts and special characters
    const umlautMap: Record<string, string> = {
      ä: 'a',
      ö: 'o',
      ü: 'u',
      ß: 'ss',
      // Also handle other common accented characters
      á: 'a',
      à: 'a',
      â: 'a',
      ã: 'a',
      é: 'e',
      è: 'e',
      ê: 'e',
      ë: 'e',
      í: 'i',
      ì: 'i',
      î: 'i',
      ï: 'i',
      ó: 'o',
      ò: 'o',
      ô: 'o',
      õ: 'o',
      ú: 'u',
      ù: 'u',
      û: 'u',
      ç: 'c',
      ñ: 'n',
    };

    // Replace each special character with its base equivalent
    for (const [accented, base] of Object.entries(umlautMap)) {
      normalized = normalized.replace(new RegExp(accented, 'g'), base);
    }

    // Remove any remaining non-alphanumeric characters except spaces and hyphens
    normalized = normalized.replace(/[^a-z0-9\s-]/g, '');

    // Replace spaces with hyphens for URL compatibility
    normalized = normalized.replace(/\s+/g, '-');

    // Remove multiple consecutive hyphens
    normalized = normalized.replace(/-+/g, '-');

    // Trim hyphens from start and end
    normalized = normalized.replace(/^-+|-+$/g, '');

    return normalized;
  }

  /**
   * Get language code from full language name or return as-is if already code
   */
  private getLanguageCode(language: string): string {
    const langMap: Record<string, string> = {
      English: 'en',
      Spanish: 'es',
      German: 'de',
      auto: 'auto',
    };

    return langMap[language] || language.toLowerCase().slice(0, 2);
  }

  /**
   * Extract word link data including PK, SK, media_ref from WebSocket data
   */
  private extractWordLinkData(wordData: Record<string, unknown>): {
    link: string;
    pk: string;
    sk: string;
    mediaRef: string;
  } {
    // The actual word data might be nested in 'result'
    let actualWordData = wordData;
    if (wordData['result'] && typeof wordData['result'] === 'object') {
      actualWordData = wordData['result'] as Record<string, unknown>;
    }

    // Extract DDB data using standard uppercase keys
    let pk = (actualWordData['PK'] as string) || '';
    let sk = (actualWordData['SK'] as string) || '';
    let mediaRef = (actualWordData['media_ref'] as string) || '';

    // Fallback to existing_item structure if main data is missing
    if ((!pk || !sk) && actualWordData['existing_item']) {
      const existingItem = actualWordData['existing_item'] as Record<
        string,
        unknown
      >;
      pk = pk || (existingItem['PK'] as string) || '';
      sk = sk || (existingItem['SK'] as string) || '';
      mediaRef = mediaRef || (existingItem['media_ref'] as string) || '';
    }

    // If still no PK/SK, try to construct from available data
    if (!pk || !sk) {
      const sourceWord = actualWordData['source_word'] as string;
      const sourceLanguage = actualWordData['source_language'] as string;
      const targetLanguage = actualWordData['target_language'] as string;
      const targetPos =
        actualWordData['target_pos'] ||
        (actualWordData['target_part_of_speech'] as string);

      if (sourceWord && sourceLanguage && targetLanguage) {
        const sourceLangCode = this.getLanguageCode(sourceLanguage);
        const targetLangCode = this.getLanguageCode(targetLanguage);

        // Decode word if it's already encoded, then normalize for database consistency
        let decodedWord = sourceWord;
        if (typeof sourceWord === 'string') {
          try {
            // Try to decode in case it's already encoded
            decodedWord = decodeURIComponent(sourceWord);
          } catch {
            // If decoding fails, just use the word as-is
            decodedWord = sourceWord;
          }
        }
        // Normalize word for PK construction (database key) - removes umlauts, lowercase
        const normalizedDbWord = this.normalizeWord(decodedWord);
        pk = `SRC#${sourceLangCode}#${normalizedDbWord}`;
        sk = `TGT#${targetLangCode}`;

        if (targetPos && typeof targetPos === 'string') {
          sk += `#POS#${this.normalizePOS(targetPos)}`;
        }
      }
    }

    // Generate link from actual word data (preserve original case)
    let link = '';
    if (pk && sk) {
      const pkParts = pk.split('#');
      const skParts = sk.split('#');

      if (pkParts.length >= 3 && skParts.length >= 2) {
        const sourceLanguage = pkParts[1];
        const targetLanguage = skParts[1];

        // Use the actual refined source_word from WebSocket data, not from PK
        const refinedWord =
          (actualWordData['source_word'] as string) || pkParts[2];

        // Extract POS if available and normalize it
        let pos = 'pending';
        const posIndex = skParts.findIndex((part) => part === 'POS');
        if (posIndex !== -1 && posIndex + 1 < skParts.length) {
          const rawPos = skParts[posIndex + 1];
          pos = this.normalizePOS(rawPos);
        }

        // Smart word handling: decode if needed, normalize umlauts, lowercase
        let finalWord = refinedWord;
        try {
          // Try to decode first in case it's already encoded
          const decodedWord = decodeURIComponent(refinedWord);
          // Always use the decoded version to ensure clean Unicode
          finalWord = decodedWord;
        } catch {
          // If decoding fails, use original word
          finalWord = refinedWord;
        }

        // Normalize umlauts and special characters to base characters
        finalWord = this.normalizeWord(finalWord);

        link = `/words/${sourceLanguage}/${targetLanguage}/${pos}/${finalWord}`;
      }
    }

    return { link, pk, sk, mediaRef };
  }

  /**
   * Generate word card link from word data
   */
  private generateWordCardLink(wordData: Record<string, unknown>): string {
    // The actual word data might be nested in 'result'
    let actualWordData = wordData;
    if (wordData['result'] && typeof wordData['result'] === 'object') {
      actualWordData = wordData['result'] as Record<string, unknown>;
    }

    let pk = (actualWordData['PK'] as string) || '';
    let sk = (actualWordData['SK'] as string) || '';

    // If still no PK/SK, try to construct from available data
    if (!pk || !sk) {
      const sourceWord = actualWordData['source_word'] as string;
      const sourceLanguage = actualWordData['source_language'] as string;
      const targetLanguage = actualWordData['target_language'] as string;
      const targetPos =
        actualWordData['target_pos'] ||
        (actualWordData['target_part_of_speech'] as string);

      if (sourceWord && sourceLanguage && targetLanguage) {
        // Map language names to codes
        const langMap: Record<string, string> = {
          English: 'en',
          Spanish: 'es',
          German: 'de',
        };

        const sourceLangCode =
          langMap[sourceLanguage] ||
          (typeof sourceLanguage === 'string'
            ? sourceLanguage.toLowerCase().slice(0, 2)
            : 'en');
        const targetLangCode =
          langMap[targetLanguage] ||
          (typeof targetLanguage === 'string'
            ? targetLanguage.toLowerCase().slice(0, 2)
            : 'es');

        // Decode word if it's already encoded, then normalize for database consistency
        let decodedWord = sourceWord;
        if (typeof sourceWord === 'string') {
          try {
            // Try to decode in case it's already encoded
            decodedWord = decodeURIComponent(sourceWord);
          } catch {
            // If decoding fails, just use the word as-is
            decodedWord = sourceWord;
          }
        }
        // Normalize word for PK construction (database key) - removes umlauts, lowercase
        const normalizedDbWord = this.normalizeWord(decodedWord);
        pk = `SRC#${sourceLangCode}#${normalizedDbWord}`;
        sk = `TGT#${targetLangCode}`;

        if (targetPos && typeof targetPos === 'string') {
          sk += `#POS#${this.normalizePOS(targetPos)}`;
        }
      }
    }

    if (!pk || !sk) {
      return '';
    }

    const pkParts = pk.split('#');
    const skParts = sk.split('#');

    if (pkParts.length >= 3 && skParts.length >= 2) {
      const sourceLanguage = pkParts[1];
      const targetLanguage = skParts[1];

      // Use the actual refined source_word from WebSocket data, not from PK
      const refinedWord =
        (actualWordData['source_word'] as string) || pkParts[2];

      // Extract POS if available and normalize it
      let pos = 'pending';
      const posIndex = skParts.findIndex((part) => part === 'POS');
      if (posIndex !== -1 && posIndex + 1 < skParts.length) {
        const rawPos = skParts[posIndex + 1];
        pos = this.normalizePOS(rawPos);
      }

      // Smart word handling: decode if needed, normalize umlauts, lowercase
      let finalWord = refinedWord;
      try {
        // Try to decode first in case it's already encoded
        const decodedWord = decodeURIComponent(refinedWord);
        // Always use the decoded version to ensure clean Unicode
        finalWord = decodedWord;
      } catch {
        // If decoding fails, use original word
        finalWord = refinedWord;
      }

      // Normalize umlauts and special characters to base characters
      finalWord = this.normalizeWord(finalWord);

      return `/words/${sourceLanguage}/${targetLanguage}/${pos}/${finalWord}`;
    }

    return '';
  }

  /**
   * Close WebSocket connection (optimized)
   */
  private closeWebSocket(): void {
    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Reconnect to an existing word request (for notifications)
   */
  reconnectToRequest(
    sourceWord: string,
    sourceLanguage: string,
    targetLanguage: string,
    requestId: string
  ): void {
    // Store request data for notifications
    this.currentRequestData = {
      sourceWord,
      sourceLanguage,
      targetLanguage,
      requestId,
    };

    // Connect to WebSocket - the backend should recognize existing request
    this.connectWebSocket('user', sourceWord, targetLanguage);
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
