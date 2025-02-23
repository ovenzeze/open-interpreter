require('dotenv').config();

const path = require('path');
const rootDir = __dirname;

module.exports = {
  apps: [{
    name: 'interpreter-prod',
    script: 'interpreter/server/cli.py',
    interpreter: process.env.PYTHON_PATH,
    args: `--host 0.0.0.0 --port ${process.env.SERVER_PORT_PROD} --log-level ${process.env.LOG_LEVEL}`,
    cwd: rootDir,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      INTERPRETER_HOME: process.env.INTERPRETER_HOME,
      PYTHONPATH: rootDir,
      VIRTUAL_ENV: process.env.VENV_PATH,
      PATH: process.env.PATH,
      PYTHONUNBUFFERED: '1',
      LOG_LEVEL: process.env.LOG_LEVEL || 'INFO'
    },
    error_file: path.join(process.env.INTERPRETER_BASE, 'logs/prod/err.log'),
    out_file: path.join(process.env.INTERPRETER_BASE, 'logs/prod/out.log'),
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
    script: 'interpreter/server/cli.py',
    interpreter: process.env.PYTHON_PATH,
    args: `--host 0.0.0.0 --port ${process.env.SERVER_PORT_DEV} --log-level DEBUG`,
    cwd: rootDir,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'development',
      PYTHONPATH: rootDir,
      VIRTUAL_ENV: process.env.VENV_PATH,
      PATH: process.env.PATH,
      PYTHONUNBUFFERED: '1',
      LOG_LEVEL: 'DEBUG'
    },
    error_file: '/Users/clay/.interpreter/logs/dev/err.log',
    out_file: '/Users/clay/.interpreter/logs/dev/out.log',
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
