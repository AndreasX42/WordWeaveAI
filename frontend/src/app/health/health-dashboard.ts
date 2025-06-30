import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatPaginatorModule } from '@angular/material/paginator';
import {
  HealthMonitorService,
  HealthMetric,
  HealthSummary,
} from '../services/health-monitor.service';

@Component({
  selector: 'app-health-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatTabsModule,
    MatProgressBarModule,
    MatPaginatorModule,
  ],
  templateUrl: './health-dashboard.html',
  styleUrl: './health-dashboard.scss',
})
export class HealthDashboardComponent implements OnInit, OnDestroy {
  private healthService = inject(HealthMonitorService);

  metrics = signal<HealthMetric[]>([]);
  paginatedMetrics = signal<HealthMetric[]>([]);
  summary = signal<HealthSummary>({
    pageLoad: 0,
    fcp: 0,
    lcp: 0,
    tti: 0,
    cls: 0,
    memory: 0,
  });
  overallHealth = signal<'excellent' | 'good' | 'poor'>('excellent');

  displayedColumns: string[] = ['name', 'value', 'status', 'page', 'timestamp'];
  private refreshInterval?: number;

  // Pagination
  pageSize = 5;
  currentPage = 0;
  totalMetrics = signal<number>(0);

  ngOnInit(): void {
    this.loadData();
    // Auto-refresh every 5 seconds
    this.refreshInterval = window.setInterval(() => {
      this.loadData();
    }, 5000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadData(): void {
    const allMetrics = this.healthService.getAllMetrics();
    this.metrics.set(allMetrics);
    this.totalMetrics.set(allMetrics.length);
    this.updatePaginatedMetrics();
    this.summary.set(this.healthService.getHealthSummary());
    this.overallHealth.set(this.healthService.getOverallHealth());
  }

  updatePaginatedMetrics(): void {
    const startIndex = this.currentPage * this.pageSize;
    const endIndex = startIndex + this.pageSize;
    const allMetrics = this.metrics();
    // Show most recent metrics first
    const sortedMetrics = [...allMetrics].reverse();
    this.paginatedMetrics.set(sortedMetrics.slice(startIndex, endIndex));
  }

  onPageChange(event: { pageIndex: number; pageSize: number }): void {
    this.currentPage = event.pageIndex;
    this.pageSize = event.pageSize;
    this.updatePaginatedMetrics();
  }

  refreshData(): void {
    this.healthService.collectMetrics();
    this.loadData();
  }

  clearAllData(): void {
    this.healthService.clearMetrics();
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

  formatValue(value: number, unit: string): string {
    if (unit === 'score') {
      return (value / 1000).toFixed(3);
    }
    return `${value.toFixed(1)} ${unit}`;
  }

  formatTimestamp(timestamp: number): string {
    return new Date(timestamp).toLocaleString();
  }

  getMetricDescription(name: string): string {
    const descriptions: Record<string, string> = {
      'Page Load': 'Time taken to fully load the page',
      'First Contentful Paint': 'Time when first content appears',
      'Largest Contentful Paint': 'Time when main content loads',
      'Time to Interactive': 'Time until page becomes interactive',
      'Cumulative Layout Shift': 'Visual stability score',
      'Memory Usage': 'Current JavaScript memory consumption',
    };
    return descriptions[name] || '';
  }

  getSummaryStatus(
    value: number,
    metricType: string
  ): 'excellent' | 'good' | 'poor' {
    switch (metricType) {
      case 'pageLoad':
        return value < 1000 ? 'excellent' : value < 3000 ? 'good' : 'poor';
      case 'fcp':
        return value < 1000 ? 'excellent' : value < 1800 ? 'good' : 'poor';
      case 'lcp':
        return value < 1500 ? 'excellent' : value < 2500 ? 'good' : 'poor';
      case 'tti':
        return value < 2000 ? 'excellent' : value < 4000 ? 'good' : 'poor';
      case 'cls':
        return value < 100 ? 'excellent' : value < 250 ? 'good' : 'poor';
      case 'memory':
        return value < 50 ? 'excellent' : value < 100 ? 'good' : 'poor';
      default:
        return 'good';
    }
  }

  exportData(): void {
    const data = {
      timestamp: new Date().toISOString(),
      summary: this.summary(),
      metrics: this.metrics(),
      overallHealth: this.overallHealth(),
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `health-dashboard-${
      new Date().toISOString().split('T')[0]
    }.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}
