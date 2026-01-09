import json
from datetime import datetime
from typing import List, Dict
import requests


class AEUIBot:
    def __init__(self):
        # 测试
        self.api_url = ("https://oapi.dingtalk.com/robot/send?"
                        "access_token=a68d48b561a32ee60470b51"
                        "e979f2dbf7b8bf4681c4fa740de9eaadb44721381")

        # 生产
        # self.api_url = ("https://oapi.dingtalk.com/robot/send?"
        #                 "access_token=b8f258163e1bac56cafe168"
        #                 "c68e43fe49436126c603d90e02f3ad8247e661ecd")

        self.headers = {"Content-Type": "application/json"}

    """格式化测试结果"""
    def format_test_results(
        self,
        format_result: List[Dict],
        report_url: str = None,
    ) -> str:

        # 统计测试结果
        total_cases = len(format_result)
        passed_cases = sum(
            1 for case in format_result if case.get("status") == "PASS"
        )
        failed_cases = total_cases - passed_cases
        success_rate = (
            (passed_cases / total_cases * 100) if total_cases > 0 else 0
        )

        # 按sheet名称分组统计
        sheet_group = {}
        for case in format_result:
            sheet_name = case.get("sheet_name", "未知工作表")
            if sheet_name not in sheet_group:
                sheet_group[sheet_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                }

            sheet_group[sheet_name]["total"] += 1
            if case.get("status") == "PASS":
                sheet_group[sheet_name]["passed"] += 1
            else:
                sheet_group[sheet_name]["failed"] += 1

        # 获取失败的测试用例详情（按sheet名称分组）
        failed_details_by_sheet = {}
        for case in format_result:
            if case.get("status") != "PASS":
                sheet_name = case.get("sheet_name", "未知工作表")
                if sheet_name not in failed_details_by_sheet:
                    failed_details_by_sheet[sheet_name] = []

                # failed_details_by_sheet[sheet_name].append(
                #     f"- 失败用例ID: {case.get('test_case_id')}\n  描述: {case.get('description')}\n  失败原因: {'请查看Log日志...'}"
                # )
                failed_details_by_sheet[sheet_name].append(case.get('test_case_id'))
        # print(f"看看你长啥样：{failed_details_by_sheet}")

        # 构建消息内容
        message = (
            f"### 📢 AE_UI自动化测试\n"
            f"- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 总用例数：{total_cases}\n"
            f"- 总通过用例：{passed_cases}\n"
            f"- 总失败用例：{failed_cases}\n"
            f"- 总成功率：{success_rate:.2f}%\n"
        )

        # 添加各sheet的统计信息
        if sheet_group:
            message += "\n### ✅ 各工作表统计\n"
            for sheet_name, stats in sheet_group.items():
                sheet_success_rate = (
                    (stats["passed"] / stats["total"] * 100)
                    if stats["total"] > 0
                    else 0
                )
                message += (
                    f"- {sheet_name}: {stats['total']}个用例, "
                    f"通过: {stats['passed']}, "
                    f"失败: {stats['failed']}, "
                    f"成功率: {sheet_success_rate:.2f}%\n"
                )

        # 如果有失败的用例，添加失败详情（按sheet名称分组）
        if failed_cases > 0:
            message += "\n### ❌ 失败用例详情"
            for (
                sheet_name,
                failed_cases_list,
            ) in failed_details_by_sheet.items():
                message += f"\n**{sheet_name}失败用例:**\n"
                # message += "\n".join(failed_cases_list)
                message += f"- {'、'.join(failed_cases_list)}"

        # 加入Allure报告链接
        if report_url and report_url.startswith("http"):
            # 使用可点击的HTTP链接
            message += f"\n### 📊 详细测试报告\n"
            message += f"- [点击查看Allure详细报告]({report_url})\n"
            message += f"- 链接有效期：服务器运行期间\n"
        else:
            # 提供本地文件路径作为备选
            allure_report_path = "./allure-report/index.html"
            import os

            if os.path.exists(allure_report_path):
                absolute_path = os.path.abspath(allure_report_path)
                message += f"\n### 📊 详细测试报告\n"
                message += f"- 报告位置: {absolute_path}\n"
                message += f"- 请在浏览器中手动打开以上路径查看详细报告\n"
            else:
                message += "\n### 📊 测试报告\n"
                message += "- Allure报告未生成，请检查allure-results目录\n"

        return message

    """发送测试结果到钉钉"""
    def send_test_results(
        self,
        result: List[Dict],
        report_url: str = None,
    ) -> bool:
        try:
            # print(f" AE_Bot.send_test_results 调试信息：开始发送测试结果 ===")
            # print(f" AE_Bot.send_test_results 测试结果数量：{len(result)}")
            # print(f" AE_Bot.send_test_results 测试结果内容：{result}")

            if not result:
                print("警告：测试结果为空，跳过发送")
                return False

            message = self.format_test_results(result, report_url)

            print(f"\n格式化后的消息：{message}\n")
            key_word = "UI自动化测试报告"
            data = {
                "msgtype": "markdown",
                "markdown": {"title": key_word, "text": message},
                "at": {"atMobiles": [], "isAtAll": False},
            }

            response = requests.post(
                self.api_url, headers=self.headers, data=json.dumps(data)
            )

            if response.status_code == 200:
                print("测试结果发送成功")
                return True
            else:
                print(f"发送失败，状态码：{response.status_code}")
                return False

        except Exception as e:
            print(f"发送测试结果时发生错误：{str(e)}")
            return False
