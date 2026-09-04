import Ajv2020 from "ajv/dist/2020";

import capabilityManifestSchema from "./schemas/capability-manifest.schema.json";
import projectSchema from "./schemas/project.schema.json";
import runtimeEventSchema from "./schemas/runtime-event.schema.json";
import validationReportSchema from "./schemas/validation-report.schema.json";
import workflowSchema from "./schemas/workflow.schema.json";

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addFormat(
  "uuid",
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
);
ajv.addFormat("date-time", {
  type: "string",
  validate(value: string): boolean {
    return (
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(
        value,
      ) && !Number.isNaN(Date.parse(value))
    );
  },
});

export const validateCapabilityManifest = ajv.compile(capabilityManifestSchema);
export const validateProject = ajv.compile(projectSchema);
export const validateRuntimeEvent = ajv.compile(runtimeEventSchema);
export const validateValidationReport = ajv.compile(validationReportSchema);
export const validateWorkflow = ajv.compile(workflowSchema);
