__version__: str = '2.2.0'
__test_version__: str = 'alpha'

import os
import re
import sys
import ssl
import json
import time
import plyer
import random
import certifi
import webbrowser
from typing import Callable, NoReturn
from geopy.exc import GeocoderUnavailable

import gps
import data_handler
import exceptions_handler
from tools import Constants
from geocoding import GeocoderClient
from data_handler import password_encrypt
from jnius_helper import JniusJavaException
from custom_errors import SaveFailedException

from kivymd.app import MDApp
from kivymd.toast import toast as _toast
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.menu.menu import MDDropdownMenu
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.taptargetview import MDTapTargetView
from kivymd.uix.transition.transition import MDFadeSlideTransition
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDFillRoundFlatButton
from kivymd.uix.expansionpanel.expansionpanel import MDExpansionPanel, MDExpansionPanelThreeLine, \
    MDExpansionPanelTwoLine, MDExpansionPanelLabel

from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.uix.button import Button
from kivy.animation import Animation
from kivy.lang.builder import Builder
from kivy.uix.screenmanager import Screen
from kivy.core.window import WindowBase, EventLoop


# usual ritual to access the internet on android
context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

context.load_verify_locations(certifi.where())  # system CA files
context.verify_mode = ssl.CERT_REQUIRED

ssl._create_default_https_context = lambda *x: context


current_screen = previous_screen = 'signin'

unsigned_float_pattern = r'\d+(?:\.\d+)?'
decimal_regex_pattern = rf'[+-]?{unsigned_float_pattern}'  # r'[+-]?\d+\.\d+|[+-]?\d+'
dms_regex_pattern_NSEW_format = r'\d+\D\d+\D\d+\.?\d*[NSEW]'  # \d+\D\d+\D\d+(?:\.\d+)?[NSEW]  <-- preferable
dms_regex_pattern_sign_format = r'[+-]?\d+\D\d+\D\d+\.?\d*'

fun_toast_messages: list[str] = [
    'This feature is in development',
    'This feature also in development',
    'Even this feature is also in development',
    'This feature also is not working',
    'No, this won\'t work for now',
    'Under construction!!!',
    'Nothing happens',
    'Thanks for testing but not works for now',
    'I\'m sleeping, see you later',
    'Available in next update',
    'There is nothing in here',
    'This feature is still in development']
fun_index: int = 0
fun_ids: dict[str, list] = {}
fun_again_press: list[str] = [
    ' ',
    ':) ',
    'I told you, ',
    'Why are you trying to open it again and again, I\'m telling you, ',
    'IMPORTANT: ',
    'Read this carefully: ',
    'This is last time: ',
    ':( ',
    'Bruh, ',
    '']

error_handler = exceptions_handler.ErrorHandler('./Error log/')
secret_data = data_handler.SecreteData()

__version__ += " " * (bool(__test_version__)) + __test_version__  # Adds <space> and version if __test_version__ present

GPS = gps.GPS()
geocoding_client = GeocoderClient(ssl_context=context)
# ssl context on geopy won't be able to access the internet on android app, so changing it with custom ssl-context

is_first_login = False


# Kivy doesn't allow changing screen from outer thread other than kivy's (tested on windows)
# This function uses kivy's Clock to change screen
def change_screen_to(screen: str) -> None:
    global current_screen, previous_screen
    if current_screen != screen:
        previous_screen = current_screen
    current_screen = screen
    Clock.schedule_once(_set_screen, 0.0)


# Actual screen changing happens here
def _set_screen(_):
    # sm.current = current_screen
    screens.set_screen(current_screen)


last_esc_down = 0


# Response every keystroke including esc button
def keyboard_listener(_, key, *__) -> None | bool:
    global last_esc_down
    if key == Constants.ESCAPE_CODE:  # Esc button on Windows and back button on Android
        if sm.current in ('settings', 'saved_locations'):
            change_screen_to('home')
        elif sm.current in ('new_location',):
            change_screen_to(previous_screen)
        else:
            if time.time() - last_esc_down < 2.5:
                return
            last_esc_down = time.time()
            toast('Press again to exit')
        return True  # To future me, Returning true is like telling System/App "this stroke is captured"
    elif key == Constants.ENTER_CODE:  # Enter key
        if screens.screen in ('login', 'signin'):
            obj = screens.get_current_screen_obj()
            obj.enter_button()
        elif screens.screen in ('new_location',):
            obj = screens.get_current_screen_obj()
            obj.get_location_info()


last_toast_msg = ''
last_toast_time = time.time()


def toast(msg: str) -> None:
    global last_toast_msg, last_toast_time
    if msg == last_toast_msg and time.time() - last_toast_time <= 2.5:
        return
    _toast(msg)
    last_toast_time = time.time()
    last_toast_msg = msg


def regex_match_gps(text: str) -> list[list[str]]:
    """
    Returns GPS co-ordinates in a given string
    :param text: input string
    :return: list of matching items,
    three items -> NSEW (direction in the form of North, south, East or West)
    two items -> hour-minute-sec format (direction in signed form)
    one item -> decimal format
    empty list -> no match (not a valid co-ords)
    """
    text = text.upper()
    out = [re.findall(pattern, text) for pattern in [dms_regex_pattern_NSEW_format,
                                                     dms_regex_pattern_sign_format,
                                                     decimal_regex_pattern]]
    print(out)
    return out


def split_gps_deci_str(string: str) -> tuple:
    """
    Splits DMS string into separate integers and its direction
    :param string: DMS input
    :return: split text
    """
    out = re.findall(r'\d+', string)
    if len(out) == 4:  # and re.match(unsigned_float_pattern, string):
        # Decimal point to last number, if we use a float pattern, it won't match the rest
        try:
            out[2] += '.' + out.pop(3)

            # I am D\_/mb, so wrote this code
            # This divides the last number by its length and add it to the last number
            # tmp = int(out.pop(3))
            # out[2] += str(tmp / (10 * (1 + int(math.log(tmp, 10)))))[1::]  # It works :)
            # print(out)
        except ValueError:
            pass
    if string.startswith('-') or string.endswith('S') or string.endswith('W'):
        direction = -1
    else:
        direction = 1
    out = tuple(map(float, out))
    return *out, direction


