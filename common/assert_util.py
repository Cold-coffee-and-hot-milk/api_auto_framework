import re
import json
from common.logger import Logger


class AssertUtil:
    @staticmethod
    def assert_response(response, expect_config):
        """增强的响应断言方法"""
        try:
            # 1. 验证状态码
            if "status_code" in expect_config:
                expected_status = expect_config["status_code"]
                actual_status = response.status_code
                if expected_status != actual_status:
                    error_msg = f"状态码不匹配: 期望={expected_status}, 实际={actual_status}"
                    raise AssertionError(error_msg)

            # 2. 验证响应体
            if "body" in expect_config:
                try:
                    response_body = response.json()
                except:
                    response_body = response.text

                body_expect = expect_config["body"]
                # 修复：使用类名调用静态方法
                AssertUtil._assert_dict_contains(response_body, body_expect, "响应体")

            # 3. 验证响应头
            if "headers" in expect_config:
                headers_expect = expect_config["headers"]
                headers_actual = dict(response.headers)
                # 修复：使用类名调用静态方法
                AssertUtil._assert_dict_contains(headers_actual, headers_expect, "响应头")

        except AssertionError as e:
            # 添加详细的上下文信息
            context = {
                "请求URL": response.request.url,
                "请求方法": response.request.method,
                "请求体": getattr(response.request, 'body', '无'),
                "响应状态码": response.status_code,
                "响应体": response.text[:1000] + ("..." if len(response.text) > 1000 else "")
            }
            
            # 处理bytes类型，确保JSON序列化成功
            def make_json_serializable(obj):
                """递归处理对象，确保所有元素都可以JSON序列化"""
                if isinstance(obj, bytes):
                    try:
                        return obj.decode('utf-8')
                    except UnicodeDecodeError:
                        return str(obj)
                elif isinstance(obj, dict):
                    return {k: make_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_json_serializable(item) for item in obj]
                else:
                    return obj
            
            serializable_context = make_json_serializable(context)
            raise AssertionError(f"{str(e)}\n\n请求上下文:\n{json.dumps(serializable_context, indent=2, ensure_ascii=False)}")

    @staticmethod
    def _assert_dict_contains(actual, expected, prefix=""):
        """断言字典包含关系"""
        for key, expected_value in expected.items():
            if key not in actual:
                raise AssertionError(f"{prefix}缺少字段: {key}")

            actual_value = actual[key]
            if isinstance(expected_value, dict):
                # 递归检查嵌套字典
                if not isinstance(actual_value, dict):
                    raise AssertionError(f"{prefix}.{key} 应为字典类型, 实际为 {type(actual_value).__name__}")
                AssertUtil._assert_dict_contains(actual_value, expected_value, f"{prefix}.{key}")
            else:
                if actual_value != expected_value:
                    raise AssertionError(f"{prefix}.{key} 值不匹配: 期望={expected_value}, 实际={actual_value}")

    @staticmethod
    def _assert_status_code(response, expected_code):
        """断言状态码，返回断言结果列表"""
        actual_code = response.status_code
        passed = actual_code == expected_code
        if passed:
            message = f"状态码匹配：实际={actual_code}，预期={expected_code}"
        else:
            message = f"状态码不匹配：实际={actual_code}，预期={expected_code}"
        result = {
            "type": "状态码",
            "field": "status_code",
            "expected": expected_code,
            "actual": actual_code,
            "passed": passed,
            "message": message
        }
        if passed:
            Logger.info(f"✅ 状态码断言通过: {expected_code}")
        else:
            Logger.error(message)
        return [result]

    @staticmethod
    def _assert_response_body(response, expected_body):
        """断言响应体，返回断言结果列表"""
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        return AssertUtil._recursive_compare(response_data, expected_body, path="body")

    @staticmethod
    def _assert_headers(response, expected_headers):
        """断言响应头，返回断言结果列表"""
        results = []
        for header_name, expected_value in expected_headers.items():
            actual_value = response.headers.get(header_name)
            passed = actual_value == expected_value
            if passed:
                message = f"响应头匹配: {header_name} 值符合预期"
            else:
                message = f"响应头不匹配: {header_name} 实际={actual_value}, 预期={expected_value}"
            results.append({
                "type": "响应头",
                "field": f"headers.{header_name}",
                "expected": expected_value,
                "actual": actual_value,
                "passed": passed,
                "message": message
            })
        # 检查所有断言结果
        all_passed = all(r["passed"] for r in results)
        if all_passed:
            Logger.info("✅ 响应头断言通过")
        else:
            # 获取失败字段列表
            failed_fields = [r["field"] for r in results if not r["passed"]]
            Logger.error(f"❌ 响应头断言失败: 失败字段={', '.join(failed_headers)}")
            # 记录每个失败字段的详细信息
            for result in results:
                if not result["passed"]:
                    Logger.debug(f"失败详情：{result['message']}")

        return results

    @staticmethod
    def _recursive_compare(actual, expected, path=""):
        """
        递归比较实际值和期望值
        返回断言结果列表
        """
        results = []

        # 类型检查层
        if type(expected) != type(actual):
            results.append({
                "type": "类型匹配",
                "field": path,
                "expected": type(expected).__name__,
                "actual": type(actual).__name__,
                "passed": False,
                "message": f"类型不匹配: 期望={type(expected).__name__}, 实际={type(actual).__name__}"
            })
            return results

        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                # 双重确保
                results.append({
                    "type": "类型匹配",
                    "field": path,
                    "expected": "dict",
                    "actual": type(actual).__name__,
                    "passed": False,
                    "message": f"类型不匹配: 期望字典, 实际{type(actual).__name__}"
                })
                return results
            for key, exp_val in expected.items():
                current_path = f"{path}.{key}" if path else key
                if key not in actual:
                    results.append({
                        "type": "字段存在",
                        "field": current_path,
                        "expected": "存在",
                        "actual": "不存在",
                        "passed": False,
                        "message": f"字段缺失: {current_path}"
                    })
                else:
                    sub_results = AssertUtil._recursive_compare(actual[key], exp_val, current_path)
                    results.extend(sub_results)

        elif isinstance(expected, list):
            if not isinstance(actual, list):
                results.append({
                    "type": "类型匹配",
                    "field": path,
                    "expected": "list",
                    "actual": type(actual).__name__,
                    "passed": False,
                    "message": f"类型不匹配: 期望列表, 实际{type(actual).__name__}"
                })
                return results
            if len(actual) != len(expected):
                results.append({
                    "type": "数组长度",
                    "field": path,
                    "expected": len(expected),
                    "actual": len(actual),
                    "passed": False,
                    "message": f"数组长度不匹配: {path} 实际长度={len(actual)}, 预期长度={len(expected)}"
                })
            else:
                for i, (act_item, exp_item) in enumerate(zip(actual, expected)):
                    sub_results = AssertUtil._recursive_compare(act_item, exp_item, f"{path}[{i}]")
                    results.extend(sub_results)

        else:
            # 处理特殊断言类型（如正则表达式）
            if isinstance(expected, str) and expected.startswith("!!python/regex "):
                pattern = expected.split(" ", 1)[1]
                # 保留原始类型信息
                actual_str = str(actual) if not isinstance(actual, str) else actual
                # 使用完全匹配
                passed = re.match(pattern, actual_str) is not None
                message = (f"正则匹配失败: {path} 值={actual_str}, 模式={pattern}"if not passed else "")
                results.append({
                    "type": "正则匹配",
                    "field": path,
                    "expected": pattern,
                    "actual": str(actual),
                    "passed": passed,
                    "message": message
                })
            else:
                passed = actual == expected
                message = (f"值不匹配: {path} 实际={actual}, 预期={expected}"
                           if not passed else f"值匹配: {path} 值符合预期")
                results.append({
                    "type": "值匹配",
                    "field": path,
                    "expected": expected,
                    "actual": actual,
                    "passed": passed,
                    "message": message
                })

        return results