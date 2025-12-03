import functools
import time
import traceback
from common.logger import Logger


class LogDecorator:
    """日志装饰器类，用于减少重复的日志记录代码"""
    
    @staticmethod
    def log_function_call(include_args=False, include_result=False, log_level="info"):
        """
        记录函数调用的装饰器
        
        参数:
            include_args (bool): 是否记录函数参数
            include_result (bool): 是否记录函数返回值
            log_level (str): 日志级别，可选值: debug, info, warning, error
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 获取日志方法
                log_method = getattr(Logger, log_level.lower(), Logger.info)
                
                # 记录函数开始
                func_name = func.__name__
                class_name = ""
                if args and hasattr(args[0], '__class__'):
                    class_name = args[0].__class__.__name__ + "."
                
                start_msg = f"开始执行 {class_name}{func_name}"
                if include_args:
                    start_msg += f" - 参数: args={args}, kwargs={kwargs}"
                
                log_method(start_msg)
                
                # 记录执行时间
                start_time = time.time()
                
                try:
                    # 执行函数
                    result = func(*args, **kwargs)
                    
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 记录函数完成
                    end_msg = f"完成执行 {class_name}{func_name} - 耗时: {duration:.3f}秒"
                    if include_result:
                        end_msg += f" - 返回值: {result}"
                    
                    log_method(end_msg)
                    
                    return result
                    
                except Exception as e:
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 记录异常
                    error_msg = f"执行 {class_name}{func_name} 时发生异常 - 耗时: {duration:.3f}秒 - 错误: {str(e)}"
                    Logger.error(error_msg)
                    
                    # 记录详细堆栈信息
                    Logger.debug(f"异常堆栈: {traceback.format_exc()}")
                    
                    # 重新抛出异常
                    raise
                    
            return wrapper
        return decorator
    
    @staticmethod
    def log_test_case(test_name=None):
        """
        测试用例日志装饰器
        
        参数:
            test_name (str): 测试用例名称，如果为None则使用函数名
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 获取测试名称
                name = test_name or func.__name__
                
                # 记录测试开始
                Logger.info(f"开始执行测试用例: {name}")
                start_time = time.time()
                
                try:
                    # 执行测试
                    result = func(*args, **kwargs)
                    
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 记录测试成功
                    Logger.success(f"测试用例执行成功: {name} - 耗时: {duration:.3f}秒")
                    
                    return result
                    
                except Exception as e:
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 记录测试失败
                    Logger.error(f"测试用例执行失败: {name} - 耗时: {duration:.3f}秒 - 错误: {str(e)}")
                    
                    # 重新抛出异常
                    raise
                    
            return wrapper
        return decorator
    
    @staticmethod
    def log_api_request():
        """
        API请求日志装饰器
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 尝试从参数中提取请求信息
                url = "未知"
                method = "未知"
                
                try:
                    if args and isinstance(args[1], dict):
                        case_info = args[1]
                        url = case_info.get('url', '未知')
                        method = case_info.get('method', '未知')
                except (IndexError, AttributeError, TypeError):
                    pass
                
                # 记录请求开始
                Logger.info(f"发送API请求: {method} {url}")
                start_time = time.time()
                
                try:
                    # 执行请求
                    result = func(*args, **kwargs)
                    
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 尝试获取响应状态码
                    status_code = "未知"
                    try:
                        if hasattr(result, 'status_code'):
                            status_code = result.status_code
                    except AttributeError:
                        pass
                    
                    # 记录请求成功
                    Logger.info(f"API请求完成: {method} {url} - 状态码: {status_code} - 耗时: {duration:.3f}秒")
                    
                    return result
                    
                except Exception as e:
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 记录请求失败
                    Logger.error(f"API请求失败: {method} {url} - 耗时: {duration:.3f}秒 - 错误: {str(e)}")
                    
                    # 重新抛出异常
                    raise
                    
            return wrapper
        return decorator
    
    @staticmethod
    def log_performance(operation_name=None):
        """
        性能监控日志装饰器
        
        参数:
            operation_name (str): 操作名称，如果为None则使用函数名
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 获取操作名称
                name = operation_name or func.__name__
                
                # 记录操作开始
                Logger.debug(f"开始性能监控: {name}")
                start_time = time.time()
                
                try:
                    # 执行操作
                    result = func(*args, **kwargs)
                    
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 根据执行时间记录不同级别的日志
                    if duration < 1.0:
                        Logger.debug(f"性能监控: {name} - 耗时: {duration:.3f}秒 (快速)")
                    elif duration < 5.0:
                        Logger.info(f"性能监控: {name} - 耗时: {duration:.3f}秒 (正常)")
                    else:
                        Logger.warning(f"性能监控: {name} - 耗时: {duration:.3f}秒 (较慢)")
                    
                    return result
                    
                except Exception as e:
                    # 计算执行时间
                    duration = time.time() - start_time
                    
                    # 记录操作失败
                    Logger.error(f"性能监控: {name} - 耗时: {duration:.3f}秒 - 错误: {str(e)}")
                    
                    # 重新抛出异常
                    raise
                    
            return wrapper
        return decorator


# 便捷函数
def log_function(include_args=False, include_result=False, log_level="info"):
    """便捷函数：记录函数调用"""
    return LogDecorator.log_function_call(include_args, include_result, log_level)


def log_test(test_name=None):
    """便捷函数：记录测试用例"""
    return LogDecorator.log_test_case(test_name)


def log_api():
    """便捷函数：记录API请求"""
    return LogDecorator.log_api_request()


def log_perf(operation_name=None):
    """便捷函数：记录性能监控"""
    return LogDecorator.log_performance(operation_name)