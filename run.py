import os
import sys
import time
from config.config import Config
from common.logger import Logger
from common.log_decorator import log_function


@log_function(include_result=True)
def run_tests():
    """执行测试并生成报告"""
    try:
        # 确保目录存在
        os.makedirs(Config.REPORT_DIR, exist_ok=True)

        # 初始化日志
        Logger()

        # 记录开始时间
        start_time = time.time()
        Logger.info("开始执行测试...")

        # 调试信息
        Logger.debug(f"使用的Python路径: {sys.executable}")
        allure_results_dir = os.path.abspath(os.path.join(Config.REPORT_DIR, "allure_results"))
        Logger.debug(f"Allure结果目录: {allure_results_dir}")
        
        # 关键修复：在运行测试前清理之前的allure结果，避免历史数据导致的重复用例
        if os.path.exists(allure_results_dir):
            import shutil
            shutil.rmtree(allure_results_dir)
            Logger.info(f"已清理历史allure结果目录: {allure_results_dir}")
        os.makedirs(allure_results_dir, exist_ok=True)

        # 运行pytest命令（关键修复：使用check=False）
        result = subprocess.run([
            sys.executable,  # 确保使用虚拟环境的Python
            '-m', 'pytest',
            f'--alluredir={allure_results_dir}',
            '-v'
        ], check=False)  # 关键修改：使用check=False

        # 检查pytest的退出码
        if result.returncode != 0:
            Logger.warning(f"测试执行完成，但有失败用例 (退出码: {result.returncode})")
        else:
            Logger.success("测试执行完成，所有用例通过")

        # 生成报告
        Logger.info("生成Allure测试报告")
        allure_report_dir = os.path.join(Config.REPORT_DIR, 'allure_report')
        subprocess.run([
            'allure', 'generate',
            allure_results_dir,
            '-o', allure_report_dir,
            '--clean'
        ], check=True)

        # 计算执行时间
        duration = time.time() - start_time
        Logger.info(f"总执行时间: {duration:.2f}秒")

        # 打开报告
        Logger.info("测试执行完成，打开Allure报告")
        subprocess.run([
            'allure', 'open',
            allure_report_dir
        ], check=True)

        # 返回pytest的退出码
        return result.returncode

    except Exception as e:
        Logger.error(f"测试执行失败: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    # 执行测试并获取退出码
    exit_code = run_tests()

    # 使用测试的退出码退出
    sys.exit(exit_code)

