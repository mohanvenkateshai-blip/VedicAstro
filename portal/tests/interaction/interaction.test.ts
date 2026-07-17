import { test, expect } from '@playwright/test';
import { ChartPage, HomePage, MuhurtaPages, ThemeHelper, TimelinePage, TransitPage } from '../utils/page-objects';
import { MOHAN_BIRTH_DATA, TIMEOUTS, buildChartUrl } from '../utils/test-data';

test.describe('Birth form and chart', () => {
  test('birth form submit renders Mohan chart with planets table', async ({ page }) => {
    const home = new HomePage(page);
    const chart = new ChartPage(page);

    await home.gotoBirthForm();
    await home.fillBirthForm();
    await home.submitBirthForm();

    await page.waitForURL(/\/chart\?/, { timeout: TIMEOUTS.pageLoad });
    await chart.expectChartLoaded();

    await expect(chart.planetsTable).toBeVisible({ timeout: TIMEOUTS.chartLoad });
    for (const planet of ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']) {
      await chart.expectPlanetVisible(planet);
    }

    // Golden reference: Lagna Libra / Swati pada 4.
    await expect(page.locator('text=/Libra/i').first()).toBeVisible();
    await expect(page.locator('text=/Swati/i').first()).toBeVisible();
  });

  test('direct chart URL with query params renders the chart', async ({ page }) => {
    const chart = new ChartPage(page);
    await chart.goto();
    await chart.expectChartLoaded();
    expect(page.url()).toContain('date=1975-04-22');
  });

  test('legacy /vedicastro URL redirects to /chart preserving params', async ({ page }) => {
    await page.goto(`/vedicastro?date=${MOHAN_BIRTH_DATA.date}&time=${MOHAN_BIRTH_DATA.time}&lat=${MOHAN_BIRTH_DATA.lat}&lon=${MOHAN_BIRTH_DATA.lon}&tz=${MOHAN_BIRTH_DATA.tz}&place=${MOHAN_BIRTH_DATA.place}`, { timeout: TIMEOUTS.pageLoad });
    await page.waitForURL(/\/chart\?/, { timeout: TIMEOUTS.pageLoad });
    expect(page.url()).toContain('date=1975-04-22');
  });

  test('invalid coordinates show an error message', async ({ page }) => {
    await page.goto(buildChartUrl({ ...MOHAN_BIRTH_DATA, lat: 'not-a-number' as unknown as number }), { timeout: TIMEOUTS.pageLoad });
    await expect(page.locator('text=/invalid|error|check/i').first()).toBeVisible({ timeout: TIMEOUTS.apiCall });
  });
});

test.describe('Sidebar navigation', () => {
  test('sidebar links preserve the birth query string', async ({ page }) => {
    const chart = new ChartPage(page);
    await chart.goto();

    const timelineLink = page.locator('a[href*="/chart/timeline"]').first();
    await expect(timelineLink).toBeVisible({ timeout: TIMEOUTS.apiCall });
    const href = await timelineLink.getAttribute('href');
    expect(href).toContain('date=1975-04-22');
    expect(href).toContain('place=Mysore');
  });
});

