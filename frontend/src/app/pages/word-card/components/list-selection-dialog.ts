import {
  Component,
  inject,
  OnInit,
  ChangeDetectionStrategy,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  MatDialogModule,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';

import { WordListService } from '../../../services/word-list.service';
import { TranslatePipe } from '../../../shared/pipes/translate.pipe';
import {
  WordList,
  AddWordToListRequest,
} from '../../../models/word-list.model';

export interface ListSelectionDialogData {
  vocabPk: string;
  vocabSk: string;
  mediaRef: string;
  sourceWord: string;
  targetWord: string;
}

@Component({
  selector: 'app-list-selection-dialog',
  template: `
    <div class="dialog-container">
      <h2 mat-dialog-title>
        <mat-icon>playlist_add</mat-icon>
        {{ 'wordCard.selectList' | translate }}
      </h2>

      <div class="word-preview">
        <span class="source-word">{{ data.sourceWord }}</span>
        <mat-icon class="arrow-icon">arrow_forward</mat-icon>
        <span class="target-word">{{ data.targetWord }}</span>
      </div>

      <mat-dialog-content>
        @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="30"></mat-spinner>
          <p>{{ 'vocabLists.loading' | translate }}</p>
        </div>
        } @else if (error()) {
        <div class="error-container">
          <mat-icon color="warn">error_outline</mat-icon>
          <p>{{ error() }}</p>
          <button mat-button (click)="loadLists()">
            {{ 'vocabLists.retry' | translate }}
          </button>
        </div>
        } @else if (lists().length === 0) {
        <div class="empty-container">
          <mat-icon class="empty-icon">list_alt</mat-icon>
          <p>{{ 'wordCard.noLists' | translate }}</p>
          <p class="empty-subtitle">
            {{ 'wordCard.createListFirst' | translate }}
          </p>
        </div>
        } @else {
        <mat-list class="lists-container">
          @for (list of lists(); track list.id) {
          <mat-list-item
            class="list-item"
            [class.adding]="addingToList() === list.id"
            (click)="addWordToList(list)"
            [disabled]="addingToList() !== null"
          >
            <mat-icon matListItemIcon>list</mat-icon>

            <div matListItemTitle>{{ list.name }}</div>

            <div matListItemLine class="list-meta">
              {{ list.word_count || 0 }}
              {{ 'vocabLists.words' | translate }} @if (list.description) { •
              {{ list.description }}
              }
            </div>

            @if (addingToList() === list.id) {
            <mat-spinner
              matListItemMeta
              diameter="20"
              strokeWidth="2"
            ></mat-spinner>
            } @else {
            <mat-icon matListItemMeta>add</mat-icon>
            }
          </mat-list-item>
          }
        </mat-list>
        }
      </mat-dialog-content>

      <mat-dialog-actions align="end">
        <button
          mat-button
          [mat-dialog-close]="false"
          [disabled]="addingToList() !== null"
        >
          {{ 'common.cancel' | translate }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styleUrl: './list-selection-dialog.scss',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatProgressSpinnerModule,
    TranslatePipe,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListSelectionDialogComponent implements OnInit {
  private vocabListService = inject(WordListService);
  private snackBar = inject(MatSnackBar);
  private dialogRef = inject(MatDialogRef<ListSelectionDialogComponent>);
  public data: ListSelectionDialogData = inject(MAT_DIALOG_DATA);

  // Component state
  lists = signal<WordList[]>([]);
  loading = signal<boolean>(true);
  error = signal<string | null>(null);
  addingToList = signal<string | null>(null);

  ngOnInit(): void {
    this.loadLists();
  }

  loadLists(): void {
    this.loading.set(true);
    this.error.set(null);

    this.vocabListService
      .getLists()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.lists.set(response.data);
        },
        error: (error) => {
          console.error('Error loading lists:', error);
          this.error.set(this.getErrorMessage(error));
        },
      });
  }

  addWordToList(list: WordList): void {
    if (this.addingToList()) return;

    this.addingToList.set(list.id);

    const request: AddWordToListRequest = {
      vocab_pk: this.data.vocabPk,
      vocab_sk: this.data.vocabSk,
      media_ref: this.data.mediaRef,
    };

    this.vocabListService
      .addWordToList(list.id, request)
      .pipe(finalize(() => this.addingToList.set(null)))
      .subscribe({
        next: () => {
          this.snackBar.open(`Word added to "${list.name}"`, 'Close', {
            duration: 3000,
          });
          this.dialogRef.close({ success: true, listName: list.name });
        },
        error: (error) => {
          console.error('Error adding word to list:', error);

          // Handle specific error cases
          let errorMessage = 'Failed to add word to list';
          if (error?.error?.message) {
            if (error.error.message.includes('already exists')) {
              errorMessage = 'Word is already in this list';
            } else {
              errorMessage = error.error.message;
            }
          }

          this.snackBar.open(errorMessage, 'Close', {
            duration: 4000,
          });
        },
      });
  }

  private getErrorMessage(error: unknown): string {
    const errorWithMessage = error as {
      error?: { message?: string };
      message?: string;
    };

    if (errorWithMessage?.error?.message) {
      return errorWithMessage.error.message;
    }
    if (errorWithMessage?.message) {
      return errorWithMessage.message;
    }
    return 'Failed to load lists. Please try again.';
  }
}
