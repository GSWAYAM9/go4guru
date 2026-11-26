import { expect, test } from "@playwright/test";

test("Phase 2 assessment runner, mark-for-review, reload recovery, negative marking, and live analytics", async ({
  page,
}) => {
  const uniqueEmail = `e2e.p2.${Date.now()}@example.com`;

  // 1. Register & complete onboarding
  await page.goto("/register");
  await page.getByLabel("Full Name").fill("E2E Phase2 Student");
  await page.getByLabel("Email Address").fill(uniqueEmail);
  await page.getByLabel("Password").fill("LearnerPass123");
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await page.getByRole("button", { name: "Save Profile & Open Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // 2. Custom Quiz generator + Quiz launch check
  await page.getByRole("link", { name: "Quizzes" }).click();
  await expect(page).toHaveURL(/\/quizzes/);
  await page.getByLabel("Quiz Title").fill("E2E Browser Sprint");
  await page.getByLabel("Question Count").fill("2");
  await page.getByRole("button", { name: "Create Quiz" }).click();
  await expect(page.getByText("E2E Browser Sprint")).toBeVisible();

  // 3. Assessments Catalog: verify configurable exam patterns + launch seeded published mock
  await page.getByRole("link", { name: "Assessments" }).click();
  await expect(page).toHaveURL(/\/assessments/);
  await expect(page.getByText(/jee-main-2026-v1/i)).toBeVisible();
  await expect(page.getByText("CBSE E2E Diagnostic Mock")).toBeVisible();

  await page.getByRole("button", { name: "Launch Test" }).first().click();
  await expect(page).toHaveURL(/\/assessments\/[0-9a-f-]+$/);

  // 4. Question 1 (MCQ): select WRONG option A (-1), Mark for Review, Save & Next
  await expect(page.getByText(/Question 1 of 2/i)).toBeVisible();
  await expect(page.getByTestId("assessment-timer")).not.toHaveText("Untimed");

  await page.locator("label", { hasText: "(A)" }).getByRole("radio").check();
  await page.getByRole("button", { name: "Mark for Review" }).click();
  await page.getByRole("button", { name: "Save & Next" }).click();

  // 5. Question 2 (Numerical): enter RIGHT value 25 (+4), Save Now
  await expect(page.getByText(/Question 2 of 2/i)).toBeVisible();
  await page.getByLabel("Numeric Value").fill("25");
  await page.getByRole("button", { name: "Save Now" }).click();
  await expect(page.getByText(/Saved 2 responses/i)).toBeVisible();

  // 6. Browser Reload Recovery: verify timer + Q1 Mark for Review + Q2 numeric value persist in PostgreSQL
  await page.reload();
  await expect(page.getByText(/Question 1 of 2/i)).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Question 1 marked for review/i })
  ).toBeVisible();
  await page.getByRole("button", { name: /Question 2/i }).click();
  await expect(page.getByLabel("Numeric Value")).toHaveValue("25");

  // 7. Submit Assessment -> Authoritative Scorecard (+4 - 1 = 3 / 8, 50% accuracy)
  await page.getByRole("button", { name: "Submit Assessment" }).click();
  await expect(page).toHaveURL(/\/assessments\/[0-9a-f-]+\/result$/);
  await expect(page.getByTestId("final-score")).toHaveText("3 / 8");
  await expect(page.getByText(/Subtract 4 to get 2x = 6/i)).toBeVisible();
  await expect(page.getByText(/9 \+ 16 = 25/i).first()).toBeVisible();

  // 8. Live Analytics projected from Outbox Events
  await page.getByRole("link", { name: "Analytics", exact: true }).click();
  await expect(page).toHaveURL(/\/analytics/);
  await expect(page.getByText("assessment.attempt_submitted")).toBeVisible();
  await expect(page.getByText("50%").first()).toBeVisible();
});
