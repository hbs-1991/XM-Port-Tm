module.exports = {
  extends: ['../../packages/config/eslint/react.js'],
  parserOptions: {
    project: './tsconfig.json'
  },
  rules: {
    'no-unused-vars': 'warn',
    'no-undef': 'warn',
    'react/no-unescaped-entities': 'warn',
    'react-hooks/exhaustive-deps': 'warn',
    'react/display-name': 'warn',
    'react/no-children-prop': 'warn',
    'no-useless-escape': 'warn'
  }
};