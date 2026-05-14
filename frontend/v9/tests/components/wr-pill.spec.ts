import { test, expect } from '@playwright/test';

test('WR pill: visible + consumes endpoint + correct format', async ({ page }) => {
  const networkRequests: string[] = [];
  page.on('request', r => networkRequests.push(r.url()));

  await page.goto('http://localhost:3000');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(5000); // allow React hydration + initial fetches

  // 1. Component visible in DOM
  const pill = page.locator('[data-testid="topbar-wr-pill"]');
  await expect(pill).toBeVisible({ timeout: 10000 });

  // 2. Text format matches
  const text = await pill.textContent();
  expect(text).toMatch(/WR:\s*-?\d+%/);

  // 3. Endpoint was called
  const wrCalls = networkRequests.filter(u => u.includes('/shadow/today_wr'));
  expect(wrCalls.length).toBeGreaterThan(0);

  // 4. In TopBar (not floating)
  const topbar = page.locator('[data-testid="topbar"]');
  await expect(topbar.locator('[data-testid="topbar-wr-pill"]')).toBeVisible();
});
