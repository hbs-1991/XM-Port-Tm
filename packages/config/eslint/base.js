module.exports = {
  extends: [
    'eslint:recommended'
  ],
  plugins: [],
  rules: {
    'prefer-const': 'error',
    'no-var': 'error'
  },
  env: {
    node: true,
    es6: true
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module'
  }
};