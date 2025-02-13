import time
from custom_threading import KillableThread

from threading import Thread
from collections.abc import Callable
from kivymd.uix.button import MDRectangleFlatButton


__all__ = ['LagRectangleFlatButton']


class LagButtonBase:
    """
    Base class that blocks button
    NOTE: DO NOT ADD '__init__' (it messes with the code)
    """

    button = None
    processes: list[KillableThread] = []
    is_running = False
    callback_functions: list[Callable] = []

    def initiate(self, button):
        """
        Used instead of __init__ as it overrides with the __init__ of the other class
        :param button:
        :return:
        """
        self.button = button
        # self.button.bind(on_release=self.disable_button)

    def disable_button(self, *_):
        self.button.disabled = True
        t = Thread(target=self._release_thread, daemon=True)
        t.start()

    def enable_button(self, *_):
        self.button.disabled = False

    def _release_thread(self):
        """
        This runs on a separate thread and waits till action to complete
        Not suppose to be called externally
        :return:
        """
        def is_any_alive(processes: list[KillableThread]):
            tmp = []
            for th in processes:
                if th.is_alive():
                    break
                else:
                    th.join()
                    tmp.append(th)
            else:  # loop completed normally
                for th in tmp:
                    processes.remove(th)  # Mutable
                return False
            return True

        if self.is_running:
            return
        self.is_running = True
        self.processes = [KillableThread(target=func, daemon=True) for func in self.callback_functions]
        for thread in self.processes:
            thread.start()
        print(self.processes)
        while is_any_alive(self.processes):
            time.sleep(0.1)  # for better performance
        # self.process.join()
        self.is_running = False
        self.processes: list[KillableThread] = []
        self.enable_button()

    def add_callback(self, func: Callable):
        """
        Currently kivy method can only add one function, this helps add more functions to callback
        :param func:
        :return:
        """
        self.callback_functions.append(func)

    def remove_callback(self, func: Callable):
        try:
            self.callback_functions.remove(func)
        except (ValueError, IndexError):
            print(f'Function \"{func.__name__}\" not found')

    def kill_all_threads(self):
        """
        Kills all running threads
        :return:
        """
        def threads_killer(threads: list[KillableThread]):
            for th in threads:
                if th.is_alive():
                    th.kill()
                    th.join()

        if self.is_running:
            threads_killer(self.processes)
            # this automatically releases thread
        self.processes: list[KillableThread] = []

    @property
    def lag_function(self) -> list[Callable]:
        """
        Returns added callback functions
        :return:
        """
        return self.callback_functions

    @lag_function.setter
    def lag_function(self, value: Callable) -> None:
        """
        Created to help with kv file since most of the time we need only one function to decide things
        :param value: function to run
        :return: None
        """
        self.callback_functions.append(value)


class LagRectangleFlatButton(MDRectangleFlatButton, LagButtonBase):
    """
    This class specifically designed to work to fetch location data
    But probably works everywhere with a small change in the release_function
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # the code should follow this pattern
        super().initiate(self)
        self.release_function: Callable = lambda *_: self.interval_sleeper(3, 0.2)
        self.add_callback(self.release_function)  # OSM request us to limit rate at 1 request per sec
        # Not faster than that

    def on_release(self):
        super().on_release()
        self.disable_button()

    @staticmethod
    def interval_sleeper(t: float | int, interval: float | int = 0.1):
        """
        time.sleep holds the process not letting to kill, this function splits the sleep time and allows to be killed.
        keep in mind that the interval is the perfect divisor of time; or else it would take much longer than excepted
        :param t: time in seconds
        :param interval: max delay, must not be zero
        :return: nothing
        """
        s_time = time.time()
        while time.time() - s_time < t:
            time.sleep(interval)
