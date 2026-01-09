import shutil
import os
import sys
import json
from datetime import datetime
# from AEUI_Bot import AEUIBot
import subprocess
import time
import socket
import glob
import base64

from dingding_bot import AEUIBot

"""
专门处理AI分析结果中的换行符号，保持其他数据结构不变
只将字符串中的 '\\n' 转换为实际的换行符 '\n'
"""
def format_ai_analysis(ai_data):
    if ai_data is None:
        return ""

    # 如果是字符串，处理其中的换行符号
    if isinstance(ai_data, str):
        # 只替换换行符号，保持其他内容不变
        return ai_data.replace('\\n', '\n')

    # 如果是列表，递归处理每个元素
    elif isinstance(ai_data, list):
        return [format_ai_analysis(item) for item in ai_data]

    # 如果是字典，递归处理每个值
    elif isinstance(ai_data, dict):
        return {key: format_ai_analysis(value) for key, value in ai_data.items()}

    # 其他类型直接返回
    else:
        return ai_data

"""将测试结果保存为Allure格式"""
def save_results_as_allure(test_results):
    if not test_results:
        print("警告：没有测试结果数据，创建空的Allure报告")
        return
    print(f"=== SUITE调试: 开始处理 {len(test_results)} 个测试用例")

    # 分析Suite分布
    suite_distribution = {}
    for test_case in test_results:
        sheet_name = test_case.get("sheet_name", "未知工作表")
        suite_distribution[sheet_name] = (
                suite_distribution.get(sheet_name, 0) + 1
        )

    print("=== SUITE分布统计:")
    for suite, count in suite_distribution.items():
        print(f"    {suite}: {count} 个用例")

    # 清理之前的测试结果
    if os.path.exists("./allure-results"):
        shutil.rmtree("./allure-results")
    os.makedirs("./allure-results", exist_ok=True)

    # 为每个工作流分配唯一偏移量
    workflow_offsets = {}
    current_offset = 0
    for test_case in test_results:
        sheet_name = test_case.get("sheet_name", "未知工作表")
        if sheet_name not in workflow_offsets:
            workflow_offsets[sheet_name] = current_offset
            current_offset += 1000000

    print(f"=== SUITE偏移量配置: {workflow_offsets}")

    case_counters = {}
    suite_files = {}

    for i, test_case in enumerate(test_results):
        test_case_id = test_case.get("test_case_id", f"test-case-{i}")
        description = test_case.get("description", "无描述")
        status = test_case.get("status", "unknown")
        sheet_name = test_case.get("sheet_name", "未知工作表")

        click_logs = test_case.get("click_logs", "")
        assert_logs = test_case.get("assert_logs", "")
        ai_analysis_result = test_case.get("AI_analysis", "")  # ⭐AI分析字段
        screenshot_base64 = test_case.get("screenshot_base64", "")
        case_log_text = test_case.get("case_log_text", "")
        # 状态转换
        if status == "PASS":
            allure_status = "passed"
        elif status == "FAIL":
            allure_status = "failed"
        elif status == "ERROR":
            allure_status = "broken"
        else:
            allure_status = "unknown"

        # 更新计数器
        if sheet_name not in case_counters:
            case_counters[sheet_name] = 0
        else:
            case_counters[sheet_name] += 1

        case_index = case_counters[sheet_name]

        # 时间戳
        base_time = 1700000000000
        workflow_offset = workflow_offsets.get(sheet_name, 0)
        start_time = base_time + workflow_offset + case_index * 1000
        stop_time = start_time + 500

        unique_test_id = f"{sheet_name}_{test_case_id}"
        current_time = int(time.time() * 1000000)
        unique_uuid = f"{sheet_name}-{test_case_id}-{current_time}"

        # print(f"=== SUITE处理: [{sheet_name}] -> {test_case_id}")
        # print(f"    UUID: {unique_uuid}")
        # print(f"    historyId: {unique_test_id}")

        # 构建状态详情
        status_details = {
            "known": False,
            "muted": False,
            "flaky": False,
            "message": None,
            "trace": None
        }

        # message：点击日志（失败原因）
        if status != "PASS":
            status_details["message"] = click_logs if click_logs else "执行失败，请查看 Log 日志..."

        # trace：断言日志 + AI 分析
        trace_parts = []

        ai_newline_result=format_ai_analysis(ai_analysis_result)

        if assert_logs:
            trace_parts.append("【断言日志】\n" + assert_logs)

        if ai_analysis_result:
            trace_parts.append("【AI 分析】\n" + ai_newline_result)

        if trace_parts:
            status_details["trace"] = "\n\n".join(trace_parts).strip()
        else:
            status_details["trace"] = "无断言日志或AI分析内容"

        attachments = []  # 存储附件列表
        if screenshot_base64:
            try:
                # 将Base64数据保存为图片文件
                screenshot_filename = f"{unique_uuid}-screenshot.png"
                screenshot_filepath = f"./allure-results/{screenshot_filename}"

                # 解码Base64数据并保存为文件
                screenshot_data = base64.b64decode(screenshot_base64)
                with open(screenshot_filepath, 'wb') as f:
                    f.write(screenshot_data)

                # 将文件路径添加到附件列表中
                attachments.append({
                    "name": screenshot_filename,
                    "source": screenshot_filename,
                    "type": "image/png"
                })
                print(f"✓ 截图已保存为附件: {screenshot_filename}")
            except Exception as e:
                print(f"❌ 截图保存失败: {e}")

        # 判断Log日志...
        if case_log_text:
            try:
                case_log_filename = f"{unique_uuid}-case-log.txt"
                case_log_filepath = f"./allure-results/{case_log_filename}"
                with open(case_log_filepath, 'w', encoding='utf-8') as f:
                    f.write(case_log_text)
                attachments.append({
                    "name": f"Log日志--{test_case_id}",
                    "source": case_log_filename,
                    "type": "text/plain"
                })
                print(f"✓ 用例日志已保存为附件: {case_log_filename}")
            except Exception as e:
                print(f"❌ 用例日志附件保存失败: {e}")

        # 添加AI分析文本附件
        if ai_analysis_result:
            try:
                ai_text_filename = f"{unique_uuid}-ai-analysis.txt"
                ai_text_filepath = f"./allure-results/{ai_text_filename}"

                with open(ai_text_filepath, 'w', encoding='utf-8') as f:
                    f.write(ai_newline_result)

                attachments.append({
                    "name": f"AI分析--{test_case_id}",
                    "source": ai_text_filename,
                    "type": "text/plain"
                })
                print(f"✓ AI分析已保存为附件: {ai_text_filename}")
            except Exception as e:
                print(f"❌ AI分析附件保存失败: {e}")

        # 生成Allure报告的JSON数据
        allure_result = {
            "name": f"{test_case_id}: {description}",
            "status": allure_status,
            "statusDetails": status_details,
            "start": start_time,
            "stop": stop_time,
            "uuid": unique_uuid,
            "historyId": unique_test_id,
            "testCaseId": unique_test_id,
            "fullName": f"{sheet_name}.{test_case_id}",
            "labels": [
                {"name": "suite", "value": sheet_name},
                {"name": "feature", "value": description},
                {"name": "story", "value": unique_test_id},
                {"name": "severity", "value": "normal"},
                {"name": "framework", "value": "pytest"},
                {"name": "language", "value": "python"},
                {"name": "package", "value": f"tests.{sheet_name}"},
            ],
            "links": [],
            "parameters": [
                {"name": "工作表", "value": sheet_name},
                {"name": "用例ID", "value": test_case_id},
            ],
            "steps": [
                {
                    "name": f" === 附件查看：{test_case_id} ===",
                    "status": allure_status,
                    "start": start_time,
                    "stop": stop_time,
                    "steps": [],
                    "attachments": attachments  # 将附件添加到步骤中
                }
            ],
        }

        # 保存Allure报告的JSON文件
        result_file = f"./allure-results/{unique_uuid}-result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(allure_result, f, ensure_ascii=False, indent=2)

        # 记录 suite
        if sheet_name not in suite_files:
            suite_files[sheet_name] = []
        suite_files[sheet_name].append(result_file)

        print(f"✓ 保存到Suite [{sheet_name}]: {test_case_id}")


    # 统计
    print("\n=== SUITE最终统计 ===")
    total_files = 0
    for suite, files in suite_files.items():
        print(f"Suite [{suite}]: {len(files)} 个文件")
        total_files += len(files)

    print(f"总文件数: {total_files}")
    print(f"期望文件数: {len(test_results)}")

    actual_files = glob.glob("./allure-results/*-result.json")
    print(f"实际生成文件数: {len(actual_files)}")

    if len(actual_files) != len(test_results):
        print("⚠️ 警告: 文件数量不匹配! 可能存在覆盖")
        for file in actual_files:
            print(f"  {file}")

    # 环境信息
    environment_info = {
        "python_version": sys.version,
        "platform": sys.platform,
        "timestamp": datetime.now().isoformat(),
    }
    with open(
        "./allure-results/environment.properties", "w", encoding="utf-8"
    ) as f:
        for key, value in environment_info.items():
            f.write(f"{key}={value}\n")


