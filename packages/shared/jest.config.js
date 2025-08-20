const base = require('../config/jest/base');

module.exports = {
  ...base,
  displayName: 'shared',
  testMatch: ['<rootDir>/src/**/*.test.{js,ts}'],
  passWithNoTests: true,
};