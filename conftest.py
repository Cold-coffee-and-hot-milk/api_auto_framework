import pytest
import yaml
from pathlib import Path
from common.logger import Logger
from fixtures.request_fixture import request_fixture
import re
import allure
from io import StringIO
import logging

# ========== 新增功能：彩色日志支持 ==========
def ansi_to_html(text):
    """将ANSI颜色代码转换为HTML样式"""
    # ANSI颜色代码到HTML的映射
    ansi_colors = {
        '30': 'color:black',
        '31': 'color:red',
        '32': 'color:green',
        '33': 'color:orange',
        '34': 'color:blue',
        '35': 'color:magenta',
        '36': 'color:cyan',
        '37': 'color:white',
        '40': 'background-color:black',
        '41': 'background-color:red',
        '42': 'background-color:green',
        '43': 'background-color:orange',
        '44': 'background-color:blue',
        '45': 'background-color:magenta',
        '46': 'background-color:cyan',
        '47': 'background-color:white',
        '1': 'font-weight:bold',  # 粗体
        '4': 'text-decoration:underline',  # 下划线
    }
    
    # 替换ANSI转义码
    def replace_ansi(match):
        codes = match.group(1).split(';')
        styles = []
        for code in codes:
            if code in ansi_colors:
                styles.append(ansi_colors[code])
        return f'<span style="{";".join(styles)}">' if styles else '<span>'
    
    # 处理ANSI转义序列
    text = re.sub(r'\x1b\[([\d;]+)m', replace_ansi, text)
    text = text.replace('\x1b[0m', '</span>')
    
    # 保留换行符
    text = text.replace('\n', '<br>')
    
    # 添加HTML包装
    return f'<div style="font-family: monospace; white-space: pre;">{text}</div>'

# 创建日志捕获器
log_capture = StringIO()
log_handler = None

def setup_colored_logging():
    """配置带颜色的日志捕获"""
    global log_handler
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 如果已经存在捕获处理器，先移除
    if log_handler:
        root_logger.removeHandler(log_handler)
    
    # 创建新的捕获处理器
    log_capture = StringIO()
    log_handler = logging.StreamHandler(log_capture)
    
    # 使用与common.logger.Logger相同的格式
    log_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    root_logger.addHandler(log_handler)
    return log_capture

# ========== 原有功能保持不变 ==========
def pytest_collect_file(file_path, parent):
    """安全识别YAML测试文件"""
    if file_path.suffix == ".yaml" and "test_cases" in str(file_path):
        return YamlFile.from_parent(parent, path=file_path)

class YamlFile(pytest.File):
    """增强安全性的YAML测试加载器"""

    def collect(self):
        try:
            with open(self.path) as f:
                test_cases = yaml.safe_load(f) or []

                for idx, case in enumerate(test_cases):
                    if not isinstance(case, dict):
                        Logger.warning(f"忽略非字典类型的用例: {self.path} 第{idx + 1}条")
                        continue

                    item = YamlItem.from_parent(
                        self,
                        name=f"{self.path.stem}-{idx}_{case.get('name', 'unnamed')}",
                        spec=case
                    )

                    # 确保fixture系统正确初始化
                    if hasattr(self.parent.session, '_fixturemanager'):
                        item._fixtureinfo = self.parent.session._fixturemanager.getfixtureinfo(
                            node=item, func=item.runtest, cls=None
                        )
                    yield item

        except yaml.YAMLError as e:
            pytest.fail(f"YAML文件解析失败: {self.path}\n错误详情: {str(e)}")
        except Exception as e:
            pytest.fail(f"用例加载异常: {str(e)}")

