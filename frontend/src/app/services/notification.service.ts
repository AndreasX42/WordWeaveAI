import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'redirect';
  timestamp: number;
  seen: boolean;
  link?: string;
  icon?: string;
  progress?: number; // 0-100 for progress notifications
  sourceWord?: string;
  targetLanguage?: string;
  requestId?: string;
  pk?: string;
  sk?: string;
  mediaRef?: string;
}

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private router = inject(Router);

  // Signals for reactive UI
  private notificationsSignal = signal<NotificationItem[]>([]);
  private lastNotificationTime = signal<number>(Date.now());

  // Computed values
  public notifications = computed(() => this.notificationsSignal());
  public unseenCount = computed(
    () => this.notificationsSignal().filter((n) => !n.seen).length
  );
  public hasUnseen = computed(() => this.unseenCount() > 0);

  // Subject for real-time updates
  private notificationUpdate = new Subject<NotificationItem>();
  public notificationUpdate$ = this.notificationUpdate.asObservable();

  private readonly STORAGE_KEY = 'wordweave_notifications';
  private readonly MAX_NOTIFICATIONS = 5; // Keep only latest 5 notifications (LRU)

  constructor() {
    this.loadNotificationsFromStorage();
  }

  /**
   * Add or update a notification
   */
  addOrUpdateNotification(
    notification: Partial<NotificationItem> & {
      id: string;
      title: string;
      message: string;
      status: NotificationItem['status'];
    },
    forceOverride = false
  ): void {
    const currentNotifications = this.notificationsSignal();
    const existingIndex = currentNotifications.findIndex(
      (n) => n.id === notification.id
    );

    // Special handling for redirect notifications - they should always override non-redirect notifications
    if (existingIndex >= 0 && notification.status === 'redirect') {
      // Redirect notifications should always override existing ones
    }

    // Check if we're trying to override a redirect notification (unless forced)
    if (existingIndex >= 0 && !forceOverride) {
      const existing = currentNotifications[existingIndex];
      if (
        existing.status === 'redirect' &&
        notification.status !== 'redirect'
      ) {
        console.log('🚫 Preventing override of redirect notification:', {
          existingStatus: existing.status,
          newStatus: notification.status,
          id: notification.id,
          timestamp: new Date().toISOString(),
        });
        return; // Don't override redirect notifications unless forced
      }
    }

    const fullNotification: NotificationItem = {
      timestamp: Date.now(),
      seen: false,
      icon: this.getIconForStatus(notification.status),
      progress: this.getProgressForStatus(notification.status),
      ...notification,
    };

    let updatedNotifications: NotificationItem[];

    if (existingIndex >= 0) {
      // Update existing notification (preserve seen status if updating)
      updatedNotifications = [...currentNotifications];
      updatedNotifications[existingIndex] = {
        ...updatedNotifications[existingIndex],
        ...fullNotification,
        // Don't override seen status when updating
        seen: updatedNotifications[existingIndex].seen,
      };
      console.log('📝 Updated existing notification:', {
        id: fullNotification.id,
        oldStatus: currentNotifications[existingIndex].status,
        newStatus: fullNotification.status,
        forceOverride,
        oldMessage: currentNotifications[existingIndex].message,
        newMessage: fullNotification.message,
        timestamp: new Date().toISOString(),
      });
    } else {
      // Add new notification at the beginning
      updatedNotifications = [fullNotification, ...currentNotifications];
    }

    // Limit notifications
    if (updatedNotifications.length > this.MAX_NOTIFICATIONS) {
      updatedNotifications = updatedNotifications.slice(
        0,
        this.MAX_NOTIFICATIONS
      );
    }

    this.notificationsSignal.set(updatedNotifications);
    this.lastNotificationTime.set(Date.now());
    this.saveNotificationsToStorage();

    // Emit update for animations/sound effects
    this.notificationUpdate.next(fullNotification);
  }

  /**
   * Mark all notifications as seen
   */
  markAllAsSeen(): void {
    const updatedNotifications = this.notificationsSignal().map((n) => ({
      ...n,
      seen: true,
    }));
    this.notificationsSignal.set(updatedNotifications);
    this.saveNotificationsToStorage();
  }

  /**
   * Mark specific notification as seen
   */
  markAsSeen(id: string): void {
    const updatedNotifications = this.notificationsSignal().map((n) =>
      n.id === id ? { ...n, seen: true } : n
    );
    this.notificationsSignal.set(updatedNotifications);
    this.saveNotificationsToStorage();
  }

  /**
   * Remove a notification
   */
  removeNotification(id: string): void {
    const updatedNotifications = this.notificationsSignal().filter(
      (n) => n.id !== id
    );
    this.notificationsSignal.set(updatedNotifications);
    this.saveNotificationsToStorage();
  }

  /**
   * Clear all notifications
   */
  clearAll(): void {
    this.notificationsSignal.set([]);
    this.saveNotificationsToStorage();
  }

  /**
   * Navigate to notification link and mark as seen
   */
  handleNotificationClick(notification: NotificationItem): void {
    this.markAsSeen(notification.id);

    // For processing/pending, ensure we navigate into request mode even if link is missing
    if (
      notification.status === 'processing' ||
      notification.status === 'pending'
    ) {
      const navigationExtras = {
        state: {
          isRequest: true,
          requestData: {
            sourceWord: notification.sourceWord,
            // If link exists, extract code from it; otherwise keep undefined/known default
            ...(notification.link && {
              sourceLanguage: this.extractSourceLanguageFromLink(
                notification.link
              ),
            }),
            targetLanguage: notification.targetLanguage,
            requestId: notification.requestId || 'reconnect',
          },
          ...(notification.pk && { pk: notification.pk }),
          ...(notification.sk && { sk: notification.sk }),
          ...(notification.mediaRef && { media_ref: notification.mediaRef }),
        },
      };
      if (notification.link) {
        this.router.navigate([notification.link], navigationExtras);
      } else {
        this.router.navigate(['/words/request'], navigationExtras);
      }
      return;
    }

    if (notification.link) {
      if (notification.pk && notification.sk) {
        const navigationExtras = {
          state: {
            pk: notification.pk,
            sk: notification.sk,
            ...(notification.mediaRef && { media_ref: notification.mediaRef }),
          },
        };
        this.router.navigate([notification.link], navigationExtras);
      } else {
        this.router.navigateByUrl(notification.link);
      }
    }
  }

  /**
   * Extract source language from notification link
   */
  private extractSourceLanguageFromLink(link: string): string {
    // Link format: /words/{sourceLanguage}/{targetLanguage}/{pos}/{word}
    const parts = link.split('/');
    if (parts.length >= 3) {
      return parts[2];
    }
    return 'en'; // fallback to English code
  }

  /**
   * Get appropriate icon for notification status
   */
  private getIconForStatus(status: NotificationItem['status']): string {
    switch (status) {
      case 'pending':
        return 'hourglass_empty';
      case 'processing':
        return 'sync';
      case 'completed':
        return 'check_circle';
      case 'failed':
        return 'error';
      case 'redirect':
        return 'redo'; // Better icon for cache hit/redirect
      default:
        return 'info';
    }
  }

  /**
   * Get progress value for status
   */
  private getProgressForStatus(status: NotificationItem['status']): number {
    switch (status) {
      case 'pending':
        return 0;
      case 'processing':
        return 50;
      case 'completed':
        return 100;
      case 'failed':
        return 0;
      case 'redirect':
        return 100;
      default:
        return 0;
    }
  }

  /**
   * Save notifications to localStorage
   */
  private saveNotificationsToStorage(): void {
    try {
      const notifications = this.notificationsSignal();
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(notifications));
    } catch (error) {
      console.warn('Failed to save notifications to localStorage:', error);
    }
  }

  /**
   * Load notifications from localStorage
   */
  private loadNotificationsFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const notifications = JSON.parse(stored) as NotificationItem[];
        // Filter out old notifications (older than 7 days)
        const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
        const filteredNotifications = notifications.filter(
          (n) => n.timestamp > sevenDaysAgo
        );
        this.notificationsSignal.set(filteredNotifications);
      }
    } catch (error) {
      console.warn('Failed to load notifications from localStorage:', error);
      this.notificationsSignal.set([]);
    }
  }
}
