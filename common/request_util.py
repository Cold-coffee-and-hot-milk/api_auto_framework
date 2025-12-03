import requests
from common.yaml_util import YamlUtil
from common.extract_util import ExtractUtil
from common.data_util import DataUtil
from common.logger import Logger
from common.log_decorator import log_api
from config.config import Config


class RequestUtil:
    session = requests.Session()
    _base_url = None

    @classmethod
    def set_base_url(cls, base_url):
        """设置基础URL"""
        cls._base_url = base_url
        Logger.info(f"设置基础URL: {base_url}")

    @classmethod
    @log_api()
    def send_request(cls, case_info):
        """
        请求发送方法
        """
        try:
            # ========== 参数校验 ==========
            if not isinstance(case_info, dict):
                raise ValueError("请求配置必须是字典类型")

            if 'url' not in case_info:
                raise ValueError("请求配置缺少必需的url字段")

            # ========== 处理URL ==========
            url = str(case_info['url']).strip()

            # 处理URL拼接
            if not url.startswith(('http://', 'https://')):
                # 优先使用类中设置的基础URL
                base_url = cls._base_url or Config.get_env_config().get('base_url', '').strip()
                if base_url:
                    # 正确处理URL拼接（避免双斜杠）
                    base_url = base_url.rstrip('/')
                    url = url.lstrip('/')
                    url = f"{base_url}/{url}"

            # ========== 处理headers ==========

            headers = DataUtil.safe_convert_to_dict(case_info.get('headers', {}))
            headers = {str(k): str(v) if v is not None else '' for k, v in headers.items()}

            # ========== 处理请求数据 ==========
            method = case_info.get('method', 'GET').upper()
            data_type = case_info.get('data_type', 'json')
            data = DataUtil.safe_convert_to_dict(case_info.get('data', {}))

            # 使用ExtractUtil替换动态变量
            data = ExtractUtil.replace_dynamic_values(data)

            # 根据数据类型处理数据
            processed_data = cls._process_request_data(data, data_type)

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

            # Form表单数据需要字符串值，但保留数组类型
            return {k: cls._convert_to_form_value(v) for k, v in processed.items()}
        else:
            # JSON数据保持原始类型但确保可序列化
            return {k: v if isinstance(v, (str, int, float, bool, list, dict)) or v is None else str(v)
                    for k, v in processed.items()}
    
    @classmethod
    def _convert_to_form_value(cls, value):
        """
        转换值为表单格式，但保留数组类型
        """
        if value is None:
            return ''
        elif isinstance(value, (list, dict)):
            # 保留复杂数据结构，不转换为字符串
            return value
        else:
            return str(value)
    
    @classmethod
    def clear_session(cls):
        """清除会话"""
        cls.session = requests.Session()
        cls._base_url = None
        Logger.info("已清除请求会话")