def convert_gps_to_decimal_degree(deg: int, minute: int, sec: float, direction: int) -> float:
    """
    Converts GPS co-ordinates to decimal format
    :param deg: degree
    :param minute: minutes
    :param sec: seconds
    :param direction: direction
    :return: decimal co-ordinate
    """
    out_deci = deg + minute / 60 + sec / 3600
    if direction in ('W', 'S', '-', -1, '-1'):
        out_deci *= -1
    return out_deci


def validate_gps_cord(lat: str, lng: str) -> bool:
    """
    Checks whether the latitude and longitude is within range
    :param lat: latitude
    :param lng: longitude
    :return: Boolean whether it's a valid co-ords or not
    """
    try:
        lat = float(lat)
        lng = float(lng)
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return True
        return False
    except ValueError:
        return False


def split_lat_lng(text: str) -> tuple[float: 2] | None:
    """
    Split GPS cords of any format into latitude and longitude
    :param text:
    :return:
    """
    text = text.upper()
    regex_cords = regex_match_gps(text)
    for index, match in enumerate(regex_cords):
        if match:
            break
    else:
        return None  # No match (for loop ended normally without breaking)
    if len(match) != 2:  # there are more or less items (2 -> 1 latitude and 1 longitude)
        if index == 1 and len(match) == 1 and len(regex_cords[-1]) == 2:  # This case will solve problem like
            # '12.34 56.78' this is GPS co-ord in decimal from, but it also matches with DMS sign format
            index = 2
            match: list[str] = regex_cords[-1]
        else:
            return None
    if index < 2:  # Match index varies according to input format (<2 means It is in DMS format)
        split_lat = split_gps_deci_str(match[0])
        split_lng = split_gps_deci_str(match[1])
        if index == 0:
            # check the last letter, In-case they are swapped
            if match[0][-1] in ('S', 'N') and match[1][-1] in ('E', 'W'):
                pass
            elif match[0][-1] in ("E", "W") and match[1][-1] in ("N", "S"):
                split_lat, split_lng = split_lng, split_lat  # latitude and longitude are swapped
            else:
                return None
        if len(split_lat) == len(split_lng) == 4:  # 4 -> deg + min + sec + direction
            lat = convert_gps_to_decimal_degree(*split_lat)
            lng = convert_gps_to_decimal_degree(*split_lng)
        else:
            return None
    else:
        lat, lng = match
    return lat, lng


def validate_gps_co_ords(text: str) -> bool:
    """
    Validates GPS co-ordinates of any format
    :param text: Co-ordinates make sure to send capitalized text
    :return: boolean; True if it is valid, else False
    """
    out = split_lat_lng(text)
    if out is None:
        return False
    lat, lng = out
    return validate_gps_cord(lat, lng)


def dialog_type_1(title: str, msg: str, buttons: list[Button], auto_dismiss_on_button_press: bool = True,
                  dismissible: bool = True, on_dismiss_callback: Callable = None,
                  extra_callbacks: dict[str, Callable] = None, __force_un_dismissible: bool = False) -> MDDialog:
    """
    Creates a dialog box, to interact with user.
    :param title: Dialog title
    :param msg: Message to deliver
    :param buttons: buttons to interact with
    :param auto_dismiss_on_button_press: If set True dismisses dialog box after button press
    :param dismissible: If set True dismisses dialog even after no button press (Make sure to give buttons or else True
    is set automatically)
    :param on_dismiss_callback: Callback after closing dialog,
    :param extra_callbacks: Custom new unknowns callbacks.In the format -> callback_name to callback
    :param __force_un_dismissible: if you really wanted to create an un-dismissible dialog!
    :return: Dialog
    """
    dialog = MDDialog(
        title=title,
        text=msg,
        buttons=buttons)
    dialog.auto_dismiss = dismissible if buttons else True
    if __force_un_dismissible and not dismissible:
        dialog.auto_dismiss = False
    if auto_dismiss_on_button_press:
        for button in buttons:
            button.bind(on_release=dialog.dismiss)
    dialog.open()
    if on_dismiss_callback is not None:
        dialog.bind(on_dismiss=on_dismiss_callback)
    if extra_callbacks is not None:
        dialog.bind(**extra_callbacks)
    return dialog  # if you want to dismiss manually


def text_input_dialog(title: str,
                      buttons: list[Button] = None,
                      filler_text: str = '',
                      hint_text: str = '',
                      dismissible: bool = False,
                      auto_dismiss_on_button_press: bool = True,
                      on_dismiss_callback: Callable = None,
                      extra_callbacks: dict[str, Callable] = None,
                      __force_un_dismissible: bool = False):
    if buttons is None:
        buttons = []
    dialog = MDDialog(title=title,
                      buttons=buttons,
                      type='custom',
                      content_cls=TextInputDialogContent(text=filler_text,
                                                         hint_text=hint_text))
    dialog.auto_dismiss = dismissible if buttons else True
    if __force_un_dismissible and not dismissible:
        dialog.auto_dismiss = False
    if auto_dismiss_on_button_press:
        for button in buttons:
            button.bind(on_release=dialog.dismiss)
    dialog.open()
    if on_dismiss_callback is not None:
        dialog.bind(on_dismiss=on_dismiss_callback)
    if extra_callbacks is not None:
        dialog.bind(**extra_callbacks)
    return dialog


__log_to_send: str = ''


def send_log(_=None):
    if platform in ('android',):  # debug with 'win'
        send_email(recipient=secret_data['mail'],
                   msg=__log_to_send,
                   create_chooser='text')
        toast('Choose \'Gmail\' or \'WhatsApp\'')
    else:
        toast('This feature only available on android')


def send_email(msg: str, recipient: str, create_chooser: str = 'text'):
    plyer.email.send(recipient=recipient,
                     text=msg,
                     create_chooser=create_chooser)


def delete_log(_=None):
    try:
        error_handler.delete_error_log(error_handler.list_log_files()[0])
    except IndexError:  # FileNotFoundError is already handled
        pass


def common_pass_check(password: str):
    """
    Function to test password validity by maintaining the consistency
    :param password: password what else
    :return: bool
    """
    return True if 4 <= len(password) <= 16 else False


class TextInputDialogContent(MDBoxLayout):
    def __init__(self, *args, hint_text, text, **kwargs):
        super().__init__(*args, **kwargs)
        self.ids['text_field'].hint_text = hint_text
        self.ids['text_field'].text = text


