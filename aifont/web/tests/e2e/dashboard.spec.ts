import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('shows the dashboard title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Font Projects' })).toBeVisible();
  });

  test('shows project cards loaded from mock data', async ({ page }) => {
    const cards = page.getByTestId('project-card');
    await expect(cards).toHaveCount(3, { timeout: 10000 });
  });

  test('can search/filter projects', async ({ page }) => {
    await page.getByTestId('search-input').fill('Geometric');
    const cards = page.getByTestId('project-card');
    await expect(cards).toHaveCount(1);
    await expect(page.getByText('Geometric Sans')).toBeVisible();
  });

  test('can open new project modal', async ({ page }) => {
    await page.getByTestId('new-project-btn').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'New Font Project' })).toBeVisible();
  });

  test('can create a new project', async ({ page }) => {
    await page.getByTestId('new-project-btn').click();
    await page.getByLabel(/project name/i).fill('Test Font');
    await page.getByRole('button', { name: 'Create Project' }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 });
  });

  test('can close modal with Escape', async ({ page }) => {
    await page.getByTestId('new-project-btn').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('can navigate to studio from project card', async ({ page }) => {
    await page.getByTestId('project-card').first().getByText('Open Studio').click();
    await expect(page).toHaveURL(/\/studio\//);
  });
});
