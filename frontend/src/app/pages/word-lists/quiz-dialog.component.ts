import { Component, inject, signal, computed, DestroyRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  MatDialogModule,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatCardModule } from '@angular/material/card';
import { MatDividerModule } from '@angular/material/divider';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import {
  WordListWord,
  UpdateWordStatusRequest,
} from '../../models/word-list.model';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { WordListService } from '../../services/word-list.service';
import { forkJoin } from 'rxjs';

export interface QuizDialogData {
  listId: string;
  listName: string;
  words: WordListWord[];
}

interface QuizQuestion {
  word: WordListWord;
  correctAnswer: string;
  options: string[];
  userAnswer?: string;
  isCorrect?: boolean;
}

interface QuizResults {
  totalQuestions: number;
  correctAnswers: number;
  incorrectAnswers: number;
  percentage: number;
  questions: QuizQuestion[];
}

@Component({
  selector: 'app-quiz-dialog',
  template: `
    <div class="quiz-dialog-container">
      <!-- Loading State -->
      @if (loading()) {
      <div class="quiz-loading">
        <mat-icon class="loading-icon animate-spin">hourglass_empty</mat-icon>
        <p>{{ 'vocabLists.quiz.preparing' | translate }}</p>
      </div>
      }

      <!-- Quiz Questions -->
      @if (!loading() && !showResults() && currentQuestion()) {
      <div class="quiz-content">
        <!-- Question Card -->
        <div class="question-card">
          <!-- Word Display (Blue Section) -->
          <div class="word-display">
            <button
              mat-icon-button
              [mat-dialog-close]="false"
              class="close-btn"
              [disabled]="loading()"
            >
              <mat-icon>close</mat-icon>
            </button>

            <div class="question-text">
              <p class="question-label">
                {{ 'vocabLists.quiz.question' | translate }}
              </p>
              <div class="source-word-container">
                @if (currentQuestion()?.word?.source_language) {
                <img
                  [src]="
                    '/assets/icons/flags/' +
                    currentQuestion()!.word!.source_language +
                    '.svg'
                  "
                  [alt]="currentQuestion()!.word!.source_language"
                  class="source-flag"
                />
                }
                <h3 class="source-word">
                  {{ currentQuestion()?.word?.source_word || 'Unknown' }}
                </h3>
              </div>
            </div>

            <!-- Media Image -->
            @if (getWordImageUrl(currentQuestion()?.word)) {
            <div class="word-media">
              <img
                [src]="getWordImageUrl(currentQuestion()?.word)"
                [alt]="currentQuestion()?.word?.source_word || 'Word image'"
                class="word-image"
              />
            </div>
            }
          </div>

          <!-- Progress Bar (Between blue and white sections) -->
          <div class="quiz-progress-bar">
            <mat-progress-bar
              mode="determinate"
              [value]="progressPercentage()"
              class="progress-bar"
            ></mat-progress-bar>
          </div>

          <!-- Answer Options (White Section) -->
          <div class="answer-options">
            <div class="options-grid">
              @for (option of currentQuestion()?.options; track option; let i =
              $index) {
              <button
                mat-raised-button
                class="option-button"
                [class.selected]="selectedAnswer() === option"
                [class.correct]="
                  showAnswer() && option === currentQuestion()?.correctAnswer
                "
                [class.incorrect]="
                  showAnswer() &&
                  selectedAnswer() === option &&
                  option !== currentQuestion()?.correctAnswer
                "
                [disabled]="showAnswer()"
                (click)="selectAnswer(option)"
              >
                <div class="option-content">
                  <span class="option-text">{{ option }}</span>
                </div>
              </button>
              }
            </div>

            <!-- Actions directly in answer section -->
            <div class="quiz-actions">
              @if (!showAnswer()) {
              <button
                mat-raised-button
                color="primary"
                [disabled]="!selectedAnswer()"
                (click)="confirmAnswer()"
                class="confirm-btn"
              >
                <mat-icon>check</mat-icon>
                {{ 'common.confirm' | translate }}
              </button>
              } @else { @if (isLastQuestion()) {
              <button
                mat-raised-button
                color="primary"
                (click)="finishQuiz()"
                class="next-btn"
              >
                <mat-icon>flag</mat-icon>
                {{ 'vocabLists.quiz.finishQuiz' | translate }}
              </button>
              } @else {
              <button
                mat-raised-button
                color="primary"
                (click)="nextQuestion()"
                class="next-btn"
              >
                <mat-icon>arrow_forward</mat-icon>
                {{ 'vocabLists.quiz.nextQuestion' | translate }}
              </button>
              } }
            </div>
          </div>
        </div>
      </div>
      }

      <!-- Quiz Results -->
      @if (showResults() && results()) {
      <div class="quiz-results">
        <button mat-icon-button [mat-dialog-close]="true" class="close-btn">
          <mat-icon>close</mat-icon>
        </button>

        <div class="results-header">
          <mat-icon class="results-icon" [class]="getResultsIconClass()">{{
            getResultsIcon()
          }}</mat-icon>
          <h3 class="results-title">
            {{ 'vocabLists.quiz.results' | translate }}
          </h3>
          <p class="results-message">{{ getResultsMessage() | translate }}</p>
        </div>

        <div class="score-display">
          <div class="score-circle">
            <span class="score-percentage">{{ results()?.percentage }}%</span>
            <span class="score-text">
              {{
                'vocabLists.quiz.score'
                  | translate
                    : {
                        correct: (results()?.correctAnswers || 0).toString(),
                        total: (results()?.totalQuestions || 0).toString()
                      }
              }}
            </span>
          </div>
        </div>

        <div class="score-breakdown">
          <div class="score-item correct">
            <mat-icon>check_circle</mat-icon>
            <span
              >{{ results()?.correctAnswers }}
              {{ 'vocabLists.quiz.correct' | translate }}</span
            >
          </div>
          <div class="score-item incorrect">
            <mat-icon>cancel</mat-icon>
            <span
              >{{ results()?.incorrectAnswers }}
              {{ 'vocabLists.quiz.incorrect' | translate }}</span
            >
          </div>
        </div>

        <div class="results-actions">
          <button mat-stroked-button (click)="retakeQuiz()" class="retake-btn">
            <mat-icon>refresh</mat-icon>
            {{ 'vocabLists.quiz.retakeQuiz' | translate }}
          </button>
        </div>
      </div>
      }
    </div>
  `,
  styleUrl: './quiz-dialog.component.scss',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatCardModule,
    MatDividerModule,
    TranslatePipe,
  ],
})
export class QuizDialogComponent {
  private dialogRef = inject(MatDialogRef<QuizDialogComponent>);
  private destroyRef = inject(DestroyRef);
  private wordListService = inject(WordListService);
  public data: QuizDialogData = inject(MAT_DIALOG_DATA);

