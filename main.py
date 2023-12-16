from kivymd.app import MDApp
from kivy.lang.builder import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.clock import Clock
from kivymd.uix.expansionpanel.expansionpanel import MDExpansionPanel, MDExpansionPanelThreeLine, \
    MDExpansionPanelTwoLine, MDExpansionPanelLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list.list import OneLineListItem
from kivymd.uix.menu.menu import MDDropdownMenu
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.core.window import WindowBase


class CustomDropDownListItem(OneLineListItem):
    ...


class CustomExpansionPanelThreeLineListItem(MDExpansionPanelThreeLine):
    is_open = False
    _txt_left_pad = dp(15)

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
        for week in self.weeks:
            self.ids[week].is_active = True
        for week in self.weeks:
            self.ids[week].is_active = False

    def remove(self):
        self.parent.remove()

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

    def validate_alarm_distance(self, text, mode, focus=True):
        if text == '' and not focus:
            if mode == 'm':
                least = 50
            else:
                least = 1
            self.ids['dist_inp'].text = f'{least}'
            return
        try:
            if mode == 'm':
                d = int(text)
                least = 50
            else:
                d = float(text)
                least = 1
            if d < least:
                self.ids['dist_inp'].text = f'{least}'
        except ValueError:
            if text != '':
                self.ids['dist_inp'].text = text[:-1]


class AlarmExpansionPanel(MDExpansionPanel):
    def on_open(self, *args):
        # for child in self.parent.children:  # on_close won't be called if we open another panel without closing opened
        #     child: AlarmExpansionPanel = child
        #     if child.get_state() == 'open':
        #         child.panel_cls.reset_corner_radii()
        #         child.close_panel(child.parent, True)
        self.panel_cls.change_canvas_corner_radii()
        self.open_panel()

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
        self.parent.remove_widget(self)


class AlarmsTab(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_start_callback = lambda x=None: x
        self.expansion_items = []

    def scroll_start(self, args):
        self.scroll_start_callback(args)

    def change_top_app_bar_color(self, _=None, color=None):
        if color is None:
            self.ids['top_app_bar'].md_bg_color = app.theme_cls.colors[app.theme_cls.primary_palette]['900'] + '15'
        else:
            self.ids['top_app_bar'].md_bg_color = color
        # self.ids['top_app_bar'].md_bg_color = 0.1, 0.1, 0.1, 0.8

    def add_active_alarms(self):
        item = AlarmExpansionPanel(
            content=AlarmExpansionContent(),
            panel_cls=CustomExpansionPanelThreeLineListItem(
                text='Bengaluru',
                secondary_text='                ',
                tertiary_text='Sun, Mon, Fri'
            ),
        )

        self.expansion_items.append(item)
        self.ids['container'].add_widget(item)


class HomeScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.is_test_scroll = True

    def scroll_start(self, dist):
        if self.is_test_scroll:
            self.is_test_scroll = False
            dist = 1
        if dist == 1:
            self.ids['alarm_tab'].change_top_app_bar_color(color=app.theme_cls.bg_normal)
            self.ids['bottom_navigation'].panel_color = app.theme_cls.bg_normal
        else:
            self.ids['alarm_tab'].change_top_app_bar_color()
            self.ids['bottom_navigation']. \
                panel_color = app.theme_cls.colors[app.theme_cls.primary_palette]['900'] + '1a'

    def on_enter(self, *args):
        # pass
        Clock.schedule_once(self.ids['alarm_tab'].change_top_app_bar_color, 0.1)
        self.is_test_scroll = True
        # Clock.schedule_once(self.scroll_start, .1)
        # self.ids['alarm_tab'].scroll_start_callback = self.scroll_start

    def add_content(self):
        self.ids['alarm_tab'].add_active_alarms()


class GoogleMapsTab(MDScreen):
    pass


class MainApp(MDApp):
    data = {
        'Python': 'language-python',
        'PHP': 'language-php',
        'C++': 'language-cpp',
    }

    def on_start(self):
        WindowBase.softinput_mode = 'pan'

    def build(self):
        self.theme_cls.material_style = 'M3'
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Teal'
        return sm


if __name__ == '__main__':
    Builder.load_file('frontend.kv')
    app = MainApp()
    sm = MDScreenManager()

    home = HomeScreen(name='home')

    sm.add_widget(home)

    app.run()
