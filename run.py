import os
import sys
import subprocess
from config.config import Config
from common.logger import Logger


def run_tests():
    # 确保目录存在
    os.makedirs(Config.REPORT_DIR, exist_ok=True)

    # 初始化日志
    Logger()

    # 调试信息
    print(f"使用的Python路径: {sys.executable}")
    allure_dir = os.path.abspath(os.path.join(Config.REPORT_DIR, "allure_results"))
    print(f"Allure报告目录: {allure_dir}")

    try:
        # 使用绝对路径确保一致性
        subprocess.run([
            sys.executable,  # 确保使用虚拟环境的Python
            '-m', 'pytest',
            f'--alluredir={allure_dir}',
            '-v'
        ], check=True)

        # 生成报告
        Logger.info("生成Allure测试报告")
        subprocess.run([
            'allure', 'generate',
            allure_dir,
            '-o', os.path.join(Config.REPORT_DIR, 'allure_report'),
            '--clean'
        ], check=True)

        # 打开报告
        Logger.info("测试执行完成，打开Allure报告")
        subprocess.run([
            'allure', 'open',
            os.path.join(Config.REPORT_DIR, 'allure_report')
        ], check=True)

    except subprocess.CalledProcessError as e:
        Logger.error(f"测试执行失败: {str(e)}")
        raise


if __name__ == '__main__':
    run_tests()