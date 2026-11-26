import { expect, test } from "@playwright/test";

test("Phase 1 end-to-end learner journey with real PostgreSQL persistence", async ({
  page,
}) => {
  const uniqueEmail = `e2e.student.${Date.now()}@example.com`;

  // 1. Register Student in browser
  await page.goto("/register");
  await page.getByLabel("Full Name").fill("E2E Aarav");
  await page.getByLabel("Email Address").fill(uniqueEmail);
  await page.getByLabel("Password").fill("LearnerPass123");
  await page.getByRole("button", { name: "Create Account" }).click();

  // 2. Onboarding persists board/class/published version
  await expect(page).toHaveURL(/\/onboarding/);
  await page.getByRole("button", { name: "Save Profile & Open Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // Brand-new student sees real 0 attempts empty state (no fake stats)
  await expect(
    page.getByText(/No practice attempts recorded yet/i)
  ).toBeVisible();

  // 3. Navigate to Curriculum Explorer and start Practice Chapter
  await page.getByRole("link", { name: "Curriculum", exact: true }).click();
  await expect(page.getByText("Linear Equations Foundations")).toBeVisible();
  await page.getByRole("link", { name: "Practice Chapter" }).first().click();

  // 4. Solve published MCQ question, reveal Hint 1, submit answer, check solution
  await expect(page).toHaveURL(/\/practice/);
  await expect(page.getByText(/Question 1 of 1/i)).toBeVisible();
  await page.getByRole("button", { name: /Reveal Hint/i }).click();
  await expect(page.getByText(/Subtract 4 from both sides/i)).toBeVisible();

  await page.locator("label", { hasText: "B." }).getByRole("radio").check();
  await page.getByRole("button", { name: "Check Answer" }).click();
  await expect(page.getByText(/Correct!/i)).toBeVisible();
  await expect(page.getByText(/2x = 6/i)).toBeVisible();

  // 5. Save bookmark and create note directly from Practice view
  await page.getByRole("button", { name: "Save Bookmark" }).click();
  await expect(page.getByText(/Question saved to your bookmarks/i)).toBeVisible();

  await page.getByPlaceholder("Note title...").fill("Algebra Isolation");
  await page
    .getByPlaceholder(/Markdown or \$LaTeX\$/i)
    .fill("Always balance operations across `=`.");
  await page.getByRole("button", { name: "Save Personal Note" }).click();
  await expect(page.getByText(/Personal note saved/i)).toBeVisible();

  // 6. Verify Notes & Bookmarks page shows persisted records
  await page.getByRole("link", { name: "Notes & Saved" }).click();
  await expect(page.getByText("Algebra Isolation")).toBeVisible();
  await expect(page.getByText("Practice Saved")).toBeVisible();

  // 7. Verify Student Dashboard shows real persisted PostgreSQL counts
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByText("100%")).toBeVisible();
  await expect(page.getByText("Hints used total: 1")).toBeVisible();
  await expect(page.getByText("1 / 1")).toBeVisible();
});
