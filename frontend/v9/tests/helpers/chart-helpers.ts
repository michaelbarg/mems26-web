import { Page } from '@playwright/test';

export async function getYRange(page: Page): Promise<number> {
  const texts = await page.locator('[data-testid="chart-svg"] text').allTextContents();
  const nums = texts.map(s => parseFloat(s.replace(/[^\d.-]/g,''))).filter(n => !isNaN(n) && n > 1000);
  if (nums.length < 2) return 0;
  return Math.max(...nums) - Math.min(...nums);
}

export async function getVisibleBarCount(page: Page): Promise<number> {
  return await page.locator('[data-testid="chart-svg"] rect[fill="#16a34a"], [data-testid="chart-svg"] rect[fill="#dc2626"]').count();
}
