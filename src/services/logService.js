/**
 * Logging service
 * Provides centralized logging using Pino
 */
const pino = require('pino');

// Configure logger based on environment
const logger = pino({
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  transport: process.env.NODE_ENV === 'development' 
    ? { target: 'pino-pretty', options: { colorize: true } }
    : undefined,
  base: {
    service: 'sms-verification-service'
  }
});

module.exports = logger; 