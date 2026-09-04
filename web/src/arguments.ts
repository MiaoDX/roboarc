import type { JsonValue, ValueSpec } from "./domain";

export interface ArgumentIssue {
  name: string;
  message: string;
}

export function defaultArguments(
  inputs: Record<string, ValueSpec>,
): Record<string, JsonValue> {
  return Object.fromEntries(
    Object.entries(inputs)
      .filter(([, spec]) => spec.default !== null)
      .map(([name, spec]) => [name, spec.default]),
  );
}

export function coerceArgument(
  spec: ValueSpec,
  raw: string | boolean,
): JsonValue {
  if (spec.type === "boolean") return Boolean(raw);
  if (["integer", "number", "duration_ms"].includes(spec.type)) {
    if (typeof raw !== "string" || raw.trim() === "") {
      throw new Error("Enter a number.");
    }
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new Error("Enter a finite number.");
    if (
      (spec.type === "integer" || spec.type === "duration_ms") &&
      !Number.isInteger(value)
    ) {
      throw new Error("Enter a whole number.");
    }
    return value;
  }
  return String(raw);
}

export function validateArguments(
  inputs: Record<string, ValueSpec>,
  args: Record<string, JsonValue>,
): ArgumentIssue[] {
  const issues: ArgumentIssue[] = [];
  for (const [name, spec] of Object.entries(inputs)) {
    const hasValue = Object.hasOwn(args, name);
    const value = args[name];
    if (!hasValue || value === null || value === "") {
      if (spec.required && spec.default === null) {
        issues.push({ name, message: `${spec.title ?? name} is required.` });
      }
      continue;
    }
    if (spec.enum && !spec.enum.some((entry) => entry === value)) {
      issues.push({
        name,
        message: `${spec.title ?? name} must use an available option.`,
      });
    }
    if (typeof value === "number") {
      if (spec.minimum !== null && value < spec.minimum) {
        issues.push({
          name,
          message: `${spec.title ?? name} must be at least ${String(spec.minimum)}.`,
        });
      }
      if (spec.maximum !== null && value > spec.maximum) {
        issues.push({
          name,
          message: `${spec.title ?? name} must be at most ${String(spec.maximum)}.`,
        });
      }
    }
  }
  for (const name of Object.keys(args)) {
    if (!(name in inputs))
      issues.push({
        name,
        message: `${name} is not accepted by this capability.`,
      });
  }
  return issues;
}
