import { Injectable } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';

export interface HealthMetric {
  id: string;
  name: string;
  value: number;
  status: 'excellent' | 'good' | 'poor';
  timestamp: number;
  page: string;
  unit: string;
}

export interface HealthSummary {
  pageLoad: number;
  fcp: number;
  lcp: number;
  tti: number;
  cls: number;
  memory: number;
}

@Injectable({
  providedIn: 'root',
})
export class HealthMonitorService {
  private metrics: HealthMetric[] = [];
  private currentPage: string = '/';
  private readonly STORAGE_KEY = 'health_metrics';
  private readonly MAX_METRICS = 100;

  constructor(private router: Router) {
    this.loadMetricsFromStorage();
    this.initializeRouteTracking();
    this.startMonitoring();
  }

  private initializeRouteTracking(): void {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        this.currentPage = event.url;
        this.capturePageMetrics();
      });
  }

  private startMonitoring(): void {
    // Monitor Core Web Vitals
    this.monitorFCP();
    this.monitorLCP();
    this.monitorCLS();
    this.monitorTTI();

    // Monitor memory usage every 10 seconds
    setInterval(() => {
      this.monitorMemoryUsage();
    }, 10000);

    // Monitor page load on navigation
    this.monitorPageLoad();
  }

  private capturePageMetrics(): void {
    // Only capture real page load metrics on actual navigation, not manual refresh
    // This prevents recording incorrect high values when refreshing manually
    if (performance.timing && performance.timing.loadEventEnd > 0) {
      setTimeout(() => {
        const loadTime =
          performance.timing.loadEventEnd - performance.timing.navigationStart;
        // Only record reasonable load times (> 0ms and < 30 seconds) to avoid stale/invalid data
        if (
          loadTime > 0 &&
          loadTime < 30000 &&
          performance.timing.navigationStart > 0
        ) {
          this.addMetric(
            'Page Load',
            loadTime,
            'ms',
            this.getPageLoadStatus(loadTime)
          );
        }
      }, 100);
    }
  }

  private monitorPageLoad(): void {
    window.addEventListener('load', () => {
      const loadTime =
        performance.timing.loadEventEnd - performance.timing.navigationStart;
      this.addMetric(
        'Page Load',
        loadTime,
        'ms',
        this.getPageLoadStatus(loadTime)
      );
    });
  }

  private monitorFCP(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            const fcp = entry.startTime;
            this.addMetric(
              'First Contentful Paint',
              fcp,
              'ms',
              this.getFCPStatus(fcp)
            );
          }
        }
      });

      try {
        observer.observe({ entryTypes: ['paint'] });
      } catch (e) {
        console.warn('FCP monitoring not supported');
      }
    }
  }

  private monitorLCP(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          const lcp = entry.startTime;
          this.addMetric(
            'Largest Contentful Paint',
            lcp,
            'ms',
            this.getLCPStatus(lcp)
          );
        }
      });

      try {
        observer.observe({ entryTypes: ['largest-contentful-paint'] });
      } catch (e) {
        console.warn('LCP monitoring not supported');
      }
    }
  }

  private monitorCLS(): void {
    if ('PerformanceObserver' in window) {
      let clsValue = 0;
      const observer = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!(entry as any).hadRecentInput) {
            clsValue += (entry as any).value;
          }
        }
        if (clsValue > 0) {
          this.addMetric(
            'Cumulative Layout Shift',
            clsValue * 1000,
            'score',
            this.getCLSStatus(clsValue)
          );
        }
      });

      try {
        observer.observe({ entryTypes: ['layout-shift'] });
      } catch (e) {
        console.warn('CLS monitoring not supported');
      }
    }
  }

  private monitorTTI(): void {
    // Simplified TTI calculation
    window.addEventListener('load', () => {
      setTimeout(() => {
        const tti =
          performance.timing.domInteractive -
          performance.timing.navigationStart;
        this.addMetric(
          'Time to Interactive',
          tti,
          'ms',
          this.getTTIStatus(tti)
        );
      }, 100);
    });
  }

  private monitorMemoryUsage(): void {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      const usedMB = Math.round(memory.usedJSHeapSize / 1024 / 1024);
      this.addMetric(
        'Memory Usage',
        usedMB,
        'MB',
        this.getMemoryStatus(usedMB)
      );
    }
  }

  private addMetric(
    name: string,
    value: number,
    unit: string,
    status: 'excellent' | 'good' | 'poor'
  ): void {
    const metric: HealthMetric = {
      id: `${Date.now()}-${Math.random()}`,
      name,
      value: Math.round(value * 100) / 100,
      status,
      timestamp: Date.now(),
      page: this.currentPage,
      unit,
    };

    this.metrics.push(metric);

    // Keep only recent metrics
    if (this.metrics.length > this.MAX_METRICS) {
      this.metrics = this.metrics.slice(-this.MAX_METRICS);
    }

    this.saveMetricsToStorage();
  }

  // Status calculation methods
  private getPageLoadStatus(time: number): 'excellent' | 'good' | 'poor' {
    if (time < 1000) return 'excellent';
    if (time < 3000) return 'good';
    return 'poor';
  }

  private getFCPStatus(time: number): 'excellent' | 'good' | 'poor' {
    if (time < 1000) return 'excellent';
    if (time < 1800) return 'good';
    return 'poor';
  }

  private getLCPStatus(time: number): 'excellent' | 'good' | 'poor' {
    if (time < 1500) return 'excellent';
    if (time < 2500) return 'good';
    return 'poor';
  }

  private getTTIStatus(time: number): 'excellent' | 'good' | 'poor' {
    if (time < 2000) return 'excellent';
    if (time < 4000) return 'good';
    return 'poor';
  }

  private getCLSStatus(score: number): 'excellent' | 'good' | 'poor' {
    if (score < 0.1) return 'excellent';
    if (score < 0.25) return 'good';
    return 'poor';
  }

  private getMemoryStatus(mb: number): 'excellent' | 'good' | 'poor' {
    if (mb < 50) return 'excellent';
    if (mb < 100) return 'good';
    return 'poor';
  }

  // Storage methods
  private saveMetricsToStorage(): void {
    try {
      const data = JSON.stringify(this.metrics);
      localStorage.setItem(this.STORAGE_KEY, data);
    } catch (error) {
      console.warn('Failed to save metrics to localStorage:', error);
      // Don't throw - this is a non-critical operation
      // Global error handler doesn't need to be involved for localStorage failures
    }
  }

  private loadMetricsFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        this.metrics = JSON.parse(stored);
        // Validate the loaded data
        if (!Array.isArray(this.metrics)) {
          throw new Error('Invalid metrics data format in localStorage');
        }
      }
    } catch (error) {
      console.warn('Failed to load metrics from localStorage:', error);
      this.metrics = [];
      // Clear corrupted data
      try {
        localStorage.removeItem(this.STORAGE_KEY);
      } catch {
        // Ignore localStorage errors
      }
    }
  }

  // Public methods
  getAllMetrics(): HealthMetric[] {
    return [...this.metrics];
  }

  getRecentMetrics(count: number = 20): HealthMetric[] {
    return this.metrics.slice(-count);
  }

  getMetricsByPage(page: string): HealthMetric[] {
    return this.metrics.filter((m) => m.page === page);
  }

  getHealthSummary(): HealthSummary {
    const recent = this.getRecentMetrics(10);

    return {
      pageLoad: this.getAverageByName(recent, 'Page Load'),
      fcp: this.getAverageByName(recent, 'First Contentful Paint'),
      lcp: this.getAverageByName(recent, 'Largest Contentful Paint'),
      tti: this.getAverageByName(recent, 'Time to Interactive'),
      cls: this.getAverageByName(recent, 'Cumulative Layout Shift'),
      memory: this.getLatestByName(recent, 'Memory Usage'),
    };
  }

  private getAverageByName(metrics: HealthMetric[], name: string): number {
    const filtered = metrics.filter((m) => m.name === name);
    if (filtered.length === 0) return 0;
    return filtered.reduce((sum, m) => sum + m.value, 0) / filtered.length;
  }

  private getLatestByName(metrics: HealthMetric[], name: string): number {
    const filtered = metrics.filter((m) => m.name === name);
    return filtered.length > 0 ? filtered[filtered.length - 1].value : 0;
  }

  getOverallHealth(): 'excellent' | 'good' | 'poor' {
    const recent = this.getRecentMetrics(10);
    if (recent.length === 0) return 'excellent';

    const statusCounts = {
      excellent: recent.filter((m) => m.status === 'excellent').length,
      good: recent.filter((m) => m.status === 'good').length,
      poor: recent.filter((m) => m.status === 'poor').length,
    };

    const total = recent.length;
    if (statusCounts.poor / total > 0.3) return 'poor';
    if (statusCounts.excellent / total > 0.7) return 'excellent';
    return 'good';
  }

  clearMetrics(): void {
    this.metrics = [];
    this.saveMetricsToStorage();
  }

  // Trigger manual collection
  collectMetrics(): void {
    // Only collect real-time metrics on manual refresh, not page load or timing metrics
    // to avoid incorrect calculations from stale performance data
    this.monitorMemoryUsage();

    // Optionally capture current FCP/LCP if available, but not page load timing
    if (performance.getEntriesByType) {
      const paintEntries = performance.getEntriesByType('paint');
      const fcpEntry = paintEntries.find(
        (entry) => entry.name === 'first-contentful-paint'
      );
      if (fcpEntry && fcpEntry.startTime > 0) {
        this.addMetric(
          'First Contentful Paint',
          fcpEntry.startTime,
          'ms',
          this.getFCPStatus(fcpEntry.startTime)
        );
      }
    }
  }
}
