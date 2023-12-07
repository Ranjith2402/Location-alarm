from kivymd.app import MDApp
from kivy.lang.builder import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.clock import Clock
from kivymd.uix.expansionpanel.expansionpanel import MDExpansionPanel, MDExpansionPanelThreeLine
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list.list import OneLineListItem
from kivymd.uix.menu.menu import MDDropdownMenu
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.core.window import WindowBase


class CustomDropDownListItem(OneLineListItem):
    ...


class AlarmExpansionContent(MDBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.drop_down_menu = None

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
    def remove(self):
        anim = Animation(x=-self.width, duration=0.4, t='out_back')
        anim.bind(on_complete=self._remove)
        anim.start(self)

    def _remove(self, *_):
        self.parent.remove_widget(self)


class AlarmsTab(MDScreen):
    def change_top_app_bar_color(self, _=None):
        print('Start')
        self.ids['top_app_bar'].md_bg_color = 1, 0, 0, 0

    def add_active_alarms(self):
        self.ids['container'].add_widget(AlarmExpansionPanel(
            content=AlarmExpansionContent(),
            panel_cls=MDExpansionPanelThreeLine(
                text='Bengaluru',
                secondary_text='                ',
                tertiary_text='Sun, Mon, Fri'
            ),
        ))


class HomeScreen(MDScreen):
    def on_enter(self, *args):
        pass
        # Clock.schedule_once(self.ids['alarm_tab'].change_top_app_bar_color, 0.1)

    def add_content(self):
        self.ids['alarm_tab'].add_active_alarms()


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
        self.theme_cls.primary_palette = 'Pink'
        print(self.theme_cls.primary_palette)
        return sm


if __name__ == '__main__':
    Builder.load_file('frontend.kv')
    app = MainApp()
    sm = MDScreenManager()

    home = HomeScreen(name='home')

    sm.add_widget(home)

    app.run()
