"""
通用响应处理工具类
用于处理HTTP响应的格式化、分析和展示
"""
import json
import yaml
from typing import Dict, Any, Optional, Union
from xml.dom import minidom
from common.logger import Logger


class ResponseUtil:
    """响应处理工具类，提供响应格式化、分析和展示功能"""
    
    @staticmethod
    def format_response_body(response) -> str:
        """
        格式化响应体内容
        
        Args:
            response: HTTP响应对象
            
        Returns:
            str: 格式化后的响应体字符串
        """
        try:
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'application/json' in content_type:
                try:
                    json_data = response.json()
                    return json.dumps(json_data, ensure_ascii=False, indent=2)
                except ValueError:
                    return response.text
                    
            elif 'application/xml' in content_type or 'text/xml' in content_type:
                try:
                    xml_doc = minidom.parseString(response.text)
                    return xml_doc.toprettyxml(indent="  ")
                except Exception:
                    return response.text
                    
            else:
                return response.text
                
        except Exception as e:
            Logger.warning(f"格式化响应体时出错: {str(e)}")
            return response.text
    
    @staticmethod
    def format_response_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """
        格式化响应头
        
        Args:
            headers: 原始响应头字典
            
        Returns:
            Dict[str, str]: 格式化后的响应头字典
        """
        formatted_headers = {}
        for key, value in headers.items():
            formatted_headers[key] = value
        return formatted_headers
    
    @staticmethod
    def analyze_response_structure(response) -> Dict[str, Any]:
        """
        分析响应结构
        
        Args:
            response: HTTP响应对象
            
        Returns:
            Dict[str, Any]: 包含响应结构信息的字典
        """
        analysis = {
            "状态码": response.status_code,
            "响应头": dict(response.headers),
            "内容类型": response.headers.get('Content-Type', '未知'),
            "响应大小": len(response.content),
            "响应时间": getattr(response, 'elapsed', None)
        }
        
        try:
            if 'application/json' in response.headers.get('Content-Type', '').lower():
                json_data = response.json()
                analysis["数据结构"] = ResponseUtil._get_json_structure(json_data)
        except Exception:
            analysis["数据结构"] = "无法解析JSON"
            
        return analysis
    
    @staticmethod
    def _get_json_structure(data, max_depth=3, current_depth=0) -> Union[Dict, list, str]:
        """
        递归获取JSON数据结构
        
        Args:
            data: JSON数据
            max_depth: 最大递归深度
            current_depth: 当前递归深度
            
        Returns:
            Union[Dict, list, str]: JSON结构描述
        """
        if current_depth >= max_depth:
            return "..."
            
        if isinstance(data, dict):
            structure = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    structure[key] = ResponseUtil._get_json_structure(value, max_depth, current_depth + 1)
                elif isinstance(value, list):
                    if value:
                        structure[key] = [ResponseUtil._get_json_structure(value[0], max_depth, current_depth + 1)]
                    else:
                        structure[key] = []
                else:
                    structure[key] = type(value).__name__
            return structure
        elif isinstance(data, list):
            if data:
                return [ResponseUtil._get_json_structure(data[0], max_depth, current_depth + 1)]
            else:
                return []
        else:
            return type(data).__name__
    
    @staticmethod
    def create_comparison_table(expected: Dict[str, Any], actual: Dict[str, Any], status: str = "FAIL") -> str:
        """
        创建期望值与实际值的对比表格 - 优化格式
        
        Args:
            expected: 期望结果
            actual: 实际结果
            status: 对比状态
            
        Returns:
            str: 格式化的对比表格
        """
        table = "\n" + "=" * 80 + "\n"
        table += "📊 断言对比详情".center(80) + "\n"
        table += "=" * 80 + "\n\n"
        
        # 表头 - 增加列宽和间距
        header = f"{'字段名':<30} | {'期望值':<20} | {'实际值':<20} | {'状态':<8}"
        table += header + "\n"
        table += "-" * len(header) + "\n"
        
        # 比较每个字段
        for key, exp_value in expected.items():
            act_value = actual.get(key, "不存在")
            field_status = "✅ PASS" if str(exp_value) == str(act_value) else "❌ FAIL"
            
            # 格式化值，确保不会太长
            exp_str = str(exp_value)[:18] + "..." if len(str(exp_value)) > 18 else str(exp_value)
            act_str = str(act_value)[:18] + "..." if len(str(act_value)) > 18 else str(act_value)
            
            table += f"{key:<30} | {exp_str:<20} | {act_str:<20} | {field_status:<8}\n"
        
        table += "\n" + "=" * 80 + "\n"
        return table
    
    @staticmethod
    def create_success_table(expected: Dict[str, Any], actual: Dict[str, Any]) -> str:
        """
        创建成功断言的表格 - 优化格式
        
        Args:
            expected: 期望值字典
            actual: 实际值字典
            
        Returns:
            str: 格式化的成功表格
        """
        table = "\n" + "=" * 80 + "\n"
        table += "🎉 所有断言通过！".center(80) + "\n"
        table += "=" * 80 + "\n\n"
        
        # 表头
        header = f"{'字段名':<30} | {'期望值':<20} | {'实际值':<20} | {'状态':<8}"
        table += header + "\n"
        table += "-" * len(header) + "\n"
        
        # 比较每个字段
        for key, exp_value in expected.items():
            act_value = actual.get(key, "不存在")
            
            # 格式化值，确保不会太长
            exp_str = str(exp_value)[:18] + "..." if len(str(exp_value)) > 18 else str(exp_value)
            act_str = str(act_value)[:18] + "..." if len(str(act_value)) > 18 else str(act_value)
            
            table += f"{key:<30} | {exp_str:<20} | {act_str:<20} | {'✅ PASS':<8}\n"
        
        table += "\n" + "✅ 所有验证项均通过测试！".center(80) + "\n"
        table += "=" * 80 + "\n"
        return table
    
    @staticmethod
    def create_failure_table(expected: Dict[str, Any], actual: Dict[str, Any], error_msg: str) -> str:
        """
        创建失败断言的表格 - 优化格式
        
        Args:
            expected: 期望值字典
            actual: 实际值字典
            error_msg: 错误信息
            
        Returns:
            str: 格式化的失败表格
        """
        table = "\n" + "=" * 80 + "\n"
        table += "🚨 断言失败".center(80) + "\n"
        table += "=" * 80 + "\n\n"
        
        # 错误信息
        table += f"错误信息: {error_msg}\n\n"
        
        # 表头
        header = f"{'字段名':<30} | {'期望值':<20} | {'实际值':<20} | {'状态':<8}"
        table += header + "\n"
        table += "-" * len(header) + "\n"
        
        # 比较每个字段
        for key, exp_value in expected.items():
            act_value = actual.get(key, "不存在")
            is_pass = str(exp_value) == str(act_value)
            status = "✅ PASS" if is_pass else "❌ FAIL"
            
            # 格式化值，确保不会太长
            exp_str = str(exp_value)[:18] + "..." if len(str(exp_value)) > 18 else str(exp_value)
            act_str = str(act_value)[:18] + "..." if len(str(act_value)) > 18 else str(act_value)
            
            table += f"{key:<30} | {exp_str:<20} | {act_str:<20} | {status:<8}\n"
        
        table += "\n" + "❌ 请检查上述标记为失败的字段".center(80) + "\n"
        table += "=" * 80 + "\n"
        return table
    
    @staticmethod
    def extract_actual_results(response, expect_config):
        """
        从响应中提取实际结果
        
        Args:
            response: HTTP响应对象
            expect_config: 期望配置
            
        Returns:
            Dict: 包含实际结果的字典
        """
        actual_results = {}
        
        try:
            # 提取状态码
            if "status_code" in expect_config:
                actual_results["status_code"] = response.status_code
            
            # 提取响应体
            if "body" in expect_config:
                try:
                    response_data = response.json()
                    # 递归提取期望的字段
                    actual_results["body"] = ResponseUtil._extract_fields_recursive(
                        response_data, expect_config["body"]
                    )
                except ValueError:
                    actual_results["body"] = response.text
            
            # 提取响应头
            if "headers" in expect_config:
                actual_results["headers"] = {}
                for header_name in expect_config["headers"].keys():
                    actual_results["headers"][header_name] = response.headers.get(header_name)
                    
        except Exception as e:
            Logger.error(f"提取实际结果时出错: {str(e)}")
            actual_results["error"] = str(e)
            
        return actual_results
    
    @staticmethod
    def _extract_fields_recursive(data, expected_fields):
        """
        递归提取期望的字段
        
        Args:
            data: 原始数据
            expected_fields: 期望提取的字段结构
            
        Returns:
            Dict: 提取的字段数据
        """
        if isinstance(expected_fields, dict):
            result = {}
            for key, value in expected_fields.items():
                if key in data:
                    if isinstance(value, dict):
                        result[key] = ResponseUtil._extract_fields_recursive(data[key], value)
                    else:
                        result[key] = data[key]
                else:
                    result[key] = None
            return result
        else:
            return data
    
    @staticmethod
    def safe_decode_request_body(body) -> str:
        """
        安全解码请求体
        
        Args:
            body: 请求体数据
            
        Returns:
            str: 解码后的请求体字符串
        """
        if not body:
            return '无'
        try:
            return body.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            return str(body)