"""生成Allure报告"""
def generate_allure_report():
    # 优先检测 Jenkins 环境
    if os.environ.get("BUILD_URL"):
        print("=== 检测到 Jenkins 环境 ===")
        build_url = os.environ.get("BUILD_URL")
        if not build_url.endswith("/"):
            build_url += "/"
        report_url = f"{build_url}allure/"
        print(f"直接使用 Jenkins Allure 报告链接: {report_url}")
        return report_url
    try:
        print("=== 开始生成Allure报告 ===")

        # 检查allure-results目录是否存在
        if not os.path.exists("./allure-results"):
            print("❌ 未找到测试结果目录: allure-results")
            return None

        # 检查allure-results目录中是否有文件
        result_files = [
            f for f in os.listdir("./allure-results") if f.endswith(".json")
        ]
        if not result_files:
            print("❌ allure-results目录中没有测试结果文件")
            return None

        print(f"找到 {len(result_files)} 个测试结果文件")

        # 首先检查allure命令是否可用
        try:
            allure_path = shutil.which("allure")
            print(f"Allure可执行路径: {allure_path or '未找到'}")
            version_result = subprocess.run(
                "allure --version",
                capture_output=True,
                text=True,
                shell=True,
            )
            java_result = subprocess.run(
                "java -version",
                capture_output=True,
                text=True,
                shell=True,
            )
            if java_result.returncode != 0:
                print("❌ 未检测到 Java 环境，Allure CLI 依赖 Java")

            if version_result.returncode == 0:
                print(f"✓ Allure版本: {version_result.stdout.strip()}")
                result = subprocess.run(
                    "allure generate ./allure-results -o ./allure-report --clean",
                    capture_output=True,
                    text=True,
                    shell=True,
                )
                if result.returncode == 0:
                    print("✓ Allure报告生成成功！")
                    return start_allure_server()
                else:
                    print("❌ Allure报告生成失败")
                    print(f"STDOUT: {result.stdout}")
                    print(f"STDERR: {result.stderr}")
                    return None
            else:
                print("❌ Allure版本检查失败，请检查allure是否安装及环境变量配置")
                print(f"STDOUT: {version_result.stdout}")
                print(f"STDERR: {version_result.stderr}")
                return None

        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Allure命令行工具未安装")
            return None

    except Exception as e:
        print(f"❌ Allure报告生成过程中发生异常: {e}")
        return None


