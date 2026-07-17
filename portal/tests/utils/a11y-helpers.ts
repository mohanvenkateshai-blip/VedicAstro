import { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { AxeResults, Result } from 'axe-core';

type RuleOptions = Record<string, { enabled: boolean }>;

export async function runAxe(page: Page, options: { rules?: RuleOptions } = {}): Promise<AxeResults> {
  const builder = new AxeBuilder({ page }).withTags(['wcag2aa', 'wcag21aa', 'best-practice']);
  for (const [rule, config] of Object.entries(options.rules ?? {})) {
    if (!config.enabled) builder.disableRules(rule);
  }
  return builder.analyze();
}

const FAILING_IMPACTS = ['critical', 'serious'];

/** Throws when the page has critical/serious axe violations not on the allow-list. */
export async function checkA11y(
  page: Page,
  options: { rules?: RuleOptions } = {},
  allowedViolations: string[] = [],
) {
  const results = await runAxe(page, options);
  const failing = results.violations.filter(
    (violation) =>
      violation.impact != null &&
      FAILING_IMPACTS.includes(violation.impact) &&
      !allowedViolations.includes(violation.id),
  );
  if (failing.length > 0) {
    throw new Error(`Accessibility violations found: ${failing.length}\n${formatViolations(failing)}`);
  }
}

export function formatViolations(violations: Result[]): string {
  return violations
    .map((violation) => {
      const nodes = violation.nodes
        .map((node) => `  - ${node.target.join(', ')}: ${node.failureSummary ?? ''}`)
        .join('\n');
      return `[${(violation.impact ?? 'unknown').toUpperCase()}] ${violation.id}: ${violation.description}\n${violation.helpUrl}\n${nodes}`;
    })
    .join('\n\n');
}
