from typing import Callable

_post_init_manager_func = []
_pre_init_manager_func = []

_post_init_manager_func_l2 = []
_pre_init_manager_func_l2 = []

_shutdown_func = []


def post_init_manager(func: Callable):
    """注册初始化各种管理器后需要执行的函数，适用于一下要获取配置项的时候用"""
    _post_init_manager_func.append(func)
    return func


def post_init_manager_l2(func: Callable):
    """注册初始化各种管理器后需要执行的函数，权重更低"""
    _post_init_manager_func_l2.append(func)
    return func


def pre_init_manager(func: Callable):
    """注册初始化各种管理器前需要执行的函数，适用于一下要获取配置项的时候用"""
    _pre_init_manager_func.append(func)
    return func


def pre_init_manager_l2(func: Callable):
    """注册初始化各种管理器前需要执行的函数，适用于一下要获取配置项的时候用"""
    _pre_init_manager_func_l2.append(func)
    return func


def shutdown(func: Callable):
    """关闭时候的方法"""
    _shutdown_func.append(func)
    return func
