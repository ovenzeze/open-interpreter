import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

class DailyRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename):
        super().__init__(
            filename=filename,
            when='midnight',     # 每天午夜进行轮转
            interval=1,          # 每1个周期轮转一次
            backupCount=30,      # 保留30天的日志文件
            encoding='utf-8'
        )
        # 设置日志文件名格式
        self.suffix = "%Y-%m-%d"  # 添加日期后缀
        self.extMatch = r"^\d{4}-\d{2}-\d{2}$"  # 匹配日期格式
