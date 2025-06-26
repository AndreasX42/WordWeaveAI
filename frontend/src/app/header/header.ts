import { Component, input, inject } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { ThemeService } from '../services/theme.service';

@Component({
  selector: 'app-header',
  imports: [
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
    MatDividerModule,
  ],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  title = input<string>();
  themeService = inject(ThemeService);

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }
}
