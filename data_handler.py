import json

from custom_errors import SaveFailedException
from jnius_helper import autoclass

String = autoclass('java.lang.String')
KeyStore = autoclass('java.security.KeyStore')
KeyGenerator = autoclass('javax.crypto.KeyGenerator')
Cipher = autoclass('javax.crypto.Cipher')
Base64 = autoclass('android.util.Base64')
KeyGenParameterSpec = autoclass('android.security.keystore.KeyGenParameterSpec')
KeyProperties = autoclass('android.security.keystore.KeyProperties')

DATA_ENCODING_ALGORITHM: str = "AES"
KEYSTORE_PROVIDER: str = "AndroidKeyStore"
KEY_ALIAS: str = "my_key"


class _DefaultUIData:
    def __init__(self):
        self.data = {'daily_ad_available_reward_type': [['color_palette', 0.8],
                                                        ['corner_rounded', 0.2]],
                     'closed_color_palettes': ['Red',
                                               'Pink',
                                               'Purple',
                                               'DeepPurple',
                                               'Indigo',
                                               'Blue',
                                               'DeepOrange',
                                               'Brown',
                                               'BlueGray'],
                     'color_palette': 'Teal',
                     'theme': 'Dark',
                     'is_new_color_opened': False,
                     'opened_palettes': ['Teal'],
                     'ad_view_daily_streak': 0,
                     'this_day_viewed_ad_count': 0,
                     'last_ad_view_day': None,
                     'is_rounded_corner': False,
                     'is_rounded_corner_opened': False}


class UIDataHandler:
    __file_name = 'UIData.json'

    def __init__(self):
        self.data: dict = {}

    def load_data(self) -> None:
        try:
            with open(self.__file_name, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = _DefaultUIData().data
            self.dump()
        except json.decoder.JSONDecodeError:
            self.data = _DefaultUIData().data
            self.dump()

    def dump(self):
        try:
            with open(self.__file_name, 'w+') as file:
                json.dump(self.data, file)
        except PermissionError:
            raise SaveFailedException('Failed to save UI data, permission error',
                                      short_error='Permission error')
        except Exception:
            raise SaveFailedException('Failed to save UI data, something went wrong',
                                      short_error='Something went wrong')

    def __getitem__(self, item):
        return self.data.get(item, None)

    def __setitem__(self, key, value):
        self.data[key] = value


class EssentialDataHandler:
    pass


class CryptoLocker:
    pass


class SecreteData:
    def __init__(self):
        self.__data: dict = {}
        self._load()

    def _load(self):
        try:
            with open('SECRETS.json', 'r') as file:
                self.__data = json.load(file)
        except FileNotFoundError:
            pass

    def __getitem__(self, item):
        self.__data.get(item, '')

    @property
    def data(self):
        return self.__data


if __name__ == '__main__':
    data = UIDataHandler()
    try:
        data.dump()
        data.load_data()
        a = data['theme']
    except SaveFailedException:
        import traceback
        print(traceback.format_exc())
        print('Hurray')
    print(data.data)
