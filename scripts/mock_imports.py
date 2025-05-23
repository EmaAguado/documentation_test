import builtins
import sys
import types

class SafeImporter:
    def __init__(self):
        self.original_import = builtins.__import__

    def fake_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        try:
            return self.original_import(name, globals, locals, fromlist, level)
        except ImportError:
            print(f"[mkdocs] Mocking missing import: {name}")
            module = types.ModuleType(name)
            sys.modules[name] = module
            return module

    def install(self):
        builtins.__import__ = self.fake_import

    def uninstall(self):
        builtins.__import__ = self.original_import

# Instalar el mock global
SafeImporter().install()
