import requests
from common.yaml_util import YamlUtil
from common.extract_util import ExtractUtil
from common.logger import Logger
from config.config import Config


class RequestUtil:
    session = requests.Session()

    @classmethod
    def send_request(cls, case_info):
        """
        增强安全性的请求发送方法
        保留原有功能并增加：
        1. 更健壮的URL处理
        2. 更严格的参数校验
        3. 更详细的错误日志
        4. 智能数据格式处理
        """
        try:
            # ========== 参数校验 ==========
            if not isinstance(case_info, dict):
                raise ValueError("请求配置必须是字典类型")

            if 'url' not in case_info:
                raise ValueError("请求配置缺少必需的url字段")

            # ========== 处理URL ==========
            url = str(case_info['url']).strip()

            # 保留原有base_url拼接逻辑
            if not url.startswith(('http://', 'https://')):
                base_url = Config.get_env_config().get('base_url', '').strip()
                if base_url:
                    # 正确处理URL拼接（避免双斜杠）
                    base_url = base_url.rstrip('/')
                    url = url.lstrip('/')
                    url = f"{base_url}/{url}"

            # ========== 处理headers ==========
            headers = {
                str(k): str(v) if v is not None else ''
                for k, v in case_info.get('headers', {}).items()
            }

            # ========== 智能处理请求数据 ==========
            method = case_info.get('method', 'GET').upper()
            data_type = case_info.get('data_type', 'json')
            data = case_info.get('data', {})

            # 保留原有的动态参数替换
            data = ExtractUtil.replace_dynamic_values(data)

            # 根据数据类型智能处理数据
            processed_data = cls._process_request_data(data, data_type)

            Logger.info(f"执行用例: {case_info.get('name', '未命名用例')}")
            Logger.debug(f"请求URL: {url}")
            Logger.debug(f"请求方法: {method}")
            Logger.debug(f"请求数据类型: {data_type}")
            Logger.debug(f"请求数据: {processed_data}")

            # ========== 发送请求 ==========
            try:
                if method == 'GET':
                    response = cls.session.request(method, url, params=processed_data, headers=headers)
                elif data_type == 'form':
                    response = cls.session.request(method, url, data=processed_data, headers=headers)
                else:
                    response = cls.session.request(method, url, json=processed_data, headers=headers)
            except requests.exceptions.InvalidHeader as e:
                raise ValueError(f"请求头格式错误: {str(e)}") from e
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"请求发送失败: {str(e)}") from e

            Logger.debug(f"响应状态码: {response.status_code}")
            Logger.debug(f"响应数据: {response.text[:500]}")  # 限制日志长度

            # ========== 提取变量 ==========
            if 'extract' in case_info and isinstance(case_info['extract'], dict):
                ExtractUtil.extract_values(response, case_info['extract'])
                Logger.debug(f"提取变量: {ExtractUtil.extract_data}")

            return response

        except Exception as e:
            Logger.error(f"请求失败 - URL: {case_info.get('url', '未提供URL')}")
            Logger.error(f"错误详情: {str(e)}")
            raise RuntimeError(f"请求处理失败: {str(e)}") from e

    @classmethod
    def _process_request_data(cls, data, data_type):
        """
        智能处理请求数据
        根据数据类型自动转换数据格式
        """
        if not isinstance(data, dict):
            return data

        # 确保所有键都是字符串
        processed = {str(k): v for k, v in data.items()}

        # 根据数据类型处理值
        if data_type == 'form':
            # Form表单数据需要字符串值
            return {k: str(v) if v is not None else '' for k, v in processed.items()}
        else:
            # JSON数据保持原始类型但确保可序列化
            return {k: v if isinstance(v, (str, int, float, bool)) or v is None else str(v)
                    for k, v in processed.items()}