class YamlItem(pytest.Item):
    """完全兼容pytest的增强测试项"""

    def __init__(self, name, parent, spec):
        super().__init__(name, parent)
        self.spec = spec
        self.fixturenames = []
        self._validate_spec()

    def _validate_spec(self):
        """验证用例必需字段（保留原有验证逻辑）"""
        required_fields = {
            'request': {
                'url': str,
                'method': str
            }
        }

        for field, checker in required_fields.items():
            if field not in self.spec:
                pytest.fail(f"测试用例缺少必需字段: {field} (用例: {self.name})")

            if isinstance(checker, dict):
                for sub_field, sub_type in checker.items():
                    if sub_field not in self.spec[field]:
                        pytest.fail(f"测试用例缺少必需字段: {field}.{sub_field} (用例: {self.name})")
                    if not isinstance(self.spec[field][sub_field], sub_type):
                        pytest.fail(f"字段类型错误: {field}.{sub_field} 应为 {sub_type} (用例: {self.name})")

    def runtest(self):
        """增强的测试执行逻辑"""
        try:
            from common.request_util import RequestUtil
            from common.extract_util import ExtractUtil

            request_spec = self.spec.get('request', {})
            if not request_spec:
                pytest.fail("测试用例缺少request配置")

            # 执行请求
            response = RequestUtil.send_request(request_spec)

            # ========== 增强的断言逻辑 ==========
            expected_status = request_spec.get('expected_status', 200)
            if response.status_code != expected_status:
                # 构建详细的错误信息
                request = response.request
                error_details = {
                    '预期状态码': expected_status,
                    '实际状态码': response.status_code,
                    '请求URL': request.url,
                    '请求方法': request.method,
                    '请求头': dict(request.headers),
                    '请求数据': self._safe_decode_request_body(request.body),
                    '响应头': dict(response.headers),
                    '响应内容': response.text[:1000]  # 限制长度防止日志过大
                }

                # 格式化错误信息
                error_msg = "\n".join(
                    f"{k}: {v}" for k, v in error_details.items()
                )
                pytest.fail(f"状态码断言失败:\n{error_msg}")

            # 保留原有的变量提取功能
            if "extract" in self.spec and isinstance(self.spec["extract"], dict):
                ExtractUtil.extract_values(response, self.spec["extract"])

        except Exception as e:
            pytest.fail(f"测试执行异常: {str(e)}")

    def _safe_decode_request_body(self, body):
        """安全解码请求体"""
        if not body:
            return '无'
        try:
            return body.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            return str(body)

# ========== 原有功能保持不变 ==========
def pytest_collection_modifyitems(items):
    """安全地为所有测试项添加fixture"""
    for item in items:
        if hasattr(item, 'fixturenames'):
            if 'request_fixture' not in item.fixturenames:
                item.fixturenames.append('request_fixture')

# ========== 修改钩子函数以添加彩色日志 ==========
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """保留原有日志功能并添加彩色日志附件"""
    outcome = yield
    rep = outcome.get_result()

    # 在测试执行阶段结束时添加日志附件
    if rep.when == 'call' and rep.outcome != 'skipped':
        # 获取捕获的日志内容
        log_content = log_capture.getvalue()
        if log_content:
            # 转换为HTML格式
            html_log = ansi_to_html(log_content)
            
            # 添加到Allure报告
            allure.attach(
                html_log,
                name="彩色测试日志",
                attachment_type=allure.attachment_type.HTML
            )
        
        # 重置日志捕获器
        log_capture.truncate(0)
        log_capture.seek(0)

    # 保留原有的日志记录功能
    if rep.when == 'call':
        try:
            case_name = getattr(item, 'name', '未命名用例')
            if rep.failed:
                Logger.error(f"用例执行失败: {case_name}")
                err_msg = str(getattr(rep, 'longrepr', '未知错误'))
                Logger.error(f"失败原因: {err_msg[:500]}")
            else:
                Logger.success(f"用例执行成功: {case_name}")
        except Exception as e:
            print(f"⚠️ 日志记录失败: {str(e)}")

# ========== 新增fixture用于设置日志捕获 ==========
@pytest.fixture(scope="session", autouse=True)
def setup_log_capture():
    """设置全局日志捕获"""
    setup_colored_logging()
    yield

# ========== 原有fixture保持不变 ==========
@pytest.fixture(autouse=True)
def auto_clean_extract():
    """保留自动清理功能"""
    from common.extract_util import ExtractUtil
    yield
    ExtractUtil.clear_extract_data()
