import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { TranslatePipe } from '@/shared/pipes/translate.pipe';

@Component({
  selector: 'app-error-state',
  templateUrl: './error-state.html',
  styleUrls: ['./error-state.scss'],
  standalone: true,
  imports: [MatIconModule, MatButtonModule, TranslatePipe],
})
export class ErrorStateComponent {
  @Input() error: string | null = null;
  @Output() back = new EventEmitter<void>();

  goBack(): void {
    this.back.emit();
  }
}
