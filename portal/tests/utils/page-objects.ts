import { Page, Locator, expect } from '@playwright/test';
import {
  BirthData,
  MOHAN_BIRTH_DATA,
  SELECTORS,
  TIMEOUTS,
  buildChartUrl,
  buildTimelineUrl,
  buildTransitsUrl,
} from './test-data';

export class HomePage {
  constructor(readonly page: Page) {}

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  /** The birth form lives on /chart (the landing page only links to it). */
  async gotoBirthForm() {
    await this.page.goto('/chart', { timeout: TIMEOUTS.pageLoad });
    await this.page.waitForSelector(SELECTORS.birthForm.date, { timeout: TIMEOUTS.pageLoad });
  }

  async fillBirthForm(data: BirthData = MOHAN_BIRTH_DATA) {
    await this.page.fill(SELECTORS.birthForm.date, data.date);
    await this.page.fill(SELECTORS.birthForm.time, data.time);
    await this.page.fill(SELECTORS.birthForm.place, data.place);
    await this.page.fill(SELECTORS.birthForm.lat, String(data.lat));
    await this.page.fill(SELECTORS.birthForm.lon, String(data.lon));
    await this.page.fill(SELECTORS.birthForm.tz, data.tz);
  }

  async submitBirthForm() {
    await this.page.click(SELECTORS.birthForm.submit);
  }
}

export class ChartPage {
  constructor(readonly page: Page) {}

  async goto(birthData: BirthData = MOHAN_BIRTH_DATA, extraParams: Record<string, string> = {}) {
    await this.page.goto(buildChartUrl(birthData, extraParams), { timeout: TIMEOUTS.pageLoad });
    await this.page.waitForLoadState('networkidle');
  }

  get kundaliSvg(): Locator {
    return this.page.locator(SELECTORS.chart.kundaliSvg).first();
  }

  get planetsTable(): Locator {
    return this.page.locator(SELECTORS.chart.planetsTable).first();
  }

  async expectChartLoaded() {
    await expect(this.kundaliSvg).toBeVisible({ timeout: TIMEOUTS.chartLoad });
    await expect(this.kundaliSvg).toHaveAttribute('viewBox', /.+/);
  }

  async expectPlanetVisible(planet: string) {
    await expect(this.planetsTable.locator(`tr:has-text("${planet}")`).first()).toBeVisible();
  }
}

export class TransitPage {
  constructor(readonly page: Page) {}

  async goto(birthData: BirthData = MOHAN_BIRTH_DATA) {
    await this.page.goto(buildTransitsUrl(birthData), { timeout: TIMEOUTS.pageLoad });
    await this.page.waitForLoadState('networkidle');
  }
}

export class TimelinePage {
  constructor(readonly page: Page) {}

  async goto(birthData: BirthData = MOHAN_BIRTH_DATA) {
    await this.page.goto(buildTimelineUrl(birthData), { timeout: TIMEOUTS.pageLoad });
    await this.page.waitForLoadState('networkidle');
  }

  get canvas(): Locator {
    return this.page.locator(SELECTORS.timeline.canvas);
  }

  get minimap(): Locator {
    return this.page.locator(SELECTORS.timeline.minimap);
  }

  get detailSheet(): Locator {
    return this.page.locator(SELECTORS.timeline.detailSheet);
  }

  get eventDialog(): Locator {
    return this.page.locator(SELECTORS.timeline.eventDialog);
  }

  digestColumn(name: 'Recently behind' | 'Active now' | 'Opening ahead'): Locator {
    return this.page.locator(`section[aria-label="${name}"]`);
  }

  lane(label: 'Life events' | 'Windows' | 'Dasha clock'): Locator {
    return this.canvas.locator(`text="${label}"`).first();
  }

  /** Milestone bands inside the canvas are buttons labelled with their valence. */
  get milestoneBands(): Locator {
    return this.canvas.locator('button[aria-pressed]');
  }

  valenceChip(label: 'Supportive' | 'Challenging' | 'Mixed' | 'Neutral'): Locator {
    return this.page.locator(SELECTORS.timeline.valenceGroup).locator(`button:has-text("${label}")`);
  }

  viewButton(label: 'Canvas' | 'List'): Locator {
    return this.page.locator(SELECTORS.timeline.viewToggle).locator(`button:has-text("${label}")`);
  }

  zoomButton(label: 'Life' | '10 yrs' | 'Year' | 'Month' | 'Week' | 'Day'): Locator {
    return this.page.locator(SELECTORS.timeline.zoomGroup).locator(`button:has-text("${label}")`);
  }

  get todayButton(): Locator {
    return this.page.locator(SELECTORS.timeline.travelGroup).locator('button:has-text("Today")');
  }

  async expectWorkspaceLoaded() {
    await expect(this.page.locator('h2:has-text("Life events, predictions and timing")')).toBeVisible({
      timeout: TIMEOUTS.pageLoad,
    });
    await expect(this.minimap).toBeVisible();
    await expect(this.canvas).toBeVisible();
  }

  async openFirstMilestone() {
    const band = this.milestoneBands.first();
    await expect(band).toBeVisible({ timeout: TIMEOUTS.apiCall });
    await band.click();
    await expect(this.detailSheet).toBeVisible({ timeout: TIMEOUTS.apiCall });
  }
}

export class MuhurtaPages {
  constructor(readonly page: Page) {}

  /**
   * /muhurta currently redirects into the feature-gated native workspace
   * (src/app/muhurta/page.tsx). The frozen standalone remains live at
   * muhurtha.uvwx.me but is no longer iframed — flagged as a product gap.
   */
  async expectRedirectToNative() {
    await this.page.goto('/muhurta', { timeout: TIMEOUTS.pageLoad });
    await this.page.waitForURL(/\/chart\/muhurta/, { timeout: TIMEOUTS.pageLoad });
  }

  /** Native muhūrta research is currently feature-gated off. */
  async expectNativeHoldPage() {
    await this.page.goto('/chart/muhurta', { timeout: TIMEOUTS.pageLoad });
    await expect(
      this.page.locator('h1:has-text("Native Muhūrta research is disabled")'),
    ).toBeVisible({ timeout: TIMEOUTS.apiCall });
  }
}

export class ThemeHelper {
  constructor(readonly page: Page) {}

  get toggle(): Locator {
    return this.page.locator('button[aria-label*="theme" i], button[aria-label*="dark" i], button[aria-label*="light" i]').first();
  }

  async getCurrentTheme(): Promise<'light' | 'dark'> {
    const cls = await this.page.locator('html').getAttribute('class');
    return cls?.includes('dark') ? 'dark' : 'light';
  }

  async toggleTheme() {
    await this.toggle.click();
    await this.page.waitForTimeout(TIMEOUTS.animation);
  }

  async storedTheme(): Promise<string | null> {
    return this.page.evaluate((key) => localStorage.getItem(key), SELECTORS.theme.storageKey);
  }
}
