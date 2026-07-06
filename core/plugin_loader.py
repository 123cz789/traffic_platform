import importlib
import inspect
from core.base_module import BaseModule


class PluginLoader:
    @staticmethod
    def load_module(module_name):
        module = importlib.import_module(f"modules.{module_name}")
        # 强制重新加载以确保代码更新
        importlib.reload(module)

        # 查找类名
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseModule) and obj is not BaseModule:
                return obj()  # 返回新的实例
        raise ImportError(f"No valid module found in {module_name}")