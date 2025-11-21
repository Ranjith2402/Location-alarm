import warnings


class Constants:
    DEFAULT_SECRETS_FILE_NAME = 'DEFAULT_SECRETS.json'
    SECRETS_FILE_NAME = 'SECRETS.json'
    PACKAGE_NAME = 'ranji.dev.location test-version'
    USER_DATA_FILE_NAME = 'gps data.lock'
    ESCAPE_CODE = 27
    ENTER_CODE = 13


class UserDataKeys:
    _full_address_key = 'full-address'
    _short_address_key = 'short-address'
    _input_cords_key = 'input-cords'
    _cords_key = 'cords'
    _active_weeks_key = 'active-weeks'
    _is_sound_active_key = 'is_sound-active'
    _is_vibrate_active_key = 'is-vibrate-active'
    _radius_key = 'radius'
    _sound_file_key = 'sound-file'


class UserDataHandler(UserDataKeys):
    """
    This class manages the UserData as same as its parent but also ensuring the key parity.
    (Writing the same key string is not usually hard, and we may change the key string in the future.
    So this class takes advantage of 'auto-complete' feature in the IDE, and hence it ensures the same key string.)
    Secondly, we save the data in 'json' format and applying another class to the data may take much more time.
    WARNING: DO NOT re-use this class anywhere outside this project
    """
    def __init__(self, data):
        self.__data = data

    def __getitem__(self, item):
        warnings.warn('Using key value method is discouraged, as it makes hard to keep up with the keys manually!\n'
                      f'Use property method instead, ex: data.{item}')
        return self.__data[item]

    @property
    def full_address(self) -> str:
        return self.__data.get(self._full_address_key, None)

#    @full_address.setter
#    def full_address(self, value):
#        pass

    @property
    def short_name(self) -> str:
        return self.__data.get(self._short_address_key, None)

#     @short_name.setter
#     def short_name(self, value):
#         pass

    @property
    def input_cords(self) -> str | None:
        return self.__data.get(self._input_cords_key, None)

#     @input_cords.setter
#     def input_cords(self, value):
#         pass

    @property
    def cords(self) -> tuple[float]:
        # print(self.__data)
        return self.__data[self._cords_key]

#     @cords.setter
#     def cords(self, value):
#         pass

    @property
    def active_weeks(self) -> list[str]:
        return self.__data.get(self._active_weeks_key, [])

#     @active_weeks.setter
#     def active_weeks(self, value):
#         pass

    @property
    def is_sound(self) -> bool:
        return self.__data.get(self._is_sound_active_key, False)

#     @is_sound.setter
#     def is_sound(self, value):
#         pass

    @property
    def is_vibrate(self) -> bool:
        return self.__data.get(self._is_vibrate_active_key, False)

#     @is_vibrate.setter
#     def is_vibrate(self, value):
#         pass

    @property
    def radius(self) -> int | float:
        return self.__data.get(self._radius_key, 50)

#     @radius.setter
#     def radius(self, value):
#         pass

    @property
    def sound_file(self) -> str | None:
        return self.__data.get(self._sound_file_key, None)

#     @sound_file.setter
#     def sound_file(self, value):
#         pass
