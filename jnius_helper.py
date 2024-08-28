__all__ = ('autoclass', "java_method", 'PythonJavaClass')

from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, java_method, PythonJavaClass
else:
    def autoclass(*_):
        return lambda *x: x

    def java_method(*_, **__):
        pass

    class PythonJavaClass:
        def __init__(self, *_):
            pass
