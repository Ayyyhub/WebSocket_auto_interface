# locust_performance/error_recorder.py
import json
import traceback
from datetime import datetime
from collections import defaultdict
from locust import events
from utils.logger import logger
import threading

class ErrorRecorder:
    """
    错误详情记录器
    记录所有失败请求的详细信息，包括请求参数、响应数据、异常信息等
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ErrorRecorder, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._errors = defaultdict(list)  # {接口名: [错误详情列表]}
        self._lock = threading.Lock()
        self._initialized = True
    
    def record_error(self, name, exception, response_time=0, request_params=None, 
                     response_data=None, user_id=None, error_type="未知异常"):
        """
        记录错误详情
        :param name: 接口名称
        :param exception: 异常对象或异常信息
        :param response_time: 响应时间（毫秒）
        :param request_params: 请求参数
        :param response_data: 响应数据
        :param user_id: 用户ID
        :param error_type: 错误类型（网络异常/业务异常/断言失败）
        """
        error_detail = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            "user_id": user_id or "unknown",
            "request_params": request_params,
            "response_data": response_data,
            "exception": str(exception),
            "exception_type": error_type,
            "response_time_ms": response_time,
            "stack_trace": traceback.format_exc() if isinstance(exception, Exception) else None
        }
        
        with self._lock:
            self._errors[name].append(error_detail)
        
        logger.error(f"[错误记录] {name}: {error_detail}")
    
    def get_errors(self):
        """获取所有错误记录"""
        with self._lock:
            return dict(self._errors)
    
    def get_error_summary(self):
        """获取错误摘要统计"""
        with self._lock:
            summary = {}
            for name, errors in self._errors.items():
                summary[name] = {
                    "total_errors": len(errors),
                    "error_types": {},
                    "latest_error": errors[-1] if errors else None
                }
                # 统计错误类型
                for error in errors:
                    error_type = error["exception_type"]
                    summary[name]["error_types"][error_type] = \
                        summary[name]["error_types"].get(error_type, 0) + 1
            return summary
    
    def export_to_json(self, filepath="locust_errors.json"):
        """导出错误详情到JSON文件"""
        import os
        # 如果是相对路径，保存到 locust_performance 目录
        if not os.path.isabs(filepath):
            base_dir = os.path.dirname(__file__)
            filepath = os.path.join(base_dir, filepath)
        with self._lock:
            data = {
                "export_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "total_errors": sum(len(errors) for errors in self._errors.values()),
                "errors_by_interface": dict(self._errors),
                "summary": self.get_error_summary()
            }
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"错误详情已导出到: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"导出错误详情失败: {e}")
                return None
    
    def clear(self):
        """清空错误记录"""
        with self._lock:
            self._errors.clear()


# 全局错误记录器实例
error_recorder = ErrorRecorder()




def on_request_failure(request_type, name, response_time, response_length, exception=None, **kwargs):
    """
    监听请求失败事件，记录错误详情
    """
    if exception:
        # 判断错误类型
        error_type = "未知异常"
        exception_str = str(exception)
        
        if "连接" in exception_str or "Connection" in exception_str or "timeout" in exception_str.lower():
            error_type = "网络异常"
        elif "断言" in exception_str or "Assertion" in exception_str:
            error_type = "断言失败"
        elif "业务" in exception_str or "success" in exception_str.lower():
            error_type = "业务异常"
        
        # 获取用户ID（如果可用）
        user_id = kwargs.get("user_id") or kwargs.get("context", {}).get("user_id")
        
        # 记录错误
        error_recorder.record_error(
            name=name,
            exception=exception,
            response_time=response_time,
            request_params=kwargs.get("request_params"),
            response_data=kwargs.get("response_data"),
            user_id=user_id,
            error_type=error_type
        )


def on_test_stop(environment, **kwargs):
    """
    压测结束时，导出错误详情报告
    """
    error_summary = error_recorder.get_error_summary()
    
    if error_summary:
        print("\n" + "="*80)
        print("【错误详情摘要】")
        print("="*80)
        for name, summary in error_summary.items():
            print(f"\n接口: {name}")
            print(f"  总错误数: {summary['total_errors']}")
            print(f"  错误类型分布: {summary['error_types']}")
            if summary['latest_error']:
                print(f"  最新错误: {summary['latest_error']['exception']}")
        print("="*80 + "\n")
        
        # 导出到文件
        error_recorder.export_to_json()
    else:
        print("\n✅ 本次压测无错误记录\n")


# 注册事件监听器
# on_request_failure 注册为 events.request 的监听器
# on_test_stop 注册为 events.test_stop 的监听器
events.request.add_listener(on_request_failure)  # 被environment.events.request.fire的exception触发
events.test_stop.add_listener(on_test_stop)      # 压测结束时触发
