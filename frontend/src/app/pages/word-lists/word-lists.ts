import {
  Component,
  inject,
  OnInit,
  ChangeDetectionStrategy,
  signal,
  DestroyRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  MatDialogModule,
  MatDialog,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, delay } from 'rxjs/operators';

import { ThemeService } from '../../services/theme.service';
import { TranslationService } from '../../services/translation.service';
import { NotificationService } from '../../services/notification.service';
import { WordListService } from '../../services/word-list.service';
import { AuthService } from '../../services/auth.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import {
  WordList,
  WordListWord,
  CreateWordListRequest,
  UpdateWordListRequest,
} from '../../models/word-list.model';

interface CreateListDialogData {
  name: string;
  description: string;
}

interface EditListDialogData {
  list: WordList;
  name: string;
  description: string;
}

@Component({
  selector: 'app-create-list-dialog',
  template: `
    <div class="dialog-container">
      <h2 mat-dialog-title>
        <mat-icon>{{ isEdit ? 'edit' : 'add_circle' }}</mat-icon>
        {{
          isEdit
            ? ('vocabLists.editList' | translate)
            : ('vocabLists.createList' | translate)
        }}
      </h2>

      <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <mat-dialog-content>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ 'vocabLists.listName' | translate }}</mat-label>
            <input
              matInput
              formControlName="name"
              [placeholder]="'vocabLists.listNamePlaceholder' | translate"
              autocomplete="off"
            />
            @if (form.get('name')?.hasError('required') &&
            form.get('name')?.touched) {
            <mat-error>{{
              'vocabLists.validation.nameRequired' | translate
            }}</mat-error>
            } @if (form.get('name')?.hasError('maxlength') &&
            form.get('name')?.touched) {
            <mat-error>{{
              'vocabLists.validation.nameTooLong' | translate
            }}</mat-error>
            }
          </mat-form-field>

          <mat-form-field appearance="outline" class="full-width">
            <mat-label>{{ 'vocabLists.description' | translate }}</mat-label>
            <textarea
              matInput
              formControlName="description"
              [placeholder]="'vocabLists.descriptionPlaceholder' | translate"
              rows="3"
            ></textarea>
            @if (form.get('description')?.hasError('maxlength') &&
            form.get('description')?.touched) {
            <mat-error>{{
              'vocabLists.validation.descriptionTooLong' | translate
            }}</mat-error>
            }
          </mat-form-field>
        </mat-dialog-content>

        <mat-dialog-actions align="end">
          <button
            type="button"
            mat-button
            [mat-dialog-close]="false"
            [disabled]="loading"
          >
            {{ 'common.cancel' | translate }}
          </button>

          <button
            type="submit"
            mat-raised-button
            color="primary"
            [disabled]="form.invalid || loading"
          >
            @if (loading) {
            <mat-spinner diameter="16" strokeWidth="2"></mat-spinner>
            }
            {{
              isEdit
                ? ('common.save' | translate)
                : ('common.create' | translate)
            }}
          </button>
        </mat-dialog-actions>
      </form>
    </div>
  `,
  styleUrl: './create-list-dialog.scss',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslatePipe,
  ],
})
export class CreateListDialogComponent {
  private wordListService = inject(WordListService);
  private snackBar = inject(MatSnackBar);
  private dialogRef = inject(MatDialogRef<CreateListDialogComponent>);
  public data: CreateListDialogData | EditListDialogData =
    inject(MAT_DIALOG_DATA);

  loading = false;

  get isEdit(): boolean {
    return 'list' in this.data;
  }

  form = new FormGroup({
    name: new FormControl(
      this.isEdit ? (this.data as EditListDialogData).list.name : '',
      [Validators.required, Validators.maxLength(100)]
    ),
    description: new FormControl(
      this.isEdit
        ? (this.data as EditListDialogData).list.description || ''
        : '',
      [Validators.maxLength(500)]
    ),
  });

  onSubmit(): void {
    if (this.form.invalid || this.loading) {
      return;
    }

    this.loading = true;
    const formValue = this.form.value;

    if (this.isEdit) {
      const editData = this.data as EditListDialogData;
      const request: UpdateWordListRequest = {
        name: formValue.name || undefined,
        description: formValue.description || undefined,
      };

      this.wordListService
        .updateList(editData.list.id, request)
        .pipe(finalize(() => (this.loading = false)))
        .subscribe({
          next: (updatedList) => {
            this.snackBar.open('List updated successfully', 'Close', {
              duration: 3000,
            });
            this.dialogRef.close(updatedList);
          },
          error: (error) => {
            console.error('Error updating list:', error);
            this.snackBar.open('Failed to update list', 'Close', {
              duration: 3000,
            });
          },
        });
    } else {
      const request: CreateWordListRequest = {
        name: formValue.name!,
        description: formValue.description || undefined,
      };

      this.wordListService
        .createList(request)
        .pipe(finalize(() => (this.loading = false)))
        .subscribe({
          next: (newList) => {
            this.snackBar.open('List created successfully', 'Close', {
              duration: 3000,
            });
            this.dialogRef.close(newList);
          },
          error: (error) => {
            console.error('Error creating list:', error);
            this.snackBar.open('Failed to create list', 'Close', {
              duration: 3000,
            });
          },
        });
    }
  }
}

