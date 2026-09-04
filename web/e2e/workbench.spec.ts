import { expect, type Locator, type Page, test } from "@playwright/test";

async function dragBlock(page: Page, block: Locator, x: number, y: number) {
  const box = await block.boundingBox();
  if (!box) throw new Error("Blockly block is not visible");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(x, y, { steps: 12 });
  await page.mouse.up();
}

async function createCapabilityWorkflow(page: Page, capability: string) {
  await page.goto("/");
  await expect(page.locator(".discovery")).toHaveText(/ready/i);
  await page
    .locator(".blocklyToolboxCategory")
    .filter({ hasText: "Demo" })
    .click();
  await dragBlock(
    page,
    page
      .locator(".blocklyFlyout .blocklyDraggable")
      .filter({ hasText: capability }),
    380,
    460,
  );

  const blocks = page.locator(".blocklyWorkspace .blocklyDraggable:visible");
  await expect(blocks).toHaveCount(2);
  const sequenceBox = await blocks.nth(0).boundingBox();
  const capabilityBox = await blocks.nth(1).boundingBox();
  if (!sequenceBox || !capabilityBox)
    throw new Error("Workflow blocks are missing");
  const targetX = sequenceBox.x + 90;
  const targetY = sequenceBox.y + 43;
  await dragBlock(
    page,
    blocks.nth(1),
    capabilityBox.x +
      capabilityBox.width / 2 +
      targetX -
      (capabilityBox.x + 22),
    capabilityBox.y + capabilityBox.height / 2 + targetY - capabilityBox.y,
  );
  await expect(
    page.getByText("Local schema valid", { exact: true }),
  ).toBeAttached();
}

async function setNumber(page: Page, label: string, value: string) {
  await page.getByLabel(label).evaluate((element, nextValue) => {
    const input = element as HTMLInputElement;
    const descriptor = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    );
    if (!descriptor?.set) {
      throw new Error("Native input value setter is unavailable");
    }
    descriptor.set.bind(input)(nextValue);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }, value);
}

async function runToState(page: Page, state: string) {
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.locator(".runtime-head h2")).toHaveText(state, {
    timeout: state === "timed_out" ? 10_000 : 7_000,
  });
}

test("creates, validates, saves, reloads, and executes a workflow", async ({
  page,
}) => {
  await createCapabilityWorkflow(page, "demo.instant_success@1");
  await page.getByLabel("value").fill("browser-ok");
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByText("Backend validation passed.")).toBeAttached();

  const downloadPromise = page.waitForEvent("download");
  await page.getByLabel("Download project").click();
  const download = await downloadPromise;
  const projectPath = await download.path();
  if (!projectPath) throw new Error("Downloaded project has no local path");

  await runToState(page, "succeeded");
  await expect(page.getByTestId("terminal-result")).toContainText("succeeded");
  await page.getByLabel("New project").click();
  await expect(
    page.getByText("Draft · Add a step", { exact: true }),
  ).toBeAttached();
  await expect(page.getByText("Block ID", { exact: true })).toHaveCount(0);
  await page.getByTestId("project-file-input").setInputFiles(projectPath);
  await expect(
    page.getByText("Local schema valid", { exact: true }),
  ).toBeAttached();
});

test("shows failure, progress, and timeout truthfully", async ({ page }) => {
  await createCapabilityWorkflow(page, "demo.fail@1");
  await page.getByLabel("message").fill("browser failure");
  await runToState(page, "failed");
  await expect(page.getByTestId("runtime-panel")).toContainText(
    "browser failure",
  );

  await createCapabilityWorkflow(page, "demo.percent_action@1");
  await setNumber(page, "steps", "8");
  await setNumber(page, "step_delay_ms", "80");
  await runToState(page, "succeeded");
  await expect(page.getByTestId("runtime-panel")).toContainText(
    "native provenance",
  );

  await createCapabilityWorkflow(page, "demo.cancellable_action@1");
  await setNumber(page, "duration_ms", "6500");
  await runToState(page, "timed_out");
  await expect(page.getByTestId("runtime-panel")).toContainText(
    "capability_timeout",
  );
});

test("distinguishes supported and incomplete cancellation", async ({
  page,
}) => {
  await createCapabilityWorkflow(page, "demo.cancellable_action@1");
  await setNumber(page, "duration_ms", "5000");
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: "Stop active run" }).click();
  await expect(page.locator(".runtime-head h2")).toHaveText("canceled");

  await createCapabilityWorkflow(page, "demo.uncancellable_action@1");
  await setNumber(page, "duration_ms", "10000");
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await page.waitForTimeout(200);
  await page.getByRole("button", { name: "Stop active run" }).click();
  await expect(page.locator(".runtime-head h2")).toHaveText("failed");
  await expect(page.getByTestId("runtime-error")).toHaveCount(1);
  await expect(page.getByTestId("runtime-error")).toContainText(
    "cancellation_incomplete",
  );
});

for (const width of [320, 375, 414, 768]) {
  test(`renders without horizontal overflow at ${String(width)}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: width < 700 ? 896 : 1024 });
    await page.goto("/");
    await expect(page.getByTestId("blockly-workspace")).toBeVisible();
    const metrics = await page.evaluate(() => ({
      viewport: window.innerWidth,
      root: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    expect(metrics.root).toBeLessThanOrEqual(metrics.viewport);
    expect(metrics.body).toBeLessThanOrEqual(metrics.viewport);
  });
}
