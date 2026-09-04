import type { JsonValue } from "./domain";

export const TIAGO_LOCATIONS = [
  { id: "reception", label: "reception" },
  { id: "home", label: "home" },
] as const;

export const TIAGO_LOOK_PRESETS = [
  {
    id: "ahead",
    label: "ahead",
    args: { frame: "base_footprint", x: 1.5, y: 0, z: 1.6 },
  },
  {
    id: "left",
    label: "left",
    args: { frame: "base_footprint", x: 1.2, y: 1, z: 1.6 },
  },
  {
    id: "right",
    label: "right",
    args: { frame: "base_footprint", x: 1.2, y: -1, z: 1.6 },
  },
] as const satisfies readonly {
  id: string;
  label: string;
  args: Record<string, JsonValue>;
}[];

export function tiagoLookPreset(id: string) {
  return TIAGO_LOOK_PRESETS.find((preset) => preset.id === id);
}

export function tiagoLocation(id: string) {
  return TIAGO_LOCATIONS.find((location) => location.id === id);
}

export function isExactArgs(
  args: Record<string, JsonValue>,
  expected: Record<string, JsonValue>,
): boolean {
  const keys = Object.keys(expected);
  return (
    Object.keys(args).length === keys.length &&
    keys.every((key) => Object.is(args[key], expected[key]))
  );
}
