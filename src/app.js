/**
 * Express Application
 * Main application setup
 */
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const logger = require('./services/logService');

// Initialize express
const app = express();

// Security middlewares
app.use(helmet());
app.use(cors());

// Request parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Setup request logging
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    logger.info({
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      duration: `${duration}ms`,
    }, 'Request completed');
  });
  
  next();
});

// Setup routes
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Create placeholder routes for testing
app.post('/api/otp/send', (req, res) => {
  const { phoneNumber, type = 'verification' } = req.body;
  
  if (!phoneNumber) {
    return res.status(400).json({ 
      success: false, 
      message: 'Phone number is required' 
    });
  }
  
  // Mock successful response
  logger.info({ phoneNumber, type }, 'OTP send request');
  
  return res.status(200).json({
    success: true,
    message: 'Verification code sent',
    expiry: 300
  });
});

app.post('/api/otp/verify', (req, res) => {
  const { phoneNumber, code } = req.body;
  
  if (!phoneNumber || !code) {
    return res.status(400).json({
      success: false,
      message: 'Phone number and verification code are required'
    });
  }
  
  // Mock successful response
  logger.info({ phoneNumber, codeLength: code.length }, 'OTP verify request');
  
  return res.status(200).json({
    success: true,
    message: 'Verification successful',
    valid: true
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'Resource not found'
  });
});

// Error handler
app.use((err, req, res, next) => {
  logger.error({
    error: err.message,
    stack: err.stack,
    url: req.originalUrl,
    method: req.method
  }, 'Error occurred');
  
  res.status(500).json({
    success: false,
    message: 'Internal server error',
    error: process.env.NODE_ENV === 'production' ? undefined : err.message
  });
});

// Export for server.js
module.exports = app; 