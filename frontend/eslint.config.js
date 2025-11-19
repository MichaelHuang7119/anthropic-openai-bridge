import js from '@eslint/js'
import svelte from 'eslint-plugin-svelte'
import prettier from 'eslint-config-prettier'
import globals from 'globals'

export default [
  js.configs.recommended,
  // Only use basic Svelte rules, skip TypeScript-specific parsing
  {
    files: ['**/*.svelte'],
    plugins: {
      svelte: svelte,
    },
    rules: {
      // Only enable basic Svelte rules that don't require TypeScript parsing
      'svelte/valid-compile': 'warn',
      'svelte/no-at-html-tags': 'warn',
    },
  },
  {
    files: ['**/*.js'],
    languageOptions: {
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
      },
    },
  },
  {
    ignores: [
      'build/',
      '.svelte-kit/',
      'dist/',
      'node_modules/',
      'static/manifest.json',
      'src/service-worker.js',
      '**/*.ts', // Skip TypeScript files for now to avoid parsing issues
    ],
  },
]