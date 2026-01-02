module.exports = {
  root: true,
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:svelte/recommended",
    "prettier",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    sourceType: "module",
    ecmaVersion: 2020,
    extraFileExtensions: [".svelte"],
  },
  env: {
    browser: true,
    es2017: true,
    node: true,
  },
  overrides: [
    {
      files: ["*.svelte"],
      parser: "svelte-eslint-parser",
      parserOptions: {
        parser: "@typescript-eslint/parser",
      },
    },
  ],
  rules: {
    // Allow unused vars that start with underscore
    "@typescript-eslint/no-unused-vars": [
      "warn",
      {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
        caughtErrors: "none",
      },
    ],
    // Disable some rules that are too strict for this project
    "@typescript-eslint/no-explicit-any": "off",
    "no-constant-condition": "warn",
    // Allow {@html} for controlled SVG icons (not user-generated content)
    "svelte/no-at-html-tags": "off",
    // Disable unused svelte-ignore warnings since they may be suppressed by Svelte version
    "svelte/no-unused-svelte-ignore": "off",
  },
};