  // Component state
  loading = signal<boolean>(true);
  showResults = signal<boolean>(false);
  showAnswer = signal<boolean>(false);

  // Quiz configuration
  readonly totalRounds = 5;
  readonly optionsPerQuestion = 4;

  // Quiz data
  questions = signal<QuizQuestion[]>([]);
  currentRound = signal<number>(0);
  selectedAnswer = signal<string | null>(null);
  results = signal<QuizResults | null>(null);

  // Computed properties
  currentQuestion = computed(() => {
    const questions = this.questions();
    const round = this.currentRound();
    return questions.length > round ? questions[round] : null;
  });

  progressPercentage = computed(() => {
    return ((this.currentRound() + 1) / this.totalRounds) * 100;
  });

  correctCount = computed(() => {
    return this.questions()
      .slice(0, this.currentRound())
      .filter((q) => q.isCorrect).length;
  });

  isLastQuestion = computed(() => {
    return this.currentRound() === this.totalRounds - 1;
  });

  get listName(): string {
    return this.data.listName;
  }

  constructor() {
    this.initializeQuiz();
  }

  private async initializeQuiz(): Promise<void> {
    // Simulate loading time for better UX
    await new Promise((resolve) => setTimeout(resolve, 1000));

    try {
      const questions = this.generateQuizQuestions();
      this.questions.set(questions);
      this.loading.set(false);
    } catch (error) {
      console.error('Error initializing quiz:', error);
      // Handle error - could show error message or close dialog
      this.dialogRef.close(false);
    }
  }

  private generateQuizQuestions(): QuizQuestion[] {
    const words = this.data.words;

    if (words.length < 5) {
      throw new Error('Not enough words for quiz');
    }

    // Shuffle words and take first 5
    const shuffledWords = this.shuffleArray([...words]).slice(
      0,
      this.totalRounds
    );

    return shuffledWords.map((word) => {
      const correctAnswer = word.target_word || word.vocab_sk;
      const options = this.generateAnswerOptions(word, words);

      return {
        word,
        correctAnswer,
        options: this.shuffleArray(options),
      };
    });
  }

  private generateAnswerOptions(
    correctWord: WordListWord,
    allWords: WordListWord[]
  ): string[] {
    const correctAnswer = correctWord.target_word || correctWord.vocab_sk;

    // Get other words as wrong options (excluding the correct one)
    const otherWords = allWords
      .filter((w) => {
        const targetWord = w.target_word || w.vocab_sk;
        return targetWord !== correctAnswer;
      })
      .map((w) => w.target_word || w.vocab_sk);

    // Shuffle and take first 3 as wrong options
    const shuffledOthers = this.shuffleArray(otherWords);
    const wrongOptions = shuffledOthers.slice(0, this.optionsPerQuestion - 1);

    // If we don't have enough words for all options, we need to handle this
    while (wrongOptions.length < this.optionsPerQuestion - 1) {
      wrongOptions.push(`Option ${wrongOptions.length + 1}`);
    }

    // Combine correct and wrong options
    return [correctAnswer, ...wrongOptions];
  }

