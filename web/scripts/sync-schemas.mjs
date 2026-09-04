import { copyFile, mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const schemaNames = [
  "workflow.schema.json",
  "project.schema.json",
  "capability-manifest.schema.json",
  "runtime-event.schema.json",
  "validation-report.schema.json",
];
const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const webDirectory = resolve(scriptDirectory, "..");
const sourceDirectory = resolve(webDirectory, "..", "schemas");
const destinationDirectory = resolve(webDirectory, "src", "schemas");
const check = process.argv.includes("--check");

await mkdir(destinationDirectory, { recursive: true });

const drift = [];
for (const name of schemaNames) {
  const source = resolve(sourceDirectory, name);
  const destination = resolve(destinationDirectory, name);
  if (check) {
    const [canonical, vendored] = await Promise.all([
      readFile(source),
      readFile(destination).catch(() => null),
    ]);
    if (vendored === null || !canonical.equals(vendored)) {
      drift.push(name);
    }
  } else {
    await copyFile(source, destination);
  }
}

if (drift.length > 0) {
  console.error(`Schema drift detected: ${drift.join(", ")}`);
  process.exitCode = 1;
} else if (check) {
  console.log(
    `All ${schemaNames.length} vendored schemas match canonical sources.`,
  );
} else {
  console.log(`Synced ${schemaNames.length} schemas.`);
}
