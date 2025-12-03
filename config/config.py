import os
import yaml



class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_DIR = os.path.join(BASE_DIR, 'config')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    TEST_CASES_DIR = os.path.join(DATA_DIR, 'test_cases')
    REPORT_DIR = os.path.join(BASE_DIR, 'reports')

    # 环境变量缓存
    _env_config = None

    @classmethod
    def get_env_config(cls, env_name=None):
        """获取环境配置
        :param env_name: 可选，指定环境名称
        """
        # 如果指定了环境名称，直接返回该环境的配置
        if env_name:
            return cls._get_env_config_by_name(env_name)

        # 否则返回当前环境的配置
        if cls._env_config is not None:
            return cls._env_config

        # 读取环境配置文件
        env_file = os.path.join(cls.CONFIG_DIR, 'env_config.yaml')
        if not os.path.exists(env_file):
            cls._env_config = {}
            return cls._env_config

        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                env_data = yaml.safe_load(f) or {}

            # 获取当前环境
            current_env = env_data.get('current_env', ' test')

            # 获取对应环境的配置
            cls._env_config = env_data.get(current_env, {})
            return cls._env_config
        except Exception as e:
            print(f"加载环境配置失败: {str(e)}")
            cls._env_config = {}
            return cls._env_config

    @classmethod
    def _get_env_config_by_name(cls, env_name):
        """根据环境名称获取配置"""
        env_file = os.path.join(cls.CONFIG_DIR, 'env_config.yaml')
        if not os.path.exists(env_file):
            return {}

        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                env_data = yaml.safe_load(f) or {}

            return env_data.get(env_name, {})
        except Exception as e:
            print(f"加载环境配置失败: {str(e)}")
            return {}

