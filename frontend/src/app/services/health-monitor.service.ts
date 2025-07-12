import { Injectable, DestroyRef, inject, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Configs } from '../shared/config';

export interface HealthTile {
  id: string;
  title: string;
  value: number;
  unit: string;
  status: 'excellent' | 'good' | 'poor';
  icon: string;
  description: string;
  lastUpdated: number;
}

@Injectable({
  providedIn: 'root',
})
export class HealthMonitorService implements OnDestroy {
  private readonly STORAGE_KEY = 'health_metrics';
  private readonly MAX_RESPONSE_TIMES = 50; // Limit response times array
  private readonly MAX_STORAGE_ENTRIES = 100; // Limit localStorage entries
  private destroyRef = inject(DestroyRef);
  private httpClient = inject(HttpClient);

  private tiles: HealthTile[] = [
    {
      id: 'backend',
      title: 'Backend Health',
      value: 0,
      unit: 'ms',
      status: 'excellent',
      icon: 'cloud',
      description: 'Backend API uptime & error rate',
      lastUpdated: Date.now(),
    },
    {
      id: 'api',
      title: 'Response Time',
      value: 0,
      unit: 'ms',
      status: 'excellent',
      icon: 'api',
      description: 'Average API response time',
      lastUpdated: Date.now(),
    },
    {
      id: 'api_errors',
      title: 'Error Rate',
      value: 0,
      unit: 'errors/min',
      status: 'excellent',
      icon: 'error_outline',
      description: 'Backend errors per minute',
      lastUpdated: Date.now(),
    },
    {
      id: 'errors',
      title: 'JS Error Rate',
      value: 0,
      unit: 'errors/min',
      status: 'excellent',
      icon: 'bug_report',
      description: 'JavaScript errors per minute',
      lastUpdated: Date.now(),
    },
  ];

  private monitoringInterval?: number;
  private apiResponseTimes: number[] = [];
  private errorCount = 0;
  private errorStartTime = Date.now();
  private apiErrorCount = 0;
  private apiErrorStartTime = Date.now();

  constructor() {
    this.loadTilesFromStorage();
    this.startMonitoring();
  }

  private startMonitoring(): void {
    // Check backend health every 2 minutes
    this.checkBackendHealth();
    this.monitoringInterval = window.setInterval(() => {
      this.checkBackendHealth();
    }, 120000);

    // Start error tracking
    this.startErrorTracking();
  }

