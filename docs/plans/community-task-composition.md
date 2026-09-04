# Community Task Composition Slice

## Plan Ledger

- Status: COMPLETE - all acceptance gates proven
- Roadmap owner: `docs/development-plan.md`
- Goal: make it easy for community robotics developers to compose, run, save,
  and review useful robot tasks from a small semantic Blockly vocabulary.
- Primary profile: `tiago-sim`
- Secondary evidence: completed Reachy 2 portability proof; no new robot in
  this slice.
- Current slice: prove task composition value before adding programming-model
  features or a new extension API.
- Next action: none; retain optional follow-up ideas as parked directions.
- Blocked on: none.
- Do not touch from this plan: core IR control-flow expansion, cloud/backend
  persistence, physical hardware, and third-party plugin loading.

## Preflight Contract

- Preflight status: DRAFT
- Task source: approved cross-review proposal and this plan
- Route: durable `$intuitive-flow`, main session as task control plane
- Goal: prove that a community developer can compose and reproduce a useful
  TIAGo task with the existing semantic Blockly and Workflow IR surfaces.
- Entity budget: reuse the current TIAGo profile, semantic blocks, generic
  capability fallback, local project import/export, review route, artifact
  validator, and test fixtures; add no public API, IR node, persistence layer,
  plugin loader, or robot profile.
- Expansion trigger: a new IR node, server persistence, dynamic extension
  loading, or cross-robot intent contract requires a new approved plan.
- Context required: `README.md`, `STATUS.md`, `docs/architecture.md`,
  `docs/demo-strategy.md`, `docs/development-plan.md`, this plan,
  `examples/workflows/tiago-observable.json`, `web/e2e/workbench.spec.ts`,
  and the existing TIAGo/review artifact commands.

### Acceptance State

- **SUCCESS:** two repository-owned, non-stable TIAGo fixtures and one
  genuinely user-created composition use only `sequence`, `wait`, and exact
  versioned capability nodes; the composition is created by changing block
  order and at least one argument; a fresh browser session imports the local
  export and runs it; one live TIAGo/Gazebo run produces a same-run review
  artifact whose Workflow IR, result, trace, profile, and video identity agree;
  the repository-local extension fixture passes discovery -> toolbox -> compile
  -> validate -> mock execution; all deterministic gates pass.
- **BLOCKED_NEEDS_DECISION:** none under the approved defaults. Stop for a new
  public contract, plugin boundary, third robot, or changed primary profile.
- **BLOCKED_NEEDS_LOCAL_VALIDATION:** Docker/Gazebo, GPU/software rendering,
  browser playback, or human visual inspection cannot produce the required
  live product proof. Do not claim completion with mock-only evidence.
- **INTERMEDIATE_ONLY:** not approved; intermediate work may be kept locally
  but is not merge-ready until required product gates pass.
- **No regressions:** existing Workflow IR/schema versions, exact capability
  references, profile-scoped toolbox filtering, export/import semantics,
  runtime lifecycle, and Reachy 2 proof artifacts remain valid.

### Verification Contract

- **Deterministic:**
  `.venv/bin/ruff check .`; `.venv/bin/mypy src/roboarc`;
  `python -m compileall -q src scripts tests`;
  `python scripts/generate_schemas.py` followed by
  `git diff --exit-code -- schemas`;
  `python -m pytest -p pytest_asyncio.plugin tests/contracts tests/api
  tests/tiago/test_profile.py tests/tiago/test_telemetry_bridge.py
  tests/test_review_artifacts.py`.
- **Web:**
  `cd web && npm run format:check && npm run lint && npm run typecheck &&
  npm test -- --run && npm run build`;
  `cd web && npm run test:e2e`.
- **Integration:** register the local extension fixture through the existing
  profile/manifest/registry seam and run its focused adapter/API/browser
  checks; validate `artifacts/tiago-proof-final` with
  `python scripts/validate_review_artifacts.py`.
- **Product run:** run the existing
  `docker/tiago-jazzy/run-gazebo-review.sh` flow for the primary composition,
  write same-run artifacts, and inspect the resulting review route.
- **Local/live/manual:** Docker daemon, TIAGo Jazzy/Gazebo image, GPU or
  software-rendering fallback, browser, and human inspection of visible robot
  behavior are required. Host `ffprobe` is optional because the TIAGo image
  performs media validation internally; host `rerun` may verify the RRD.
- **Optional:** a second live fixture run, Reachy rerun, or embedded viewer
  exploration is non-blocking and outside this slice.

### Execution Contract

- Main: root session owns scope, implementation order, product proof,
  integration, docs, commits, and final complete/blocked judgment.
- Worker: none initially; delegate only a disjoint, read-only or slow proof
  probe if it materially improves control without changing scope.
- Stop condition: stop and report when a required product gate is unavailable,
  when the extension needs a new generic compiler/runtime seam, or when the
  cut order cannot preserve the user-created composition plus one honest review.
- To execute after approval:

  ```text
  /goal execute docs/plans/community-task-composition.md with intuitive-flow
  ```

- Approval: `LGTM`, `approve`, or `go ahead` approves this contract; scope or
  verification changes require a revised preflight.

## Problem

RoboArc already demonstrates a runtime and two robot integrations, but the
current evidence is still organized around platform capabilities and canned
proofs. The community value is not another robot or a larger programming
language. It is a small UI that lets a researcher combine existing semantic
actions into a task, run it, and understand what happened well enough to save
and share the workflow.

