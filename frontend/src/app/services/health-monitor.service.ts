import { Injectable, DestroyRef, inject, ErrorHandler } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { PoorHealthError } from '../models/errors.model';

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
  private currentPage = '/';
  private readonly STORAGE_KEY = 'health_metrics';
  private readonly MAX_METRICS = 100;
  private destroyRef = inject(DestroyRef);
  private router = inject(Router);
  private errorHandler = inject(ErrorHandler);
  private poorHealthReported = false;

  constructor() {
    this.loadMetricsFromStorage();
    this.initializeRouteTracking();
    this.startMonitoring();
  }

  private initializeRouteTracking(): void {
    this.router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((event: NavigationEnd) => {
        this.currentPage = event.url;
      });
  }

  private startMonitoring(): void {
    // Monitor Core Web Vitals
    this.monitorFCP();
    this.monitorLCP();
    this.monitorCLS();
    this.monitorPageTimings();

    // Monitor memory usage every 10 seconds
    setInterval(() => {
      this.monitorMemoryUsage();
    }, 10000);
  }

  private monitorPageTimings(): void {
    window.addEventListener('load', () => {
      // Use setTimeout to run this after the load event has fully completed,
      // ensuring the navigation timing metrics are accurate.
      setTimeout(() => {
        const navEntries = performance.getEntriesByType('navigation');
        if (navEntries.length > 0) {
          const navTiming = navEntries[0] as PerformanceNavigationTiming;

          // Page Load
          const loadTime = navTiming.duration;
          if (loadTime > 0) {
            this.addMetric(
              'Page Load',
              loadTime,
              'ms',
              this.getPageLoadStatus(loadTime)
            );
          }

          // TTI
          const tti = navTiming.domInteractive;
          if (tti > 0) {
            this.addMetric(
              'Time to Interactive',
              tti,
              'ms',
              this.getTTIStatus(tti)
            );
          }
        }
      }, 0);
    });
  }

  private monitorFCP(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((entryList, obs) => {
        for (const entry of entryList.getEntries()) {
          if (entry.name === 'first-contentful-paint') {
            const fcp = entry.startTime;
            this.addMetric(
              'First Contentful Paint',
              fcp,
              'ms',
              this.getFCPStatus(fcp)
            );
            // Disconnect the observer after FCP is recorded to avoid multiple entries.
            obs.disconnect();
          }
        }
      });

      try {
        observer.observe({ type: 'paint', buffered: true });
      } catch {
        console.warn('FCP monitoring not supported');
      }
    }
  }

  private monitorLCP(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        if (entries.length > 0) {
          // The last entry is the most up-to-date LCP value.
          const lcpEntry = entries[entries.length - 1];
          const lcp = lcpEntry.startTime;
          this.addMetric(
            'Largest Contentful Paint',
            lcp,
            'ms',
            this.getLCPStatus(lcp)
          );
        }
      });

      try {
        observer.observe({ type: 'largest-contentful-paint', buffered: true });
      } catch {
        console.warn('LCP monitoring not supported');
      }
    }
  }

  private monitorCLS(): void {
    if ('PerformanceObserver' in window) {
      let clsValue = 0;
      const observer = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          const layoutShiftEntry = entry as PerformanceEntry & {
            hadRecentInput?: boolean;
            value: number;
          };
          if (!layoutShiftEntry.hadRecentInput) {
            clsValue += layoutShiftEntry.value;
          }
        }
        // Report final CLS value when page is hidden.
        this.addMetric(
          'Cumulative Layout Shift',
          clsValue * 1000,
          'score',
          this.getCLSStatus(clsValue)
        );
      });

      try {
        observer.observe({ type: 'layout-shift', buffered: true });

        // Report CLS when the page is hidden
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'hidden') {
            observer.takeRecords();
            observer.disconnect();
          }
        });
      } catch {
        console.warn('CLS monitoring not supported');
      }
    }
  }

  private monitorMemoryUsage(): void {
    if ('memory' in performance) {
      const memory = (performance as { memory: { usedJSHeapSize: number } })
        .memory;
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
    this.checkHealthAndReport();
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

  /**
   * Checks the overall health and reports to the global error handler if it is 'poor'.
   * To avoid log spam, it only reports the first time health degrades.
   * The flag is reset when health improves.
   */
  private checkHealthAndReport(): void {
    const health = this.getOverallHealth();
    if (health === 'poor') {
      if (!this.poorHealthReported) {
        const recentMetrics = this.getRecentMetrics();
        const error = new PoorHealthError(
          'User experience performance has degraded to "poor".',
          recentMetrics
        );
        this.errorHandler.handleError(error);
        this.poorHealthReported = true;
      }
    } else {
      // Health is good or excellent, so reset the flag.
      this.poorHealthReported = false;
    }
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

  getRecentMetrics(count = 20): HealthMetric[] {
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
