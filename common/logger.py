import os  # 添加这行
import logging
import colorlog
from config.config import Config  # 确保这行存在


class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_logger()
        return cls._instance

    def init_logger(self):
        # 配置彩色格式器
        self.formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        # 确保报告目录存在
        os.makedirs(Config.REPORT_DIR, exist_ok=True)

        self.logger = logging.getLogger('api_auto')
        self.logger.setLevel(logging.DEBUG)

        if self.logger.handlers:
            return

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(
            filename=os.path.join(Config.REPORT_DIR, 'api_test.log'),
            mode='a',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )

        # file_formatter = logging.Formatter(
        #     '%(asctime)s - %(levelname)-8s - %(message)s',
        #     datefmt='%Y-%m-%d %H:%M:%S'
        # )

        file_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    @classmethod
    def info(cls, message):
        cls().logger.info(message)

    @classmethod
    def debug(cls, message):
        cls().logger.debug(message)

    @classmethod
    def warning(cls, message):
        cls().logger.warning(message)

    @classmethod
    def error(cls, message):
        cls().logger.error('\033[1;31m%s\033[0m' % message)

    @classmethod
    def success(cls, message):
        cls().logger.info('\033[1;32m%s\033[0m' % message)
