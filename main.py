__version__: str = '1.5.1'
__test_version__: str = 'alpha'

import os
import re
import sys
import time
import plyer
import random
import webbrowser
from typing import Callable

import data_handler
import exceptions_handler
import gps

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

current_screen = previous_screen = 'home'

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


# Kivy doesn't allow changing screen from outer thread other than kivy's (tested on windows)
# This function uses kivy's Clock to change screen
def change_screen_to(screen: str) -> None:
    global current_screen, previous_screen
    previous_screen = current_screen
    current_screen = screen
    Clock.schedule_once(_set_screen, 0.0)


# Actual screen changing happens here
def _set_screen(_):
    # sm.current = current_screen
    screens.change_screen(current_screen)


last_esc_down = 0


# Response every keystroke including esc button
def hook_keyboard(_, key, *__) -> None | bool:
    global last_esc_down
    if key == 27:  # Esc button on Windows and back button on Android
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


last_toast_msg = ''
last_toast_time = time.time()


def toast(msg: str) -> None:
    global last_toast_msg, last_toast_time
    if msg == last_toast_msg and time.time() - last_toast_time <= 2.5:
        return
    _toast(msg)
    last_toast_time = time.time()
    last_toast_msg = msg


def regex_match_gps(text: str) -> list:
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


def validate_gps_co_ords(text: str) -> bool:
    """
    Validates GPS co-ordinates of any format
    :param text: Co-ordinates make sure to send capitalized text
    :return: boolean; True if it is valid, else False
    """
    text = text.upper()
    regex_cords = regex_match_gps(text)
    for ind, match in enumerate(regex_cords):
        if match:
            break
    else:
        return False  # No match (for loop ended normally without breaking)
    if len(match) != 2:  # there are more or less items (2 -> 1 latitude and 1 longitude)
        if ind == 1 and len(match) == 1 and len(regex_cords[-1]) == 2:  # This case will solve problem like
            # '12.34 56.78' this is GPS co-ord in decimal from, but it also matches with DMS of sign format
            ind = 2
            match: list = regex_cords[-1]
        else:
            return False
    if ind < 2:  # Match index varies according to input format (<2 means It is in DMS format)
        split_lat = split_gps_deci_str(match[0])
        split_lng = split_gps_deci_str(match[1])
        if ind == 0:
            # check the last letter, In-case they are swapped
            if match[0][-1] in ('S', 'N') and match[1][-1] in ('E', 'W'):
                pass
            elif match[0][-1] in ("E", "W") and match[1][-1] in ("N", "S"):
                split_lat, split_lng = split_lng, split_lat  # latitude and longitude are swapped
            else:
                return False
        if len(split_lat) == len(split_lng) == 4:  # 4 -> deg + min + sec + direction
            lat = convert_gps_to_decimal_degree(*split_lat)
            lng = convert_gps_to_decimal_degree(*split_lng)
        else:
            return False
    else:
        lat, lng = match

    return validate_gps_cord(lat, lng)


