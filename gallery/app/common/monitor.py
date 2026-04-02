import time
import numpy as np
import os
import psutil
from functools import wraps
from memory_profiler import memory_usage
import csv
def get_process_memory():
    
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  
def get_accurate_memory():
    psutil_mem = get_process_memory()
    mprof_mem = memory_usage(-1, interval=0.5, timeout=1)[0]
    return (psutil_mem + mprof_mem) / 2
# class PerformanceMonitor:
#     def __init__(self):
#         self.process = psutil.Process(os.getpid())
    
#     def __call__(self, func):
#         @wraps(func)
#         def wrapped(instance):
#             start_time = time.perf_counter()
#             # mem_before = memory_usage(-1, interval=0.1, timeout=1)[0]
#             mem_before = self.process.memory_info().rss / 1024 / 1024
#             cpu_before = self.process.cpu_percent(interval=None)
            
#             result = func(instance)
            
#             end_time = time.perf_counter()
#             # mem_after = memory_usage(-1, interval=0.1, timeout=1)[0]
#             mem_after = self.process.memory_info().rss / 1024 / 1024
#             cpu_after = self.process.cpu_percent(interval=None)
            
#             exec_time = end_time - start_time
#             mem_used = mem_after - mem_before
#             cpu_used = cpu_after - cpu_before
            
            
#             return result
#         return wrapped
class PerformanceMonitor:
    def __init__(self, samples=10):
        
        self.samples = samples
        self.process = psutil.Process(os.getpid())
        self.process.cpu_percent(interval=None)
    
    def __call__(self, func):
        @wraps(func)
        def wrapped(instance):
            
            self.process.cpu_percent(interval=None)
            
            exec_times = []
            mem_usages = []
            cpu_usages = []
            
            for i in range(self.samples):
                import gc
                gc.collect()
                
                start_time = time.perf_counter()
                
                mem_before = self.process.memory_info()
                cpu_before = self.process.cpu_percent(interval=None)
                
                result = func(instance)
                
                end_time = time.perf_counter()
                mem_after = self.process.memory_info()
                cpu_after = self.process.cpu_percent(interval=None)
                
                exec_time = end_time - start_time
                
                mem_used = (mem_after.rss - mem_before.rss) / (1024 * 1024)
                
                cpu_used = cpu_after - cpu_before
                
                exec_times.append(exec_time)
                mem_usages.append(mem_used)
                cpu_usages.append(cpu_used)
                
                if i < self.samples - 1:
                    time.sleep(0.1)
            
            with open("E:\learningData\BIBM paper submission\log_all.csv", 'a') as file:
                writer = csv.writer(file)
                for i in range(10):
                    writer.writerow([exec_times[i], mem_usages[i], cpu_usages[i]])

            avg_time = np.mean(exec_times) * 1000  
            avg_mem = np.mean(mem_usages)
            avg_cpu = np.mean(cpu_usages)
            
            std_time = np.std(exec_times) * 1000
            std_mem = np.std(mem_usages)
            std_cpu = np.std(cpu_usages)
            
            print(f"\n{func.__name__} 性能指标 ({self.samples}次采样):")
            print(f"├─ 执行时间: {avg_time:.2f} ± {std_time:.2f} 毫秒")
            print(f"├─ 内存消耗: {avg_mem:.2f} ± {std_mem:.2f} MiB")
            print(f"└─ CPU占用: {avg_cpu:.2f} ± {std_cpu:.2f}%")

            with open("E:\learningData\BIBM paper submission\log.csv", 'a') as file:
                writer = csv.writer(file)
                writer.writerow([f"{avg_time:.2f} ± {std_time:.2f}", f"{avg_mem:.2f} ± {std_mem:.2f}", f"{avg_cpu:.2f} ± {std_cpu:.2f}"])
            
            return result
        return wrapped