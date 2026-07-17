import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1280, height: 720 },
];

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const MOHAN_PARAMS = 'date=1975-04-22&time=19:15&lat=12.2958&lon=76.6394&tz=5.5&place=Mysore';

VIEWPORTS.forEach(({ name, width, height }) => {
  test.describe(`Person Timeline - ${name}`, () => {
    test.use({ viewport: { width, height } });

    test('person timeline visual regression', async ({ page }) => {
      await page.goto(`${BASE_URL}/chart/timeline?${MOHAN_PARAMS}`, { waitUntil: 'networkidle' });
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1500);

      await expect(page).toHaveScreenshot(`timeline-${name}.png`, {
        fullPage: true,
        threshold: 0.2,
        maxDiffPixels: 1500,
      });
    });
  });
});