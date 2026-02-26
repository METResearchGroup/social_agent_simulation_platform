import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import localRules from "./eslint-rules/index.mjs";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    plugins: {
      local: localRules,
    },
    rules: {
      "local/no-fetch-outside-api": "error",
      "local/no-process-env-outside-boundaries": "error",
      "local/supabase-auth-boundary": "error",
      "local/useeffect-requires-request-id-guard": "error",
      "local/ui-import-layering": "error",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
