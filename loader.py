import os
import importlib
import inspect

def load_plugins(folder, base_class, *init_args):
    instances = []

    for file in os.listdir(folder):
        if file.endswith(".py") and file != "__init__.py":

            module_name = folder.replace("/", ".") + "." + file[:-3]
            module = importlib.import_module(module_name)

            for _, obj in inspect.getmembers(module, inspect.isclass):

                if (
                    issubclass(obj, base_class)
                    and obj is not base_class
                ):
                    instance = obj(*init_args)
                    instances.append(instance)

    return instances