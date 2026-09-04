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

test("uses the active profile toolbox and blocks incompatible runs", async ({
  page,
}) => {
  let runRequests = 0;
  await page.route("**/api/v1/profile", (route) =>
    route.fulfill({
      json: {
        profile_schema_version: 1,
        id: "reachy2-sim",
        title: "Reachy 2 MuJoCo",
        adapter: "reachy2-sdk",
        capabilities: [{ id: "demo.instant_success", version: 1 }],
      },
    }),
  );
  await page.route("**/api/v1/capabilities", (route) =>
    route.fulfill({
      json: [
        {
          manifest_schema_version: 1,
          id: "demo.instant_success",
          version: 1,
          title: "Instant success",
          category: "Demo",
          inputs: { value: { type: "string", required: true } },
          outputs: {},
          execution: { timeout_ms: 1000, cancellable: false },
          progress: { mode: "none", source: null },
          resources: [],
          compatible_profiles: [],
        },
        {
          manifest_schema_version: 1,
          id: "demo.fail",
          version: 1,
          title: "Must be filtered",
          category: "Hidden",
          inputs: {},
          outputs: {},
          execution: { timeout_ms: 1000, cancellable: false },
          progress: { mode: "none", source: null },
          resources: [],
          compatible_profiles: [],
        },
      ],
    }),
  );
  await page.route("**/api/v1/workflows/compatibility", (route) =>
    route.fulfill({
      json: {
        active_profile_id: "reachy2-sim",
        source_profile_id: "reachy2-sim",
        compatible: false,
        nodes: {
          capability_1: {
            status: "unknown",
            capability: { id: "demo.instant_success", version: 1 },
            reason: "profile_compatibility_unknown",
          },
        },
      },
    }),
  );
  await page.route("**/api/v1/runs", (route) => {
    runRequests += 1;
    return route.fulfill({ status: 500 });
  });

  await createCapabilityWorkflow(page, "demo.instant_success@1");
  await expect(page.getByTestId("active-profile")).toContainText(
    "Reachy 2 MuJoCo (reachy2-sim)",
  );
  await expect(page.getByText("Hidden", { exact: true })).toHaveCount(0);
  await page.getByLabel("value").fill("blocked");
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await expect(page.getByTestId("compatibility-capability_1")).toContainText(
    "unknown (profile_compatibility_unknown)",
  );
  expect(runRequests).toBe(0);
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

test("renders a canonical review manifest as Blockly", async ({ page }) => {
  await page.route("**/artifacts/review.json", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        review_schema_version: 1,
        workflow: {
          workflow_schema_version: 1,
          id: "review-demo",
          name: "Stable review demo",
          workflow: {
            type: "sequence",
            id: "root",
            children: [
              { type: "wait", id: "settle", duration_ms: 250 },
              {
                type: "capability",
                id: "speak",
                capability: { id: "speech.say", version: 1 },
                args: { text: "hello" },
              },
            ],
          },
        },
        result: {
          run_id: "run-browser-review",
          workflow_id: "review-demo",
          state: "succeeded",
          error: null,
          started_at: "2026-09-01T00:00:00Z",
          finished_at: "2026-09-01T00:00:01Z",
        },
        profile_id: "review-sim",
        observation_count: 42,
        artifacts: {
          trace: "trace.jsonl",
          rerun: null,
          video: "review.mp4",
        },
        timeline: {
          timebase: "utc",
          media: [
            {
              id: "gazebo-camera",
              artifact: "review.mp4",
              origin: "2026-09-01T00:00:00Z",
            },
          ],
        },
      }),
    });
  });
  await page.route("**/trace.jsonl?run=run-browser-review", async (route) => {
    await route.fulfill({
      contentType: "application/x-ndjson",
      body: [
        {
          event_protocol_version: 1,
          event_id: "00000000-0000-4000-8000-000000000001",
          seq: 1,
          run_id: "run-browser-review",
          node_id: "settle",
          type: "node.started",
          occurred_at: "2026-09-01T00:00:00.100Z",
          data: {},
        },
        {
          event_protocol_version: 1,
          event_id: "00000000-0000-4000-8000-000000000002",
          seq: 2,
          run_id: "run-browser-review",
          node_id: "settle",
          type: "node.finished",
          occurred_at: "2026-09-01T00:00:00.900Z",
          data: {},
        },
      ]
        .map((event) => JSON.stringify(event))
        .join("\n"),
    });
  });
  await page.route("**/review.mp4?run=run-browser-review", async (route) => {
    await route.fulfill({ contentType: "video/mp4", body: Buffer.from([]) });
  });

  await page.goto("/?review");

  await expect(
    page.getByRole("heading", { name: "Stable review demo" }),
  ).toBeVisible();
  await expect(page.getByText("run-browser-review")).toBeVisible();
  await expect(page.locator(".blockly-review")).toContainText("speech.say@1");
  await expect(page.locator(".step-list")).toContainText("250 ms");
  await expect(page.getByRole("link", { name: "Rerun RRD" })).toHaveCount(0);
  await page.evaluate(() => {
    const video = document.querySelector(".video-panel video");
    if (!(video instanceof HTMLVideoElement)) throw new Error("video missing");
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      value: 0.5,
    });
    video.dispatchEvent(new Event("timeupdate"));
  });
  await expect(page.locator(".blockly-review .blocklyHighlighted")).toHaveCount(
    1,
  );
  await page.evaluate(() => {
    const video = document.querySelector(".video-panel video");
    if (!(video instanceof HTMLVideoElement)) throw new Error("video missing");
    Object.defineProperty(video, "currentTime", {
      configurable: true,
      value: 1.0,
    });
    video.dispatchEvent(new Event("seeked"));
  });
  await expect(page.locator(".blockly-review .blocklyHighlighted")).toHaveCount(
    0,
  );

  const blockColors = await page.evaluate(() => {
    const tokenColor = (name: string) => {
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Canvas color conversion is unavailable");
      context.fillStyle = getComputedStyle(document.documentElement)
        .getPropertyValue(name)
        .trim();
      context.fillRect(0, 0, 1, 1);
      const [red, green, blue] = context.getImageData(0, 0, 1, 1).data;
      return `#${[red, green, blue]
        .map((channel) => channel.toString(16).padStart(2, "0"))
        .join("")}`;
    };
    const fills = Array.from(
      document.querySelectorAll(
        ".blockly-review .blocklyBlockCanvas .blocklyPath",
      ),
      (path) => path.getAttribute("fill"),
    );
    return {
      accent: tokenColor("--color-accent"),
      success: tokenColor("--color-success"),
      fills,
    };
  });
  expect(blockColors.fills).toEqual([
    blockColors.accent,
    blockColors.accent,
    blockColors.success,
  ]);

  await page.setViewportSize({ width: 375, height: 896 });
  const metrics = await page.evaluate(() => ({
    viewport: window.innerWidth,
    root: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(metrics.root).toBeLessThanOrEqual(metrics.viewport);
  expect(metrics.body).toBeLessThanOrEqual(metrics.viewport);
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
