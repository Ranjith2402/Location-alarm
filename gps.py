"""
In this file we handel mobile GPS
"""

import plyer
from custom_errors import GPSNotImplementedError


class GPS:
    def __init__(self):
        self.location = None
        self.stype = None
        self.status = None
        self.is_configured = False

    def configure(self, raise_error: bool = True) -> bool:
        """
        Configures GPS listeners
        :param raise_error: if set False error will be suppressed and returns are error occurred or not
        :return:
        """
        is_error = False
        try:
            plyer.gps.configure(on_status=self.on_status, on_location=self.on_location)
        except NotImplementedError:
            is_error = True
            if raise_error:
                raise GPSNotImplementedError(short_error="GPS not implemented")
        except ModuleNotFoundError:
            is_error = True
            if raise_error:
                raise GPSNotImplementedError(short_error='This feature is available on Android and IOS')
        finally:
            self.is_configured = True
            if not raise_error:
                return is_error

    def on_status(self, stype='', status=''):
        self.stype = stype
        self.status = status

    def on_location(self, **kwargs):
        self.location = kwargs.copy()

    def start(self):
        pass

    def stop(self):
        pass

