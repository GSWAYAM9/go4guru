import { expect, test } from "@playwright/test";

test("Phase 5 Adaptive Concept Mastery, Misconceptions, Missed-Q SM-2+ Flashcards & Study Planner", async ({
  page,
}) => {
  const uniqueEmail = `e2e.p5.${Date.now()}@example.com`;

  // 1. Register & onboard Class 10 student
  await page.goto("/register");
  await page.getByLabel("Full Name").fill("E2E Phase5 Student");
  await page.getByLabel("Email Address").fill(uniqueEmail);
  await page.getByLabel("Password").fill("LearnerPass123");
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await page.getByLabel("Class / Grade").selectOption({ label: "Class 10" });
  await page.getByRole("button", { name: "Save Profile & Open Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // 2. Intentionally miss a Linear Equations practice question (with hint) to seed mastery + misconception + missed-Q
  await page.getByRole("link", { name: "Curriculum", exact: true }).click();
  await expect(page.getByText("Linear Equations Foundations")).toBeVisible();
  await page.getByRole("link", { name: "Practice Chapter" }).first().click();
  await expect(page).toHaveURL(/\/practice/);

  await page.getByRole("button", { name: /Reveal Hint/i }).click();
  await page.locator("label", { hasText: "A." }).getByRole("radio").check();
  await page.getByRole("button", { name: "Check Answer" }).click();
  await expect(page.getByText(/Not quite right/i)).toBeVisible();

  // 3. Open Adaptive Mastery -> inspect multi-signal score, active misconception, alert & Learning Path
  await page.getByRole("link", { name: "Adaptive Mastery", exact: true }).click();
  await expect(page).toHaveURL(/\/adaptive/);
  await expect(page.getByTestId("mastery-card-MATH-10-LIN-01")).toBeVisible();
  await expect(page.getByText(/remediate_concept/i)).toBeVisible();
  await expect(page.getByText(/Needs Remediation:/i).first()).toBeVisible();

  await page.getByLabel("Learning path title").fill("Algebra Remediation Path");
  await page.getByRole("button", { name: "Build Path" }).click();
  await expect(page.getByText(/1\. Solving Linear Equations/i)).toBeVisible();
  await page.getByRole("button", { name: "Complete" }).first().click();
  await expect(page.getByRole("button", { name: "Done" }).first()).toBeVisible();

  // 4. Open Revision & Plan -> sync missed question -> rate SM-2+ -> add formula card -> build study plan
  await page.getByRole("link", { name: "Revision & Plan", exact: true }).click();
  await expect(page).toHaveURL(/\/revision/);

  await page
    .getByRole("button", { name: "Sync Missed Questions to Cards" })
    .click();
  await expect(
    page.getByText(/Synced missed questions: 1 new revision card/i)
  ).toBeVisible();
  await expect(page.getByText(/Due Revision Queue \(1\)/i)).toBeVisible();

  await page.getByRole("button", { name: /Reveal Answer/i }).click();
  await page.getByRole("button", { name: "5 · Effortless" }).click();
  await expect(
    page.getByText(/Scheduled next review in 1 day/i)
  ).toBeVisible();

  // Add manual formula flashcard
  await page.getByLabel("Card Type").selectOption("formula");
  await page
    .getByLabel(/Front Prompt/i)
    .fill("Standard Linear Equation Form");
  await page.getByLabel("Back Answer").fill("$ax + b = c \\implies x = (c-b)/a$");
  await page.getByRole("button", { name: "Add Flashcard to Deck" }).click();
  await expect(
    page.getByText(/Flashcard added cleanly to due SM-2\+ deck/i)
  ).toBeVisible();

  // Generate Personalized Study Plan & complete step 1
  await page
    .getByLabel("Study plan title")
    .fill("Class 10 Sprint Plan");
  await page
    .getByRole("button", { name: "Generate Adaptive Study Plan" })
    .click();
  await expect(page.getByText(/Class 10 Sprint Plan/i)).toBeVisible();
  await page.getByRole("button", { name: "Mark Done" }).first().click();
  await expect(page.getByRole("button", { name: "Completed" }).first()).toBeVisible();

  // 5. Browser reload restores persisted Revision Analytics & Study Plan completion
  await page.reload();
  await expect(page.getByText(/Class 10 Sprint Plan/i)).toBeVisible();
  await expect(page.getByText("Completed").first()).toBeVisible();
});
