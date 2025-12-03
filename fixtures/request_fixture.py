
# import pytest
# from common.request_util import RequestUtil
# from common.extract_util import ExtractUtil
# from common.logger import Logger
#
#
# @pytest.fixture(scope='function')
# def request_fixture():
#     ExtractUtil.clear_extract_data()
#     Logger.info("=" * 50)
#     Logger.info("开始执行测试用例")
#
#     yield RequestUtil
#
#     Logger.info("测试用例执行结束")
#     Logger.info("=" * 50)


# fixtures/request_fixture.py

import pytest
from common.request_util import RequestUtil
from common.logger import Logger
import globals  # 导入全局变量模块


@pytest.fixture(scope="function")
def request_fixture():
    """请求fixture - 设置基础URL"""
    # 设置基础URL
    base_url = globals.ENV_VARS.get("base_url", "")

    if base_url:
        RequestUtil.set_base_url(base_url)
        Logger.info(f"设置基础URL: {base_url}")

    yield

    # 清理操作
    RequestUtil.clear_session()

