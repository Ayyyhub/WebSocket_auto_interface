# locust_performance/scenarios_stats.py
import os
import time
import functools
from collections import defaultdict
from datetime import datetime
from utils.logger import logger
import gevent.lock
import gevent
import json

class ScenarioStats:
    """
    场景级统计管理器
    统计每个场景的执行次数、成功率、耗时等指标
    """
    _instance = None
    _lock = gevent.lock.Semaphore()
    # gevent.lock.Semaphore()特点：
    # - 基于 gevent 协程
    # - 在 gevent 环境中不会阻塞整个线程
    # - 只阻塞当前协程，其他协程可以继续运行
    
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
            
        # 统计场景数据共享字典
        self.shared_stats = defaultdict(lambda: {
            "total_count": 0,
            "success_count": 0,
            "fail_count": 0,
            "response_times": []
        })
        self._lock = gevent.lock.Semaphore()
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
        elapsed_time = (time.perf_counter() - start_time) * 1000
        
        # 使用非阻塞方式获取锁，避免卡住
        if self._lock.acquire(blocking=False):
            try:
                stats = self.shared_stats[scenario_name]              # 1. 读取
                stats["total_count"] += 1                       # 2. 读取 + 计算 + 写入（3步操作！） 
                stats["response_times"].append(elapsed_time)    # 3. 读取 + 修改 + 写入
                
                if success: 
                    stats["success_count"] += 1                 # 4. 读取 + 修改 + 写入
                else:
                    stats["fail_count"] += 1
            finally:
                self._lock.release()
        else:
            # 如果无法获取锁，记录警告但不阻塞
            logger.warning(f"无法获取锁记录场景统计: {scenario_name}")
    
    def _get_stats_snapshot(self):
        """
        获取统计数据的快照（不使用锁，直接复制数据）
        用于 test_stop 时生成报告，避免死锁
        """
        snapshot = {}
        try:
            # 尝试非阻塞获取锁
            if self._lock.acquire(blocking=False):
                try:
                    for name, stats in self.shared_stats.items():
                        snapshot[name] = {
                            "total_count": stats["total_count"],
                            "success_count": stats["success_count"],
                            "fail_count": stats["fail_count"],
                            "response_times": stats["response_times"].copy()  # 深拷贝列表
                        }
                finally:
                    self._lock.release()
            else:
                # 如果无法获取锁，使用当前数据（可能不完整，但不会卡住）
                logger.warning("无法获取锁，使用当前数据快照（可能不完整）")
                for name, stats in self.shared_stats.items():
                    snapshot[name] = {
                        "total_count": stats["total_count"],
                        "success_count": stats["success_count"],
                        "fail_count": stats["fail_count"],
                        "response_times": stats["response_times"].copy()
                    }
        except Exception as e:
            logger.error(f"获取统计数据快照失败: {e}")
        
        return snapshot
    
    def get_stats(self):
        """获取所有场景统计"""
        if self._lock.acquire(blocking=False):
            try:
                return dict(self.shared_stats)
            finally:
                self._lock.release()
        else:
            return {}
    
    def get_scenario_stats(self, scenario_name, snapshot=None):
        """
        获取指定场景的统计
        :param scenario_name: 场景名称
        :param snapshot: 可选的数据快照（用于避免锁）
        """
        if snapshot:
            stats = snapshot.get(scenario_name)
        else:
            if not self._lock.acquire(blocking=False):
                return None
            try:
                stats = self.shared_stats.get(scenario_name)
            finally:
                self._lock.release()
        
        if not stats:
            return None
        
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
    
    def get_summary_report(self, use_snapshot=True):
        """
        获取汇总报告
        :param use_snapshot: 是否使用快照（避免锁）
        """
        if use_snapshot:
            # 使用快照，避免死锁
            snapshot = self._get_stats_snapshot()
            report = {
                "report_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "scenarios": {}
            }
            
            for scenario_name in snapshot.keys():
                report["scenarios"][scenario_name] = self.get_scenario_stats(scenario_name, snapshot=snapshot)
            
            return report
        else:
            # 使用锁（可能卡住，不推荐在 test_stop 时使用）
            try:
                if self._lock.acquire(blocking=False):
                    try:
                        report = {
                            "report_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "scenarios": {}
                        }
                        
                        for scenario_name in self.shared_stats.keys():
                            report["scenarios"][scenario_name] = self.get_scenario_stats(scenario_name)
                        
                        return report
                    finally:
                        self._lock.release()
                else:
                    logger.warning("无法获取锁生成报告，返回空报告")
                    return {
                        "report_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "scenarios": {},
                        "error": "无法获取锁"
                    }
            except Exception as e:
                logger.warning(f"获取场景统计报告失败: {e}")
                return {
                    "report_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "scenarios": {},
                    "error": str(e)
                }
    
    # def print_summary(self):
    #     """打印统计摘要到控制台"""
    #     report = self.get_summary_report()
        
    #     print("\n" + "="*80)
    #     print("【场景级统计报告】")
    #     print("="*80)
        
    #     for scenario_name, stats in report.get("scenarios", {}).items():
    #         if stats is None:
    #             continue
    #         print(f"\n场景: {scenario_name}")
    #         print(f"  总执行次数: {stats.get('total_count', 0)}")
    #         print(f"  成功次数: {stats.get('success_count', 0)}")
    #         print(f"  失败次数: {stats.get('fail_count', 0)}")
    #         print(f"  成功率: {stats.get('success_rate', 0)*100:.2f}%")
    #         print(f"  平均耗时: {stats.get('avg_time_ms', 0):.2f}ms")
    #         print(f"  最小耗时: {stats.get('min_time_ms', 0):.2f}ms")
    #         print(f"  最大耗时: {stats.get('max_time_ms', 0):.2f}ms")
    #         print(f"  P50耗时: {stats.get('p50_time_ms', 0):.2f}ms")
    #         print(f"  P90耗时: {stats.get('p90_time_ms', 0):.2f}ms")
    #         print(f"  P95耗时: {stats.get('p95_time_ms', 0):.2f}ms")
    #         print(f"  P99耗时: {stats.get('p99_time_ms', 0):.2f}ms")
        
    #     print("="*80 + "\n")
    
    def export_to_json(self, filepath="locust_scenario_stats.json"):
        """导出场景统计到JSON文件"""
        if not os.path.isabs(filepath):
            base_dir = os.path.dirname(__file__)
            filepath = os.path.join(base_dir, filepath)
        # 使用快照，避免死锁
        report = self.get_summary_report(use_snapshot=True)
        
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
        if self._lock.acquire(blocking=False):
            try:
                self.shared_stats.clear()
            finally:
                self._lock.release()


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


# 在压测结束时导出统计报告
from locust import events

def on_test_stop_scenario_stats(environment, **kwargs):
    """压测结束时，导出场景统计"""
    try:
        # 使用 gevent.spawn 异步处理，避免阻塞主事件循环
        gevent.spawn(scenario_stats.export_to_json)
        # 给一点时间让异步任务启动
        gevent.sleep(0.1)
    except Exception as e:
        logger.error(f"场景统计报告生成失败: {e}")


# 注册事件监听器
events.test_stop.add_listener(on_test_stop_scenario_stats)