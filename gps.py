"""
In this file we handel mobile GPS
"""
# todo delete unused modules
import random
import time
from collections.abc import Callable
from threading import Thread

import plyer
from custom_errors import GPSNotImplementedError
from jnius_helper import autoclass

content_Context = autoclass('android.content.Context')
LocationManager = autoclass('android.location.LocationManager')


class GPS:
    def __init__(self):
        self.status_change_callback: list[Callable] = []
        self.location_change_callback: list[Callable] = []

        self.location: dict = None
        self.stype = None
        self.status = None
        self.is_configured = False

        self.is_active = False

        # self.location_manager = mActivity.getSystemService(content_Context.LOCATION_SERVICE)
        # related to get_last_known_location function

    def register_callback(self, location_change_callback: Callable, status_change_callback: Callable):
        """
        Functions to call when the respective event is triggered
        :param location_change_callback:
        :param status_change_callback:
        :return:
        """
        self.status_change_callback.append(status_change_callback)
        self.location_change_callback.append(location_change_callback)
        return len(self.status_change_callback)-1

    def unregister_callback(self, trg: int | Callable) -> None:
        if callable(trg):
            for index, val in enumerate(self.status_change_callback):
                if val is trg:
                    self.status_change_callback.pop(index)
                    self.location_change_callback.pop(index)
                    break
        elif type(trg) is int:
            self.status_change_callback.pop(trg)
            self.location_change_callback.pop(trg)

    def configure(self, raise_error: bool = True) -> bool:
        """
        Configures GPS listeners
        :param raise_error: if set False error will be suppressed and return weather errors were occurred or not
        :return: boolean GPS configured, (NOTE: Boolean is returned only when the raise_error set False otherwise
          error is raised)
        """
        is_error = False
        try:
            plyer.gps.configure(on_status=self.__on_status, on_location=self.__on_location)
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
            if not raise_error:  # return state if not said to raise error (for debugging)
                return is_error

    def __on_status(self, stype='', status=''):
        self.stype = stype
        self.status = status
        for callback in self.status_change_callback:
            callback(stype, status)

    def __on_location(self, **kwargs):
        self.location = kwargs.copy()
        for callback in self.location_change_callback:
            callback(kwargs)

    def start(self):
        """
        Starts receiving GPS updates
        :return:
        :raises: NotImplementedError
        """
        plyer.gps.start()
        self.is_active = True

    def stop(self):
        plyer.gps.stop()
        self.is_active = False

    def non_android(self):
        # todo delete this
        self.is_active = True
        p = Thread(target=self.__repeater, daemon=True)
        p.start()

    def __repeater(self):
        # todo delete this function
        while True:
            time.sleep(5)
            self.__on_location(lat=random.randint(-90000, 90000)/1000,
                               lon=random.randint(-180000, 180000)/1000,
                               heading=random.randint(0, 360000)/1000,
                               bearing=random.randint(0, 360000)/1000,
                               speed=random.randint(0, 360000)/1000)

    # def get_last_known_location(self) -> tuple[int, int] | None:
    #     location = self.location_manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
    #     if location is not None:
    #         latitude = location.getLatitude()
    #         longitude = location.getLongitude()
    #         return latitude, longitude
    #     return None
