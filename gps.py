"""
In this file we handel mobile GPS
"""
from typing import Callable

import plyer
from custom_errors import GPSNotImplementedError


class GPS:
    def __init__(self):
        self.status_change_callback = lambda: None
        self.location_change_callback = lambda: None
        self.is_callback_set = False

        self.location = None
        self.stype = None
        self.status = None
        self.is_configured = False

    def set_callback(self, status_change_callback: Callable, location_change_callback: Callable):
        self.status_change_callback = status_change_callback
        self.location_change_callback = location_change_callback
        self.is_callback_set = True

    def configure(self, raise_error: bool = True) -> bool:
        """
        Configures GPS listeners
        :param raise_error: if set False error will be suppressed and returns are error occurred or not
        :return: boolean GPS configured, (NOTE: Boolean is returned only when the raise_error set False otherwise
          error is raised)
        """
        is_error = False
        try:
            plyer.gps.configure(on_status=self.on_status, on_location=self.on_location)
            self.is_configured = True
        except NotImplementedError:
            is_error = True
            if raise_error:
                raise GPSNotImplementedError(short_error="GPS not implemented")
        except ModuleNotFoundError:
            is_error = True
            if raise_error:
                raise GPSNotImplementedError(short_error='This feature is available on Android and IOS')
        finally:
            if not raise_error:
                return is_error

    def on_status(self, stype='', status=''):
        self.stype = stype
        self.status = status
        self.status_change_callback()

    def on_location(self, **kwargs):
        self.location = kwargs.copy()
        self.location_change_callback()

    @staticmethod
    def start():
        plyer.gps.start()

    @staticmethod
    def stop():
        plyer.gps.stop()

