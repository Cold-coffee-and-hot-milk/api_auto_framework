import pytest
import yaml
from pathlib import Path
from common.logger import Logger
from fixtures.request_fixture import request_fixture


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


# ========== 保留原有功能 ==========
def pytest_collection_modifyitems(items):
    """安全地为所有测试项添加fixture"""
    for item in items:
        if hasattr(item, 'fixturenames'):
            if 'request_fixture' not in item.fixturenames:
                item.fixturenames.append('request_fixture')


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """保留原有日志功能"""
    outcome = yield
    rep = outcome.get_result()

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


@pytest.fixture(autouse=True)
def auto_clean_extract():
    """保留自动清理功能"""
    from common.extract_util import ExtractUtil
    yield
    ExtractUtil.clear_extract_data()