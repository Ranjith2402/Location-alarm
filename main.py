import re
import time

from kivymd.toast import toast as _toast
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list.list import OneLineListItem
from kivymd.uix.menu.menu import MDDropdownMenu
from kivymd.uix.transition.transition import MDFadeSlideTransition
from kivymd.uix.expansionpanel.expansionpanel import MDExpansionPanel, MDExpansionPanelThreeLine, \
    MDExpansionPanelTwoLine, MDExpansionPanelLabel

from kivy.clock import Clock
from kivy.lang.builder import Builder
from kivy.animation import Animation
from kivy.metrics import dp, sp
from kivy.core.window import WindowBase, EventLoop

current_screen = previous_screen = 'home'

decimal_regex_pattern = r'[+-]?\d+\.?\d*'  # r'[+-]?\d+\.\d+|[+-]?\d+'
dms_regex_pattern_NEWS_format = r'\d+\D\d+\D\d+\.?\d*[NEWS]'
dms_regex_pattern_sign_format = r'[+-]?\d+\D\d+\D\d+\.?\d*'


def change_screen_to(screen: str) -> None:
    global current_screen, previous_screen
    previous_screen = current_screen
    current_screen = screen
    Clock.schedule_once(_set_screen, 0.1)


def _set_screen(_):
    sm.current = current_screen


last_esc_down = 0


def hook_keyboard(_, key, *__):
    global last_esc_down
    if key == 27:
        if sm.current in ('settings', 'saved_locations'):
            change_screen_to('home')
        elif sm.current in ('new_location',):
            change_screen_to(previous_screen)
        else:
            if time.time() - last_esc_down < 2.5:
                return
            last_esc_down = time.time()
            toast('Press again to exit')
        return True


last_toast_msg = ''
last_toast_time = time.time()


