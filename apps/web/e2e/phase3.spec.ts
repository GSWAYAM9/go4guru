import { expect, test } from "@playwright/test";

test("Phase 3 Grounded AI Tutor: RAG citations, SymPy verification, anti-spoiler hints, reporting, and reload persistence", async ({
  page,
}) => {
  const uniqueEmail = `e2e.p3.${Date.now()}@example.com`;

  // 1. Register & onboard
  await page.goto("/register");
  await page.getByLabel("Full Name").fill("E2E Phase3 Student");
  await page.getByLabel("Email Address").fill(uniqueEmail);
  await page.getByLabel("Password").fill("LearnerPass123");
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await page.getByLabel("Class / Grade").selectOption({ label: "Class 10" });
  await page.getByRole("button", { name: "Save Profile & Open Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // 2. Open Grounded AI Tutor & check truthful model catalog status (no keys exposed)
  await page.getByRole("link", { name: "AI Tutor", exact: true }).click();
  await expect(page).toHaveURL(/\/tutor/);
  await expect(page.getByText(/grounded_fallback:/i)).toBeVisible();

  // 3. Create Session & ask mathematical doubt referencing Linear Equations
  await page.getByLabel("Session Topic").fill("Linear Equations Doubt");
  await page.getByLabel("Mode").selectOption("step_by_step");
  await page.getByRole("button", { name: "Create Tutor Session" }).click();
  await expect(
    page.getByRole("heading", { name: "Linear Equations Doubt" })
  ).toBeVisible();

  await page
    .getByLabel("Ask your academic question")
    .fill("Solve 2*x + 4 = 10 linear equation");
  await page.getByRole("button", { name: "Ask Tutor" }).click();

  // Verify deterministic SymPy result + Grounded Fallback badge + Cited Curriculum Source
  await expect(page.getByText("verified", { exact: true })).toBeVisible();
  await expect(page.getByText("x = [3]")).toBeVisible();
  await expect(
    page
      .getByText(/CBSE > Class 10 > Mathematics > Linear Equations Foundations/i)
      .first()
  ).toBeVisible();

  // 4. Switch to Hint (Anti-Spoiler) mode & ask an equation -> Turn-1 answer withheld
  await page.locator("#turn-mode").selectOption("hint");
  await page
    .getByLabel("Ask your academic question")
    .fill("2*x + 6 = 14");
  await page.getByRole("button", { name: "Ask Tutor" }).click();

  await expect(page.getByText("Anti-Spoiler", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/Guided Hint \(Anti-Spoiler Active\)/i)
  ).toBeVisible();
  await expect(page.getByText("x = [4]")).toHaveCount(0);

  // 5. Flag a response cleanly to AI Review Queue
  await page.getByRole("button", { name: "Report Issue" }).first().click();
  await expect(
    page.getByText(/Message flagged for Academic Reviewer queue/i)
  ).toBeVisible();

  // 6. Browser reload restores persisted session & conversation turns from PG18
  await page.reload();
  await expect(page.getByText("x = [3]")).toBeVisible();
  await expect(
    page.getByText(/Guided Hint \(Anti-Spoiler Active\)/i)
  ).toBeVisible();
});
