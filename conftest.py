
import os
import sys
import platform
from datetime import datetime
import pytest
import yaml
import allure
import logging
import json
import re
from pathlib import Path
from common.logger import Logger
from fixtures.request_fixture import request_fixture
from common.log_decorator import log_function, log_test
import globals  # 导入全局变量模块


@log_function()
def _fix_environment_encoding():
    """修复环境编码问题 - 安全版本"""
    try:
        import locale
        import sys
        import os

        # 1. 设置环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['LANG'] = 'en_US.UTF-8'
        os.environ['LC_ALL'] = 'en_US.UTF-8'

        # 2. 尝试设置locale
        try:
            # 尝试设置UTF-8 locale
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error:
            try:
                # 回退到C.UTF-8
                locale.setlocale(locale.LC_ALL, 'C.UTF-8')
            except:
                # 最终回退
                Logger.warning("无法设置locale为UTF-8，使用系统默认")

        # 3. 修复标准输出流的编码
        try:
            # Python 3.7+ 方法
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8')
        except:
            try:
                # 旧版本Python的回退方法
                sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
                sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)
            except Exception as e:
                Logger.warning(f"无法重新配置标准流编码: {str(e)}")

        # 4. 设置文件系统编码
        try:
            sys.getfilesystemencoding = lambda: 'utf-8'
        except:
            pass

        Logger.info("环境编码已设置为UTF-8")

    except Exception as e:
        Logger.warning(f"设置编码失败: {str(e)}")


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="覆盖当前环境配置: test 或 pre_release"
    )


@log_function()
def pytest_configure(config):
    """配置初始化"""
    # 修复编码问题
    _fix_environment_encoding()

    # 获取命令行参数
    env_name = config.getoption("--env")

    # 加载环境变量
    from config.config import Config  # 延迟导入以避免循环导入问题
    env_config = Config.get_env_config()

    # 如果命令行指定了环境，覆盖当前配置
    if env_name:
        # 重新加载环境配置
        env_file = os.path.join(Config.CONFIG_DIR, 'env_config.yaml')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                env_data = yaml.safe_load(f) or {}

            # 使用命令行指定的环境
            globals.ENV_VARS = env_data.get(env_name, {})
            Logger.info(f"使用命令行指定环境: {env_name}, 配置: {globals.ENV_VARS}")
        else:
            globals.ENV_VARS = env_config
            Logger.warning(f"环境配置文件不存在, 使用默认配置")
    else:
        globals.ENV_VARS = env_config
        Logger.info(f"使用默认环境配置: {globals.ENV_VARS}")
    # 打印加载的环境变量
    Logger.debug(f"加载的环境变量: {globals.ENV_VARS}")

    # 记录环境信息到Allure报告
    _record_environment_info(globals.ENV_VARS, config)

    # 其他配置...
    config.addinivalue_line("markers", "priority(value): 设置测试用例优先级")
    config.addinivalue_line("markers", "feature(name): 设置测试功能模块")

    try:
        log_level = config.getoption("--log-level", "INFO")
        if log_level and hasattr(logging, log_level.upper()):
            logging.getLogger().setLevel(log_level.upper())
        else:
            logging.getLogger().setLevel(logging.INFO)
    except Exception as e:
        Logger.warning(f"设置日志级别失败: {str(e)}")
        logging.getLogger().setLevel(logging.INFO)

    Logger.info("pytest配置初始化完成")


@log_function()
def _record_environment_info(env_vars, config):
    """记录环境信息到Allure报告"""
    try:
        # 创建环境信息字典 - 使用英文键名避免乱码
        environment_info = {
            "Test Environment": "Default" if not config.getoption("--env") else f"Custom: {config.getoption('--env')}",
            "Base URL": env_vars.get("base_url", "Not configured"),
            "Username": env_vars.get("username", "Not configured"),
            "Project Path": str(Path.cwd()),
            "Python Version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "Operating System": f"{platform.system()} {platform.release()}",
            "Execution Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Pytest Version": pytest.__version__
        }

        # 安全处理密码信息（脱敏显示）
        if "password" in env_vars:
            password = env_vars["password"]
            environment_info["Password"] = f"{password[:2]}***{password[-2:]}" if len(password) > 4 else "***"

        # 将环境信息写入Allure环境文件
        allure_report_dir = config.getoption("--allure-report-dir", "reports/allure_results")
        os.makedirs(allure_report_dir, exist_ok=True)

        # 创建environment.properties文件
        env_properties_file = os.path.join(allure_report_dir, "environment.properties")
        with open(env_properties_file, 'w', encoding='utf-8') as f:
            for key, value in environment_info.items():
                # 确保所有值都是字符串
                f.write(f"{key}={str(value)}\n")
    except Exception as e:
        Logger.warning(f"记录环境信息失败: {str(e)}")

def pytest_collect_file(file_path, parent):
    """安全识别YAML测试文件 - 修复重复收集问题"""
    # 确保只收集特定目录下的yaml文件，避免重复收集
    if file_path.suffix == ".yaml" and str(file_path).startswith(str(Path.cwd() / "data" / "test_cases")):
        # 使用绝对路径确保唯一性
        return YamlFile.from_parent(parent, path=file_path)



