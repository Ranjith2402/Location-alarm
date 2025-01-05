"""
Since jinus is not works on Windows, this files helps debugging easy and not have any special impact whatsoever
"""

__all__ = ('autoclass', "java_method", 'PythonJavaClass', 'mActivity', 'PythonActivity', 'jnius', 'JniusJavaException')

from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, java_method, PythonJavaClass  # NOQA
    import jnius  # noqa
    JniusJavaException = jnius.jnius.JavaException  # noqa
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    mActivity = PythonActivity.mActivity
else:

    JniusJavaException = Exception

    def java_method(*_, **__):
        pass

    class autoclass:  # NOQA
        def __init__(self, *_):
            pass

        def __call__(self, *args, **kwargs):
            pass

        @property
        def LOCATION_SERVICE(self):  # NOQA
            return 1

    class mActivity:  # NOQA
        def __init__(self, *_):
            pass

        @staticmethod
        def getSystemService(*_):  # NOQA
            return lambda *_: _

    class PythonJavaClass:
        def __init__(self, *_):
            pass
