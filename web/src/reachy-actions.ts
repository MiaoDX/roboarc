import type { JsonValue } from "./domain";

export const REACHY_ACTIONS = [
  { id: "home", label: "Return arm home" },
  { id: "raise", label: "Raise arm" },
  { id: "wave", label: "Wave arm" },
  { id: "present", label: "Present with arm" },
] as const;

export type ReachyActionId = (typeof REACHY_ACTIONS)[number]["id"];

export function reachyAction(id: ReachyActionId) {
  return REACHY_ACTIONS.find((action) => action.id === id) ?? REACHY_ACTIONS[0];
}

export function isReachyActionArgs(args: Record<string, JsonValue>): args is {
  gesture: ReachyActionId;
  side: "left" | "right";
  duration_ms: number;
} {
  const gesture = args.gesture;
  const side = args.side;
  const duration = args.duration_ms;
  return (
    Object.keys(args).length === 3 &&
    typeof gesture === "string" &&
    REACHY_ACTIONS.some((action) => action.id === gesture) &&
    (side === "left" || side === "right") &&
    typeof duration === "number" &&
    Number.isFinite(duration)
  );
}
