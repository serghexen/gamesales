import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import globals from 'globals'

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  ...vue.configs['flat/essential'],
  js.configs.recommended,
  {
    files: ['**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // На этапе активного рефакторинга оставляем прагматичный набор правил.
      'no-console': 'warn',
      'no-debugger': 'error',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'vue/no-mutating-props': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },
]
