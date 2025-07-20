import { Injectable, inject, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject, BehaviorSubject, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { Configs } from '../shared/config';

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

  constructor() {
    this.initializeWebSocket();
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
   * Removes extra whitespace and ensures proper formatting
   */
  private cleanWord(word: string): string {
    return word.trim().toLowerCase();
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

    switch (messageType) {
      case 'subscription_confirmed':
        notification.status = 'pending';
        notification.message = `Subscription confirmed for: ${
          message.source_word || (data['source_word'] as string) || 'word'
        }`;
        break;

      case 'processing_started':
        notification.status = 'processing';
        notification.message = `Processing started for: ${
          (data['source_word'] as string) || 'word'
        }`;
        break;

      case 'chunk_update':
        notification.status = 'processing';
        notification.message = `Processing update received`;
        notification.word_data = data['chunk'] as Record<string, unknown>;
        break;

      case 'step_update':
        notification.status = 'processing';
        notification.message = `Step: ${message.step || 'Processing'}`;
        notification.word_data = data['result'] as Record<string, unknown>;
        break;

      case 'processing_completed':
        notification.status = 'completed';
        notification.message = `Processing completed for: ${
          (data['source_word'] as string) || 'word'
        }`;
        notification.word_data = data['result'] as Record<string, unknown>;
        break;

      case 'processing_failed':
        notification.status = 'failed';
        notification.message = `Processing failed for: ${
          (data['source_word'] as string) || 'word'
        }`;
        notification.error = data['error'] as string;
        break;

      case 'validation_failed':
        notification.status = 'invalid';
        notification.message = `Validation failed for: ${
          (data['source_word'] as string) || 'word'
        }`;
        notification.error =
          ((data['validation_result'] as Record<string, unknown>)?.[
            'validation_issue'
          ] as string) || 'Validation failed';
        notification.word_data = data['validation_result'] as Record<
          string,
          unknown
        >;
        break;

      case 'ddb_hit':
        notification.status = 'completed';
        notification.message = `Word already exists: ${
          (data['source_word'] as string) || 'word'
        }`;
        notification.word_data = data['result'] as Record<string, unknown>;
        break;

      case 'word_exists_redirect':
        notification.status = 'redirect';
        notification.message = `Word already exists: ${
          (data['source_word'] as string) || 'word'
        } - redirecting to existing entry`;
        notification.word_data = data['word_data'] as Record<string, unknown>;
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

    this.notificationSubject.next(notification);
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
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
