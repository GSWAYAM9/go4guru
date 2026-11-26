import { expect, test } from "@playwright/test";

test("Phase 4 Live AI Classroom: lesson generation, FSM playback, checkpoints, doubts, interactive whiteboard undo/redo/snapshot, reload recovery & completion", async ({
  page,
}) => {
  const uniqueEmail = `e2e.p4.${Date.now()}@example.com`;

  // 1. Register & onboard student
  await page.goto("/register");
  await page.getByLabel("Full Name").fill("E2E Phase4 Student");
  await page.getByLabel("Email Address").fill(uniqueEmail);
  await page.getByLabel("Password").fill("LearnerPass123");
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await page.getByLabel("Class / Grade").selectOption({ label: "Class 10" });
  await page.getByRole("button", { name: "Save Profile & Open Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // 2. Open Live Classroom & inspect language capabilities
  await page.getByRole("link", { name: "Live Classroom", exact: true }).click();
  await expect(page).toHaveURL(/\/classroom/);
  await expect(
    page.getByRole("heading", { name: /Interactive Live AI Classroom/i })
  ).toBeVisible();

  // 3. Generate & launch a structured lesson on Quadratic Kinematics
  await page.getByLabel("Lesson Topic").fill("Quadratic Kinematics");
  await page.getByRole("button", { name: "Generate & Start Lesson" }).click();
  await expect(
    page.getByRole("heading", { name: /Quadratic Kinematics/i })
  ).toBeVisible();
  await expect(page.getByText("READY", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/timed_subtitles_only/i)).toBeVisible();

  // 4. Play -> verify SVG whiteboard diagram & subtitles -> Pause -> Speed 1.25x -> Resume
  await page.getByRole("button", { name: "Play Lesson" }).click();
  await expect(
    page.getByText("PLAYING_SEGMENT", { exact: true }).first()
  ).toBeVisible();
  await expect(page.getByTestId("wb-el-s1_heading")).toBeVisible();
  await expect(page.getByTestId("live-subtitle-banner")).toBeVisible();

  await page.getByRole("button", { name: "Pause" }).click();
  await expect(page.getByText("PAUSED", { exact: true }).first()).toBeVisible();

  await page.locator("#speed-select").selectOption("1.25");
  await page.getByRole("button", { name: "Resume" }).click();
  await expect(
    page.getByText("PLAYING_SEGMENT", { exact: true }).first()
  ).toBeVisible();

  // 5. Advance to Segment 2 (Formula + Graph), then Segment 3 (Checkpoint)
  await page.getByRole("button", { name: "Next Segment" }).click();
  await expect(page.getByText(/Segment 2 of 4/i)).toBeVisible();
  await expect(page.getByTestId("wb-el-s2_graph")).toBeVisible();

  await page.getByRole("button", { name: "Next Segment" }).click();
  await expect(page.getByText(/Segment 3 of 4/i)).toBeVisible();
  await expect(
    page.getByText("CHECKPOINT_WAIT", { exact: true }).first()
  ).toBeVisible();

  // 6. Submit wrong checkpoint answer -> hint shown; then submit correct option B -> advances cleanly
  await page.locator('input[name="checkpoint-opt"][value="A"]').check();
  await page.getByRole("button", { name: "Submit Checkpoint Answer" }).click();
  await expect(page.getByText(/Not quite yet/i)).toBeVisible();

  await page.locator('input[name="checkpoint-opt"][value="B"]').check();
  await page.getByRole("button", { name: "Submit Checkpoint Answer" }).click();
  await expect(page.getByText(/Segment 4 of 4/i)).toBeVisible();

  // 7. Raise Hand / Student Doubt Interruption + Resume
  await page
    .getByPlaceholder(/Pause & ask a question about this diagram/i)
    .fill("Why is y = 0.5 x^2 symmetric around x = 0?");
  await page.getByRole("button", { name: "Ask Doubt" }).click();
  await expect(
    page.getByText("DOUBT_INTERRUPTION", { exact: true }).first()
  ).toBeVisible();
  await expect(page.getByText("AI Classroom Clarification")).toBeVisible();

  await page.getByRole("button", { name: "Resume" }).click();
  await expect(
    page.getByText("PLAYING_SEGMENT", { exact: true }).first()
  ).toBeVisible();

  // 8. Interactive Whiteboard Student Note + Undo + Redo + Save Snapshot
  await page.getByRole("button", { name: "Place Note" }).click();
  await page.getByLabel("Whiteboard note text").fill("Vertex check OK");
  await page
    .getByRole("img", { name: "Synchronized Classroom Whiteboard" })
    .click({ position: { x: 180, y: 220 } });
  await expect(page.getByText("Vertex check OK").first()).toBeVisible();

  await page.getByRole("button", { name: "Undo" }).click();
  await expect(page.getByRole("button", { name: "Redo" })).toBeEnabled();

  await page.getByRole("button", { name: "Redo" }).click();
  await expect(page.getByText("Vertex check OK").first()).toBeVisible();

  await page.getByRole("button", { name: "Save Snapshot" }).click();
  await expect(page.getByText(/Saved snapshot v\d+/i)).toBeVisible();

  // 9. Browser reload restores persisted session state, speed & whiteboard action
  await page.reload();
  await expect(page.getByText(/Segment 4 of 4/i)).toBeVisible();
  await expect(page.locator("#speed-select")).toHaveValue("1.25");
  await expect(page.getByText("Vertex check OK").first()).toBeVisible();

  // 10. Complete Lesson
  await page.getByRole("button", { name: "Complete Lesson" }).click();
  await expect(
    page.getByText("COMPLETED", { exact: true }).first()
  ).toBeVisible();
});
