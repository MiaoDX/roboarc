import * as Blockly from "blockly/core";

function cssToken(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function blocklyColorToken(name: string): string {
  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas color conversion is unavailable.");
  context.fillStyle = cssToken(name);
  context.fillRect(0, 0, 1, 1);
  const [red, green, blue] = context.getImageData(0, 0, 1, 1).data;
  return `#${[red, green, blue]
    .map((channel) => channel.toString(16).padStart(2, "0"))
    .join("")}`;
}

export function createRoboArcTheme(): Blockly.Theme {
  return Blockly.Theme.defineTheme("roboarc", {
    name: "roboarc",
    base: Blockly.Themes.Classic,
    blockStyles: {
      roboarc_workflow_blocks: {
        colourPrimary: blocklyColorToken("--color-accent"),
      },
      roboarc_capability_blocks: {
        colourPrimary: blocklyColorToken("--color-success"),
      },
    },
    categoryStyles: {
      roboarc_workflow_category: {
        colour: blocklyColorToken("--color-accent"),
      },
      roboarc_capability_category: {
        colour: blocklyColorToken("--color-success"),
      },
    },
    componentStyles: {
      workspaceBackgroundColour: blocklyColorToken("--color-workspace"),
      toolboxBackgroundColour: blocklyColorToken("--color-paper-2"),
      toolboxForegroundColour: blocklyColorToken("--color-ink"),
      flyoutBackgroundColour: blocklyColorToken("--color-paper"),
      flyoutForegroundColour: blocklyColorToken("--color-ink"),
      scrollbarColour: blocklyColorToken("--color-rule-strong"),
      insertionMarkerColour: blocklyColorToken("--color-accent"),
    },
  });
}
