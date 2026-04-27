import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // 历史调试脚本（CommonJS）。仅手工执行，不参与构建；不让 lint 报 require() 错。
    "fork-test.js",
    "fork-child.js",
  ]),
]);

export default eslintConfig;