def dialog_type_1(title: str, msg: str, buttons: list[Button], auto_dismiss_on_button_press: bool = True,
                  dismissible: bool = True, on_dismiss_callback: Callable = None,
                  extra_callbacks: dict[str, Callable] = None) -> MDDialog:
    """
    Creates a dialog box, to interact with user.
    :param title: Dialog title
    :param msg: Message to deliver
    :param buttons: buttons to interact with
    :param auto_dismiss_on_button_press: If set True dismisses dialog box after button press
    :param dismissible: If set True dismisses dialog even after no button press
    :param on_dismiss_callback: Callback after closing dialog,
    :param extra_callbacks: Custom new unknowns callbacks.In the format -> callback_name to callback
    :return: Dialog
    """
    dialog = MDDialog(
        title=title,
        text=msg,
        buttons=buttons)
    dialog.auto_dismiss = dismissible if buttons else True  # Make sure to give buttons or else no way to dismiss
    if auto_dismiss_on_button_press:
        for button in buttons:
            button.bind(on_release=dialog.dismiss)
    dialog.open()
    if on_dismiss_callback is not None:
        dialog.bind(on_dismiss=on_dismiss_callback)
    if extra_callbacks is not None:
        dialog.bind(**extra_callbacks)
    return dialog  # if you want to dismiss manually


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

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.drop_down_menu = None
        self.weeks = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
        self.refresh_week_buttons()

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

    def toggle_panel(self, _=None):
        self.check_open_panel(self.panel_cls)

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
                MDExpansionPanelThreeLine,
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
            content=AlarmExpansionContent(),
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

    def on_enter(self):
        self.ids['ess_content'].refresh_week_buttons()

    def validate_gps_cords(self):
        if self.ids['cords_in'].focus:
            return
        txt = self.ids['cords_in'].text.upper()
        if txt == '':
            return
        try:
            # out = split_gps_deci_str(txt)
            # if len(out) != 2:
            #     raise KeyError
            # lat, lng = out[0], out[1]
            self.ids['cords_in'].error = not validate_gps_co_ords(txt)
        except (KeyError, TypeError, ValueError) as e:
            print('Error while validating gps cords')
            print(e)
        else:
            # if no error
            return
        self.ids['cords_in'].error = True


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

    def change_screen(self, target_screen: str) -> None:
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

    def get_screen(self, screen_name: str) -> Screen:
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

    def add_screen(self, screen_name: str, cls, _overwrite: bool = False) -> None:
        """
        Adds screen name and class to future rendering items
        :param screen_name: Name of screen (this name is used to represent the object)
        :param cls: Class
        :param _overwrite: If set True and screen_name exists, overwrites the previous Class of the same
        :return: None
        :raise KeyError: When screen-name already exists
        """
        if screen_name in self.__screens_to_render:
            if not _overwrite:
                raise KeyError("This screen name already exists!")
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
    def on_location():
        pass

    @staticmethod
    def on_status():
        pass

    def on_start(self):
        global __log_to_send
        WindowBase.softinput_mode = 'below_target'
        WindowBase.on_maximize = lambda x=None: print(x, 'maximised')
        WindowBase.on_restore = lambda x=None: print(x, 'window restore')
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
            class FirstInfoScreen(MDScreen):
                @staticmethod
                def agree():
                    change_screen_to('home')
                    os.mkdir('Error log')
                    toast("Made by Ranjith")

            screens.add_screen('first_info', FirstInfoScreen)
            # sm.add_widget(first_info)
            change_screen_to('first_info')
        if GPS.configure(raise_error=False):
            button = MDFillRoundFlatButton(text='Close app')
            button.bind(on_release=lambda *_: sys.exit)
            dialog_type_1('Oh no!',
                          'It seems like GPS is not implemented on your device!!!',
                          [button],
                          dismissible=False,
                          auto_dismiss_on_button_press=False,
                          on_dismiss_callback=lambda *_: sys.exit())  # extra safety
            # lambda is used to prevent sys.exit getting args and thinking it as an error
        GPS.set_callback(status_change_callback=self.on_status,
                         location_change_callback=self.on_location)
        if GPS.is_configured:
            GPS.start()

        # app.theme_cls.bg
        EventLoop.window.bind(on_keyboard=hook_keyboard)

    def build(self):
        self.theme_cls.material_style = 'M3'
        self.theme_cls.theme_style = 'Dark'
        # palette = random.choice(['Red', 'Pink', 'Purple', 'DeepPurple', 'Indigo', 'Blue', 'DeepOrange', 'Teal',
        #                          'Green', 'LightGreen', 'Lime', 'Yellow', 'Amber', 'Orange', 'LightBlue', 'Cyan'])
        # self.theme_cls.primary_palette = palette
        self.theme_cls.primary_palette = 'Blue'
        # print(palette)
        # self.theme_cls.primary_palette = 'Teal'
        # ['Red', 'Pink', 'Purple', 'DeepPurple', 'Indigo', 'Blue', 'DeepOrange', 'Teal', 'Brown', 'BlueGray']
        #
        # Don't use below colors (These colors changes text color to black, wiz not suitable for dark mode)
        # 'Green', 'LightGreen', 'Lime', 'Yellow', 'Amber', 'Orange',  'LightBlue',  'Cyan',  'Gray'
        return sm


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

    screens.get_screen('home')
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
    error_handler.call__catch_and_crash(app.run, raise_error=True)  # platform != 'android')
