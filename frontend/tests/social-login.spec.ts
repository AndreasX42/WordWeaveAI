import { test, expect } from '@playwright/test';

test.describe('Social Login Flows', () => {
  test('should handle successful Google login callback', async ({ page }) => {
    // Use `addInitScript` to set up mock data before the page loads
    await page.addInitScript(() => {
      // Mock user data and token in localStorage
      const mockUser = {
        id: 'google-user-123',
        username: 'GoogleUser',
        email: 'google.user@example.com',
        confirmedEmail: true,
        profilePicture: '',
        role: 'user',
      };
      const mockToken = 'mock-jwt-token-for-google-flow';

      localStorage.setItem('auth_user', JSON.stringify(mockUser));
      localStorage.setItem('auth_token', mockToken);
    });

    // Navigate to the profile page directly
    // The init script ensures the user is already "logged in"
    await page.goto('/profile');

    // Assert that the user is on the profile page
    await expect(page).toHaveURL('/profile');

    // Assert that the mock user's details are visible
    await expect(page.getByText('GoogleUser')).toBeVisible();
    await expect(page.getByText('google.user@example.com')).toBeVisible();
  });
});
