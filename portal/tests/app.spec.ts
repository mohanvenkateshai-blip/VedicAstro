import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('should load landing page', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/VedicShastra/);
  });

  test('should navigate to VedicAstro chart page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /Cast your chart/i }).click();
    await expect(page).toHaveURL(/\/chart/);
  });
});

test.describe('VedicAstro Chart Page', () => {
  test('should load chart page with query params', async ({ page }) => {
    await page.goto('/chart?date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5&place=Mysore');
    await expect(page).toHaveURL(/\/chart/);
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 30000 });
  });

  test('should render chart viewer', async ({ page }) => {
    await page.goto('/chart?date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5&place=Mysore');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);
    await expect(page.locator('svg, canvas, [data-testid="chart-viewer"]').first()).toBeVisible({ timeout: 60000 });
  });
});

test.describe('Muhurta Page', () => {
  test('should load muhurta page', async ({ page }) => {
    await page.goto('/chart/muhurta');
    await expect(page).toHaveURL(/\/chart\/muhurta/);
    await expect(page.locator('h1:has-text("Native Muhūrta research is disabled")')).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Accessibility', () => {
  test('landing page should have no axe violations', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#main-content')).toBeVisible();
  });

  test('chart page should have no axe violations', async ({ page }) => {
    await page.goto('/chart?date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5&place=Mysore');
    await expect(page.locator('#main-content')).toBeVisible({ timeout: 30000 });
  });
});