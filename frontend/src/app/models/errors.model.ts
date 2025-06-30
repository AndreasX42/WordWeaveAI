import { HealthMetric } from '../services/health-monitor.service';

/**
 * Custom error to represent a degradation in application health.
 * This allows us to specifically catch and report performance issues
 * through the global error handler.
 */
export class PoorHealthError extends Error {
  /**
   * @param message The error message.
   * @param metrics The collection of recent health metrics that led to this error.
   */
  constructor(message: string, public metrics: HealthMetric[]) {
    super(message);
    this.name = 'PoorHealthError';
  }
}
