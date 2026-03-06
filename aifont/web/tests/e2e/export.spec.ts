import { test, expect } from '@playwright/test';

const PROJECT_ID = 'proj-1';

test.describe('Export Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/studio/${PROJECT_ID}/export`);
  });

  test('shows the Export Font heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Export Font' })).toBeVisible();
  });

  test('shows export panel', async ({ page }) => {
    await expect(page.getByTestId('export-panel')).toBeVisible();
  });

  test('shows all format options', async ({ page }) => {
    await expect(page.getByText('OTF')).toBeVisible();
    await expect(page.getByText('TTF')).toBeVisible();
    await expect(page.getByText('WOFF2')).toBeVisible();
    await expect(page.getByText('SVG')).toBeVisible();
  });

  test('can select TTF format', async ({ page }) => {
    await page.locator('[data-format="ttf"]').click();
    await expect(page.getByRole('button', { name: /export as ttf/i })).toBeVisible();
  });

  test('can select WOFF2 format', async ({ page }) => {
    await page.locator('[data-format="woff2"]').click();
    await expect(page.getByRole('button', { name: /export as woff2/i })).toBeVisible();
  });

  test('can trigger export and see result', async ({ page }) => {
    await page.getByRole('button', { name: /export as/i }).click();
    await expect(page.getByText('Export Complete')).toBeVisible({ timeout: 15000 });
  });

  test('shows export history after export', async ({ page }) => {
    await page.getByRole('button', { name: /export as/i }).click();
    await expect(page.getByTestId('export-history')).toBeVisible({ timeout: 15000 });
  });

  test('export options checkboxes are present', async ({ page }) => {
    await expect(page.getByLabel(/enable hinting/i)).toBeVisible();
    await expect(page.getByLabel(/optimize file size/i)).toBeVisible();
    await expect(page.getByLabel(/include metadata/i)).toBeVisible();
  });
});