## Appetite

One focused implementation slice, bounded to the existing IR and UI surfaces.
Do not add a new Workflow IR node type, persistence service, plugin system, or
third robot. If the slice requires any of those, stop and reshape the plan.

## Core Outcome

A developer can open the TIAGo workbench, create a task that is not one of the
repository's canned fixtures, run it in the simulator, inspect the correlated
result/review, export the project, import it into a fresh session, and run the
same Workflow IR again without touching ROS or vendor SDK calls.

## Scope

### Phase 1 - Composition Experience

- Use only the existing `sequence`, `wait`, and `capability` nodes.
- Make TIAGo the required primary experience and reuse its current semantic
  capabilities: navigation, stop, look, and speech.
- Maintain two repository-owned example fixtures as non-stable demos:
  `reception greeting` and `look-and-say`. They are examples, not a task
  catalog or a compatibility promise.
- Prove one genuinely user-created composition by rearranging existing blocks
  and changing at least one argument, rather than merely opening a fixture.
- Keep the generic capability block as a lossless fallback for capabilities
  without a semantic preset.

### Phase 2 - Round-Trip And Review Proof

- Exercise compose -> validate -> run -> observe -> export -> import -> run in
  one browser workflow using a fresh client session for import.
- Treat export/import as a local file round-trip. It does not imply server
  persistence, accounts, collaboration, or a database.
- Reuse the existing manifest-backed review route and validator. Workflow IR,
  result, trace, active profile, and video must be from the same run and must
  retain exact capability references.
- Require one live TIAGo/Gazebo product run for the primary composition. Use
  deterministic/runtime and browser evidence for the remaining fixture; do not
  multiply expensive simulator runs without a product reason.

### Phase 3 - Minimal Extension Smoke Test

- Add one repository-local, in-process capability fixture on the existing
  TIAGo profile and prove discovery -> toolbox -> compile -> validate -> mock
  execution.
- Reuse the existing manifest/profile/registry seam. This is a test of current
  extension locality, not a third-party plugin API.
- Do not add dynamic loading, remote registration, marketplace packaging,
  universal capability catalog, or a new semantic intent/binding layer.
- If the smoke test cannot pass without changing the generic compiler/runtime,
  stop and report the smallest seam that needs a separate decision.

## Non-Goals

- Conditions, expressions, variables, output references, loops, parallelism,
  retry/fallback, subflows, resource arbitration, or replay as a batch.
- A promise that one workflow runs unchanged on TIAGo and Reachy 2.
- A third robot, including Reachy Mini, in the mainline roadmap.
- Per-run profile switching, fleet orchestration, hardware control, perception,
  SLAM, MoveIt, or manipulation expansion.
- Authentication, cloud services, server/database persistence, collaboration,
  accounts, or arbitrary code execution.
- A universal capability catalog, plugin marketplace, or public extension API.

## Acceptance Criteria

- `tiago-sim` is the visible primary profile for the complete product journey.
- Two non-stable example fixtures and one non-prebuilt composition use only
  existing exact-version TIAGo capabilities and the current three IR node types.
- The non-prebuilt composition is made by a user changing block order and at
  least one argument; it is not just a renamed fixture.
- A fresh browser session can import the exported project, preserve canonical
  Workflow IR independently of Blockly editor state, validate it, and run it.
- At least one primary composition run produces a same-run review artifact with
  matching workflow/result/trace/profile/video identity and visible behavior.
- One local extension fixture passes discovery, toolbox/compile, validation,
  and mock execution without a core runtime or generic compiler change.
- No new public persistence, plugin, intent, or cross-profile compatibility
  contract is introduced.

## Verification

Focused proof should include:

```bash
python -m pytest tests/contracts tests/api tests/tiago tests/test_review_artifacts.py
.venv/bin/ruff check .
.venv/bin/mypy src/roboarc
python -m compileall -q src scripts tests
cd web && npm run format:check && npm run lint && npm run typecheck
cd web && npm test -- --run && npm run build && npm run test:e2e
python scripts/validate_review_artifacts.py artifacts/tiago-proof-final
```

The live gate is the existing TIAGo/Gazebo review command and one manual
inspection of the primary composition. If Docker/Gazebo is unavailable, stop
the live gate rather than replacing it with a misleading mock claim.

## Cut Order

If appetite is exceeded, cut in this order while preserving the core outcome:

1. Remove the second example fixture.
2. Defer the extension smoke test.
3. Keep local export/import and one primary live review run as the final proof.

Do not cut the user-created composition or the same-run review identity check.

## Stop Gates And Parked Directions

- Stop if the primary journey needs a new IR node or a server persistence layer.
- Stop if TIAGo/Gazebo cannot produce one honest live product proof; record the
  environment blocker instead of expanding simulator infrastructure.
- Stop before any plugin, intent/binding, or third-robot design; those are new
  product bets, not implementation details.

The following are intentionally unplanned until real usage justifies them:

- additional programming-model nodes, each as its own workflow-driven proposal;
- manifest UI metadata beyond what the current generic editor needs;
- a separate adapter/profile such as Reachy Mini;
- verified cross-robot intents and bindings;
- stable v1 contract/migration policy.

## Decision Trigger For The Next Bet

Reconsider the roadmap only after observing a real composition failure or
extension-maintenance problem. The failure should identify the smallest missing
semantic or UI capability; do not infer a feature list from general platform
ambition.
