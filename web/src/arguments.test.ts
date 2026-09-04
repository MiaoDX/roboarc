import { describe, expect, it } from "vitest";

import {
  coerceArgument,
  defaultArguments,
  validateArguments,
} from "./arguments";
import type { ValueSpec } from "./domain";

function spec(overrides: Partial<ValueSpec> = {}): ValueSpec {
  return {
    type: "string",
    required: false,
    title: null,
    description: null,
    default: null,
    enum: null,
    minimum: null,
    maximum: null,
    ...overrides,
  };
}

describe("capability argument logic", () => {
  it("applies declared defaults without inventing absent values", () => {
    expect(
      defaultArguments({ text: spec({ default: "hello" }), optional: spec() }),
    ).toEqual({ text: "hello" });
  });

  it("coerces boolean, integer, duration and string fields", () => {
    expect(coerceArgument(spec({ type: "boolean" }), true)).toBe(true);
    expect(coerceArgument(spec({ type: "integer" }), "4")).toBe(4);
    expect(coerceArgument(spec({ type: "duration_ms" }), "250")).toBe(250);
    expect(coerceArgument(spec({ type: "map_location" }), "dock")).toBe("dock");
    expect(() => coerceArgument(spec({ type: "integer" }), "1.5")).toThrow(
      /whole number/,
    );
  });

  it("reports required, enum, range, and unknown argument violations", () => {
    const issues = validateArguments(
      {
        mode: spec({ required: true, enum: ["safe"] }),
        speed: spec({ type: "number", minimum: 0, maximum: 1 }),
      },
      { mode: "fast", speed: 2, extra: true },
    );
    expect(issues.map((issue) => issue.name)).toEqual([
      "mode",
      "speed",
      "extra",
    ]);
  });
});
