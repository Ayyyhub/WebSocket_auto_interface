# locust_performance/scenario_stats.py
import os
import time
import functools
from collections import defaultdict
from datetime import datetime
from utils.logger import logger
import threading
import json

class ScenarioStats:
    """
    场景级 统计管理器（有bug，待修复）
    统计每个场景的执行次数、成功率、耗时等指标
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ScenarioStats, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    

    def __init__(self):
        if self._initialized:
            return
        
        self._stats = defaultdict(lambda: {
            "total_count": 0,
            "success_count": 0,
            "fail_count": 0,
            "response_times": []
        })
        self._lock = threading.Lock()
        self._initialized = True
    
    def start_scenario(self, scenario_name):
        """场景开始执行"""
        return time.perf_counter()
    
    def end_scenario(self, scenario_name, start_time, success=True):
        """
        场景执行结束
        :param scenario_name: 场景名称
        :param start_time: 开始时间（perf_counter返回值）
        :param success: 是否成功
        """
        elapsed_time = (time.perf_counter() - start_time) * 1000  # 转换为毫秒
        
        with self._lock:
            stats = self._stats[scenario_name]
            stats["total_count"] += 1
            stats["response_times"].append(elapsed_time)
            
            if success:
                stats["success_count"] += 1
            else:
                stats["fail_count"] += 1
    
    def get_stats(self):
        """获取所有场景统计"""
        with self._lock:
            return dict(self._stats)
    
    def get_scenario_stats(self, scenario_name):
        """获取指定场景的统计"""
        with self._lock:
            if scenario_name not in self._stats:
                return None
            
            stats = self._stats[scenario_name]
            response_times = stats["response_times"]
            
            if not response_times:
                return {
                    "scenario_name": scenario_name,
                    "total_count": stats["total_count"],
                    "success_count": stats["success_count"],
                    "fail_count": stats["fail_count"],
                    "success_rate": 0.0
                }
            
            # 计算统计指标
            sorted_times = sorted(response_times)
            total = len(sorted_times)
            
            return {
                "scenario_name": scenario_name,
                "total_count": stats["total_count"],
                "success_count": stats["success_count"],
                "fail_count": stats["fail_count"],
                "success_rate": stats["success_count"] / stats["total_count"] if stats["total_count"] > 0 else 0.0,
                "avg_time_ms": sum(response_times) / total,
                "min_time_ms": min(response_times),
                "max_time_ms": max(response_times),
                "p50_time_ms": sorted_times[int(total * 0.5)] if total > 0 else 0,
                "p90_time_ms": sorted_times[int(total * 0.9)] if total > 0 else 0,
                "p95_time_ms": sorted_times[int(total * 0.95)] if total > 0 else 0,
                "p99_time_ms": sorted_times[int(total * 0.99)] if total > 0 else 0,
            }
    
    def get_summary_report(self):
        """获取汇总报告"""
        with self._lock:
            report = {
                "report_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "scenarios": {}
            }
            
            for scenario_name in self._stats.keys():
                report["scenarios"][scenario_name] = self.get_scenario_stats(scenario_name)
            
            return report
    
    def print_summary(self):
        """打印统计摘要到控制台"""
        report = self.get_summary_report()
        
        print("\n" + "="*80)
        print("【场景级统计报告】")
        print("="*80)
        
        for scenario_name, stats in report["scenarios"].items():
            print(f"\n场景: {scenario_name}")
            print(f"  总执行次数: {stats['total_count']}")
            print(f"  成功次数: {stats['success_count']}")
            print(f"  失败次数: {stats['fail_count']}")
            print(f"  成功率: {stats['success_rate']*100:.2f}%")
            print(f"  平均耗时: {stats['avg_time_ms']:.2f}ms")
            print(f"  最小耗时: {stats['min_time_ms']:.2f}ms")
            print(f"  最大耗时: {stats['max_time_ms']:.2f}ms")
            print(f"  P50耗时: {stats['p50_time_ms']:.2f}ms")
            print(f"  P90耗时: {stats['p90_time_ms']:.2f}ms")
            print(f"  P95耗时: {stats['p95_time_ms']:.2f}ms")
            print(f"  P99耗时: {stats['p99_time_ms']:.2f}ms")
        
        print("="*80 + "\n")
    
    def export_to_json(self, filepath="locust_scenario_stats.json"):
        """导出场景统计到JSON文件"""
        # 如果传入的是相对路径，则相对于当前模块所在目录（locust_performance）
        if not os.path.isabs(filepath):     # 如果不是绝对路径abs
            base_dir = os.path.dirname(__file__)
            filepath = os.path.join(base_dir, filepath)
        report = self.get_summary_report()
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"场景统计已导出到: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"导出场景统计失败: {e}")
            return None
    
    def clear(self):
        """清空统计"""
        with self._lock:
            self._stats.clear()


# 全局场景统计实例
scenario_stats = ScenarioStats()


def scenario_tracker(scenario_name):
    """
    场景统计装饰器
    用法：
        @scenario_tracker("load_model_flow")
        def load_model_flow(user_instance):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user_instance, *args, **kwargs):
            start_time = scenario_stats.start_scenario(scenario_name)
            success = False
            try:
                result = func(user_instance, *args, **kwargs)
                success = True
                return result
            except Exception as e:
                logger.error(f"[场景失败] {scenario_name}: {e}")
                raise
            finally:
                scenario_stats.end_scenario(scenario_name, start_time, success=success)
        
        return wrapper
    return decorator


# 在压测结束时打印和导出统计报告
from locust import events

def on_test_stop_scenario_stats(environment, **kwargs):
    """压测结束时，打印和导出场景统计"""
    scenario_stats.print_summary()      # 打印到控制台
    scenario_stats.export_to_json()     # 不管是单接口还是工作流压测，都导出场景统计报告


# 注册事件监听器
events.test_stop.add_listener(on_test_stop_scenario_stats)