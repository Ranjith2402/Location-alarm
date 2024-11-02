from kivy.animation import Animation
from kivy.metrics import dp
from kivymd.uix.selectioncontrol import MDSwitch
from main import MainApp


class MySwitch(MDSwitch):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.is_thumb_size_changed = False

    def on_touch_down(self, touch):
        # print(dir(touch))
        # print(self.pos, touch.pos, [self.size[0] + self.pos[0], self.size[1] + self.pos[1]])

        # Not my code start
        # IDK if it is needed but added from its parent class
        if self.disabled and self.collide_point(*touch.pos):
            return True
        for child in self.children[:]:
            if child.dispatch('on_touch_down', touch):
                return True
        # Not my code end

        if self.ids['thumb'].collide_point(touch.pos[0], touch.pos[1]):
            self.on_thumb_down()
            self._update_thumb_pos()
        # print(self.pos[1] + self.size[1] - touch.pos[1])

    def on_touch_up(self, touch):
        # Below line is copied from kivymd.uix.selectioncontrol.selectioncontrol.kv (line 84-97 kivymd version 1.0.2)
        # This draws a line around switch, I used this as a new bigger hit-box
        material_style = MainApp.material_style
        hit_box = (self.x - dp(2), self.center_y - dp(14), self.width + dp(14), dp(28)) if self.widget_style == "ios" \
            else ((1, 1, 1, 1) if material_style == "M2" else
                  (self.x + dp(8), self.center_y - dp(8), self.width + dp(16), dp(32)))

        # Draws the hit box
        # with self.canvas.after:
        #     Color(rgba=(1, 1, 1, 1))
        #     Line(points=[(a[0], a[1]),
        #                  (a[0] + a[2], a[1]),
        #                  (a[0] + a[2], a[1] + a[3]),
        #                  (a[0], a[1] + a[3]),
        #                  (a[0], a[1])
        #                  ])

        if (hit_box[0] <= touch.pos[0] <= hit_box[0] + hit_box[2] and
                hit_box[1] <= touch.pos[1] <= hit_box[1] + hit_box[3]):
            setattr(self, "active", not self.active)
            self.is_thumb_size_changed = False
            # print('activated')

    def on_thumb_down(self) -> None:
        """
        Called at the on_touch_down event of the class: 'Thumb' object.
        Indicates the state of the switch "on/off" by an animation of
        increasing the size of the thumb.
        """

        if self.widget_style != "ios" and self.theme_cls.material_style == "M3":
            if self.active:
                size = (dp(28), dp(28))
                pos = (self.ids.thumb.pos[0] - dp(2), self.ids.thumb.pos[1] - dp(1.8),) \
                    if not self.is_thumb_size_changed \
                    else self.ids.thumb.pos
            else:
                size = (dp(26), dp(26))
                pos = (
                    (
                        self.ids.thumb.pos[0] - dp(5),
                        self.ids.thumb.pos[1] - dp(5),
                    )
                    if not self.icon_inactive
                    else (
                        self.ids.thumb.pos[0] + dp(1),
                        self.ids.thumb.pos[1] - dp(1),
                    )
                ) if not self.is_thumb_size_changed else self.ids.thumb.pos
            Animation(size=size, pos=pos, t="out_quad", d=0.2).start(
                self.ids.thumb
            )
            self.is_thumb_size_changed = True
