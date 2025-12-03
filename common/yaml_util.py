import yaml
import os
from config.config import Config
from common.logger import Logger  # 导入日志记录器


class YamlUtil:
    @staticmethod
    def read_yaml(file_path):
        """读取YAML文件并返回解析后的内容
        参数:
            file_path (str): YAML文件路径（绝对或相对路径）
        返回:
            dict/list: 解析后的YAML内容
        异常:
            FileNotFoundError: 当文件不存在时抛出
            yaml.YAMLError: 当YAML解析错误时抛出
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(Config.BASE_DIR, file_path)
        # 规范化路径
        file_path = os.path.normpath(file_path)

        try:
            # 确保文件存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            # 读取并解析文件
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError as e:
            logger.error(f"YAML文件不存在：{file_path}")
            raise Exception(f"YAML文件不存在：{file_path}")
        except yaml.YAMLError as e:
            # 记录详细的解析错误
            error_msg = f"YAML解析错误：{file_path}-{str(e)}"
            Logger.error(error_msg)
            raise yaml.YAMLError(error_msg) from e
        except Exception as e:
            # 捕获其他意外错误
            Logger.error(f"处理YAML文件时发生意外错误: {file_path} - {str(e)}")
            raise

    @staticmethod
    def read_test_cases(file_name):
        """读取测试用例YAML文件
        参数:
            file_name (str): 测试用例文件名
        返回:
            list: 测试用例列表
        """
        # 构建完整路径
        file_path = os.path.join(Config.TEST_CASES_DIR, file_name)
        # 使用通用的read_yaml方法
        return YamlUtil.read_yaml(file_path)

    @staticmethod
    def write_yaml(file_path, data):
        """将数据写入YAML文件
        参数:
            file_path (str): 文件路径
            data (dict/list): 要写入的数据
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(Config.BASE_DIR, file_path)

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True)

            Logger.info(f"YAML文件写入成功: {file_path}")

        except PermissionError as e:
            Logger.error(f"文件写入权限不足: {file_path} - {str(e)}")
            raise
        except Exception as e:
            Logger.error(f"写入YAML文件时发生错误: {file_path} - {str(e)}")
            raise