class UserData:
    if platform == 'win':
        # FIXME: remove this
        _file_path = './tmp files'
        _data_file = os.path.join(_file_path, secret_data['user-data-file-name'])
        _backup_file = os.path.join(_file_path, secret_data['user-data-backup-file-name'])  # :)
    else:
        _file_path = os.path.join(*secret_data['user-data-file-path'])
        _data_file = os.path.join(_file_path, secret_data['user-data-file-name'])
        _backup_file = os.path.join(_file_path, secret_data['user-data-backup-file-name'])

    def __init__(self):
        self.data_locker = data_handler.CryptoLocker(secret_data['key-store-keyAlias'])
        self.__password = secret_data['key-store-password']
        self.__data: dict = {}
        # if self.__password is not None:
        #     raise
        #     if self.data_locker.check_password(self.__password):
        #         encrypted_text = self.__load_data()
        #         decrypted_text = self.data_locker.decrypt_text(encrypted_text, self.__password)
        #         try:
        #             self._data = json.loads(decrypted_text)
        #         except json.JSONDecoder:
        #             button = MDRaisedButton(text='Exit app')
        #             button.bind(on_release=lambda *_: sys.exit())
        #             button.bind(on_release=lambda *_: exit())
        #             dialog_type_1(title="Error",
        #                           msg='Unable to decode data: \'JSONDecodeError\', please restart the app again.',
        #                           buttons=[button],
        #                           auto_dismiss_on_button_press=False,
        #                           dismissible=False,
        #                           __force_un_dismissible=True,
        #                           on_dismiss_callback=lambda *_: sys.exit())
        #     else:
        #         self._data = None
        # else:
        #     self._data = None

    def __load_data(self) -> str:
        """
        Loads encrypted data stored in files (From Internal Shared storage)
        :return: scrambled text (Encrypted one)
        """
        try:
            with open(self._data_file, 'r') as file:
                return file.read()
        except FileNotFoundError:
            out = self.__load_backup_data()
            if out is not None:
                return out
            else:
                pass
        except PermissionError:
            pass
        except OSError:
            pass

    def __load_backup_data(self) -> str:
        """
        DO NOT USE FROM OUTSIDE
        :return:
        """
        try:
            with open(self._backup_file, 'r') as file:
                return file.read()
        except FileNotFoundError:
            pass
        except PermissionError:
            pass
        except OSError:
            pass

    def __save_backup_data(self, data: str) -> bool:
        try:
            with open(self._backup_file, 'w+') as file:
                file.write(data)
            return True
        except (PermissionError, OSError):
            return False

    def __save_data(self, data: str):
        """
        Saves data, remember to give an encrypted version of data
        :return: None
        """
        try:
            with open(self._data_file, 'w+') as file:
                file.write(data)
            self.__save_backup_data(data)
        except (PermissionError, OSError) as e:
            if self.__save_backup_data(data):  # try to save backup data
                pass
            else:
                raise SaveFailedException(f"Unable to save user data: {e.args}")

    @property
    def password(self):
        raise TypeError("Cannot get password")

    @password.setter
    def password(self, value: str):
        """
        Only set encrypted password
        :param value:
        :return:
        """
        self.__password = value

    def save_password(self):
        secret_data['key-store-password'] = self.__password  # auto save enabled

    def create_data_file(self):
        try:
            if platform == 'win':
                files = os.listdir('.')  # TODO: Remove this code
            else:
                files = os.listdir(self._file_path)
            if secret_data['user-data-file-name'] in files:
                os.remove(self._data_file)
            if secret_data['user-data-backup-file-name'] in files:
                os.remove(self._backup_file)
            self.save_data_file()
        except PermissionError:
            raise

    def save_data_file(self):
        """
        Saves current snapshot of the data
        :return: Nothing
        """
        if platform == 'android':
            json_str = json.dumps(self.__data)
            encoded_str: str = self.data_locker.encrypt_text(json_str, self.__password)
            self.__save_data(encoded_str)
        else:
            self.__save_data(json.dumps({'Somewhere in the universe': [(0.0, 0.0), 50],  # FIXME: remove this
                                                                                         #      while making app
                                         'Out there in the cosmos': [(90.0, 90.0), 250]}))

    def check_password(self, password: str) -> bool:
        """
        Checks both the user entered and saved password
        :param password:
        :return: True, if password matches else False
        :rtype: bool
        """
        if platform == 'win':
            return password == secret_data['key-store-password']
        else:
            return self.data_locker.check_password(password)

    def load_user_data(self):
        """
        Decrypts and sets data variable
        :return: Nothing
        """
        try:
            enc_data = self.__load_data()
            if platform == 'win':
                decrypt_data = enc_data
            else:
                decrypt_data = self.data_locker.decrypt_text(enc_data, self.__password)
            self.__data: dict = json.loads(decrypt_data)
        except json.decoder.JSONDecodeError:
            stop = MDRaisedButton(text='Exit')
            ignore = MDFlatButton(text='Continue anyway')
            stop.bind(on_release=lambda *_: exit())
            stop.bind(on_release=lambda *_: sys.exit())
            dialog_type_1(title='Oh on!',
                          msg='Unable to decode data "JSONDecodeError" please restart the app, '
                              'if this error persists try re-installing the app '
                              '(Continuing to app may cause unwanted behaviour)',
                          buttons=[ignore, stop],
                          dismissible=False)
            ignore.bind(on_release=lambda *_: change_screen_to('home'))

    def is_password_present(self) -> bool:
        return self.__password is not None

    def decode_and_decide_screen(self):
        if self.check_data_file():
            if self.__password is not None:
                try:
                    if self.check_password(self.__password):
                        self.load_user_data()
                        change_screen_to('home')
                    else:
                        raise JniusJavaException
                except JniusJavaException:
                    ok = MDRaisedButton(text='OK')
                    change_screen_to('login')
                    dialog_type_1(title='Oh no!',
                                  msg='It seems that the stored password is corrupted,'
                                      'You need to enter password again',
                                  buttons=[ok])
            else:
                change_screen_to('login')
        else:
            if self.__password is not None:
                ok = MDRaisedButton(text='OK')
                dialog_type_1(title='Error :(',
                              msg='Password present but unable to locate data file, your data is maybe unrecoverable, '
                                  'sorry for the inconvenience',
                              buttons=[ok])
                self.create_data_file()
                change_screen_to('home')
            else:
                change_screen_to('signin')

    def check_data_file(self) -> bool:
        try:
            files = os.listdir(self._file_path)
            return secret_data['user-data-file-name'] in files or secret_data['user-data-backup-file-name'] in files
        except FileNotFoundError:
            os.mkdir(self._file_path)
            return False
        except (OSError, PermissionError):
            return False


