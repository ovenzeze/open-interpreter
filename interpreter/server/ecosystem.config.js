module.exports = {
  apps: [{
    name: 'interpreter-prod',
    script: 'python',
    args: '-m interpreter.server.cli --host 0.0.0.0 --port 5001 --log-level INFO',
    cwd: '/Users/clay/.interpreter/.prod',
    exec_mode: 'fork',  // 改为 fork 模式
    env: {
      INTERPRETER_HOME: '/Users/clay/.interpreter/.prod',
      PYTHONPATH: '/Users/clay/.interpreter/.prod',
      PYTHONUNBUFFERED: '1',
      LOG_LEVEL: 'INFO',
      ENV: 'production'
    },
    error_file: '/Users/clay/.interpreter/logs/prod/err.log',
    out_file: '/Users/clay/.interpreter/logs/prod/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    time: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    max_restarts: 10,
    restart_delay: 4000,
    wait_ready: true,
    instances: 1
  }, {
    name: 'interpreter-dev',
    script: 'python',
    args: '-m interpreter.server.cli --host 0.0.0.0 --port 5002 --log-level DEBUG',
    cwd: '/Users/clay/Code/open-interpreter',
    exec_mode: 'fork',  // 改为 fork 模式
    env: {
      PYTHONPATH: '/Users/clay/Code/open-interpreter',
      PYTHONUNBUFFERED: '1',
      LOG_LEVEL: 'DEBUG',
      ENV: 'development'
    },
    error_file: '/Users/clay/.interpreter/logs/dev/err.log',
    out_file: '/Users/clay/.interpreter/logs/dev/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    time: true,
    autorestart: true,
    watch: true,
    ignore_watch: ['logs', 'tests', '*.pyc', '__pycache__'],
    max_memory_restart: '1G',
    max_restarts: 10,
    restart_delay: 4000,
    wait_ready: true,
    instances: 1
  }]
};
