import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 720 },
];

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';

VIEWPORTS.forEach(({ name, width, height }) => {
  test.describe(`Dashboard - ${name}`, () => {
    test.use({ viewport: { width, height } });

    test('dashboard visual regression', async ({ page }) => {
      await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      if (await page.locator('text=Sign in').isVisible().catch(() => false)) {
        test.skip(true, 'Requires authentication');
      }

      await expect(page).toHaveScreenshot(`dashboard-${name}.png`, {
        fullPage: true,
        threshold: 0.2,
        maxDiffPixels: 2000,
      });
    });
  });
});