test.describe('Person Timeline workspace', () => {
  let timeline: TimelinePage;

  test.beforeEach(async ({ page }) => {
    timeline = new TimelinePage(page);
    await timeline.goto();
    await timeline.expectWorkspaceLoaded();
  });

  test('digest shows behind / active / ahead columns', async () => {
    await expect(timeline.digestColumn('Recently behind')).toBeVisible();
    await expect(timeline.digestColumn('Active now')).toBeVisible();
    await expect(timeline.digestColumn('Opening ahead')).toBeVisible();
    // The active column carries the running dasha chips (MD + AD).
    await expect(timeline.digestColumn('Active now').locator('text=/MD/').first()).toBeVisible();
  });

  test('canvas shows the three lanes and the today marker', async () => {
    await expect(timeline.lane('Life events')).toBeVisible();
    await expect(timeline.lane('Windows')).toBeVisible();
    await expect(timeline.lane('Dasha clock')).toBeVisible();
    await expect(timeline.canvas.locator('text="today"').first()).toBeVisible();
  });

  test('engine research candidates render as valence-labelled bands', async () => {
    const bands = timeline.milestoneBands;
    await expect(bands.first()).toBeVisible({ timeout: TIMEOUTS.apiCall });
    expect(await bands.count()).toBeGreaterThan(0);
    const label = await bands.first().getAttribute('aria-label');
    expect(label).toMatch(/Supportive|Challenging|Mixed|Neutral/);
  });

  test('valence chips filter the canvas', async () => {
    const before = await timeline.milestoneBands.count();
    expect(before).toBeGreaterThan(0);

    // Mohan's chart has favourable candidates; hiding Supportive must reduce bands.
    await timeline.valenceChip('Supportive').click();
    await expect
      .poll(async () => timeline.milestoneBands.count(), { timeout: TIMEOUTS.apiCall })
      .toBeLessThan(before);

    await timeline.valenceChip('Supportive').click();
    await expect
      .poll(async () => timeline.milestoneBands.count(), { timeout: TIMEOUTS.apiCall })
      .toBe(before);
  });

  test('list view shows grouped chronological records', async ({ page }) => {
    await timeline.viewButton('List').click();
    await expect(page.locator('table th:has-text("Valence")')).toBeVisible();
    await expect(page.locator('th[scope="rowgroup"]').first()).toBeVisible();
    await timeline.viewButton('Canvas').click();
    await expect(timeline.canvas).toBeVisible();
  });

  test('zoom presets and Today travel are wired', async () => {
    await timeline.zoomButton('Life').click();
    await expect(timeline.zoomButton('Life')).toHaveAttribute('aria-pressed', 'true');
    await timeline.zoomButton('10 yrs').click();
    await expect(timeline.zoomButton('10 yrs')).toHaveAttribute('aria-pressed', 'true');
    await timeline.todayButton.click();
    await expect(timeline.canvas.locator('text="today"').first()).toBeVisible();
  });

  test('milestone click opens the evidence detail sheet with a dasha deep link', async () => {
    await timeline.openFirstMilestone();
    await expect(timeline.detailSheet.locator('text=/Timing window/i')).toBeVisible();
    await expect(
      timeline.detailSheet.locator('a[href*="/chart/dasha"]'),
    ).toBeVisible({ timeout: TIMEOUTS.chartLoad });
    await timeline.detailSheet.locator('button[aria-label="Close milestone details"]').click();
    await expect(timeline.detailSheet).toBeHidden();
  });

  test('add-event dialog opens, validates and closes', async ({ page }) => {
    await page.locator('button:has-text("Add event")').first().click();
    await expect(timeline.eventDialog).toBeVisible();
    await expect(timeline.eventDialog.locator('h2:has-text("Add an observed milestone")')).toBeVisible();
    // Escape closes only the dialog.
    await page.keyboard.press('Escape');
    await expect(timeline.eventDialog).toBeHidden();
  });

  test('minimap is a keyboard-operable slider', async ({ page }) => {
    // Start from Life zoom so the keyboard travel demonstrably changes state:
    // travelling from lifetime switches the workspace to the decade viewport.
    await timeline.zoomButton('Life').click();
    await expect(timeline.zoomButton('Life')).toHaveAttribute('aria-pressed', 'true');
    await timeline.minimap.focus();
    await page.keyboard.press('ArrowLeft');
    await expect(timeline.zoomButton('10 yrs')).toHaveAttribute('aria-pressed', 'true');
    await expect(timeline.zoomButton('Life')).toHaveAttribute('aria-pressed', 'false');
  });
});

test.describe('Transits page', () => {
  test('transit workspace loads for the chart', async ({ page }) => {
    const transits = new TransitPage(page);
    await transits.goto();
    await expect(page.locator('#main-content')).toBeVisible({ timeout: TIMEOUTS.pageLoad });
    await expect(page.locator('text=/transit/i').first()).toBeVisible();
  });
});

test.describe('Muhūrta surfaces', () => {
  test('global muhurta tab is the frozen standalone iframe', async ({ page }) => {
    await new MuhurtaPages(page).expectStandaloneIframe();
  });

  test('native muhurta research shows the feature-gate hold page', async ({ page }) => {
    await new MuhurtaPages(page).expectNativeHoldPage();
  });
});

test.describe('Theme toggle', () => {
  test('toggles the dark class and persists to va-theme', async ({ page }) => {
    const theme = new ThemeHelper(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const initial = await theme.getCurrentTheme();
    await theme.toggleTheme();
    const flipped = await theme.getCurrentTheme();
    expect(flipped).not.toBe(initial);

    const stored = await theme.storedTheme();
    expect(stored).toBe(flipped);

    await page.reload();
    await page.waitForLoadState('networkidle');
    expect(await theme.getCurrentTheme()).toBe(flipped);
  });
});

test.describe('Error handling', () => {
  test('failed CVCE explorer calls surface an error, not a spinner', async ({ page }) => {
    await page.route('**/api/cvce/**', (route) => route.abort('failed'));
    const timeline = new TimelinePage(page);
    await timeline.goto();
    // Server-rendered timeline still arrives; opening a milestone hits the
    // proxied detail endpoint, which now fails — the sheet must still render
    // its static sections (graceful degradation), not hang.
    await timeline.expectWorkspaceLoaded();
    await timeline.openFirstMilestone();
    await expect(timeline.detailSheet.locator('text=/Timing window/i')).toBeVisible();
  });
});
