"""
通用数据处理工具类
用于处理数据转换、变量替换和验证等通用功能
"""
import re
import json
import yaml
from typing import Dict, Any, List, Union, Optional
from jsonpath import jsonpath
from common.logger import Logger


class DataUtil:
    """数据处理工具类，提供数据转换、变量替换和验证功能"""
    
    @staticmethod
    def replace_variables(data: Any, variables: Dict[str, Any]) -> Any:
        """
        递归替换数据中的变量
        
        Args:
            data: 原始数据
            variables: 变量字典
            
        Returns:
            Any: 替换变量后的数据
        """
        if isinstance(data, dict):
            return {key: DataUtil.replace_variables(value, variables) for key, value in data.items()}
        elif isinstance(data, list):
            return [DataUtil.replace_variables(item, variables) for item in data]
        elif isinstance(data, str):
            return DataUtil._replace_string_variables(data, variables)
        else:
            # 处理非字符串类型（如数字、布尔值等）
            return data
    
    @staticmethod
    def _replace_string_variables(text: str, variables: Dict[str, Any]) -> str:
        """
        替换字符串中的变量
        
        Args:
            text: 原始字符串
            variables: 变量字典
            
        Returns:
            str: 替换变量后的字符串
        """
        if not isinstance(text, str):
            return text
            
        # 匹配 ${variable} 格式的变量
        pattern = r'\$\{([^}]+)\}'
        
        def replace_match(match):
            var_name = match.group(1)
            # 递归替换嵌套变量
            value = variables.get(var_name, match.group(0))
            if isinstance(value, str):
                return DataUtil._replace_string_variables(value, variables)
            return str(value)
        
        return re.sub(pattern, replace_match, text)
    
    @staticmethod
    def extract_data_from_response(response, extract_config: Dict[str, str]) -> Dict[str, Any]:
        """
        从响应中提取数据
        
        Args:
            response: HTTP响应对象
            extract_config: 提取配置字典
            
        Returns:
            Dict[str, Any]: 提取的数据字典
        """
        extracted_data = {}
        
        try:
            # 尝试解析JSON响应
            if hasattr(response, 'json'):
                try:
                    response_data = response.json()
                except ValueError:
                    # 处理非JSON响应
                    response_data = DataUtil.safe_convert_to_dict(response.content)
            else:
                response_data = response
                
            # 根据配置提取数据
            for key, extract_rule in extract_config.items():
                if ':' in extract_rule:
                    method, path = extract_rule.split(':', 1)
                    if method.lower() == 'jsonpath':
                        value = jsonpath(response_data, path)
                        extracted_data[key] = value[0] if value else None
                    elif method.lower() == 'header':
                        extracted_data[key] = response.headers.get(path)
                    elif method.lower() == 'regex':
                        # 确保使用文本内容进行正则匹配
                        text_content = response.text if hasattr(response, 'text') else str(response)
                        match = re.search(path, text_content)
                        extracted_data[key] = match.group(1) if match else None
                    elif method.lower() == 'body':
                        # 直接从响应体提取
                        extracted_data[key] = DataUtil._extract_from_body(response_data, path)
                else:
                    # 默认使用jsonpath
                    value = jsonpath(response_data, extract_rule)
                    extracted_data[key] = value[0] if value else None
                    
        except Exception as e:
            Logger.error(f"提取数据时出错: {str(e)}")
            
        return extracted_data
    
    @staticmethod
    def _extract_from_body(data: Any, path: str) -> Any:
        """
        从响应体中提取数据
        
        Args:
            data: 响应数据
            path: 提取路径
            
        Returns:
            Any: 提取的数据
        """
        try:
            keys = path.split('.')
            result = data
            for key in keys:
                if isinstance(result, dict):
                    result = result.get(key)
                elif isinstance(result, list) and key.isdigit():
                    index = int(key)
                    result = result[index] if 0 <= index < len(result) else None
                else:
                    result = None
                    
                if result is None:
                    break
                    
            return result
        except Exception:
            return None
    
    @staticmethod
    def validate_data(data: Any, validation_rules: List[str]) -> bool:
        """
        验证数据
        
        Args:
            data: 要验证的数据
            validation_rules: 验证规则列表
            
        Returns:
            bool: 验证结果
        """
        try:
            # 准备验证环境
            safe_env = {
                'response': data,
                'data': data.get('data', {}) if isinstance(data, dict) else {},
                'headers': data.get('headers', {}) if isinstance(data, dict) else {},
                'status_code': data.get('status_code') if isinstance(data, dict) else None,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
            }
            
            # 添加提取的变量
            from common.extract_util import ExtractUtil
            safe_env.update(ExtractUtil.get_all_extract_vars())
            
            # 执行验证规则
            for rule in validation_rules:
                try:
                    result = eval(rule, {"__builtins__": {}}, safe_env)
                    if not result:
                        Logger.error(f"验证规则失败: {rule}")
                        return False
                except Exception as e:
                    Logger.error(f"执行验证规则时出错: {rule}, 错误: {str(e)}")
                    return False
                    
            return True
            
        except Exception as e:
            Logger.error(f"数据验证时出错: {str(e)}")
            return False
    
    @staticmethod
    def safe_json_serialize(data: Any) -> str:
        """安全地将数据转换为JSON字符串"""
        try:
            if isinstance(data, bytes):
                return data.decode('utf-8')
            return json.dumps(data, ensure_ascii=False)
        except TypeError:
            return str(data)
    
    @staticmethod
    def safe_convert_to_dict(data: Any) -> Dict[str, Any]:
        """安全地将数据转换为字典"""
        if isinstance(data, dict):
            return data
        elif isinstance(data, bytes):
            try:
                # 先尝试解码为字符串
                return json.loads(data.decode('utf-8'))
            except UnicodeDecodeError:
                return {"raw_bytes": str(data)}
            except json.JSONDecodeError:
                return {"value": data.decode('utf-8')}
        elif isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                try:
                    return yaml.safe_load(data)
                except yaml.YAMLError:
                    return {"value": data}
        else:
            return {"value": str(data)}
    
    @staticmethod
    def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并两个字典
        
        Args:
            dict1: 第一个字典
            dict2: 第二个字典
            
        Returns:
            Dict[str, Any]: 合并后的字典
        """
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtil.merge_dicts(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def flatten_dict(data: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """
        扁平化字典
        
        Args:
            data: 原始字典
            parent_key: 父键名
            sep: 分隔符
            
        Returns:
            Dict[str, Any]: 扁平化后的字典
        """
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(DataUtil.flatten_dict(value, new_key, sep).items())
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        items.extend(DataUtil.flatten_dict(item, f"{new_key}{sep}{i}", sep).items())
                    else:
                        items.append((f"{new_key}{sep}{i}", item))
            else:
                items.append((new_key, value))
        return dict(items)
    
    @staticmethod
    def safe_get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        安全地获取嵌套字典中的值
        
        Args:
            data: 数据字典
            path: 嵌套路径，如 'data.user.name'
            default: 默认值
            
        Returns:
            Any: 获取到的值或默认值
        """
        keys = path.split('.')
        result = data
        
        try:
            for key in keys:
                if isinstance(result, dict):
                    result = result.get(key)
                elif isinstance(result, list) and key.isdigit():
                    index = int(key)
                    result = result[index] if 0 <= index < len(result) else None
                else:
                    return default
                    
                if result is None:
                    return default
                    
            return result
        except Exception:
            return default