class YamlFile(pytest.File):
    """增强安全性的YAML测试加载器"""

    def collect(self):
        """收集测试用例，统一处理异常和fixture初始化"""
        try:
            test_cases = self._load_and_validate_yaml()

            for idx, case in enumerate(test_cases):
                item = self._create_yaml_item(idx, case)
                self._setup_fixture_info(item)
                yield item


        except yaml.YAMLError as e:
            pytest.fail(f"YAML文件解析失败: {self.path}\n错误详情: {str(e)}")
        except Exception as e:
            pytest.fail(f"用例加载异常: {str(e)}")

    def _load_and_validate_yaml(self):
        """加载并验证YAML文件内容"""
        with open(self.path, 'r', encoding='utf-8') as f:
            test_cases = yaml.safe_load(f) or []

        if not isinstance(test_cases, list):
            Logger.warning(f"YAML文件根元素应为列表: {self.path}")
            return []

        return test_cases

    def _create_yaml_item(self, idx, case):
        """创建YAML测试项 - 确保用例名称唯一性"""
        if not isinstance(case, dict):
            Logger.warning(f"忽略非字典类型的用例: {self.path} 第{idx + 1}条")
            case = {'name': f'invalid_case_{idx}', 'invalid': True}

        # 使用更唯一的命名方式，包含文件的相对路径，避免不同目录下同名文件导致的冲突
        rel_path = str(self.path.relative_to(Path.cwd() / "data" / "test_cases")).replace("/", "_")
        unique_name = f"{rel_path}-{idx}_{case.get('name', 'unnamed')}"

        return YamlItem.from_parent(
            self,
            name=unique_name,
            spec=case
        )

    def _setup_fixture_info(self, item):
        """
        统一设置fixture信息：标是在测试执行前动态收集并注入测试所需的依赖项（fixtures），确保测试运行时能正确访问预定义的 fixture 资源
        """
        if hasattr(self.parent.session, '_fixturemanager'):
            item._fixtureinfo = self.parent.session._fixturemanager.getfixtureinfo(
                node=item, func=item.runtest, cls=None
            )