"""启动Allure服务器"""
def start_allure_server():
    try:
        if not os.path.exists("./allure-report"):
            print("❌ 未找到allure-report目录")
            return None

        print("🚀 启动Allure报告服务器...")

        # 查找可用端口
        port = find_available_port(8080)

        # 使用指定端口启动allure
        # 尝试绑定到 0.0.0.0 以便外部访问
        _process = subprocess.Popen(
            f"allure open ./allure-report -p {port} -h 0.0.0.0",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
        )
        time.sleep(2)
        if _process.poll() is not None:
            print("⚠️ allure open 启动失败，尝试使用 Python 内置HTTP服务器作为回退")
            # py_server = subprocess.Popen(
            #     f"python3 -m http.server {port}",
            #     cwd="./allure-report",
            #     stdout=subprocess.PIPE,
            #     stderr=subprocess.PIPE,
            #     text=True,
            #     shell=True,
            # )

            # 重定向日志到文件，避免父进程退出导致 Broken Pipe，同时绑定到 0.0.0.0
            try:
                log_file = open("./allure-report/server.log", "w", encoding="utf-8")
                py_server = subprocess.Popen(
                    f"python3 -m http.server {port} --bind 0.0.0.0",
                    cwd="./allure-report",
                    stdout=log_file,
                    stderr=log_file,
                    text=True,
                    shell=True,
                )
                time.sleep(2)
                print(f"✓ Python HTTP Server 已启动，日志位于 ./allure-report/server.log")
            except Exception as e:
                print(f"⚠️ 启动 Python HTTP 服务器失败: {e}")

        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return "localhost"

        local_ip = get_local_ip()
        url = f"http://{local_ip}:{port}"
        print(f"✅ 报告可访问: {url}")
        print(f"📍 本地访问: http://localhost:{port}")
        print("💡 如无法访问，请检查端口/防火墙/反向代理")
        return url

    except Exception as e:
        print(f"❌ 启动Allure服务器时发生异常: {e}")
        return "Allure服务器启动异常"


"""找可用端口"""
def find_available_port(start_port=8080, max_attempts=50):
    """查找可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue
    return start_port  # 如果都不可用，返回起始端口



"""在Allure报告生成后发送钉钉消息"""
def send_dingtalk_message_with_report(test_results):

    # 先生成Allure报告并获取URL
    report_url = generate_allure_report()

    if report_url:
        print(f"✓ Allure报告生成成功，URL: {report_url}")

        # 发送钉钉消息（包含可点击的URL）
        bot = AEUIBot()
        if test_results:
            print("开始调用send_test_results方法...")
            # 传递报告URL给发送方法
            bot.send_test_results(test_results, report_url)
        else:
            print("没有测试结果，跳过钉钉消息发送")
    else:
        print("⚠ Allure报告生成失败，将发送不含报告链接的消息")
        bot = AEUIBot()
        if test_results:
            bot.send_test_results(test_results)


# # 运行测试
# python -v --alluredir=./allure-results
#
# # 生成报告 -o: output
# allure generate ./allure-results -o ./allure-report --clean
#
# # 打开报告
# allure open ./allure-report
