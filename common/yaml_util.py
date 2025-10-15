import yaml
import os
from config.config import Config


class YamlUtil:
    @staticmethod
    def read_yaml(file_path):
        if not os.path.isabs(file_path):
            file_path = os.path.join(Config.BASE_DIR, file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @staticmethod
    def read_test_cases(file_name):
        file_path = os.path.join(Config.TEST_CASES_DIR, file_name)
        return YamlUtil.read_yaml(file_path)

    @staticmethod
    def write_yaml(file_path, data):
        if not os.path.isabs(file_path):
            file_path = os.path.join(Config.BASE_DIR, file_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)