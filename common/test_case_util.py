"""
测试用例工具类
用于处理测试用例的加载、验证和管理
"""
import os
import yaml
from typing import Dict, Any, List, Optional
from common.logger import Logger
from config.config import Config


class TestCaseUtil:
    """测试用例工具类，提供测试用例的加载、验证和管理功能"""
    
    @staticmethod
    def load_test_cases(file_path: str) -> List[Dict[str, Any]]:
        """
        加载测试用例文件
        
        Args:
            file_path: 测试用例文件路径
            
        Returns:
            List[Dict[str, Any]]: 测试用例列表
        """
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(Config.TEST_CASES_DIR, file_path)
                
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"测试用例文件不存在: {file_path}")
                
            with open(file_path, 'r', encoding='utf-8') as f:
                test_cases = yaml.safe_load(f)
                
            if not isinstance(test_cases, list):
                raise ValueError("测试用例文件格式错误，应为列表格式")
                
            Logger.info(f"成功加载测试用例: {file_path}，共 {len(test_cases)} 个用例")
            return test_cases
            
        except Exception as e:
            Logger.error(f"加载测试用例失败: {str(e)}")
            raise
    
    @staticmethod
    def validate_test_case(test_case: Dict[str, Any]) -> bool:
        """
        验证测试用例格式
        
        Args:
            test_case: 测试用例字典
            
        Returns:
            bool: 验证结果
        """
        if not isinstance(test_case, dict):
            Logger.error("测试用例必须是字典格式")
            return False
            
        # 检查必需字段
        required_fields = ['name', 'request']
        for field in required_fields:
            if field not in test_case:
                Logger.error(f"测试用例缺少必需字段: {field}")
                return False
                
        # 检查request字段
        request = test_case['request']
        if not isinstance(request, dict):
            Logger.error("测试用例的request字段必须是字典格式")
            return False
            
        if 'url' not in request:
            Logger.error("测试用例的request字段缺少url")
            return False
            
        return True
    
    @staticmethod
    def get_test_case_info(test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取测试用例信息
        
        Args:
            test_case: 测试用例字典
            
        Returns:
            Dict[str, Any]: 测试用例信息
        """
        info = {
            'name': test_case.get('name', '未命名用例'),
            'description': test_case.get('description', ''),
            'method': test_case.get('request', {}).get('method', 'GET'),
            'url': test_case.get('request', {}).get('url', ''),
            'has_extract': 'extract' in test_case,
            'has_expect': 'expect' in test_case,
            'has_validate': 'validate' in test_case
        }
        return info
    
    @staticmethod
    def get_test_case_tags(test_case: Dict[str, Any]) -> List[str]:
        """
        获取测试用例标签
        
        Args:
            test_case: 测试用例字典
            
        Returns:
            List[str]: 标签列表
        """
        tags = test_case.get('tags', [])
        if not isinstance(tags, list):
            tags = [str(tags)]
        return tags
    
    @staticmethod
    def get_test_case_priority(test_case: Dict[str, Any]) -> Optional[int]:
        """
        获取测试用例优先级
        
        Args:
            test_case: 测试用例字典
            
        Returns:
            Optional[int]: 优先级，如果未设置则返回None
        """
        priority = test_case.get('priority')
        if priority is not None:
            try:
                return int(priority)
            except (ValueError, TypeError):
                Logger.warning(f"无效的优先级设置: {priority}，将使用默认优先级")
                return None
        return None
    
    @staticmethod
    def get_test_case_feature(test_case: Dict[str, Any]) -> str:
        """
        获取测试用例功能模块
        
        Args:
            test_case: 测试用例字典
            
        Returns:
            str: 功能模块名称
        """
        feature = test_case.get('feature', '默认功能')
        return str(feature)
    
    @staticmethod
    def filter_test_cases(test_cases: List[Dict[str, Any]], 
                          tags: List[str] = None, 
                          priority: int = None, 
                          feature: str = None) -> List[Dict[str, Any]]:
        """
        过滤测试用例
        
        Args:
            test_cases: 测试用例列表
            tags: 标签过滤
            priority: 优先级过滤
            feature: 功能模块过滤
            
        Returns:
            List[Dict[str, Any]]: 过滤后的测试用例列表
        """
        filtered_cases = []
        
        for test_case in test_cases:
            # 标签过滤
            if tags:
                case_tags = TestCaseUtil.get_test_case_tags(test_case)
                if not any(tag in case_tags for tag in tags):
                    continue
                    
            # 优先级过滤
            if priority is not None:
                case_priority = TestCaseUtil.get_test_case_priority(test_case)
                if case_priority != priority:
                    continue
                    
            # 功能模块过滤
            if feature:
                case_feature = TestCaseUtil.get_test_case_feature(test_case)
                if case_feature != feature:
                    continue
                    
            filtered_cases.append(test_case)
            
        return filtered_cases