  private async checkBackendHealth(): Promise<void> {
    const startTime = performance.now();

    try {
      await fetch(`${Configs.BASE_URL}${Configs.HEALTH_URL}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const responseTime = performance.now() - startTime;
      this.updateTile(
        'backend',
        responseTime,
        this.getBackendStatus(responseTime)
      );
    } catch {
      // Backend is down - set to poor status with -1 to indicate offline
      this.updateTile('backend', -1, 'poor');
      // Also track this as an API error since health check failed
      this.trackApiError();
    }
  }

  private startErrorTracking(): void {
    console.log('Starting error tracking...');

    // Track JavaScript errors
    window.addEventListener('error', (event) => {
      console.log('Error caught:', event.error);
      this.recordError();
    });

    // Track unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      console.log('Promise rejection caught:', event.reason);
      this.recordError();
    });

    // Update error rate every minute
    setInterval(() => {
      this.updateErrorRate();
      this.updateApiErrorRate();
    }, 60000);

    // Also update every 10 seconds for more responsive testing
    setInterval(() => {
      this.updateErrorRate();
      this.updateApiErrorRate();
    }, 10000);
  }

  private recordError(): void {
    this.errorCount++;
    console.log(`Error recorded. Total errors: ${this.errorCount}`);

    // Update immediately for testing purposes
    setTimeout(() => {
      this.updateErrorRate();
    }, 1000);
  }

  private updateErrorRate(): void {
    const timeElapsed = (Date.now() - this.errorStartTime) / 60000; // minutes
    const errorRate =
      timeElapsed > 0 ? this.errorCount / timeElapsed : this.errorCount; // If less than 1 minute, use raw count

    console.log(
      `Updating error rate: ${this.errorCount} errors in ${timeElapsed.toFixed(
        2
      )} minutes = ${errorRate.toFixed(2)} errors/min`
    );

    this.updateTile('errors', errorRate, this.getErrorStatus(errorRate));

    // Reset for next period only if we've been running for more than a minute
    if (timeElapsed >= 1) {
      this.errorCount = 0;
      this.errorStartTime = Date.now();
      console.log('Error counter reset');
    }
  }

  // Method to track API errors from interceptor
  trackApiError(): void {
    this.apiErrorCount++;
    console.log(`API Error recorded. Total API errors: ${this.apiErrorCount}`);

    // Update immediately for testing purposes
    setTimeout(() => {
      this.updateApiErrorRate();
    }, 1000);
  }

  private updateApiErrorRate(): void {
    const timeElapsed = (Date.now() - this.apiErrorStartTime) / 60000; // minutes
    const apiErrorRate =
      timeElapsed > 0 ? this.apiErrorCount / timeElapsed : this.apiErrorCount; // If less than 1 minute, use raw count

    console.log(
      `Updating API error rate: ${
        this.apiErrorCount
      } errors in ${timeElapsed.toFixed(2)} minutes = ${apiErrorRate.toFixed(
        2
      )} errors/min`
    );

    this.updateTile(
      'api_errors',
      apiErrorRate,
      this.getErrorStatus(apiErrorRate)
    );

    // Reset for next period only if we've been running for more than a minute
    if (timeElapsed >= 1) {
      this.apiErrorCount = 0;
      this.apiErrorStartTime = Date.now();
      console.log('API Error counter reset');
    }
  }

  // Method to track API response times from interceptor
  trackApiResponseTime(responseTime: number): void {
    this.apiResponseTimes.push(responseTime);

    // Keep only last MAX_RESPONSE_TIMES response times to prevent overflow
    if (this.apiResponseTimes.length > this.MAX_RESPONSE_TIMES) {
      this.apiResponseTimes = this.apiResponseTimes.slice(
        -this.MAX_RESPONSE_TIMES
      );
    }

    // Calculate average
    const avgResponseTime =
      this.apiResponseTimes.reduce((sum, time) => sum + time, 0) /
      this.apiResponseTimes.length;

    // Check if backend is offline - if so, API should also show as poor
    const backendTile = this.getTileById('backend');
    if (backendTile && backendTile.value < 0) {
      // Backend is offline, so API response time is also problematic
      this.updateTile('api', -1, 'poor');
    } else {
      this.updateTile(
        'api',
        avgResponseTime,
        this.getApiStatus(avgResponseTime)
      );
    }
  }

  private updateTile(
    id: string,
    value: number,
    status: 'excellent' | 'good' | 'poor'
  ): void {
    const tileIndex = this.tiles.findIndex((tile) => tile.id === id);
    if (tileIndex !== -1) {
      this.tiles[tileIndex] = {
        ...this.tiles[tileIndex],
        value: Math.round(value * 100) / 100,
        status,
        lastUpdated: Date.now(),
      };
      this.saveTilesToStorage();

      // If backend goes offline, update API status too
      if (id === 'backend' && value < 0) {
        const apiTileIndex = this.tiles.findIndex((tile) => tile.id === 'api');
        if (apiTileIndex !== -1) {
          this.tiles[apiTileIndex] = {
            ...this.tiles[apiTileIndex],
            value: -1,
            status: 'poor',
            lastUpdated: Date.now(),
          };
        }
      }

      // If backend comes back online and API was offline, reset API to last known good value
      if (id === 'backend' && value >= 0) {
        const apiTile = this.getTileById('api');
        if (apiTile && apiTile.value < 0 && this.apiResponseTimes.length > 0) {
          const avgResponseTime =
            this.apiResponseTimes.reduce((sum, time) => sum + time, 0) /
            this.apiResponseTimes.length;
          const apiTileIndex = this.tiles.findIndex(
            (tile) => tile.id === 'api'
          );
          if (apiTileIndex !== -1) {
            this.tiles[apiTileIndex] = {
              ...this.tiles[apiTileIndex],
              value: Math.round(avgResponseTime * 100) / 100,
              status: this.getApiStatus(avgResponseTime),
              lastUpdated: Date.now(),
            };
          }
        }
      }
    }
  }

  // Status calculation methods
  private getBackendStatus(time: number): 'excellent' | 'good' | 'poor' {
    if (time < 0) return 'poor'; // Offline
    if (time < 200) return 'excellent';
    if (time < 500) return 'good';
    return 'poor';
  }

  private getApiStatus(time: number): 'excellent' | 'good' | 'poor' {
    if (time < 0) return 'poor'; // Offline/unavailable
    if (time < 300) return 'excellent';
    if (time < 800) return 'good';
    return 'poor';
  }

  private getErrorStatus(
    errorsPerMinute: number
  ): 'excellent' | 'good' | 'poor' {
    if (errorsPerMinute === 0) return 'excellent';
    if (errorsPerMinute < 1) return 'good';
    return 'poor';
  }

  // Storage methods with overflow protection
  private saveTilesToStorage(): void {
    try {
      const dataToStore = {
        tiles: this.tiles,
        timestamp: Date.now(),
      };

      const serializedData = JSON.stringify(dataToStore);

      // Check if we're approaching localStorage limits
      if (serializedData.length > this.MAX_STORAGE_ENTRIES * 1000) {
        console.warn(
          'Health metrics data approaching localStorage limits, cleaning up...'
        );
        this.cleanupStorage();
      }

      localStorage.setItem(this.STORAGE_KEY, serializedData);
    } catch (error) {
      console.warn('Failed to save health tiles to localStorage:', error);
      // Try to clean up and save again
      this.cleanupStorage();
      try {
        localStorage.setItem(
          this.STORAGE_KEY,
          JSON.stringify({
            tiles: this.tiles,
            timestamp: Date.now(),
          })
        );
      } catch (retryError) {
        console.error(
          'Failed to save health tiles even after cleanup:',
          retryError
        );
      }
    }
  }

  private cleanupStorage(): void {
    try {
      // Remove old health metrics if they exist
      const keys = Object.keys(localStorage);
      const healthKeys = keys.filter(
        (key) => key.startsWith('health_') || key === this.STORAGE_KEY
      );

      // Keep only the most recent entries
      if (healthKeys.length > 5) {
        healthKeys.slice(0, -5).forEach((key) => {
          localStorage.removeItem(key);
        });
      }
    } catch (error) {
      console.warn('Failed to cleanup localStorage:', error);
    }
  }

  private loadTilesFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const parsedData = JSON.parse(stored);

        // Handle both old format (array) and new format (object)
        let loadedTiles;
        if (Array.isArray(parsedData)) {
          loadedTiles = parsedData;
        } else if (parsedData.tiles && Array.isArray(parsedData.tiles)) {
          loadedTiles = parsedData.tiles;
        }

        if (
          loadedTiles &&
          Array.isArray(loadedTiles) &&
          loadedTiles.length === 4
        ) {
          // Check if tiles have translation keys or old hardcoded strings
          const firstTile = loadedTiles[0];
          if (
            firstTile &&
            firstTile.title &&
            !firstTile.title.startsWith('health.dashboard.')
          ) {
            // Old format detected - clear cache and use default tiles with translation keys
            console.log(
              'Clearing old health tiles cache - updating to use translations'
            );
            localStorage.removeItem(this.STORAGE_KEY);
            return;
          }

          // Only restore values and status, keep translation keys for titles/descriptions/units
          this.tiles.forEach((defaultTile, index) => {
            if (
              loadedTiles[index] &&
              loadedTiles[index].id === defaultTile.id
            ) {
              defaultTile.value = loadedTiles[index].value;
              defaultTile.status = loadedTiles[index].status;
              defaultTile.lastUpdated = loadedTiles[index].lastUpdated;
            }
          });
        }
      }
    } catch (error) {
      console.warn('Failed to load health tiles from localStorage:', error);
    }
  }

  // Public methods
  getAllTiles(): HealthTile[] {
    return [...this.tiles];
  }

  getTileById(id: string): HealthTile | undefined {
    return this.tiles.find((tile) => tile.id === id);
  }

  getOverallHealth(): 'excellent' | 'good' | 'poor' {
    const statusCounts = {
      excellent: this.tiles.filter((tile) => tile.status === 'excellent')
        .length,
      good: this.tiles.filter((tile) => tile.status === 'good').length,
      poor: this.tiles.filter((tile) => tile.status === 'poor').length,
    };

    if (statusCounts.poor > 0) return 'poor';
    if (statusCounts.excellent >= 4) return 'excellent'; // Updated for 4 tiles
    return 'good';
  }

  // Manual refresh method
  async refreshAll(): Promise<void> {
    await this.checkBackendHealth();
  }

  // Cleanup method
  ngOnDestroy(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }
  }

  // Add public method to manually trigger error rate update for testing
  public triggerErrorRateUpdate(): void {
    this.updateErrorRate();
    this.updateApiErrorRate();
  }

  // Public method to force clear cached tiles and use latest translation keys
  public clearCachedTiles(): void {
    localStorage.removeItem(this.STORAGE_KEY);
    console.log(
      'Health tiles cache cleared - tiles will use latest translation keys'
    );
  }
}
