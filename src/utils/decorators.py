"""
工具装饰器
提供重试、超时控制等常用装饰器
"""

import asyncio
import functools
import time
from typing import Callable, Any, Optional
import logging


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logging.warning(
                            f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}，"
                            f"{current_delay:.1f} 秒后重试..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"函数 {func.__name__} {max_attempts} 次尝试均失败")
            
            raise last_exception
        
        return wrapper
    return decorator


def timeout(seconds: float):
    """
    超时装饰器
    
    Args:
        seconds: 超时时间（秒）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), 
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"函数 {func.__name__} 执行超时 ({seconds}秒)"
                )
        
        return wrapper
    return decorator


def rate_limit(calls: int = 10, period: float = 1.0):
    """
    速率限制装饰器
    
    Args:
        calls: 时间窗口内的最大调用次数
        period: 时间窗口（秒）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        call_times = []
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal call_times
            
            # 清理过期的调用记录
            current_time = time.time()
            call_times = [t for t in call_times if current_time - t < period]
            
            # 检查是否超过限制
            if len(call_times) >= calls:
                sleep_time = period - (current_time - call_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                call_times = [t for t in call_times if current_time - t < period]
            
            result = await func(*args, **kwargs)
            call_times.append(time.time())
            return result
        
        return wrapper
    return decorator


def cache_result(ttl: float = 60.0, key_func: Optional[Callable] = None):
    """
    结果缓存装饰器
    
    Args:
        ttl: 缓存有效期（秒）
        key_func: 生成缓存键的函数，None则使用默认参数组合
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal cache
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = str(args) + str(sorted(kwargs.items()))
            
            # 检查缓存
            current_time = time.time()
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl:
                    return result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            
            # 清理过期缓存
            expired_keys = [
                k for k, (_, t) in cache.items() 
                if current_time - t > ttl
            ]
            for k in expired_keys:
                del cache[k]
            
            return result
        
        return wrapper
    return decorator


def log_execution(logger: Optional[logging.Logger] = None):
    """
    执行日志装饰器
    
    Args:
        logger: 日志记录器，None则使用默认
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            
            log.info(f"开始执行 {func.__name__}")
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                log.info(f"函数 {func.__name__} 执行成功，耗时 {elapsed:.2f} 秒")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                log.error(f"函数 {func.__name__} 执行失败，耗时 {elapsed:.2f} 秒: {e}")
                raise
        
        return wrapper
    return decorator


def validate_args(**validators):
    """
    参数验证装饰器
    
    Args:
        **validators: 参数验证函数，如 amount=lambda x: x > 0
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 验证关键字参数
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"参数 {param_name} 验证失败: {value}"
                        )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator</parameter>
</write_to_file>