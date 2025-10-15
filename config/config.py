import os


class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_DIR = os.path.join(BASE_DIR, 'config')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    TEST_CASES_DIR = os.path.join(DATA_DIR, 'test_cases')
    REPORT_DIR = os.path.join(BASE_DIR, 'reports')

    @classmethod
    def get_env_config(cls):
        from common.yaml_util import YamlUtil
        env_config = YamlUtil.read_yaml(os.path.join(cls.CONFIG_DIR, 'env_config.yaml'))
        current_env = env_config.get('current_env', 'dev')
        return env_config.get(current_env, {})