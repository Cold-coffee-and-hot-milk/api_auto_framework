import pytest
from common.request_util import RequestUtil
from common.extract_util import ExtractUtil
from common.logger import Logger


@pytest.fixture(scope='function')
def request_fixture():
    ExtractUtil.clear_extract_data()
    Logger.info("=" * 50)
    Logger.info("开始执行测试用例")

    yield RequestUtil

    Logger.info("测试用例执行结束")
    Logger.info("=" * 50)