class YamlItem(pytest.Item):
    """完全兼容pytest的增强测试项"""

    def __init__(self, name, parent, spec):
        super().__init__(name, parent)
        self.spec = spec
        self._validate_spec()
        self.feature = self.spec.get("feature", "默认模块")
        self.priority = self.spec.get("priority")

    @log_function()
    def _replace_env_vars(self):
        """替换环境变量"""
        # 直接使用 globals.ENV_VARS 而不是从 conftest 导入
        env_vars = globals.ENV_VARS

        # 递归替换变量
        self.spec = self._replace_vars_recursive(self.spec, env_vars)

    @log_function()
    def _replace_vars_recursive(self, data, env_vars):
        """递归替换变量"""
        if isinstance(data, dict):
            return {k: self._replace_vars_recursive(v, env_vars) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_vars_recursive(item, env_vars) for item in data]
        elif isinstance(data, str):
            return self._replace_var_in_string(data)
        return data

    @log_function()
    def _replace_var_in_string(self, value):
        """替换字符串中的变量"""
        if not isinstance(value, str):
            return value

        # 匹配 ${var} 格式的变量
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)

        if not matches:
            return value

        for var_name in matches:
            if var_name in globals.ENV_VARS:
                var_value = globals.ENV_VARS[var_name]
                value = value.replace(f'${{{var_name}}}', str(var_value))
            else:
                Logger.warning(f"未定义的环境变量: {var_name} (用例: {self.name})")

        return value

    def _validate_spec(self):
        """验证用例必需字段"""
        if self.spec.get('invalid'):
            return
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

    @log_test()
    def runtest(self):
        """增强的测试执行逻辑"""
        # 在执行测试前，先显示环境信息
        self._display_environment_info()

        # 在执行测试前，先替换用例中的变量
        self._replace_env_vars()
        # 打印替换后的用例配置
        Logger.debug(f"替换后的用例配置: {json.dumps(self.spec, indent=2)}")

        if self.spec.get('invalid'):
            pytest.skip("无效的测试用例格式")

        # 添加Allure动态描述和标题
        description = self.spec.get('description', '')
        allure.dynamic.description(description)
        allure.dynamic.title(self.name)

        try:
            from common.request_util import RequestUtil
            from common.extract_util import ExtractUtil
            # 准备测试环境
            with allure.step("准备测试环境"):
                ExtractUtil.clear_extract_data()
                # 显示详细的环境信息
                self._attach_environment_details()

                Logger.info("测试环境准备完成")
                allure.attach(
                    "测试环境初始化完成",
                    name="环境准备",
                    attachment_type=allure.attachment_type.TEXT
                )

            request_spec = self.spec.get('request', {})
            if not request_spec:
                pytest.fail("测试用例缺少request配置")

            # 执行请求
            response = self._execute_and_validate_request(request_spec)

            # 变量提取
            self._handle_extraction(response)

            # 关键修复：确保验证步骤始终执行
            self._handle_assertions(response)

        except Exception as e:
            allure.attach(
                str(e),
                name="错误信息",
                attachment_type=allure.attachment_type.TEXT
            )
            pytest.fail(f"测试执行异常: {str(e)}")

    @log_function()
    def _display_environment_info(self):
        """在测试开始时显示环境信息"""
        env_info = {
            "当前环境": "默认环境" if not hasattr(self.config, 'env_name') else self.config.env_name,
            "基础URL": globals.ENV_VARS.get("base_url", "未配置"),
            "测试用户": globals.ENV_VARS.get("username", "未配置"),
            "用例文件": str(self.path) if hasattr(self, 'path') else "未知"
        }

        # 安全显示密码
        if "password" in globals.ENV_VARS:
            pwd = globals.ENV_VARS["password"]
            env_info["用户密码"] = f"{pwd[:2]}***{pwd[-2:]}" if len(pwd) > 4 else "***"

        Logger.info("=" * 50)
        Logger.info("📋 测试环境信息")
        for key, value in env_info.items():
            Logger.info(f"  {key}: {value}")
        Logger.info("=" * 50)

    @log_function()
    def _attach_environment_details(self):
        """附加详细的环境信息到Allure报告"""
        try:
            # 系统环境信息
            system_info = {
                "操作系统": f"{platform.system()} {platform.release()}",
                "Python版本": sys.version,
                "工作目录": str(Path.cwd()),
                "执行时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 测试环境信息
            test_env_info = {
                "基础URL": globals.ENV_VARS.get("base_url", "未配置"),
                "用户名": globals.ENV_VARS.get("username", "未配置"),
                "环境配置文件": "env_config.yaml",
                "测试用例": self.name
            }

            # 安全处理密码
            if "password" in globals.ENV_VARS:
                pwd = globals.ENV_VARS["password"]
                test_env_info["密码"] = f"{pwd[:2]}***{pwd[-2:]}" if len(pwd) > 4 else "***"

            # 添加到Allure报告
            with allure.step("🌍 环境配置详情"):
                allure.attach(
                    yaml.dump(system_info, allow_unicode=True, default_flow_style=False),
                    name="系统环境信息",
                    attachment_type=allure.attachment_type.YAML
                )

                allure.attach(
                    yaml.dump(test_env_info, allow_unicode=True, default_flow_style=False),
                    name="测试环境配置",
                    attachment_type=allure.attachment_type.YAML
                )

                # 添加环境变量文件内容（如果有）
                env_file_path = Path("config/env_config.yaml")
                if env_file_path.exists():
                    with open(env_file_path, 'r', encoding='utf-8') as f:
                        env_content = f.read()
                    allure.attach(
                        env_content,
                        name="环境配置文件内容",
                        attachment_type=allure.attachment_type.YAML
                    )

        except Exception as e:
            Logger.warning(f"附加环境信息失败: {str(e)}")
            allure.attach(
                f"环境信息记录失败: {str(e)}",
                name="环境信息错误",
                attachment_type=allure.attachment_type.TEXT
            )

    @log_function()
    def _execute_and_validate_request(self, request_spec):
        """执行请求并验证响应 """
        from common.request_util import RequestUtil

        with allure.step("发送API请求"):
            # 记录请求详情
            allure.attach(
                yaml.dump(request_spec, allow_unicode=True, default_flow_style=False),
                name="请求配置",
                attachment_type=allure.attachment_type.YAML
            )

            # 执行请求
            response = RequestUtil.send_request(request_spec)

            # 优化：美化响应内容显示
            self._attach_beautified_response(response)

            # 优化：美化响应头显示
            self._attach_formatted_headers(response)

            Logger.info(f"请求完成，状态码: {response.status_code}")

            return response

    @log_function()
    def _attach_beautified_response(self, response):
        """美化响应内容显示"""
        try:
            response_text = getattr(response, 'text', '')

            if not response_text:
                allure.attach("无响应内容", name="响应内容", attachment_type=allure.attachment_type.TEXT)
                return

            # 尝试美化JSON响应
            if self._is_json_response(response):
                self._attach_formatted_json(response)
            # 尝试美化XML响应
            elif self._is_xml_response(response):
                self._attach_formatted_xml(response)
            # 其他文本内容
            else:
                self._attach_plain_text(response)

        except Exception as e:
            Logger.error(f"美化响应内容失败: {str(e)}")
            # 失败时使用原始内容
            allure.attach(
                getattr(response, 'text', '无响应内容'),
                name="响应内容（原始）",
                attachment_type=allure.attachment_type.TEXT
            )

    @log_function()
    def _is_json_response(self, response):
        """检查是否为JSON响应"""
        content_type = getattr(response, 'headers', {}).get('Content-Type', '').lower()
        return 'application/json' in content_type or self._looks_like_json(response.text)

    @log_function()
    def _looks_like_json(self, text):
        """检查文本是否像JSON"""
        text = text.strip()
        return (text.startswith('{') and text.endswith('}')) or (text.startswith('[') and text.endswith(']'))

    @log_function()
    def _is_xml_response(self, response):
        """检查是否为XML响应"""
        content_type = getattr(response, 'headers', {}).get('Content-Type', '').lower()
        return 'application/xml' in content_type or 'text/xml' in content_type

    @log_function()
    def _attach_formatted_json(self, response):
        """附加格式化的JSON响应"""
        try:
            # 解析并美化JSON
            json_data = response.json()
            formatted_json = json.dumps(json_data, ensure_ascii=False, indent=2)

            # 添加JSON格式的附件（有语法高亮）
            allure.attach(
                formatted_json,
                name="响应内容（JSON格式化）",
                attachment_type=allure.attachment_type.JSON
            )

            # 计算JSON大小信息
            json_size = len(response.text)
            beautified_size = len(formatted_json)
            size_info = f"原始大小: {json_size} 字符, 格式化后: {beautified_size} 字符"

            allure.attach(
                size_info,
                name="JSON大小信息",
                attachment_type=allure.attachment_type.TEXT
            )

            Logger.debug("JSON响应已格式化")

        except Exception as e:
            Logger.warning(f"JSON格式化失败，使用原始文本: {str(e)}")
            allure.attach(
                response.text,
                name="响应内容（JSON原始）",
                attachment_type=allure.attachment_type.TEXT
            )

    @log_function()
    def _attach_formatted_xml(self, response):
        """附加格式化的XML响应"""
        try:
            # 需要安装xml.dom.minidom来格式化XML
            from xml.dom import minidom
            parsed_xml = minidom.parseString(response.text)
            formatted_xml = parsed_xml.toprettyxml(indent="  ")

            allure.attach(
                formatted_xml,
                name="响应内容（XML格式化）",
                attachment_type=allure.attachment_type.XML
            )

        except Exception as e:
            Logger.warning(f"XML格式化失败，使用原始文本: {str(e)}")
            allure.attach(
                response.text,
                name="响应内容（XML原始）",
                attachment_type=allure.attachment_type.TEXT
            )

    def _attach_plain_text(self, response):
        """附加普通文本响应"""
        text = response.text
        # 如果文本过长，进行截断
        if len(text) > 10000:
            text = text[:10000] + "\n\n...（内容过长，已截断）"

        allure.attach(
            text,
            name="响应内容",
            attachment_type=allure.attachment_type.TEXT
        )

    def _attach_formatted_headers(self, response):
        """美化响应头显示"""
        try:
            headers = dict(response.headers)
            formatted_headers = "\n".join([f"{k}: {v}" for k, v in headers.items()])

            allure.attach(
                formatted_headers,
                name="响应头（格式化）",
                attachment_type=allure.attachment_type.TEXT
            )

            # 同时添加YAML格式的响应头，便于阅读
            allure.attach(
                yaml.dump(headers, allow_unicode=True, default_flow_style=False),
                name="响应头（YAML）",
                attachment_type=allure.attachment_type.YAML
            )

        except Exception as e:
            Logger.error(f"格式化响应头失败: {str(e)}")
            allure.attach(
                str(getattr(response, 'headers', '无响应头')),
                name="响应头",
                attachment_type=allure.attachment_type.TEXT
            )

    def _handle_extraction(self, response):
        """处理变量提取 """
        if "extract" in self.spec and isinstance(self.spec["extract"], dict):
            from common.extract_util import ExtractUtil

            with allure.step("🔍 提取响应数据"):
                try:
                    # 1. 记录提取配置
                    if self.spec["extract"]:
                        allure.attach(
                            yaml.dump(self.spec["extract"], allow_unicode=True),
                            name="提取配置",
                            attachment_type=allure.attachment_type.YAML
                        )
                    else:
                        allure.attach("未配置提取规则", name="提取配置",
                                      attachment_type=allure.attachment_type.TEXT)

                    # 2. 记录完整响应体用于调试
                    self._attach_response_for_debug(response)

                    # 3. 执行提取
                    ExtractUtil.extract_values(response, self.spec["extract"])
                    extracted_vars = ExtractUtil.get_all_extract_vars()

                    # 4. 显示提取结果 - 修复MARKDOWN错误
                    self._display_extraction_results(extracted_vars)

                except Exception as e:
                    Logger.error(f"提取过程发生错误: {str(e)}")
                    # 记录详细的错误信息
                    allure.attach(
                        f"提取过程错误: {str(e)}\n\n"
                        f"错误类型: {type(e).__name__}\n\n"
                        f"请检查提取工具配置和响应体结构",
                        name="提取错误详情",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    raise

    def _attach_response_for_debug(self, response):
        """附加响应体用于调试"""
        try:
            response_json = response.json()
            allure.attach(
                json.dumps(response_json, ensure_ascii=False, indent=2),
                name="完整响应体(JSON)",
                attachment_type=allure.attachment_type.JSON
            )

            # 分析响应体结构
            structure_info = self._analyze_response_structure(response_json)
            allure.attach(
                structure_info,
                name="响应体结构分析",
                attachment_type=allure.attachment_type.TEXT
            )

        except Exception as e:
            allure.attach(
                f"响应文本: {response.text}\n错误: {str(e)}",
                name="响应体(原始)",
                attachment_type=allure.attachment_type.TEXT
            )

    def _analyze_response_structure(self, response_json):
        """分析响应体结构"""
        lines = ["响应体结构分析:"]

        def analyze_obj(obj, path="", depth=0):
            if depth > 3:  # 限制递归深度
                return

            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    value_type = type(value).__name__
                    lines.append(f"{'  ' * depth}{key} ({value_type})")
                    analyze_obj(value, new_path, depth + 1)
            elif isinstance(obj, list) and obj:
                lines.append(f"{'  ' * depth}[列表] 长度: {len(obj)}")
                if len(obj) > 0:
                    analyze_obj(obj[0], f"{path}[0]", depth + 1)

        analyze_obj(response_json)
        return "\n".join(lines)

    def _display_extraction_results(self, extracted_vars):
        """显示提取结果"""
        if extracted_vars:
            # 成功提取 - 使用纯文本表格
            table = "=" * 60 + "\n"
            table += "✅ 提取成功\n"
            table += "=" * 60 + "\n"
            table += "变量名".ljust(20) + "变量值".ljust(30) + "类型\n"
            table += "-" * 60 + "\n"

            for name, value in extracted_vars.items():
                display_value = str(value)
                if len(display_value) > 30:
                    display_value = display_value[:30] + "..."
                value_type = type(value).__name__
                table += f"{name.ljust(20)}{display_value.ljust(30)}{value_type}\n"

            allure.attach(
                table,
                name="提取结果",
                attachment_type=allure.attachment_type.TEXT
            )
            Logger.info(f"✅ 提取变量: {list(extracted_vars.keys())}")
        else:
            # 提取失败 - 提供解决方案
            solution_guide = """
            🚨 提取失败 - 解决方案指南

            🔍 从响应体分析发现的问题:
            1. data字段是数组：响应体中的data是一个数组[]，不是对象
            2. 需要数组索引：提取数组元素需要使用索引，如data[0]

            🔧 立即修复方案:
            修改YAML测试用例中的提取规则：

            修改前:
            extract:
              X-Auth-Code: jsonpath:$.data.user_uniquecode
              user_id: jsonpath:$.data.user_id

            修改后:
            extract:
              X-Auth-Code: jsonpath:$.data[0].user_uniquecode
              user_id: jsonpath:$.data[0].user_id

            📚 JSONPath 数组处理指南:
            - 获取第一个元素: $.data[0].field
            - 获取最后一个元素: $.data[-1].field
            - 获取所有元素: $.data[*].field

            🔍 调试技巧:
            1. 查看上方的"响应体结构分析"确认实际数据结构
            2. 使用在线JSONPath验证工具测试表达式
            3. 逐步测试路径: 先试$.data，再试$.data[0]
            """

            allure.attach(
                solution_guide,
                name="提取失败解决方案",
                attachment_type=allure.attachment_type.TEXT
            )
            Logger.warning("❌ 未提取到变量，请查看提取失败解决方案")

    def _handle_assertions(self, response):
        """处理断言验证 - 关键修复：确保验证步骤始终显示"""
        # 关键修复：无论是否有断言配置，都显示验证步骤
        with allure.step("🔍 验证响应结果"):
            # 记录响应基本信息
            response_info = {
                "状态码": response.status_code,
                "响应大小": f"{len(response.text)} 字节",
                "响应类型": response.headers.get('Content-Type', 'Unknown')
            }

            allure.attach(
                yaml.dump(response_info, allow_unicode=True),
                name="响应基本信息",
                attachment_type=allure.attachment_type.YAML
            )

            # 检查是否有断言配置
            has_expect = "expect" in self.spec and self.spec["expect"]
            has_validate = "validate" in self.spec and self.spec["validate"]

            if not has_expect and not has_validate:
                # 关键修复：即使没有断言配置，也显示信息
                allure.attach(
                    "该测试用例未配置断言验证规则",
                    name="无断言配置",
                    attachment_type=allure.attachment_type.TEXT
                )
                Logger.warning(f"测试用例 {self.name} 未配置断言")
                return

            # 处理基础断言
            if has_expect:
                self._handle_expect_assertions(response)
            else:
                with allure.step("基础断言"):
                    allure.attach("未配置基础断言(expect)", name="无基础断言",
                                  attachment_type=allure.attachment_type.TEXT)

            # 处理自定义验证
            if has_validate:
                self._handle_custom_validations(response)
            else:
                with allure.step("自定义验证"):
                    allure.attach("未配置自定义验证(validate)", name="无自定义验证",
                                  attachment_type=allure.attachment_type.TEXT)

    @log_function()
    def _handle_expect_assertions(self, response):
        """处理expect断言 - 修复MARKDOWN错误"""
        with allure.step("基础断言验证"):
            try:
                # 记录预期结果
                allure.attach(
                    yaml.dump(self.spec["expect"], allow_unicode=True),
                    name="预期结果配置",
                    attachment_type=allure.attachment_type.YAML
                )

                # 获取实际结果
                actual_results = self._get_actual_results_safe(response, self.spec["expect"])
                allure.attach(
                    yaml.dump(actual_results, allow_unicode=True),
                    name="实际响应结果",
                    attachment_type=allure.attachment_type.YAML
                )

                # 使用新的表格生成方法
                comparison_table = self._generate_comparison_table(
                    self.spec["expect"],
                    actual_results
                )

                # 安全添加对比表格到报告
                with allure.step("📊 断言对比详情"):
                    try:
                        allure.attach(
                            comparison_table,
                            name="期望值 vs 实际结果对比",
                            attachment_type=allure.attachment_type.TEXT
                        )
                    except Exception as e:
                        Logger.error(f"添加对比表格到报告失败: {str(e)}")
                        allure.attach(
                            "无法生成对比表格，请查看日志",
                            name="对比表格生成失败",
                            attachment_type=allure.attachment_type.TEXT
                        )

                # 执行断言
                from common.assert_util import AssertUtil
                AssertUtil.assert_response(response, self.spec["expect"])

                # 断言通过，记录成功信息
                with allure.step("✅ 断言结果"):
                    success_table = self._generate_success_text_table(self.spec["expect"], actual_results)
                    allure.attach(
                        success_table,
                        name="所有断言通过",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    Logger.info("✅ 所有断言通过")

            except AssertionError as e:
                # 断言失败，记录详细失败信息
                self._handle_assertion_failure_safe(e, response, self.spec["expect"], actual_results)
                raise
            except Exception as e:
                Logger.error(f"断言处理异常: {str(e)}")
                self._handle_general_assertion_error(e, response, self.spec["expect"])
                raise

    @log_function()
    def _generate_safe_text_table(self, expected, actual):
        """安全生成纯文本对比表格"""
        return self._generate_comparison_table(expected, actual)

    def _get_actual_results_safe(self, response, expect_config):
        """安全获取实际结果"""
        try:
            from common.response_util import ResponseUtil
            return ResponseUtil.extract_actual_results(response, expect_config)
        except Exception as e:
            Logger.error(f"获取实际结果时发生错误: {str(e)}")
            return {"error": f"获取实际结果失败: {str(e)}"}

    def _extract_expected_fields_safe(self, data, expected_fields):
        """安全提取期望字段"""
        try:
            from common.response_util import ResponseUtil
            return ResponseUtil.extract_fields(data, expected_fields)
        except Exception as e:
            Logger.error(f"提取期望字段失败: {str(e)}")
            return {"error": f"提取失败: {str(e)}"}

    def _extract_expected_fields(self, data, expected_fields):
        """递归提取期望字段"""
        try:
            from common.response_util import ResponseUtil
            return ResponseUtil.extract_fields(data, expected_fields)
        except Exception as e:
            Logger.error(f"提取期望字段失败: {str(e)}")
            return {"error": f"提取失败: {str(e)}"}

    # ========== 以下是新增的表格生成方法 ==========

    @log_function()
    def _calculate_string_width(self, text):
        """计算字符串的显示宽度（考虑中英文字符）"""
        if not text:
            return 0
        width = 0
        for char in str(text):
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                width += 2
            else:
                width += 1
        return width

    @log_function()
    def _pad_string(self, text, target_width, align='left'):
        """填充字符串到目标宽度"""
        current_width = self._calculate_string_width(text)

        if current_width >= target_width:
            return text

        padding_needed = target_width - current_width
        padding = ' ' * padding_needed

        if align == 'left':
            return text + padding
        else:  # right align
            return padding + text

    @log_function()
    def _calculate_column_widths(self, expected, actual):
        """计算每列的最大宽度"""
        # 初始化最小列宽
        min_widths = {
            'field': 15,  # 字段名最小宽度
            'expected': 20,  # 期望值最小宽度
            'actual': 20,  # 实际值最小宽度
            'status': 10  # 状态最小宽度
        }

        max_widths = min_widths.copy()

        # 处理状态码
        if "status_code" in expected:
            exp_val = self._generate_formatted_value(expected["status_code"])
            act_val = self._generate_formatted_value(actual.get("status_code", "N/A"))

            max_widths['field'] = max(max_widths['field'], self._calculate_string_width("状态码"))
            max_widths['expected'] = max(max_widths['expected'], self._calculate_string_width(exp_val))
            max_widths['actual'] = max(max_widths['actual'], self._calculate_string_width(act_val))
            max_widths['status'] = max(max_widths['status'], self._calculate_string_width("PASS"))

        # 处理响应头
        if "headers" in expected:
            for header, exp_val in expected["headers"].items():
                act_val = actual.get("headers", {}).get(header, "N/A")
                field_name = f"headers.{header}"
                exp_val_fmt = self._generate_formatted_value(exp_val)
                act_val_fmt = self._generate_formatted_value(act_val)

                max_widths['field'] = max(max_widths['field'], self._calculate_string_width(field_name))
                max_widths['expected'] = max(max_widths['expected'], self._calculate_string_width(exp_val_fmt))
                max_widths['actual'] = max(max_widths['actual'], self._calculate_string_width(act_val_fmt))
                max_widths['status'] = max(max_widths['status'], self._calculate_string_width("PASS"))

        # 处理响应体
        if "body" in expected:
            for field, exp_val in expected["body"].items():
                if isinstance(exp_val, dict):
                    for sub_field, sub_exp_val in exp_val.items():
                        full_field = f"body.{field}.{sub_field}"
                        sub_act_val = actual.get("body", {}).get(field, {}).get(sub_field, "N/A")
                        exp_val_fmt = self._generate_formatted_value(sub_exp_val)
                        act_val_fmt = self._generate_formatted_value(sub_act_val)

                        max_widths['field'] = max(max_widths['field'], self._calculate_string_width(full_field))
                        max_widths['expected'] = max(max_widths['expected'], self._calculate_string_width(exp_val_fmt))
                        max_widths['actual'] = max(max_widths['actual'], self._calculate_string_width(act_val_fmt))
                        max_widths['status'] = max(max_widths['status'], self._calculate_string_width("PASS"))
                else:
                    full_field = f"body.{field}"
                    act_val = actual.get("body", {}).get(field, "N/A")
                    exp_val_fmt = self._generate_formatted_value(exp_val)
                    act_val_fmt = self._generate_formatted_value(act_val)

                    max_widths['field'] = max(max_widths['field'], self._calculate_string_width(full_field))
                    max_widths['expected'] = max(max_widths['expected'], self._calculate_string_width(exp_val_fmt))
                    max_widths['actual'] = max(max_widths['actual'], self._calculate_string_width(act_val_fmt))
                    max_widths['status'] = max(max_widths['status'], self._calculate_string_width("PASS"))

        # 添加一些缓冲空间
        for key in max_widths:
            max_widths[key] = min(max_widths[key] + 2, 80)  # 限制最大宽度为80

        return max_widths

    @log_function()
    def _generate_formatted_value(self, value):
        """格式化值以便在表格中显示 - 限制最大长度"""
        if value is None:
            return "None"

        if isinstance(value, (dict, list)):
            try:
                # 使用JSON格式化复杂数据结构
                formatted = json.dumps(value, ensure_ascii=False, indent=2)
                # 限制总长度
                if len(formatted) > 100:
                    # 只保留前80个字符
                    formatted = formatted[:80] + "..."
                return formatted
            except:
                return str(value)[:80] + ("..." if len(str(value)) > 80 else "")

        # 限制字符串长度
        str_value = str(value)
        if len(str_value) > 80:
            return str_value[:80] + "..."

        return str_value  # 修复：移除多余的括号

    @log_function()
    def _generate_comparison_table(self, expected, actual, status_map=None):
        """生成格式化的对比表格 - 固定列宽版本"""
        status_map = status_map or {}

        # 计算列宽
        column_widths = self._calculate_column_widths(expected, actual)

        # 创建表格标题
        field_header = self._pad_string("字段名", column_widths['field'])
        expected_header = self._pad_string("期望值", column_widths['expected'])
        actual_header = self._pad_string("实际值", column_widths['actual'])
        status_header = self._pad_string("状态", column_widths['status'])

        table = [
            f"| {field_header} | {expected_header} | {actual_header} | {status_header} |",
            f"|{'-' * column_widths['field']}|{'-' * column_widths['expected']}|{'-' * column_widths['actual']}|{'-' * column_widths['status']}|"
        ]

        # 处理状态码
        if "status_code" in expected:
            exp_value = self._generate_formatted_value(expected["status_code"])
            act_value = self._generate_formatted_value(actual.get("status_code", "N/A"))
            status = status_map.get("status_code", "N/A")

            field_cell = self._pad_string("状态码", column_widths['field'])
            exp_cell = self._pad_string(exp_value, column_widths['expected'])
            act_cell = self._pad_string(act_value, column_widths['actual'])
            status_cell = self._pad_string(status, column_widths['status'])

            table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        # 处理响应头
        if "headers" in expected:
            for header, exp_val in expected["headers"].items():
                act_val = actual.get("headers", {}).get(header, "N/A")
                status = status_map.get(f"headers.{header}", "N/A")

                field_name = f"headers.{header}"
                exp_val_fmt = self._generate_formatted_value(exp_val)
                act_val_fmt = self._generate_formatted_value(act_val)

                field_cell = self._pad_string(field_name, column_widths['field'])
                exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                status_cell = self._pad_string(status, column_widths['status'])

                table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        # 处理响应体
        if "body" in expected:
            for field, exp_val in expected["body"].items():
                # 处理嵌套字段
                if isinstance(exp_val, dict):
                    for sub_field, sub_exp_val in exp_val.items():
                        full_field = f"body.{field}.{sub_field}"
                        sub_act_val = actual.get("body", {}).get(field, {}).get(sub_field, "N/A")
                        status = status_map.get(full_field, "N/A")

                        exp_val_fmt = self._generate_formatted_value(sub_exp_val)
                        act_val_fmt = self._generate_formatted_value(sub_act_val)

                        field_cell = self._pad_string(full_field, column_widths['field'])
                        exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                        act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                        status_cell = self._pad_string(status, column_widths['status'])

                        table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")
                else:
                    full_field = f"body.{field}"
                    act_val = actual.get("body", {}).get(field, "N/A")
                    status = status_map.get(full_field, "N/A")

                    exp_val_fmt = self._generate_formatted_value(exp_val)
                    act_val_fmt = self._generate_formatted_value(act_val)

                    field_cell = self._pad_string(full_field, column_widths['field'])
                    exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                    act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                    status_cell = self._pad_string(status, column_widths['status'])

                    table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        return "\n".join(table)

    @log_function()
    def _generate_success_text_table(self, expected, actual):
        """生成成功断言表格 - 固定列宽版本"""
        # 计算列宽
        column_widths = self._calculate_column_widths(expected, actual)

        # 创建表格标题
        field_header = self._pad_string("字段名", column_widths['field'])
        expected_header = self._pad_string("期望值", column_widths['expected'])
        actual_header = self._pad_string("实际值", column_widths['actual'])
        status_header = self._pad_string("状态", column_widths['status'])

        table = [
            "✅ 所有断言通过",
            "=" * (column_widths['field'] + column_widths['expected'] + column_widths['actual'] + column_widths[
                'status'] + 12),
            f"| {field_header} | {expected_header} | {actual_header} | {status_header} |",
            f"|{'-' * column_widths['field']}|{'-' * column_widths['expected']}|{'-' * column_widths['actual']}|{'-' * column_widths['status']}|"
        ]

        # 状态码
        if "status_code" in expected:
            exp_val = self._generate_formatted_value(expected["status_code"])
            act_val = self._generate_formatted_value(actual.get("status_code", "N/A"))

            field_cell = self._pad_string("状态码", column_widths['field'])
            exp_cell = self._pad_string(exp_val, column_widths['expected'])
            act_cell = self._pad_string(act_val, column_widths['actual'])
            status_cell = self._pad_string("PASS", column_widths['status'])

            table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        # 其他字段
        for field in ["headers", "body"]:
            if field in expected:
                for key, exp_val in expected[field].items():
                    if isinstance(exp_val, dict):
                        for sub_key, sub_exp_val in exp_val.items():
                            full_key = f"{field}.{key}.{sub_key}"
                            sub_act_val = actual.get(field, {}).get(key, {}).get(sub_key, "N/A")

                            exp_val_fmt = self._generate_formatted_value(sub_exp_val)
                            act_val_fmt = self._generate_formatted_value(sub_act_val)

                            field_cell = self._pad_string(full_key, column_widths['field'])
                            exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                            act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                            status_cell = self._pad_string("PASS", column_widths['status'])

                            table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")
                    else:
                        full_key = f"{field}.{key}"
                        act_val = actual.get(field, {}).get(key, "N/A")

                        exp_val_fmt = self._generate_formatted_value(exp_val)
                        act_val_fmt = self._generate_formatted_value(act_val)

                        field_cell = self._pad_string(full_key, column_widths['field'])
                        exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                        act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                        status_cell = self._pad_string("PASS", column_widths['status'])

                        table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        table.append("\n所有验证项均通过测试！")
        return "\n".join(table)

    @log_function()
    def _generate_failure_text_table(self, expected, actual, error_msg):
        """生成失败对比表格 - 固定列宽版本"""
        # 解析错误信息，提取失败字段
        failed_fields = {}
        if "status_code" in error_msg:
            failed_fields["status_code"] = "FAIL"

        # 尝试从错误消息中提取更多失败字段
        pattern = r"字段 '(.*?)'"
        matches = re.findall(pattern, error_msg)
        for match in matches:
            failed_fields[match] = "FAIL"

        # 计算列宽
        column_widths = self._calculate_column_widths(expected, actual)

        # 创建表格标题
        field_header = self._pad_string("字段名", column_widths['field'])
        expected_header = self._pad_string("期望值", column_widths['expected'])
        actual_header = self._pad_string("实际值", column_widths['actual'])
        status_header = self._pad_string("状态", column_widths['status'])

        table = [
            f"🚨 断言失败: {error_msg}",
            "=" * (column_widths['field'] + column_widths['expected'] + column_widths['actual'] + column_widths[
                'status'] + 12),
            f"| {field_header} | {expected_header} | {actual_header} | {status_header} |",
            f"|{'-' * column_widths['field']}|{'-' * column_widths['expected']}|{'-' * column_widths['actual']}|{'-' * column_widths['status']}|"
        ]

        # 状态码
        if "status_code" in expected:
            exp_val = self._generate_formatted_value(expected["status_code"])
            act_val = self._generate_formatted_value(actual.get("status_code", "N/A"))
            status = failed_fields.get("status_code", "PASS")

            field_cell = self._pad_string("状态码", column_widths['field'])
            exp_cell = self._pad_string(exp_val, column_widths['expected'])
            act_cell = self._pad_string(act_val, column_widths['actual'])
            status_cell = self._pad_string(status, column_widths['status'])

            table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        # 其他字段
        for field in ["headers", "body"]:
            if field in expected:
                for key, exp_val in expected[field].items():
                    if isinstance(exp_val, dict):
                        for sub_key, sub_exp_val in exp_val.items():
                            full_key = f"{field}.{key}.{sub_key}"
                            sub_act_val = actual.get(field, {}).get(key, {}).get(sub_key, "N/A")

                            exp_val_fmt = self._generate_formatted_value(sub_exp_val)
                            act_val_fmt = self._generate_formatted_value(sub_act_val)
                            status = failed_fields.get(full_key, "PASS")

                            field_cell = self._pad_string(full_key, column_widths['field'])
                            exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                            act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                            status_cell = self._pad_string(status, column_widths['status'])

                            table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")
                    else:
                        full_key = f"{field}.{key}"
                        act_val = actual.get(field, {}).get(key, "N/A")

                        exp_val_fmt = self._generate_formatted_value(exp_val)
                        act_val_fmt = self._generate_formatted_value(act_val)
                        status = failed_fields.get(full_key, "PASS")

                        field_cell = self._pad_string(full_key, column_widths['field'])
                        exp_cell = self._pad_string(exp_val_fmt, column_widths['expected'])
                        act_cell = self._pad_string(act_val_fmt, column_widths['actual'])
                        status_cell = self._pad_string(status, column_widths['status'])

                        table.append(f"| {field_cell} | {exp_cell} | {act_cell} | {status_cell} |")

        table.append("\n请检查标记为FAIL的字段")
        return "\n".join(table)

    @log_function()
    def _handle_assertion_failure_safe(self, error, response, expected, actual):
        """安全处理断言失败"""
        try:
            with allure.step("❌ 断言失败详情"):
                # 错误信息
                allure.attach(str(error), name="错误详情", attachment_type=allure.attachment_type.TEXT)

                # 上下文信息
                context = {
                    "请求URL": response.request.url,
                    "请求方法": response.request.method,
                    "响应状态码": response.status_code
                }
                allure.attach(
                    yaml.dump(context, allow_unicode=True),
                    name="请求上下文",
                    attachment_type=allure.attachment_type.YAML
                )

                # 生成失败对比表格
                failure_table = self._generate_failure_text_table(expected, actual, str(error))
                allure.attach(
                    failure_table,
                    name="失败项对比",
                    attachment_type=allure.attachment_type.TEXT
                )

                # 附加原始响应数据
                self._attach_beautified_response(response)
        except Exception as e:
            # 降级处理
            Logger.error(f"生成失败报告时出错: {str(e)}")
            with allure.step("❌ 断言失败详情"):
                allure.attach(str(error), name="错误详情", attachment_type=allure.attachment_type.TEXT)

    @log_function()
    def _handle_general_assertion_error(self, error, response, expected):
        """处理一般断言错误"""
        try:
            with allure.step("❌ 断言异常处理"):
                # 记录错误信息
                allure.attach(str(error), name="错误详情", attachment_type=allure.attachment_type.TEXT)

                # 获取实际结果
                actual_results = self._get_actual_results_safe(response, expected)
                
                # 生成错误报告
                error_report = self._generate_error_report(error, response, expected, actual_results)
                allure.attach(
                    error_report,
                    name="错误报告",
                    attachment_type=allure.attachment_type.TEXT
                )

                # 附加响应数据
                self._attach_beautified_response(response)
                
                Logger.error(f"断言处理异常: {str(error)}")
        except Exception as e:
            # 降级处理
            Logger.error(f"处理断言异常时出错: {str(e)}")
            with allure.step("❌ 断言异常处理"):
                allure.attach(str(error), name="错误详情", attachment_type=allure.attachment_type.TEXT)

    @log_function()
    def _generate_error_report(self, error, response, expected, actual):
        """生成错误报告"""
        try:
            # 基本错误信息
            error_type = type(error).__name__
            error_msg = str(error)
            
            # 请求上下文
            request_context = {
                "URL": response.request.url,
                "方法": response.request.method,
                "状态码": response.status_code
            }
            
            # 构建错误报告
            report = [
                f"🚨 断言处理异常",
                "=" * 60,
                f"错误类型: {error_type}",
                f"错误信息: {error_msg}",
                "",
                "请求上下文:",
                yaml.dump(request_context, allow_unicode=True),
                "",
                "预期配置:",
                yaml.dump(expected, allow_unicode=True),
                "",
                "实际结果:",
                yaml.dump(actual, allow_unicode=True)
            ]
            
            return "\n".join(report)
        except Exception as e:
            return f"生成错误报告失败: {str(e)}\n原始错误: {str(error)}"

    def _handle_custom_validations(self, response):
        """处理自定义验证"""
        with allure.step("处理自定义验证"):
            allure.attach(
                "\n".join(self.spec["validate"]),
                name="验证规则",
                attachment_type=allure.attachment_type.TEXT
            )

            try:
                self._custom_validation(response, self.spec["validate"])
                allure.attach("所有自定义验证通过", name="验证结果", attachment_type=allure.attachment_type.TEXT)
                Logger.info("✅ 所有自定义验证通过")
            except Exception as e:
                allure.attach(str(e), name="验证失败详情", attachment_type=allure.attachment_type.TEXT)
                raise

    def _custom_validation(self, response, validate_rules):
        """执行自定义验证规则"""
        try:
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            safe_env = {
                'response': response_data,
                'data': response_data.get('data', {}) if isinstance(response_data, dict) else {},
                'headers': dict(response.headers),
                'status_code': response.status_code,
                'len': len,
                'str': str,
                'int': int,
                'float': float
            }

            from common.extract_util import ExtractUtil
            safe_env.update(ExtractUtil.get_all_extract_vars())

            for i, rule in enumerate(validate_rules):
                result = eval(rule, {"__builtins__": {}}, safe_env)
                if not result:
                    pytest.fail(f"自定义验证失败: {rule}")

        except Exception as e:
            pytest.fail(f"自定义验证执行错误: {str(e)}")

    def _safe_decode_request_body(self, body):
        """安全解码请求体"""
        if not body:
            return '无'
        try:
            return body.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            return str(body)

    def repr_failure(self, excinfo):
        """增强的错误报告"""
        if self.spec.get('invalid'):
            return f"无效测试用例格式: {self.name}"
        return super().repr_failure(excinfo)


def pytest_collection_modifyitems(config, items):
    """安全地为所有测试项添加fixture（优化版本）"""
    for item in items:
        if isinstance(item, YamlItem) and hasattr(item, 'fixturenames'):
            if 'request_fixture' not in item.fixturenames:
                item.fixturenames.append('request_fixture')

        if isinstance(item, YamlItem):
            item.add_marker(pytest.mark.feature(item.feature))
            if item.priority is not None:
                item.add_marker(pytest.mark.priority(item.priority))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """统一的测试报告处理"""
    outcome = yield
    rep = outcome.get_result()

    if rep.when == 'call':
        _handle_test_report(rep, item)


def _handle_test_report(rep, item):
    """处理测试报告日志"""
    try:
        from common.logger import Logger
        case_name = getattr(item, 'name', '未命名用例')

        if rep.failed:
            Logger.error(f"用例执行失败: {case_name}")
            err_msg = str(getattr(rep, 'longrepr', '未知错误'))
            Logger.error(f"失败原因: {err_msg[:500]}{'...' if len(err_msg) > 500 else ''}")
        else:
            Logger.success(f"用例执行成功: {case_name}")

    except Exception as e:
        print(f"❌ 测试报告日志记录失败: {str(e)}")


@pytest.fixture(autouse=True)
def auto_clean_extract():
    """自动清理提取数据"""
    from common.extract_util import ExtractUtil
    yield
    ExtractUtil.clear_extract_data()

