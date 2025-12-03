
import os
import logging
import colorlog
from config.config import Config



class Logger:
    _instance = None

    def __new__(cls):
        """实现单例模式，确保只有一个Logger实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.init_logger()
        return cls._instance

    def init_logger(self):
        """初始化日志记录器"""
        # 确保报告目录存在
        os.makedirs(Config.REPORT_DIR, exist_ok=True)
        # 创建日志记录器logger
        self.logger = logging.getLogger('api_auto')
        self.logger.setLevel(logging.DEBUG)

        # 如果已有处理器，直接返回
        if self.logger.handlers:
            return

        # 创建控制台处理器，并将等级设置为debug。
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(
            filename=os.path.join(Config.REPORT_DIR, 'api_test.log'),
            mode='a',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # 创建控制台格式化器。
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


        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        # 添加处理器

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    @classmethod
    def info(cls, message):
        """记录信息级别日志"""
        cls().logger.info(message)
        # 控制台输出（带颜色）
        # print(f"\033[1;32m[INFO] {message}\033[0m")

    @classmethod
    def debug(cls, message):
        """记录调试级别日志"""
        cls().logger.debug(message)
        # 控制台输出（带颜色）
        # print(f"\033[1;34m[DEBUG] {message}\033[0m")

    @classmethod
    def warning(cls, message):
        """记录警告级别日志"""
        cls().logger.warning(message)
        # 控制台输出（带颜色）
        # print(f"\033[1;33m[WARNING] {message}\033[0m")

    @classmethod
    def error(cls, message, exc_info=False):
        """
        记录错误级别日志
        参数:
            message (str): 错误消息
            exc_info (bool): 是否包含异常信息
        """
        if exc_info:
            cls().logger.error(message, exc_info=True)
        else:
            cls().logger.error(message)
        # 控制台输出（带颜色）
        # print(f"\033[1;31m[ERROR] {message}\033[0m")

    @classmethod
    def critical(cls, message, exc_info=False):
        """
        记录严重级别日志
        参数:
            message (str): 错误消息
            exc_info (bool): 是否包含异常信息
        """
        if exc_info:
            cls().logger.critical(message, exc_info=True)
        else:
            cls().logger.critical(message)
        # 控制台输出（带颜色）
        # print(f"\033[1;41m[CRITICAL] {message}\033[0m")

    @classmethod
    def success(cls, message):
        """
        记录成功信息（使用INFO级别但特殊标记）
        注意：这里使用INFO级别，但通过颜色区分
        """
        # 使用INFO级别记录，但通过颜色显示为成功
        cls().logger.info(f"SUCCESS: {message}")
        # 控制台输出（带颜色）
        # print(f"\033[1;32m[SUCCESS] {message}\033[0m")

    @classmethod
    def exception(cls, message):
        """记录异常信息（自动包含堆栈跟踪）"""
        cls().logger.exception(message)
        # 控制台输出（带颜色）
        # print(f"\033[1;31m[EXCEPTION] {message}\033[0m")

