try {
  require('dotenv').config();
} catch (e) {
  console.warn('Warning: dotenv module not found, using process.env directly');
}

const path = require('path');
const rootDir = __dirname;

// 设置默认值
const defaultConfig = {
  PYTHON_PATH: process.env.PYTHON_PATH || 'python',
  SERVER_PORT_PROD: process.env.SERVER_PORT_PROD || 5001,
  SERVER_PORT_DEV: process.env.SERVER_PORT_DEV || 5002,
  INTERPRETER_BASE: process.env.INTERPRETER_BASE || path.join(process.env.HOME, '.interpreter'),
  INTERPRETER_HOME: process.env.INTERPRETER_HOME || path.join(process.env.HOME, '.interpreter/.prod'),
  LOG_LEVEL: process.env.LOG_LEVEL || 'INFO',
  VENV_PATH: process.env.VIRTUAL_ENV
};

module.exports = {
  apps: [{
    name: 'interpreter-prod',
    // 修改启动方式
    script: defaultConfig.PYTHON_PATH,
    args: [
      '-m',
      'interpreter.server.cli',
      '--host', '0.0.0.0',
      '--port', defaultConfig.SERVER_PORT_PROD.toString(),
      '--log-level', defaultConfig.LOG_LEVEL
    ],
    interpreter: null,  // 移除interpreter设置，直接使用script指定Python路径
    cwd: rootDir,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      INTERPRETER_HOME: defaultConfig.INTERPRETER_HOME,
      PYTHONPATH: rootDir,
      VIRTUAL_ENV: defaultConfig.VENV_PATH,
      PATH: process.env.PATH,
      PYTHONUNBUFFERED: '1',
      LOG_LEVEL: defaultConfig.LOG_LEVEL
    },
    error_file: path.join(defaultConfig.INTERPRETER_BASE, 'logs/prod/err.log'),
    out_file: path.join(defaultConfig.INTERPRETER_BASE, 'logs/prod/out.log'),
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    time: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    max_restarts: 10,
    restart_delay: 4000,
    wait_ready: true,
    kill_timeout: 10000
  }, {
    name: 'interpreter-dev',
    // 修改启动方式
    script: defaultConfig.PYTHON_PATH,
    args: [
      '-m',
      'interpreter.server.cli',
      '--host', '0.0.0.0',
      '--port', defaultConfig.SERVER_PORT_DEV.toString(),
      '--log-level', 'DEBUG'
    ],
    interpreter: null,  // 移除interpreter设置，直接使用script指定Python路径
    cwd: rootDir,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'development',
      PYTHONPATH: rootDir,
      VIRTUAL_ENV: defaultConfig.VENV_PATH,
      PATH: process.env.PATH,
      PYTHONUNBUFFERED: '1',
      LOG_LEVEL: 'DEBUG'
    },
    error_file: path.join(defaultConfig.INTERPRETER_BASE, 'logs/dev/err.log'),
    out_file: path.join(defaultConfig.INTERPRETER_BASE, 'logs/dev/out.log'),
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    time: true,
    autorestart: true,
    watch: ['interpreter'],
    ignore_watch: [
      'logs',
      'tests',
      '**/*.pyc',
      '**/__pycache__',
      '.git',
      'node_modules'
    ],
    max_memory_restart: '1G',
    max_restarts: 10,
    restart_delay: 4000,
    wait_ready: true,
    kill_timeout: 10000
  }]
};
