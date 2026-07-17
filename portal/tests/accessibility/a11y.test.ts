import { test, expect } from '@playwright/test';
import { checkA11y } from '../utils/a11y-helpers';
import { TIMEOUTS, buildChartUrl, buildTimelineUrl } from '../utils/test-data';
// (checkA11y drives @axe-core/playwright directly; no injection step needed.)

/**
 * Axe-driven WCAG 2.1 AA checks over the real routes (with a computed chart,
 * not the empty shell), plus structural checks axe cannot express.
 */
const PAGES_TO_TEST = [
  { path: '/', name: 'Landing' },
  { path: buildChartUrl(), name: 'Chart with Mohan data' },
  { path: buildTimelineUrl(), name: 'Person Timeline' },
  { path: '/chart/muhurta', name: 'Native Muhurta hold page' },
  { path: '/dashboard', name: 'Dashboard' },
];

// Colour-contrast is tracked in DESIGN.md and audited there; axe flags the
// intentional muted-on-dark tokens, so it stays report-only for now.
const ALLOWED_VIOLATIONS = ['color-contrast'];

test.describe.configure({ retries: 0 });

test.describe('WCAG 2.1 AA', () => {
  for (const pageConfig of PAGES_TO_TEST) {
    test(`${pageConfig.name} has no critical or serious axe violations`, async ({ page }) => {
      await page.goto(pageConfig.path, { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
      await page.waitForTimeout(500);
      await checkA11y(page, {}, ALLOWED_VIOLATIONS);
    });
  }

  test('kundali SVG exposes role=img with a descriptive label', async ({ page }) => {
    await page.goto(buildChartUrl(), { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
    const svg = page.locator('svg[role="img"][aria-label*="kundali" i]').first();
    await expect(svg).toBeVisible({ timeout: TIMEOUTS.chartLoad });
    await expect(svg).toHaveAttribute('aria-label', /Lagna/);

    const planetsTable = page.locator('table[aria-label="Planetary positions"]').first();
    await expect(planetsTable).toBeVisible();
    expect(await planetsTable.locator('thead th').count()).toBeGreaterThan(0);
  });

  test('timeline canvas has an accessible list alternative', async ({ page }) => {
    await page.goto(buildTimelineUrl(), { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
    await page.locator('[role="group"][aria-label="Timeline view"] button:has-text("List")').click();
    const table = page.locator('table:has(th:has-text("Valence"))');
    await expect(table).toBeVisible();
    expect(await table.locator('th[scope="col"]').count()).toBeGreaterThan(3);
  });

  test('keyboard: tab reaches interactive controls with visible focus', async ({ page }) => {
    await page.goto(buildChartUrl(), { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });

    const seen = new Set<string>();
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press('Tab');
      const focused = page.locator(':focus');
      if ((await focused.count()) === 0) continue;
      const descriptor = await focused.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        const hasFocusStyle =
          styles.outlineStyle !== 'none' || styles.boxShadow !== 'none';
        return `${el.tagName}#${el.id}.${el.className}|${hasFocusStyle}`;
      });
      seen.add(descriptor);
      expect(descriptor.endsWith('|true')).toBeTruthy();
    }
    expect(seen.size).toBeGreaterThan(3);
  });

  test('heading hierarchy: single h1, no level skipped downward', async ({ page }) => {
    for (const pageConfig of PAGES_TO_TEST) {
      await page.goto(pageConfig.path, { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
      const levels = await page
        .locator('h1, h2, h3, h4, h5, h6')
        .evaluateAll((els) => els.map((el) => parseInt(el.tagName.charAt(1), 10)));
      if (!levels.length) continue;
      expect(levels.filter((level) => level === 1).length, `${pageConfig.name} h1 count`).toBeLessThanOrEqual(1);
      for (let i = 1; i < levels.length; i++) {
        expect(levels[i] - levels[i - 1], `${pageConfig.name} heading order`).toBeLessThanOrEqual(1);
      }
    }
  });

  test('form inputs have accessible names', async ({ page }) => {
    await page.goto('/chart', { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
    const inputs = page.locator('input:not([type="hidden"]), select, textarea');
    const count = await inputs.count();
    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i);
      const hasName = await input.evaluate((el) => {
        const id = el.getAttribute('id');
        const explicit = id ? document.querySelector(`label[for="${id}"]`) : null;
        const implicit = el.closest('label');
        return Boolean(
          explicit || implicit || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'),
        );
      });
      expect(hasName, `input ${i} on /chart has an accessible name`).toBeTruthy();
    }
  });

  test('images have alt text or are marked decorative', async ({ page }) => {
    for (const pageConfig of PAGES_TO_TEST) {
      await page.goto(pageConfig.path, { waitUntil: 'networkidle', timeout: TIMEOUTS.pageLoad });
      const images = page.locator('img');
      const count = await images.count();
      for (let i = 0; i < count; i++) {
        const img = images.nth(i);
        const decorative =
          (await img.getAttribute('role')) === 'presentation' ||
          (await img.getAttribute('aria-hidden')) === 'true';
        const alt = await img.getAttribute('alt');
        expect(decorative || alt !== null, `image ${i} on ${pageConfig.name}`).toBeTruthy();
      }
    }
  });
});
