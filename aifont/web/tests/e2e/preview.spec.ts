import { test, expect } from '@playwright/test';

const PROJECT_ID = 'proj-1';

test.describe('Preview Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/studio/${PROJECT_ID}/preview`);
  });

  test('shows preview controls', async ({ page }) => {
    await expect(page.getByTestId('preview-controls')).toBeVisible();
  });

  test('shows font preview area', async ({ page }) => {
    await expect(page.getByTestId('font-preview')).toBeVisible();
  });

  test('can change font size with slider', async ({ page }) => {
    const slider = page.getByTestId('font-size-slider');
    await expect(slider).toBeVisible();
    await slider.fill('72');
    await expect(slider).toHaveValue('72');
  });

  test('can change letter spacing with slider', async ({ page }) => {
    const slider = page.getByTestId('letter-spacing-slider');
    await expect(slider).toBeVisible();
    await slider.fill('0.1');
    await expect(slider).toHaveValue('0.1');
  });

  test('can switch to waterfall mode', async ({ page }) => {
    await page.getByRole('button', { name: 'Waterfall' }).click();
    await expect(page.getByTestId('font-preview')).toHaveAttribute('data-mode', 'waterfall');
  });

  test('can switch to alphabet mode', async ({ page }) => {
    await page.getByRole('button', { name: 'Alphabet' }).click();
    await expect(page.getByTestId('font-preview')).toHaveAttribute('data-mode', 'alphabet');
  });

  test('can switch to sentence mode', async ({ page }) => {
    await page.getByRole('button', { name: 'Waterfall' }).click();
    await page.getByRole('button', { name: 'Sentence' }).click();
    await expect(page.getByTestId('font-preview')).toHaveAttribute('data-mode', 'sentence');
  });

  test('can edit preview text', async ({ page }) => {
    const input = page.getByTestId('preview-text-input');
    await input.clear();
    await input.fill('Hello World');
    await expect(page.getByText('Hello World')).toBeVisible();
  });
});
