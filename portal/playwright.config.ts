import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  // GitHub's standard hosted runners have 2 CPU cores. 2 workers here meant
  // 2 Playwright processes + Next.js dev-mode compilation + CVCE's
  // CPU-bound ephemeris/dasha computation all contended for those same 2
  // cores — every /chart/timeline navigation (heaviest client bundle: the
  // canvas/minimap/digest components) timed out at 60s, 100% of the time,
  // even though CVCE's own responses were logged as fast 200s throughout —
  // this was CPU starvation, not a hang in the app or CVCE. The same suite
  // with 2 workers against a local CVCE completes in 2.9 min on a normal
  // multi-core dev machine, which is why this never reproduced locally.
  workers: process.env.CI ? 1 : 4,
  reporter: [
    // 'list' gives per-test progress as it runs — without it, a hang looks
    // identical to silence until the whole job dies on GitHub's hard
    // timeout, which is exactly what happened the first time this ran.
    ['list'],
    ...(process.env.CI ? [['github'] as const] : []),
    // A distinct top-level folder, not 'test-results/html-report': the html
    // reporter previously nested inside the same dir Playwright clears for
    // trace/screenshot/video artifacts on every run, which the html
    // reporter warned would wipe its own output ("HTML reporter output
    // folder clashes with the tests output folder").
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  // In CI a hung test must fail fast with a partial report instead of
  // silently eating the whole job's time budget until GitHub force-cancels
  // it (which produces no report and no diagnostic signal at all).
  globalTimeout: process.env.CI ? 15 * 60 * 1000 : undefined,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },
  projects: [
    // Chromium runs everything, including visual baselines (the visual specs
    // drive their own viewport matrix, so device projects skip them).
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: ['**/visual/**'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testIgnore: ['**/visual/**'],
    },
    // Device projects are engine + touch smoke checks; the responsive suite
    // already covers viewport behavior explicitly.
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      testMatch: ['**/app.spec.ts'],
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      testMatch: ['**/app.spec.ts'],
    },
    {
      name: 'Tablet',
      use: { ...devices['iPad Pro'] },
      testMatch: ['**/app.spec.ts'],
    },
  ],
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100,
      threshold: 0.2,
    },
  },
  timeout: 120000,
});