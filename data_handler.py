import json
import random

from hashlib import sha256, sha384

from custom_errors import SaveFailedException, MissingFileError
from jnius_helper import autoclass, JniusJavaException, String
from tools import Constants

KeyStore = autoclass('java.security.KeyStore')
KeyGenerator = autoclass('javax.crypto.KeyGenerator')
Cipher = autoclass('javax.crypto.Cipher')
Base64 = autoclass('android.util.Base64')
KeyGenParameterSpec = autoclass('android.security.keystore.KeyGenParameterSpec')
KeyProperties = autoclass('android.security.keystore.KeyProperties')

DATA_ENCODING_ALGORITHM: str = "AES"
KEYSTORE_PROVIDER: str = "AndroidKeyStore"
KEY_ALIAS: str = "my_key"

CryptoLockerJava = autoclass('ranji.dev.CryptoLocker')


def sha256_encrypt(text: str, encode_mode: str = 'utf-8') -> str:
    return sha256(text.encode(encode_mode)).hexdigest()


def sha384_encrypt(text: str, encode_mode: str = 'utf-8') -> str:
    return sha384(text.encode(encode_mode)).hexdigest()


def password_encrypt(password: str, encode_mode: str = 'utf-8') -> str:
    return sha256_encrypt(password, encode_mode) + sha384_encrypt(password, encode_mode)


class _DefaultUIData:
    """
    This class restores Default UI Data if anything goes wrong and while first login
    """
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
                json.dump(self.data, file, indent='  ', separators=(',', ': '))
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
    def __init__(self, password: str):
        self.password = String(password)


class CryptoLocker:
    def __init__(self, key_alias: str):
        self.crypto_locker = CryptoLockerJava()

        self.__KEY_ALIAS = key_alias

        self._key = None

    def __get_key(self, password: String):
        self._key = self.crypto_locker.getKey(self.key_alias, password)
        return self._key

    def _store_key(self, password: String):
        """
        The key is automatically stored in java code (This code probably not needed)
        :param password: password what else?
        :return: Nothing
        """
        if self._key is not None:
            self.crypto_locker.storeKey(self._key, self.key_alias, password)
        else:
            pass

    def check_password(self, password: str):
        try:
            self.__get_key(String(password))
            return True
        except JniusJavaException:
            return False

    @property
    def key_alias(self):
        return self.__KEY_ALIAS

    @key_alias.setter
    def key_alias(self, value: str):
        self.__KEY_ALIAS = String(value)

    @staticmethod
    def generate_new_password() -> str:
        chars = "aAbBcCdDeEfFgGhHiIjJkKlLmMnNoOpPqQrRsStTuUvVwWxXyYzZ1234567890.,<>/?'[]{}()-_=+!@#$%^&*~`\""
        password = ''

        # using random may not be a secure idea,
        # but, change it later (if I remember) ;)

        # uses seed change algorithm developed by me :)
        for i in range(random.randint(32, 128)):
            random.seed = random.randint(2 ** 10, 2 ** 100)

        for i in range(random.randint(32, 128)):
            password += random.choice(chars)

        return password

    def encrypt_text(self, text: str, password: str) -> str:
        self.__get_key(password)
        return self.crypto_locker.encryptText(String(text), self._key)

    def decrypt_text(self, encrypted_text: str, password: str) -> str:
        self.__get_key(password)
        return self.crypto_locker.decryptText(String(encrypted_text), self._key)


class _DefaultSecreteData:
    def __init__(self):
        self.is_error = False
        self._data = {}

    @property
    def data(self):
        return self._data

    def load(self):
        try:
            with open(Constants.DEFAULT_SECRETS_FILE_NAME, 'r') as file:
                self._data = json.load(file)
                return True
        except FileNotFoundError:
            self.is_error = True
            return False


class SecreteData:
    def __init__(self):
        self.is_error = False  # This variable must be created before loading data
        self.__data: dict = {}
        self._load()

    def _load(self):
        try:
            with open(Constants.SECRETS_FILE_NAME, 'r') as file:
                self.__data = json.load(file)
        except FileNotFoundError:
            tmp = _DefaultSecreteData()
            if tmp.load():
                self.data = tmp.data
                self.save_data()
            else:
                self.is_error = True

    def __raise_file_not_found_error(self):
        raise MissingFileError('Missing required "secrets" file!!!\nPlease reinstall the app', is_write_log=True)

    def __getitem__(self, item):
        if self.is_error:
            self.__raise_file_not_found_error()
        return self.__data.get(item, '')

    def __setitem__(self, key: str, value):
        if self.is_error:
            self.__raise_file_not_found_error()
        self.__data[key] = value
        self.save_data()

    def save_data(self):
        try:
            with open(Constants.SECRETS_FILE_NAME, 'w+') as file:
                json.dump(self.__data, file, indent=' ' * 4, separators=(',', ': '))
        except OSError:
            raise SaveFailedException('Unable to save  "secrets" file')

    @property
    def data(self):
        if self.is_error:
            self.__raise_file_not_found_error()
        return self.__data

    @data.setter
    def data(self, __value: dict):
        self.__data = __value
        self.save_data()


if __name__ == '__main__':
    data = UIDataHandler()
    try:
        # data.dump()
        data.load_data()
        a = data['theme']
    except SaveFailedException:
        import traceback
        print(traceback.format_exc())
        print('Hurray')
    print(data.data)