class WeeksToggleButtons(MDBoxLayout):
    weeks = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

    def refresh_week_buttons(self):
        # On android week buttons are not visible until they are pressed,
        # This function will refresh and make visible
        for week in self.weeks:
            self.ids[week].is_active = True
        for week in self.weeks:
            self.ids[week].is_active = False


class EssentialContent(MDBoxLayout):
    # Contains common items
    def __init__(self, *args, **kwargs):
        super().__init__(args, **kwargs)
        self.drop_down_menu = None

    def refresh_week_buttons(self):
        self.ids['week_buttons'].refresh_week_buttons()

    def open_menu(self):
        menu = ['m', 'km']
        menu_items = [
            {
                "text": menu_item,
                "viewclass": 'CustomDropDownListItem',
                "height": dp(54),
                "on_release": lambda x=menu_item: self.set_drop_down_item(x),
            } for menu_item in menu
        ]

        self.drop_down_menu = MDDropdownMenu(caller=self.ids['m_km_button'],
                                             items=menu_items,
                                             width_mult=2)
        self.drop_down_menu.open()

    def set_drop_down_item(self, opt):
        self.ids['m_km_button'].text = opt
        self.drop_down_menu.dismiss()


class CustomDropDownListItem(OneLineListItem):
    ...


class CustomExpansionPanelThreeLineListItem(MDExpansionPanelThreeLine):
    # Expansion panel for alarm_tab

    is_open = False
    _txt_left_pad = dp(15)

    # _height = NumericProperty(115)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.ids['_text_container'].spacing = dp(-3)
        self.ids['_lbl_secondary'].halign = 'right'
        self.ids['_lbl_secondary'].valign = 'top'

    def change_canvas_corner_radii(self):
        self.is_open = True
        self.radius = [dp(15), dp(15), 0, 0]

    def reset_corner_radii(self):
        self.is_open = False
        self.radius = dp(15),


class AlarmExpansionContent(MDBoxLayout):
    # Content for expansion panel

    def __init__(self, *args, full_address, **kwargs):
        print('Content init')
        super().__init__(args, kwargs)
        self.drop_down_menu = None
        self.weeks = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
        self.refresh_week_buttons()
        # self.full_address = full_address
        self.ids['full_address'].text = full_address

    def refresh_week_buttons(self):
        # on android, initially all buttons were texted as 's' by default;
        # this function eliminates it by refreshing all buttons
        self.ids['ess_content'].refresh_week_buttons()

    def remove(self):
        self.parent.remove()

    def set_drop_down_item(self, option):
        self.ids['m_km_button'].text = option
        self.drop_down_menu.dismiss()


