"""
变量管理工具类
用于处理环境变量、全局变量和测试变量的管理
"""
import os
from typing import Dict, Any, Optional, List
from common.logger import Logger
from config.config import Config
import globals


class VariableUtil:
    """变量管理工具类，提供环境变量、全局变量和测试变量的管理功能"""
    
    @staticmethod
    def load_env_variables(env_name: str = None) -> Dict[str, Any]:
        """
        加载环境变量
        
        Args:
            env_name: 环境名称，如果为None则使用默认环境
            
        Returns:
            Dict[str, Any]: 环境变量字典
        """
        try:
            env_config = Config.get_env_config(env_name)
            Logger.info(f"成功加载环境变量: {env_name or '默认环境'}")
            return env_config
        except Exception as e:
            Logger.error(f"加载环境变量失败: {str(e)}")
            return {}
    
    @staticmethod
    def set_global_variable(key: str, value: Any) -> None:
        """
        设置全局变量
        
        Args:
            key: 变量名
            value: 变量值
        """
        globals.ENV_VARS[key] = value
        Logger.debug(f"设置全局变量: {key} = {value}")
    
    @staticmethod
    def get_global_variable(key: str, default: Any = None) -> Any:
        """
        获取全局变量
        
        Args:
            key: 变量名
            default: 默认值
            
        Returns:
            Any: 变量值
        """
        return globals.ENV_VARS.get(key, default)
    
    @staticmethod
    def get_all_global_variables() -> Dict[str, Any]:
        """
        获取所有全局变量
        
        Returns:
            Dict[str, Any]: 全局变量字典
        """
        return globals.ENV_VARS.copy()
    
    @staticmethod
    def clear_global_variables() -> None:
        """
        清空所有全局变量
        """
        globals.ENV_VARS.clear()
        Logger.info("已清空所有全局变量")
    
    @staticmethod
    def merge_variables(*var_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并多个变量字典
        
        Args:
            *var_dicts: 要合并的变量字典
            
        Returns:
            Dict[str, Any]: 合并后的变量字典
        """
        merged = {}
        for var_dict in var_dicts:
            if var_dict and isinstance(var_dict, dict):
                merged.update(var_dict)
        return merged
    
    @staticmethod
    def get_all_variables(include_env: bool = True, 
                         include_global: bool = True, 
                         include_os: bool = True) -> Dict[str, Any]:
        """
        获取所有可用变量
        
        Args:
            include_env: 是否包含环境配置变量
            include_global: 是否包含全局变量
            include_os: 是否包含系统环境变量
            
        Returns:
            Dict[str, Any]: 所有可用变量字典
        """
        all_vars = {}
        
        # 环境配置变量
        if include_env:
            env_vars = VariableUtil.load_env_variables()
            all_vars.update(env_vars)
        
        # 全局变量
        if include_global:
            global_vars = VariableUtil.get_all_global_variables()
            all_vars.update(global_vars)
        
        # 系统环境变量
        if include_os:
            os_vars = dict(os.environ)
            all_vars.update(os_vars)
        
        return all_vars
    
    @staticmethod
    def validate_variable_name(name: str) -> bool:
        """
        验证变量名是否有效
        
        Args:
            name: 变量名
            
        Returns:
            bool: 是否有效
        """
        if not name or not isinstance(name, str):
            return False
        
        # 变量名不能以数字开头，只能包含字母、数字和下划线
        import re
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def mask_sensitive_variables(var_dict: Dict[str, Any], 
                                 sensitive_keys: List[str] = None) -> Dict[str, Any]:
        """
        屏蔽敏感变量
        
        Args:
            var_dict: 变量字典
            sensitive_keys: 敏感变量名列表，如果为None则使用默认列表
            
        Returns:
            Dict[str, Any]: 屏蔽敏感变量后的字典
        """
        if sensitive_keys is None:
            sensitive_keys = ['password', 'token', 'secret', 'key', 'auth', 'passwd']
        
        masked_vars = {}
        for key, value in var_dict.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                # 屏蔽敏感变量值
                if value is not None:
                    masked_vars[key] = '*' * min(20, len(str(value)))
                else:
                    masked_vars[key] = None
            else:
                masked_vars[key] = value
        
        return masked_vars
    
    @staticmethod
    def get_variable_value(key: str, 
                          default: Any = None, 
                          include_env: bool = True, 
                          include_global: bool = True, 
                          include_os: bool = True) -> Any:
        """
        获取变量值，按优先级从不同来源查找
        
        Args:
            key: 变量名
            default: 默认值
            include_env: 是否包含环境配置变量
            include_global: 是否包含全局变量
            include_os: 是否包含系统环境变量
            
        Returns:
            Any: 变量值
        """
        # 按优先级查找：全局变量 > 环境配置变量 > 系统环境变量
        
        if include_global:
            global_value = VariableUtil.get_global_variable(key)
            if global_value is not None:
                return global_value
        
        if include_env:
            env_vars = VariableUtil.load_env_variables()
            if key in env_vars:
                return env_vars[key]
        
        if include_os and key in os.environ:
            return os.environ[key]
        
        return default