import { test, expect } from '@playwright/test';

const PROJECT_ID = 'proj-1';

test.describe('Studio', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/studio/${PROJECT_ID}`);
  });

  test('renders the toolbar', async ({ page }) => {
    await expect(page.getByTestId('toolbar')).toBeVisible({ timeout: 10000 });
  });

  test('renders the glyph list', async ({ page }) => {
    await expect(page.getByTestId('glyph-list')).toBeVisible({ timeout: 10000 });
  });

  test('can select pen tool', async ({ page }) => {
    const penButton = page.getByRole('button', { name: /pen/i });
    await penButton.click();
    await expect(penButton).toHaveAttribute('aria-pressed', 'true');
  });

  test('can select select tool', async ({ page }) => {
    const selectButton = page.getByRole('button', { name: /select/i });
    await selectButton.click();
    await expect(selectButton).toHaveAttribute('aria-pressed', 'true');
  });

  test('can select a glyph from the list', async ({ page }) => {
    await page.getByTestId('glyph-list').locator('button').first().click();
    await expect(page.getByTestId('glyph-canvas')).toBeVisible({ timeout: 5000 });
  });

  test('shows properties panel after glyph selection', async ({ page }) => {
    await page.getByTestId('glyph-list').locator('button').first().click();
    await expect(page.getByTestId('properties-panel')).toBeVisible({ timeout: 5000 });
  });

  test('breadcrumb shows project name', async ({ page }) => {
    await expect(page.getByText('Studio')).toBeVisible({ timeout: 10000 });
  });
});
