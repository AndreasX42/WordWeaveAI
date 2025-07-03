import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslatePipe } from '../shared/pipes/translate.pipe';
import { TranslationService } from '../services/translation.service';
import {
  HealthMonitorService,
  HealthTile,
} from '../services/health-monitor.service';

@Component({
  selector: 'app-health-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    TranslatePipe,
  ],
  templateUrl: './health-dashboard.html',
  styleUrl: './health-dashboard.scss',
})
export class HealthDashboardComponent implements OnInit, OnDestroy {
  private healthService = inject(HealthMonitorService);
  private translationService = inject(TranslationService);

  tiles = signal<HealthTile[]>([]);
  overallHealth = signal<'excellent' | 'good' | 'poor'>('excellent');

  private refreshInterval?: number;

  ngOnInit(): void {
    this.loadData();
    // Auto-refresh every 10 seconds
    this.refreshInterval = window.setInterval(() => {
      this.loadData();
    }, 10000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadData(): void {
    this.tiles.set(this.healthService.getAllTiles());
    this.overallHealth.set(this.healthService.getOverallHealth());
  }

  async refreshData(): Promise<void> {
    await this.healthService.refreshAll();
    this.loadData();
  }

  getStatusIcon(status: string): string {
    switch (status) {
      case 'excellent':
        return 'check_circle';
      case 'good':
        return 'thumb_up';
      case 'poor':
        return 'warning';
      default:
        return 'help';
    }
  }

  getStatusClass(status: string): string {
    return `status-${status}`;
  }

  getOverallHealthIcon(): string {
    return this.getStatusIcon(this.overallHealth());
  }

  getOverallHealthClass(): string {
    return this.getStatusClass(this.overallHealth());
  }

  getOverallHealthStatus(): string {
    return `health.dashboard.status.${this.overallHealth()}`;
  }

  getStatusText(status: string): string {
    return `health.dashboard.status.${status}`;
  }

  formatValue(value: number, unitKey: string): string {
    // Handle offline status for backend and API
    if (value < 0) {
      return this.translationService.translate(
        'health.dashboard.values.offline'
      );
    }

    // Handle error rate with better formatting
    if (unitKey === 'health.dashboard.values.errorsPerMinute') {
      if (value === 0) {
        return this.translationService.translate(
          'health.dashboard.values.noErrors'
        );
      }
      const unit = this.translationService.translate(unitKey);
      return `${value.toFixed(1)} ${unit}`;
    }

    const unit = this.translationService.translate(unitKey);
    return `${value.toFixed(1)} ${unit}`;
  }

  formatTimestamp(timestamp: number): string {
    return new Date(timestamp).toLocaleTimeString();
  }
}
