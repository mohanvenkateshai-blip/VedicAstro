import { test, expect, Page } from '@playwright/test';
import { TIMEOUTS, buildChartUrl, buildTimelineUrl } from '../utils/test-data';

/**
 * Responsive behavior across the three canonical breakpoints. The core
 * invariant everywhere: the page body never scrolls horizontally — wide
 * content (tables, the timeline canvas) scrolls inside its own container.
 */
const BREAKPOINTS = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
];

const PAGES = [
  { path: '/', name: 'Landing' },
  { path: buildChartUrl(), name: 'Chart' },
  { path: buildTimelineUrl(), name: 'Timeline' },
];

async function expectNoBodyHorizontalScroll(page: Page, label: string) {
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(
    overflow.scrollWidth - overflow.clientWidth,
    `${label}: body horizontal overflow (scrollWidth ${overflow.scrollWidth} vs clientWidth ${overflow.clientWidth})`,
  ).toBeLessThanOrEqual(1);
}

for (const bp of BREAKPOINTS) {
  test.describe(`${bp.name} (${bp.width}x${bp.height})`, () => {
    test.use({ viewport: { width: bp.width, height: bp.height } });

    for (const pageConfig of PAGES) {
      test(`${pageConfig.name} renders without body horizontal scroll`, async ({ page }) => {
        await page.goto(pageConfig.path, { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
        await expect(page.locator('#main-content, main').first()).toBeVisible();
        await expectNoBodyHorizontalScroll(page, `${pageConfig.name} @ ${bp.name}`);
      });
    }

    test('kundali SVG scales inside its container', async ({ page }) => {
      await page.goto(buildChartUrl(), { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
      const svg = page.locator('svg[role="img"][aria-label*="kundali" i]').first();
      await expect(svg).toBeVisible({ timeout: TIMEOUTS.chartLoad });
      const box = await svg.boundingBox();
      expect(box, 'kundali bounding box').toBeTruthy();
      expect(box!.width).toBeGreaterThan(100);
      expect(box!.width).toBeLessThanOrEqual(bp.width);
    });

    test('timeline workspace is usable', async ({ page }) => {
      await page.goto(buildTimelineUrl(), { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
      await expect(page.locator('[role="slider"][aria-label*="Lifetime overview"]')).toBeVisible({
        timeout: TIMEOUTS.pageLoad,
      });
      await expect(page.locator('[role="group"][aria-label*="Person timeline canvas"]')).toBeVisible();
      await expectNoBodyHorizontalScroll(page, `Timeline @ ${bp.name}`);
    });
  });
}

test.describe('Touch target sizing on mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('timeline primary controls meet a 24px minimum hit size', async ({ page }) => {
    await page.goto(buildTimelineUrl(), { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
    const controls = page.locator(
      '[role="group"][aria-label="Timeline view"] button, [role="group"][aria-label="Move through time"] button, button:has-text("Add event")',
    );
    const count = await controls.count();
    expect(count).toBeGreaterThan(3);
    for (let i = 0; i < count; i++) {
      const box = await controls.nth(i).boundingBox();
      if (!box) continue; // hidden controls (inert groups) are exempt
      expect(box.height, `control ${i} height`).toBeGreaterThanOrEqual(24);
      expect(box.width, `control ${i} width`).toBeGreaterThanOrEqual(24);
    }
  });
});
