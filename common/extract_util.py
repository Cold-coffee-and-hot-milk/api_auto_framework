import jsonpath
import re
import os
import json
from common.logger import Logger
from config.config import Config
from common.data_util import DataUtil
import globals  # 导入全局变量模块


class ExtractUtil:
    """
        数据提取和变量替换工具类
        功能：从HTTP响应中提取数据，并替换请求中的动态变量
    """
    # 类变量，存储提取的数据

    extract_data = {}

    @classmethod
    def extract_values(cls, response, extract_rules):
        """
        从HTTP响应中提取数据
        参数:
            response: HTTP响应对象
            extract_rules: 提取规则字典 {变量名: 提取规则}
        """
        if not extract_rules or not isinstance(extract_rules, dict):
            Logger.warning("提取规则为空或格式错误，跳过提取")
            return

        # 使用DataUtil提取数据
        extracted_data = DataUtil.extract_data_from_response(response, extract_rules)
        
        # 将提取的数据添加到类变量中
        for key, value in extracted_data.items():
            if value is not None:
                cls.extract_data[key] = value
                Logger.debug(f"提取成功: {key} = {value}")
            else:
                Logger.warning(f"提取失败: {key} = None")

    @classmethod
    def replace_dynamic_values(cls, data):
        """
        替换数据中的动态变量占位符

        参数:
            data: 要处理的数据（支持字典、列表、字符串等）

        返回:
            处理后的数据
        """
        try:
            # 准备变量字典
            variables = {}
            variables.update(globals.ENV_VARS)
            variables.update(cls.extract_data)
            variables.update(os.environ)
            
            # 添加配置变量
            for attr in dir(Config):
                if not attr.startswith('_'):
                    variables[attr] = getattr(Config, attr)
            
            # 使用DataUtil替换变量
            return DataUtil.replace_variables(data, variables)
        except Exception as e:
            Logger.error(f"变量替换失败: {str(e)}")
            return data

    @classmethod
    def clear_extract_data(cls, secure_cleanup=False):
        """
        清空提取的数据

        参数:
            secure_cleanup: 是否安全清理敏感数据
        """
        if secure_cleanup:
            # 安全清理敏感数据
            sensitive_keys = ['password', 'token', 'secret', 'key', 'auth']
            for key in list(cls.extract_data.keys()):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    if cls.extract_data[key] is not None:
                        # 用星号覆盖敏感数据
                        cls.extract_data[key] = '*' * min(20, len(str(cls.extract_data[key])))

        cls.extract_data = {}
        Logger.debug("已清空提取数据" + ("（安全模式）" if secure_cleanup else ""))

    @classmethod
    def get_extracted_value(cls, key, default=None):
        """
        安全获取提取的值

        参数:
            key: 极名
            default: 默认值

        返回:
            变量值或默认值
        """
        return cls.extract_data.get(key, default)

    @classmethod
    def set_extracted_value(cls, key, value):
        """
        手动设置提取的值

        参数:
            key: 变量名
            value: 变量值
        """
        cls.extract_data[key] = value
        Logger.debug(f"手动设置变量: {key} = {value}")

    @classmethod
    def list_extracted_variables(cls):
        """
        列出所有已提取的变量（不包含敏感数据值）

        返回:
            变量名列表
        """
        # 过滤掉敏感数据的实际值
        safe_list = {}
        sensitive_keys = ['password', 'token', 'secret', 'key', 'auth']

        for key, value in cls.extract_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_list[key] = '***敏感数据***'
            else:
                safe_list[key] = value

        return safe_list

    @classmethod
    def validate_extracted_data(cls, required_vars=None):
        """
        验证必需的变量是否已提取

        参数:
            required_vars: 必需变量列表

        返回:
            (bool, list): (是否验证成功, 缺失变量列表)
        """
        if not required_vars:
            return True, []

        missing_vars = [var for var in required_vars if var not in cls.extract_data]
        is_valid = len(missing_vars) == 0

        if not is_valid:
            Logger.warning(f"缺失必需变量: {missing_vars}")

        return is_valid, missing_vars

    # 新增方法：获取所有提取的变量
    @classmethod
    def get_all_extract_vars(cls):
        """
        获取所有提取的变量

        返回:
            dict: 所有提取的变量字典
        """
        return cls.extract_data.copy()  # 返回副本，避免外部修改

    # 新增方法：提取值并返回结果（用于调试）
    @classmethod
    def extract_and_get(cls, response, extract_rules):
        """
        提取值并返回结果（用于调试）

        参数:
            response: HTTP响应对象
            extract_rules: 提取规则字典 {变量名: 提取规则}

        返回:
            dict: 提取结果
        """
        cls.extract_values(response, extract_rules)
        return cls.get_all_extract_vars()


# 便捷函数
def extract_values(response, extract_rules):
    """便捷函数：提取值"""
    ExtractUtil.extract_values(response, extract_rules)


def replace_variables(data):
    """便捷函数：替换变量"""
    return ExtractUtil.replace_dynamic_values(data)


def clear_extracted_data(secure_cleanup=False):
    """便捷函数：清空数据"""
    ExtractUtil.clear_extract_data(secure_cleanup)


def get_variable(key, default=None):
    """便捷函数：获取变量值"""
    return ExtractUtil.get_extracted_value(key, default)


def set_variable(key, value):
    """便捷函数：设置变量值"""
    ExtractUtil.set_extracted_value(key, value)


# 新增便捷函数
def get_all_variables():
    """便捷函数：获取所有变量"""
    return ExtractUtil.get_all_extract_vars()


# 新增调试函数
def extract_and_get(response, extract_rules):
    """便捷函数：提取值并返回结果（用于调试）"""
    return ExtractUtil.extract_and_get(response, extract_rules)