@Component({
  selector: 'app-word-lists',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule,
    MatSnackBarModule,
    TranslatePipe,
  ],
  templateUrl: './word-lists.html',
  styleUrls: ['./word-lists.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WordListsComponent implements OnInit {
  private wordListService = inject(WordListService);
  private authService = inject(AuthService);
  private router = inject(Router);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private destroyRef = inject(DestroyRef);

  public themeService = inject(ThemeService);
  public translationService = inject(TranslationService);
  public notificationService = inject(NotificationService);

  // Component state
  lists = signal<WordList[]>([]);
  loading = signal<boolean>(true);
  error = signal<string | null>(null);

  // Selected list details
  selectedList = signal<WordList | null>(null);
  selectedListId = signal<string | null>(null);
  selectedListWords = signal<WordListWord[] | null>(null);
  loadingWords = signal<boolean>(false);
  wordsError = signal<string | null>(null);

  ngOnInit(): void {
    // Check authentication
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }

    this.loadLists();
  }

  loadLists(): void {
    this.loading.set(true);
    this.error.set(null);

    this.wordListService
      .getLists()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.loading.set(false))
      )
      .subscribe({
        next: (response) => {
          this.lists.set(response.data);
        },
        error: (error) => {
          console.error('Error loading vocabulary lists:', error);
          this.error.set(this.getErrorMessage(error));
        },
      });
  }

  openCreateListDialog(): void {
    const dialogRef = this.dialog.open(CreateListDialogComponent, {
      width: '500px',
      data: { name: '', description: '' } as CreateListDialogData,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        // Reload lists after successful creation
        this.loadLists();
      }
    });
  }

  openEditListDialog(list: WordList): void {
    const dialogRef = this.dialog.open(CreateListDialogComponent, {
      width: '500px',
      data: {
        list,
        name: list.name,
        description: list.description || '',
      } as EditListDialogData,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        // Reload lists after successful update
        this.loadLists();
      }
    });
  }

  confirmDeleteList(list: WordList): void {
    const confirmed = confirm(
      `Are you sure you want to delete "${list.name}"? This action cannot be undone.`
    );

    if (confirmed) {
      this.deleteList(list);
    }
  }

  deleteList(list: WordList): void {
    this.wordListService
      .deleteList(list.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.snackBar.open('List deleted successfully', 'Close', {
            duration: 3000,
          });

          // Remove from local state
          this.lists.set(this.lists().filter((l) => l.id !== list.id));

          // Close details panel if this list was selected
          if (this.selectedListId() === list.id) {
            this.closeListDetails();
          }
        },
        error: (error) => {
          console.error('Error deleting list:', error);
          this.snackBar.open('Failed to delete list', 'Close', {
            duration: 3000,
          });
        },
      });
  }

  openList(list: WordList): void {
    this.selectedList.set(list);
    this.selectedListId.set(list.id);
    this.selectedListWords.set(null);
    this.wordsError.set(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    this.loadWordsInList(list.id);
  }

  closeListDetails(): void {
    this.selectedList.set(null);
    this.selectedListId.set(null);
    this.selectedListWords.set(null);
    this.wordsError.set(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  loadWordsInList(listId: string): void {
    this.loadingWords.set(true);
    this.wordsError.set(null);

    this.wordListService
      .getWordsInList(listId)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        delay(500),
        finalize(() => this.loadingWords.set(false))
      )
      .subscribe({
        next: (response) => {
          this.selectedListWords.set(response.data);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        error: (error) => {
          console.error('Error loading words in list:', error);
          this.wordsError.set(this.getErrorMessage(error));
          window.scrollTo({ top: 0, behavior: 'smooth' });
        },
      });
  }

  viewWordDetails(word: WordListWord): void {
    const sourceLanguage =
      word.source_language || this.parseLanguageFromPk(word.vocab_pk);
    const targetLanguage =
      word.target_language || this.parseLanguageFromSk(word.vocab_sk);
    const pos = this.parsePosFromSk(word.vocab_sk) || 'word';
    const sourceWord = word.source_word || this.parseWordFromPk(word.vocab_pk);

    if (sourceLanguage && targetLanguage && sourceWord) {
      const mappedWord = {
        ...word,
        pk: word.vocab_pk,
        sk: word.vocab_sk,
        source_language: word.source_language || sourceLanguage,
        target_language: word.target_language || targetLanguage,
      };

      this.router.navigate(
        ['/words', sourceLanguage, targetLanguage, pos, sourceWord],
        {
          state: {
            pk: word.vocab_pk,
            sk: word.vocab_sk,
            word: mappedWord,
          },
        }
      );
    } else {
      // Fallback to query parameter format if we can't parse the URL components
      const queryParams: Record<string, string> = {
        pk: word.vocab_pk,
        sk: word.vocab_sk,
      };

      if (word['media_ref']) {
        queryParams['media_ref'] = word['media_ref'];
      }

      this.router.navigate(['/words'], {
        queryParams,
      });
    }
  }

  private parseLanguageFromPk(pk: string): string | null {
    // PK format: SRC#language#word
    const parts = pk.split('#');
    return parts.length >= 2 ? parts[1] : null;
  }

  private parseWordFromPk(pk: string): string | null {
    // PK format: SRC#language#word
    const parts = pk.split('#');
    return parts.length >= 3 ? parts[2] : null;
  }

  private parseLanguageFromSk(sk: string): string | null {
    // SK format: TGT#language#POS#pos
    const parts = sk.split('#');
    return parts.length >= 2 ? parts[1] : null;
  }

  private parsePosFromSk(sk: string): string | null {
    // SK format: TGT#language#POS#pos
    const parts = sk.split('#');
    return parts.length >= 4 ? parts[3] : null;
  }

  confirmRemoveWordFromList(word: WordListWord): void {
    const confirmed = confirm(
      `Are you sure you want to remove "${word.source_word}" from this list?`
    );

    if (confirmed) {
      this.removeWordFromList(word);
    }
  }

  removeWordFromList(word: WordListWord): void {
    if (!this.selectedList()) return;

    const request = {
      vocab_pk: word.vocab_pk,
      vocab_sk: word.vocab_sk,
    };

    this.wordListService
      .removeWordFromList(this.selectedList()!.id, request)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          // Update local state
          const words = this.selectedListWords();
          if (words) {
            const updatedWords = words.filter(
              (w) =>
                w.vocab_pk !== word.vocab_pk || w.vocab_sk !== word.vocab_sk
            );
            this.selectedListWords.set(updatedWords);
          }

          // Update the list's word count
          const currentList = this.selectedList();
          if (currentList && currentList.word_count !== undefined) {
            const updatedList = {
              ...currentList,
              word_count: currentList.word_count - 1,
            };
            this.selectedList.set(updatedList);

            // Update in lists array as well
            const lists = this.lists();
            const updatedLists = lists.map((l) =>
              l.id === updatedList.id ? updatedList : l
            );
            this.lists.set(updatedLists);
          }

          this.snackBar.open('Word removed from list', 'Close', {
            duration: 2000,
          });
        },
        error: (error) => {
          console.error('Error removing word from list:', error);
          this.snackBar.open('Failed to remove word from list', 'Close', {
            duration: 3000,
          });
        },
      });
  }

  getFormattedDate(dateString: string): string {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

      // Show hours if less than 1 day
      if (diffHours < 24) {
        if (diffHours === 0) return 'now';
        if (diffHours === 1) return '1h ago';
        return `${diffHours}h ago`;
      }

      if (diffDays === 1) return '1d ago';
      if (diffDays < 7) return `${diffDays}d ago`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
      if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
      });
    } catch {
      return dateString;
    }
  }

  getListColor(index: number): string {
    const colors = [
      '#FF6B6B',
      '#4ECDC4',
      '#45B7D1',
      '#96CEB4',
      '#FFEAA7',
      '#DDA0DD',
      '#F4A261',
      '#E76F51',
      '#2A9D8F',
      '#E9C46A',
      '#F72585',
      '#7209B7',
      '#A663CC',
      '#4361EE',
      '#4CC9F0',
    ];
    return colors[index % colors.length];
  }

  getListIcon(listName: string): string {
    const name = listName.toLowerCase();
    if (name.includes('verb') || name.includes('action')) return 'flash_on';
    if (name.includes('noun') || name.includes('thing')) return 'category';
    if (name.includes('adjective') || name.includes('describe'))
      return 'palette';
    if (name.includes('travel') || name.includes('trip')) return 'flight';
    if (name.includes('food') || name.includes('eat')) return 'restaurant';
    if (
      name.includes('work') ||
      name.includes('job') ||
      name.includes('business') ||
      name.includes('invest')
    )
      return 'business_center';
    if (name.includes('family') || name.includes('people'))
      return 'family_restroom';
    if (
      name.includes('school') ||
      name.includes('education') ||
      name.includes('study')
    )
      return 'school';
    if (name.includes('advanced') || name.includes('expert'))
      return 'military_tech';
    if (name.includes('basic') || name.includes('beginner')) return 'start';
    if (name.includes('book') || name.includes('read')) return 'menu_book';
    return 'folder';
  }

  getProgressText(list: WordList): string {
    const totalWords = list.word_count || 0;
    const learnedWords = list.learned_count || 0;

    return `${learnedWords}/${totalWords} learned`;
  }

  getWordImageUrl(word: WordListWord): string | null {
    if (!word.media || typeof word.media !== 'object') {
      return null;
    }

    const src = word.media['src'];
    if (src && typeof src === 'object') {
      // Prioritize image sizes: medium > large > large2x > any other available
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
    return 'An unexpected error occurred. Please try again.';
  }
}
