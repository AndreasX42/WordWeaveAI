import { Component } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslatePipe } from '@/shared/pipes/translate.pipe';

@Component({
  selector: 'app-loading-state',
  templateUrl: './loading-state.html',
  styleUrls: ['./loading-state.scss'],
  standalone: true,
  imports: [MatProgressSpinnerModule, TranslatePipe],
})
export class LoadingStateComponent {}