  private shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  selectAnswer(option: string): void {
    if (this.showAnswer()) return;
    this.selectedAnswer.set(option);
  }

  confirmAnswer(): void {
    if (!this.selectedAnswer()) return;

    const currentQ = this.currentQuestion();
    if (!currentQ) return;

    // Update question with user's answer
    const isCorrect = this.selectedAnswer() === currentQ.correctAnswer;
    currentQ.userAnswer = this.selectedAnswer()!;
    currentQ.isCorrect = isCorrect;

    this.showAnswer.set(true);
  }

  nextQuestion(): void {
    this.selectedAnswer.set(null);
    this.showAnswer.set(false);
    this.currentRound.update((round) => round + 1);
  }

  finishQuiz(): void {
    const questions = this.questions();
    const correctAnswers = questions.filter((q) => q.isCorrect).length;
    const totalQuestions = questions.length;
    const percentage = Math.round((correctAnswers / totalQuestions) * 100);

    const results: QuizResults = {
      totalQuestions,
      correctAnswers,
      incorrectAnswers: totalQuestions - correctAnswers,
      percentage,
      questions,
    };

    this.results.set(results);
    this.showResults.set(true);

    // Mark correctly answered words as learned
    this.markLearnedWords();
  }

  private markLearnedWords(): void {
    const questions = this.questions();
    const correctlyAnsweredWords = questions
      .filter((q) => q.isCorrect)
      .map((q) => q.word)
      .filter((word) => !word.is_learned); // Only update words that aren't already learned

    if (correctlyAnsweredWords.length === 0) {
      return; // No new words to mark as learned
    }

    // Create update requests for all correctly answered words
    const updateRequests: UpdateWordStatusRequest[] =
      correctlyAnsweredWords.map((word) => ({
        vocab_pk: word.vocab_pk,
        vocab_sk: word.vocab_sk,
        status: 'learned' as const,
      }));

    // Execute all updates in parallel
    const updateObservables = updateRequests.map((request) =>
      this.wordListService.updateWordStatus(this.data.listId, request)
    );

    if (updateObservables.length > 0) {
      forkJoin(updateObservables)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            console.log(
              `Successfully marked ${correctlyAnsweredWords.length} words as learned`
            );
            // Update local word data to reflect the learned status
            correctlyAnsweredWords.forEach((word) => {
              word.is_learned = true;
              word.learned_at = new Date().toISOString();
            });
          },
          error: (error) => {
            console.error('Error updating word learning status:', error);
            // Note: We don't show error to user as this shouldn't interrupt the quiz completion flow
          },
        });
    }
  }

  retakeQuiz(): void {
    this.loading.set(true);
    this.showResults.set(false);
    this.showAnswer.set(false);
    this.selectedAnswer.set(null);
    this.currentRound.set(0);
    this.results.set(null);

    this.initializeQuiz();
  }

  isCurrentAnswerCorrect(): boolean {
    const currentQ = this.currentQuestion();
    return currentQ?.isCorrect ?? false;
  }

  getResultsIcon(): string {
    const percentage = this.results()?.percentage ?? 0;
    if (percentage >= 80) return 'emoji_events';
    if (percentage >= 60) return 'thumb_up';
    return 'school';
  }

  getResultsIconClass(): string {
    const percentage = this.results()?.percentage ?? 0;
    if (percentage >= 80) return 'excellent';
    if (percentage >= 60) return 'good';
    return 'needs-practice';
  }

  getResultsMessage(): string {
    const percentage = this.results()?.percentage ?? 0;
    if (percentage >= 80) return 'vocabLists.quiz.excellent';
    if (percentage >= 60) return 'vocabLists.quiz.good';
    return 'vocabLists.quiz.needsPractice';
  }

  getWordImageUrl(word?: WordListWord): string | null {
    if (!word?.media || typeof word.media !== 'object') {
      return null;
    }

    const src = word.media['src'];
    if (src && typeof src === 'object') {
      const sizeOrder = ['medium', 'large', 'large2x'];
      const srcWithIndex = src as Record<string, unknown>;

      for (const size of sizeOrder) {
        if (srcWithIndex[size] && typeof srcWithIndex[size] === 'string') {
          return srcWithIndex[size] as string;
        }
      }
    }

    return null;
  }
}