class AlarmExpansionPanel(MDExpansionPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chevron.disabled = False
        self.chevron._no_ripple_effect = True
        # self.chevron.icon_color = self.chevron.disabled_color
        self.chevron.bind(on_release=lambda x=None: self.toggle_panel(x))

    def update_height(self):
        self.height = self.content.height + self.panel_cls.height
        # print(self.content.height)

    def toggle_panel(self, _=None):
        self.check_open_panel(self.panel_cls)

    def open_panel(self, *args) -> None:
        """Method opens a panel."""
        if self._anim_playing:
            return

        self._anim_playing = True
        self._state = "open"

        # print('\n'.join(dir(self.content.ids['full_address'])))

        anim = Animation(
            height=self.content.height + self.height,
            d=self.opening_time,
            t=self.opening_transition,
        )
        anim.bind(on_complete=self._add_content)
        anim.bind(on_complete=self._disable_anim)
        anim.start(self)

    def on_open(self, *args):
        # for child in self.parent.children:  # on_close won't be called if we open another panel without closing opened
        #     child: AlarmExpansionPanel = child
        #     if child.get_state() == 'open':
        #         child.panel_cls.reset_corner_radii()
        #         child.close_panel(child.parent, True)
        self.open_panel()
        self.panel_cls.change_canvas_corner_radii()
        Clock.schedule_once(self._focus, .1)

    def on_close(self, *args):
        self.panel_cls.reset_corner_radii()
        self._reset_scroll()
        self.height = self.panel_cls.height  # resets height manually

    def check_open_panel(
            self,
            instance_panel: [
                MDExpansionPanelThreeLine,
                MDExpansionPanelTwoLine,
                MDExpansionPanelLabel,
            ],
    ) -> None:
        """
        Called when you click on the panel.
        Called to open or close a panel.
        """

        press_current_panel = False
        for panel in self.parent.children:
            if isinstance(panel, MDExpansionPanel):
                if len(panel.children) == 2:
                    if instance_panel is panel.children[1]:
                        press_current_panel = True
                    panel.remove_widget(panel.children[0])
                    if not isinstance(self.panel_cls, MDExpansionPanelLabel):
                        chevron = panel.children[0].children[0].children[0]
                        self.set_chevron_up(chevron)
                    self.close_panel(panel, press_current_panel)
                    panel.dispatch("on_close")
        if not press_current_panel:
            self.set_chevron_down()

    def _reset_scroll(self):
        if self.parent.parent.scroll_y == 0:
            self.parent.parent.scroll_y = (self.parent.parent.height - self.height) / self.parent.parent.height
            # self.parent.parent.scroll_to(self.parent.children[0].panel_cls)

    def _focus(self, *_):
        min_items = 1 + (app.root.height - (dp(100) + dp(80) + self.panel_cls.height + self.content.height)) // \
                    self.panel_cls.height
        if min_items < len(self.parent.children):
            self.parent.parent.scroll_to(widget=self)
        # print(min_items)
        # print(self.height, self.content.height, self.panel_cls.height, app.root.height, home.ids['top_app_bar'].pos)
        Clock.schedule_once(self._modify_top_app_bar_color, 0.35)

    # widget = self.content
    # print(*widget.pos, *widget.size)
    # pos = self.parent.to_widget(*widget.to_window(*widget.pos))
    # cor = self.parent.to_widget(*widget.to_window(widget.right,
    #                                               widget.top))
    # print(self.panel_cls.height+self.height, pos, cor)

    def _modify_top_app_bar_color(self, *_):
        self.parent.parent.parent.parent.scroll_movement(self.parent.parent.scroll_y)

    def remove(self):
        anim = Animation(x=-self.width, duration=0.4, t='out_back')
        anim.bind(on_complete=self._remove)
        anim.start(self)

    def _remove(self, *_):
        self._reset_scroll()
        self.parent.remove_widget(self)  # goodbye
        del self


class PasswordInputScreen(MDScreen):
    def on_enter(self, *args):
        pass

    @staticmethod
    def open_info_dialog():
        button = MDRaisedButton(text='ok')
        dialog_type_1(title='Password protection',
                      msg='In order to protect your privacy, and store your data securely we use password protected '
                          'encryption, so you need create a new password',
                      buttons=[button])

    @staticmethod
    def key_stroke(_from, _to, text):
        """
        Checks every keystroke and switches focus to '_to' if it is a tab
        :param _from:
        :param _to:
        :param text:
        :return:
        """
        try:
            key = text[-1]
        except (KeyError, IndexError):
            return
        if key == '\t':
            _from.text = text[:-1]  # removes tab
            _from.focus = False
            _to.focus = True

    def proceed(self):
        password_field = self.ids['password']
        confirm_field = self.ids['confirm_password']

        password: str = password_field.text
        confirm_password = confirm_field.text

        if common_pass_check(password) and password == confirm_password:
            pass
        else:
            self.ids['proceed'].disabled = True
            return  # maybe mistakenly pressed/enabled
        user_data.password = password_encrypt(password)
        if self.ids['check_box'].active:
            user_data.save_password()
        user_data.create_data_file()
        change_screen_to('home')
        ok = MDRaisedButton(text='I Understood')
        dialog_type_1(title='Note',
                      msg='Please remember this password, '
                          'In case you re-installed this app you need to enter this password to recover data',
                      buttons=[ok],
                      dismissible=False)

    def enter_button(self):
        if self.ids['password'].focus:
            self.ids['password'].focus = False
            self.ids['confirm_password'].focus = True
        elif self.ids['confirm_password'].focus:
            self.ids['confirm_password'].focus = False
            self.proceed()

    @staticmethod
    def check_data_file():
        if user_data.check_data_file():
            change_screen_to('login')
        else:
            ok = MDRaisedButton(text='OK')
            dialog_type_1(title='No Data',
                          msg='Unable to find old data file!, Please login to create one',
                          buttons=[ok])


class PasswordLoginScreen(MDScreen):
    def on_enter(self, *args):
        if is_first_login:
            # defaulted to false
            # if not first time login then user is opted not to store the password
            # else we offer to save the password
            self.ids['check_box'].active = True

    def enter_button(self):
        password = self.ids['password'].text
        if not self.is_pass_valid():
            return
        if user_data.check_password(password_encrypt(password)):
            user_data.password = password_encrypt(password)
            if self.ids['check_box'].active:
                user_data.save_password()
            user_data.load_user_data()
            change_screen_to('home')
        else:
            self.ids['password'].helper_text = 'Wrong password!'
            self.ids['password'].error = True

    def is_pass_valid(self):
        return common_pass_check(self.ids['password'].text)

    @staticmethod
    def forgot_password():
        ok = MDRaisedButton(text='I understood')
        no = MDFlatButton(text='I know password')
        dialog_type_1(title='Note',
                      msg='Remember, old data will be lost without password!!!',
                      buttons=[no, ok])
        ok.bind(on_release=lambda *_: change_screen_to('signin'))


class LoadingScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loading_text = ['Please wait...',
                             'Loading...']

    def on_enter(self, *args):
        self.ids['label'].text = random.choice(self.loading_text)


class AlarmsTab(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_start_callback = lambda x=None: x
        self.expansion_items: list[AlarmExpansionPanel] = []
        self.checker_clock = Clock.schedule_interval(self.check_scroll, 5)
        # self.checker_clock.cancel()

    def on__enter(self):
        self.checker_clock()

    def on__leave(self):
        self.checker_clock.cancel()

    def check_scroll(self, *_):
        scroll_dist = self.ids['scroll_view'].scroll_y
        # print(scroll_dist)
        if scroll_dist > 1:
            self.ids['scroll_view'].scroll_y = 1
        elif scroll_dist < 0:
            self.ids['scroll_view'].scroll_y = 0

    def add_active_alarms(self):
        item = AlarmExpansionPanel(
            content=AlarmExpansionContent(full_address='Full address will appear here ' * 30),
            panel_cls=CustomExpansionPanelThreeLineListItem(
                text='Bengaluru',
                secondary_text='25km',
                tertiary_text=', '.join(map(lambda x: x.capitalize(), ['sun', 'mon', 'fri']))
            ),
        )

        self.expansion_items.append(item)
        self.ids['container'].add_widget(item)

    def scroll_movement(self, *args):
        # TODO_: change top app bar color as scroll movement
        # pass
        # print(args)
        if args[0] >= 0.99:
            color = app.theme_cls.bg_normal
        else:
            color = app.theme_cls.colors[app.theme_cls.primary_palette]['900'] + '1a'
        # print(self.parent.parent.parent.parent.parent.ids, self.parent.parent.parent.parent.parent)
        self.parent.parent.parent.parent.parent.change_top_app_bar_color(color=color)


class GoogleMapsTab(MDScreen):
    pass


class SettingsScreen(MDScreen):
    ...


class HomeScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_test_scroll = True
        self._color = None
        self.is_tap_target_shown = True  # TODO: disabled for debugging make it False for production

    def on_enter(self, *args):
        # pass
        # Clock.schedule_once(self.ids['alarm_tab'].change_top_app_bar_color, 0.1)
        self.is_test_scroll = True

        # self._color = app.theme_cls.bg_normal
        Clock.schedule_once(self.change_top_app_bar_color, .1)
        # Clock.schedule_once(self.scroll_start, .1)
        # self.ids['alarm_tab'].scroll_start_callback = self.scroll_start
        if self.ids['bottom_navigation'].current == 'screen 1':
            self.ids['alarm_tab'].on__enter()

        if not self.is_tap_target_shown:
            Clock.schedule_once(self.show_tap_target, 0.1)

    def show_tap_target(self, _=None):
        widget = MDTapTargetView(widget=self.ids['spd_dial'],
                                 title_text='Add new item',
                                 description_text='This adds new items \n'
                                                  'to active alarms tab\n'
                                                  'This button may take\n'
                                                  'long to respond.\n'
                                                  'So, don\'t spam this button\n'
                                                  'Add items one by one',
                                 widget_position='right_bottom',
                                 cancelable=True, )
        widget.outer_circle_color = app.theme_cls.primary_dark[:3]
        widget.outer_circle_alpha = 0.75
        widget.start()
        self.is_tap_target_shown = True

    def on_leave(self, *args):
        self.ids['alarm_tab'].on__leave()

    def change_top_app_bar_color(self, color=None):
        return
        # if isinstance(color, float):
        #     color = self._color if self._color is not None else app.theme_cls.bg_normal
        # self.ids['top_app_bar'].ids['top_app_bar'].md_bg_color = color
        # self.ids['bottom_navigation'].panel_color = color

    def add_content(self):
        self.ids['alarm_tab'].add_active_alarms()

    @staticmethod
    def tab_press(widget):
        """
        Called when clicking on a panel item.
        Everything performed in this function
        because: 1. built-in method overrides some functionalities of its parent
                 2. Using on_tab_press again overrides its parent functionality,
                    blocking everything except what we assign
        So we perform what was supposed to happen
        (Our main intention is to add directional scroll according to tab location,
        which was previously unavailable due to the fact that I explained in reason 1)
        NOTE: Everything is copied from kivymd/uix/bottomnavigation/bottomavigation.py
        basically this combines 2 functions
        """

        bottom_navigation_object = widget.parent_widget
        if bottom_navigation_object.previous_tab is not widget:
            if bottom_navigation_object.previous_tab.index > widget.index:
                bottom_navigation_object.ids.tab_manager.transition.direction = "right"
            elif bottom_navigation_object.previous_tab.index < widget.index:
                bottom_navigation_object.ids.tab_manager.transition.direction = "left"
            # bottom_navigation_object.ids.tab_manager.current = widget.name
            # bottom_navigation_object.previous_tab = widget

        bottom_navigation_header_object = (
            bottom_navigation_object.previous_tab.header
        )
        bottom_navigation_object.ids.tab_manager.current = widget.name

        if bottom_navigation_object.previous_tab is not widget:
            if bottom_navigation_object.use_text:
                Animation(_label_font_size=sp(12), d=0.1).start(
                    bottom_navigation_object.previous_tab.header
                )
            Animation(
                _selected_region_width=0,
                t="in_out_sine",
                d=0,
            ).start(bottom_navigation_header_object)
            Animation(
                _text_color_normal=bottom_navigation_header_object.text_color_normal
                if bottom_navigation_object.previous_tab.header.text_color_normal != [1, 1, 1, 1]
                else widget.theme_cls.disabled_hint_text_color,
                d=0.1,
            ).start(bottom_navigation_object.previous_tab.header)
            bottom_navigation_object.previous_tab.header.active = False
            widget.header.active = True
        bottom_navigation_object.previous_tab = widget


class SavedLocationsScreen(MDScreen):
    """
    Displays saved locations
    """


class AddNewLocationScreen(MDScreen):
    # Provides interface to add new location
    def __init__(self, *args, **kwargs):
        super().__init__(args, **kwargs)
        self.drop_down_menu = None
        self.post_proc_arg = None

    def on_enter(self):
        self.ids['ess_content'].refresh_week_buttons()

    def validate_gps_cords(self) -> bool:
        if self.ids['cords_in'].focus:
            return False
        txt = self.ids['cords_in'].text.upper()
        if txt == '':
            return False
        try:
            # out = split_gps_deci_str(txt)
            # if len(out) != 2:
            #     raise KeyError
            # lat, lng = out[0], out[1]
            out = validate_gps_co_ords(txt)
            self.ids['cords_in'].error = not out  # Not-Out yeahhh  🏏🥳
            return out
        except (KeyError, TypeError, ValueError) as e:
            print('Error while validating gps cords')
            print(e)
        self.ids['cords_in'].error = True
        return False

    def get_location_info(self) -> None:
        """
        This function is called by a non-kivy thread and uses kivy feature which must be used within the kivy thread
        Used for both geocode and reverse-geocode (Auto switch), relies on button is_reverse variable
        :return: None
        """
        self.location_input()  # sometime button is not updated properly this manually updates the button
        if self.ids['get_button'].is_reverse:
            if self.validate_gps_cords():
                try:
                    text = self.ids['cords_in'].text
                    out = split_lat_lng(text)
                    if out is None:
                        return
                    lat, lng = map(float, out)
                    out, is_cached = geocoding_client.reverse_geocode(lat, lng)
                    if out is None:
                        self.ids['location_name'].helper_text = 'Unknown Location!'
                        self.ids['location_name'].error = True
                        return
                    name: str = out.address
                    self.post_proc_arg = name
                    Clock.schedule_once(self.post_process_text, 0.0)
                    if is_cached:  # if the data is retrieved from cache, then quickly enable the button
                        self.ids['get_button'].kill_all_threads()
                except ValueError:
                    # we're already tested this while validating, and probably never called
                    dialog_type_1(title='Something went wrong',
                                  msg='Something unexpected happened while phrasing co-ordinates, please try again',
                                  buttons=MDFlatButton(text='ok'))
                except GeocoderUnavailable:
                    self.ids['location_name'].helper_text = 'No Internet!'
                    self.ids['location_name'].error = True
            else:
                self.ids['get_button'].kill_all_threads()
        else:
            try:
                text = self.ids['location_name'].text.strip()
                out, is_cached = geocoding_client.geocode(text)
                if out is None:
                    self.ids['location_name'].helper_text = 'Unknown Location!'
                    self.ids['location_name'].error = True
                    return
                name: str = f'{out.latitude}, {out.longitude}'
                self.post_proc_arg = name
                Clock.schedule_once(self.post_process_cords, 0.0)
                if is_cached:  # if the data is retrieved from cache, then quickly enable the button
                    self.ids['get_button'].kill_all_threads()
            except GeocoderUnavailable:
                self.ids['location_name'].helper_text = 'No Internet!'
                self.ids['location_name'].error = True

    def post_process_text(self, *_):
        self.ids['location_name'].text = self.post_proc_arg
        self.reset_text_field_error_stat()

    def post_process_cords(self, *_):
        self.ids['cords_in'].text = self.post_proc_arg
        self.reset_text_field_error_stat()

    def reset_text_field_error_stat(self):
        self.ids['location_name'].error = False
        self.ids['cords_in'].error = False

        self.validate_gps_cords()  # incase cords were wrong

    def location_input(self):  # function name doesn't make sense thou
        location_text = self.ids['location_name'].text.strip()
        co_ords_text = self.ids['cords_in'].text.strip()
        if location_text == '' or co_ords_text != '':
            self.ids['get_button'].is_reverse = True
            self.ids['get_button'].text = 'Get address'
        else:
            self.ids['get_button'].is_reverse = False
            self.ids['get_button'].text = 'Get co-ordinates'

    @staticmethod
    def format_short_name(text: str) -> str:
        if ',' in text:
            text = text.split(',')[0]
        else:
            text = text.split()[0]
        if len(text) > 15:
            text = text[:15]
        return text

    def open_short_address_dialog(self):
        cancel = MDFlatButton(text='Cancel')
        add = MDRaisedButton(text='Add')
        txt: str = self.ids['location_name'].text
        if not txt.strip():
            self.ids['location_name'].helper_text = 'This field is required'
            self.ids['location_name'].error = True
            return
        txt = self.format_short_name(txt)
        text_input_dialog(title='Add short name',
                          hint_text='Short name',
                          filler_text=txt,
                          buttons=[cancel, add])


class MyScreenManager:
    """
    This class manages screens and creates screen when needed
    Since, loading all screens while starting the app, create a blank screen for a while
    which is not great.

    NOTE: This class is only for this specific use case and not recommended for other cases (as of 12-09-2024)
    Result:
        v1.2.8.1-------v1.5.0
    time---8s------------5s------(Time to load home screen)
    results seem to be promising with improvement of 3s
    """

    def __init__(self, manager: MDScreenManager):
        self.__rendered_screens: list[str] = []
        self.screen_manager = manager
        self.__screens: dict[str, Screen] = {}

        self.__screens_to_render = {}

    @property
    def screen(self):
        return self.screen_manager.current

    @screen.setter
    def screen(self, value: str):
        self.set_screen(value)

    def set_screen(self, target_screen: str) -> None:
        """
        Changes sets current screen to target screen\n
        Note: Must be called in from kivy thread
        :param target_screen: Target screen, what else?
        :return: None
        """
        if target_screen in self.__rendered_screens:
            self.screen_manager.current = target_screen
        else:
            self.get_screen(target_screen)
            self.screen_manager.current = target_screen

    def get_screen(self, screen_name: str) -> Screen | NoReturn:
        """
        Returns the requested screen
        :param screen_name: Required screen name
        :return: Screen object
        :raise TypeError: When screen is not added but called to render
        """
        if screen_name in self.__rendered_screens:
            return self.__screens[screen_name]
        else:
            # Fixme: kwargs/args not supported
            try:
                screen = self.__screens_to_render[screen_name](name=screen_name)
            except KeyError:
                raise TypeError(f"Screen {screen_name} is not added")
            self.screen_manager.add_widget(screen)
            self.__screens[screen_name] = screen
            self.__rendered_screens.append(screen_name)
            return screen

    def get_current_screen_obj(self):
        return self.get_screen(self.screen)

    def add_screen(self, screen_name: str, cls, _overwrite: bool = False) -> None:
        """
        Adds screen name and class to future rendering items
        :param screen_name: Name of screen (this name is used to represent the object)
        :param cls: Class
        :param _overwrite: If set True and screen_name exists,
        overwrites the previous Class of the same or else error will be raised.
        :return: None
        :raise KeyError: When screen-name already exists
        """
        if screen_name in self.__screens_to_render:
            if not _overwrite:
                raise KeyError(f"{screen_name} this screen already exists!")
        self.__screens_to_render[screen_name] = cls

    def _render_all(self):
        """
        Renders all provided screens and might cause a lag
        :return: Nothing
        """
        for screen in self.__screens_to_render:
            self.get_screen(screen)


class MainApp(MDApp):
    version = f'v{__version__}'

    @property
    def material_style(self) -> MDApp:
        return self.theme_cls.material_style

    @staticmethod
    def goto_screen(screen: str):
        # Called from frontend.kv*
        # Even though we can change screen there itself we need some function to use this method
        change_screen_to(screen)

    @staticmethod
    def validate_alarm_distance(root: MDScreen, text: str, mode: str, focus: bool = True, key: str = 'dist_inp'):
        if text == '' and not focus:
            if mode == 'm':
                least = 50
            else:
                least = 1
            root.ids[key].text = f'{least}'
            return
        try:
            if mode == 'm':
                d = int(text)
                least = 50
            else:
                d = float(text)
                least = 1
            if d < least:
                root.ids[key].text = f'{least}'
        except ValueError:
            if text != '':
                root.ids[key].text = text[:-1]

    @staticmethod
    def toast(message: str = '', fun=False, id_: str = ''):
        global fun_index
        if fun:
            message = fun_toast_messages[fun_index]
            if id_ in fun_ids:
                message = fun_again_press[fun_ids[id_][1]]
                fun_ids[id_][1] += 1
                if fun_ids[id_][1] >= len(fun_again_press):
                    fun_ids[id_][1] = len(fun_again_press) - 1
                if fun_index + 1 != len(fun_toast_messages):
                    if message == '':
                        message = fun_toast_messages[-1]
                    else:
                        message += fun_toast_messages[fun_ids[id_][0]]
            else:
                fun_ids[id_] = [fun_index, 0]
                fun_index += 1
            if fun_index >= len(fun_toast_messages):
                fun_index = len(fun_toast_messages) - 1
            # message = message.capitalize()
        toast(message)

    @staticmethod
    def open_url(url: str) -> None:
        webbrowser.open(url)

    @staticmethod
    def color_converter(inp: str, mode: str = 'code'):
        if mode == "code":
            # TODO: format consideration
            pass
        r = int(inp[:2], 16) / 255
        g = int(inp[2:4], 16) / 255
        b = int(inp[4:6], 16) / 255
        try:
            a = int(inp[6:8], 16) / 255
        except IndexError:
            a = 1
        except ValueError:
            a = 1
        return r, g, b, a

    @staticmethod
    def send_feedback():
        global __log_to_send

        def send_without_log(_=None):
            send_email(recipient=secret_data['mail'], msg='')

        #
        if __log_to_send:  # and error_handler.list_log_files():
            include = MDRaisedButton(text='Yes, include')
            no = MDFlatButton(text='No, thanks')
            include.bind(on_release=send_log)
            no.bind(on_release=send_without_log)
            dialog_type_1('Error log found', "Error log was found do you want to include this file?",
                          auto_dismiss_on_button_press=True, buttons=[no, include])
        else:
            send_without_log()

    @staticmethod
    def escape_button():
        """
        Used by frontend app
        :return:
        """
        global last_esc_down
        last_esc_down = 0  # making sure that this isn't combine with real back/escape button
        keyboard_listener(None, Constants.ESCAPE_CODE)

    def on_start(self):
        global __log_to_send, is_first_login
        WindowBase.softinput_mode = 'below_target'  # noqa
        WindowBase.on_maximize = lambda x=None: print(x, 'maximised')
        WindowBase.on_restore = lambda x=None: print(x, 'window restore')
        # WindowBase.on_resize = lambda x=None: print(x, 'Window resize')
        # is_first_login = False
        if GPS.configure(raise_error=False):
            button = MDFillRoundFlatButton(text='Close app')
            button.bind(on_release=lambda *_: sys.exit())
            dialog_type_1('Oh no!',
                          'It seems like GPS is not implemented on your device!!!',
                          [button],
                          dismissible=False,
                          auto_dismiss_on_button_press=False,
                          on_dismiss_callback=lambda *_: sys.exit())  # extra safety
            # lambda is used, to prevent sys.exit getting args and thinking it as an error
        try:
            files = error_handler.list_log_files(raise_folder_not_found=True)
            if files:
                __log_to_send = error_handler.read_error_log(files[0])
                cancel = MDFlatButton(text='Cancel')
                send = MDRaisedButton(text='Send')
                dialog_type_1(title="Error detected!",
                              msg='Error detected or App closed unexpectedly, please send this error log to developer'
                                  ' (This file will be automatically deleted after sending it!)',
                              buttons=[cancel, send],
                              auto_dismiss_on_button_press=True)
                send.bind(on_press=send_log)
                send.bind(on_press=delete_log)
                # cancel.bind(on_press=delete_log)
            else:
                # without this line code will raise "NameError: name '_MainApp__log_to_send' is not defined"
                __log_to_send = ''  # I don't think this is needed but without this send_feedback function will break
                # And the app will crash :(, IDK why
        except FileNotFoundError:
            is_first_login = True

            class FirstInfoScreen(MDScreen):
                @staticmethod
                def hyper_link_press(link):
                    try:
                        app.open_url(link[1])
                    except IndexError:
                        pass

                @staticmethod
                def agree():
                    change_screen_to('loading')
                    os.mkdir('Error log')
                    toast("Made by Ranjith")
                    if user_data.check_data_file():
                        yes = MDRaisedButton(text='Yes')
                        yes.bind(on_release=lambda *_: change_screen_to('login'))
                        no = MDFlatButton(text='No thanks', theme_text_color='Custom', text_color=(1, 0.2, 0.2, 1))
                        no.bind(on_release=lambda *_: change_screen_to('signin'))
                        dialog_type_1(title='Data Recovery',
                                      msg='Old data was found in this device, do you want to recover?',
                                      buttons=[no, yes])
                    else:
                        change_screen_to('signin')

            screens.add_screen('first_info', FirstInfoScreen)
            # sm.add_widget(first_info)

        if is_first_login:
            change_screen_to('first_info')
        else:
            user_data.decode_and_decide_screen()

        # app.theme_cls.bg
        EventLoop.window.bind(on_keyboard=keyboard_listener)

    def build(self):
        self.theme_cls.material_style = 'M3'
        self.theme_cls.theme_style = 'Dark'
        # palette = random.choice(['Red', 'Pink', 'Purple', 'DeepPurple', 'Indigo', 'Blue', 'DeepOrange', 'Teal',
        #                          'Green', 'LightGreen', 'Lime', 'Yellow', 'Amber', 'Orange', 'LightBlue', 'Cyan'])
        # self.theme_cls.primary_palette = palette
        self.theme_cls.primary_palette = 'Teal'
        # print(palette)
        # self.theme_cls.primary_palette = 'Teal'
        # ['Red', 'Pink', 'Purple', 'DeepPurple', 'Indigo', 'Blue', 'DeepOrange', 'Teal', 'Brown', 'BlueGray']
        #
        # Don't use below colors (These colors changes text color to black, wiz not suitable for dark mode)
        # 'Green', 'LightGreen', 'Lime', 'Yellow', 'Amber', 'Orange',  'LightBlue',  'Cyan',  'Gray'
        return sm

    @error_handler.call_wrapper
    def run(self):
        super().run()


if __name__ == '__main__':
    Builder.load_file('frontend.kv')
    app = MainApp()
    sm = MDScreenManager(transition=MDFadeSlideTransition())

    screens = MyScreenManager(sm)

    screens.add_screen('home', HomeScreen)
    screens.add_screen('loading', LoadingScreen)
    screens.add_screen('settings', SettingsScreen)
    screens.add_screen('saved_locations', SavedLocationsScreen)
    screens.add_screen('new_location', AddNewLocationScreen)
    screens.add_screen('login', PasswordLoginScreen)
    screens.add_screen('signin', PasswordInputScreen)

    screens.set_screen('loading')
    screens.get_screen('home')  # preloading home screen

    user_data = UserData()
    # secret_data._render_all()

    # home = HomeScreen(name='home')
    # loading = LoadingScreen(name='loading')
    # settings = SettingsScreen(name='settings')
    # saved_locations = SavedLocationsScreen(name='saved_locations')
    # new_location = AddNewLocationScreen(name='new_location')
    #
    # sm.add_widget(home)
    # sm.add_widget(loading)
    # sm.add_widget(settings)
    # sm.add_widget(saved_locations)
    # sm.add_widget(new_location)

    # sm.current = 'new_location'

    # TODO: Make raise_error to False for production, disabled for debugging
    app.run(raise_error=True)  # platform != 'android')