def toast(msg: str):
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
    three items -> NEWS (direction in the form of North, south, East or West)
    two items -> hour-minute-sec format (direction in signed)
    one item -> decimal format
    empty list -> no match (not a valid sco-ords)
    """
    text = text.upper()
    out = [re.findall(pattern, text) for pattern in [dms_regex_pattern_NEWS_format,
                                                     dms_regex_pattern_sign_format,
                                                     decimal_regex_pattern]]
    print(out)
    return out


def split_gps_deci_str(string: str) -> tuple:
    out = re.findall(decimal_regex_pattern, string)
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
    if direction in ('W', 'S', '-', -1):
        out_deci *= -1
    return out_deci


def validate_gps_cord(lat: str, lng: str) -> bool:
    try:
        lat = float(lat)
        lng = float(lng)
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return True
        return False
    except ValueError:
        return False


def validate_gps_co_ords(text: str) -> bool:
    regex_cords = regex_match_gps(text)
    for ind, match in enumerate(regex_cords):
        if match:
            break
    else:
        return False
    if len(match) != 2:
        return False
    if ind < 2:
        split_lat = split_gps_deci_str(match[0])
        split_lng = split_gps_deci_str(match[1])
        if len(split_lat) == len(split_lng) == 4:
            lat = convert_gps_to_decimal_degree(*split_lat)
            lng = convert_gps_to_decimal_degree(*split_lng)
        else:
            return False
    else:
        lat, lng = match

    return validate_gps_cord(lat, lng)


class WeeksToggleButtons(MDBoxLayout):
    weeks = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

    def refresh_week_buttons(self):
        for week in self.weeks:
            self.ids[week].is_active = True
        for week in self.weeks:
            self.ids[week].is_active = False


class EssentialContent(MDBoxLayout):
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

    def set_drop_down_item(self, opt):
        self.ids['m_km_button'].text = opt
        self.drop_down_menu.dismiss()


class AlarmExpansionPanel(MDExpansionPanel):
    def on_open(self, *args):
        # for child in self.parent.children:  # on_close won't be called if we open another panel without closing opened
        #     child: AlarmExpansionPanel = child
        #     if child.get_state() == 'open':
        #         child.panel_cls.reset_corner_radii()
        #         child.close_panel(child.parent, True)
        self.open_panel()
        self.panel_cls.change_canvas_corner_radii()
        Clock.schedule_once(self._focus, .1)

    def _focus(self, *_):
        self.parent.parent.scroll_to(widget=self)
        Clock.schedule_once(self._modify_top_app_bar_color, 0.35)

    # widget = self.content
    # print(*widget.pos, *widget.size)
    # pos = self.parent.to_widget(*widget.to_window(*widget.pos))
    # cor = self.parent.to_widget(*widget.to_window(widget.right,
    #                                               widget.top))
    # print(self.panel_cls.height+self.height, pos, cor)

    def _modify_top_app_bar_color(self, *_):
        self.parent.parent.parent.parent.scroll_movement(self.parent.parent.scroll_y)

    def on_close(self, *args):
        self.panel_cls.reset_corner_radii()

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
        Called when you click on the panel. Called methods to open or close
        a panel.
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

    def remove(self):
        anim = Animation(x=-self.width, duration=0.4, t='out_back')
        anim.bind(on_complete=self._remove)
        anim.start(self)

    def _remove(self, *_):
        if self.parent.parent.scroll_y == 0:
            self.parent.parent.scroll_y = (self.parent.parent.height - self.height) / self.parent.parent.height
            # self.parent.parent.scroll_to(self.parent.children[0].panel_cls)
        self.parent.remove_widget(self)  # goodbye


class AlarmsTab(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_start_callback = lambda x=None: x
        self.expansion_items = []

    def add_active_alarms(self):
        item = AlarmExpansionPanel(
            content=AlarmExpansionContent(),
            panel_cls=CustomExpansionPanelThreeLineListItem(
                text='Bengaluru',
                secondary_text='25km',
                tertiary_text='Sun, Mon, Fri'
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
    pass


class HomeScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_test_scroll = True
        self._color = None

    def on_enter(self, *args):
        # pass
        # Clock.schedule_once(self.ids['alarm_tab'].change_top_app_bar_color, 0.1)
        self.is_test_scroll = True

        # self._color = app.theme_cls.bg_normal
        Clock.schedule_once(self.change_top_app_bar_color, .1)
        # Clock.schedule_once(self.scroll_start, .1)
        # self.ids['alarm_tab'].scroll_start_callback = self.scroll_start

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
        """Called when clicking on a panel item."""

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
    ...


class AddNewLocationScreen(MDScreen):
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
        except KeyError:
            print('Key')
        except TypeError:
            print('Type')
        except ValueError:
            print('Value')
        else:
            return
        self.ids['cords_in'].error = True


class MainApp(MDApp):
    data = {
        'Python': 'language-python',
        'PHP': 'language-php',
        'C++': 'language-cpp',
    }

    @staticmethod
    def goto_screen(screen: str):
        change_screen_to(screen)

    @staticmethod
    def validate_alarm_distance(root, text, mode, focus=True):
        if text == '' and not focus:
            if mode == 'm':
                least = 50
            else:
                least = 1
            root.ids['dist_inp'].text = f'{least}'
            return
        try:
            if mode == 'm':
                d = int(text)
                least = 50
            else:
                d = float(text)
                least = 1
            if d < least:
                root.ids['dist_inp'].text = f'{least}'
        except ValueError:
            if text != '':
                root.ids['dist_inp'].text = text[:-1]

    @staticmethod
    def toast(message: str = ''):
        toast(message)

    def on_start(self):
        WindowBase.softinput_mode = 'below_target'
        WindowBase.on_maximize = lambda x=None: print(x, 'Hello')
        WindowBase.on_restore = lambda x=None: print(x, 'hell')
        # app.theme_cls.bg
        EventLoop.window.bind(on_keyboard=hook_keyboard)

    def build(self):
        self.theme_cls.material_style = 'M3'
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Teal'
        return sm


if __name__ == '__main__':
    Builder.load_file('frontend.kv')
    app = MainApp()
    sm = MDScreenManager(transition=MDFadeSlideTransition())

    home = HomeScreen(name='home')
    settings = SettingsScreen(name='settings')
    saved_locations = SavedLocationsScreen(name='saved_locations')
    new_location = AddNewLocationScreen(name='new_location')

    sm.add_widget(home)
    sm.add_widget(settings)
    sm.add_widget(saved_locations)
    sm.add_widget(new_location)

    # sm.current = 'new_location'

    app.run()
