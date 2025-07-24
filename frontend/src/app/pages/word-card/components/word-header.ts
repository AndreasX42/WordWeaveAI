import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { VocabularyWord } from '@/models/word.model';
import { TranslatePipe } from '@/shared/pipes/translate.pipe';
import { LoadingStates } from './word-details';

@Component({
  selector: 'app-word-header',
  templateUrl: './word-header.html',
  styleUrls: ['./word-header.scss'],
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, TranslatePipe],
})
export class WordHeaderComponent {
  @Input() word!: VocabularyWord;
  @Input() loadingStates!: LoadingStates;
  @Input() isRequestMode!: boolean;
  @Input() hasTargetSyllables!: boolean;
  @Input() hasValidPronunciation!: boolean;
  @Output() playCombinedAudio = new EventEmitter<void>();
}
