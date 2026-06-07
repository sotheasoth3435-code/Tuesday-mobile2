"""
screens/profile_screen.py — TUESDAY Mobile
===========================================
Edit Albe's profile and TUESDAY's behaviour rules.
Saves to the shared memory.json / config.json.
"""
from kivy.clock        import Clock
from kivy.metrics      import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout  import MDBoxLayout
from kivymd.uix.textfield  import MDTextField
from kivymd.uix.button     import MDRaisedButton
from kivymd.uix.label      import MDLabel

ACCENT_HEX = "#14B8A6"
TEXT_SEC   = "#8B949E"


class ProfileScreen(MDScreen):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self._build_ui()
        self._load()

    def _build_ui(self):
        scroll = ScrollView()
        root   = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(14),
            size_hint_y=None,
        )
        root.bind(minimum_height=root.setter("height"))

        root.add_widget(MDLabel(
            text="Profile & Settings",
            font_style="H5",
            theme_text_color="Custom",
            text_color=ACCENT_HEX,
            size_hint_y=None,
            height=dp(44),
        ))

        # Display name
        root.add_widget(MDLabel(
            text="Display Name",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
        ))
        self.name_field = MDTextField(
            mode="fill",
            fill_color_normal=(22/255, 25/255, 31/255, 1),
            line_color_focus=ACCENT_HEX,
            size_hint_y=None,
            height=dp(48),
        )
        root.add_widget(self.name_field)

        # Bio
        root.add_widget(MDLabel(
            text="Background & Context (TUESDAY reads this)",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
        ))
        self.bio_field = MDTextField(
            mode="fill",
            multiline=True,
            max_height=dp(160),
            fill_color_normal=(22/255, 25/255, 31/255, 1),
            line_color_focus=ACCENT_HEX,
        )
        root.add_widget(self.bio_field)

        # Behaviour rules
        root.add_widget(MDLabel(
            text="TUESDAY Behaviour Rules",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
        ))
        self.rules_field = MDTextField(
            mode="fill",
            multiline=True,
            max_height=dp(160),
            fill_color_normal=(22/255, 25/255, 31/255, 1),
            line_color_focus=ACCENT_HEX,
        )
        root.add_widget(self.rules_field)

        # Save button
        save_btn = MDRaisedButton(
            text="Save to Memory",
            md_bg_color=(20/255, 184/255, 166/255, 1),
            size_hint_y=None,
            height=dp(44),
            on_release=lambda *_: self._save(),
        )
        root.add_widget(save_btn)

        # Status
        self.status_lbl = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=ACCENT_HEX,
            size_hint_y=None,
            height=dp(24),
        )
        root.add_widget(self.status_lbl)

        scroll.add_widget(root)
        self.add_widget(scroll)

    def _load(self):
        cfg   = self.app.memory.load_config()
        albe  = cfg.get("albe_profile", {})
        tues  = cfg.get("tuesday_settings", {})
        Clock.schedule_once(lambda *_: self._fill(albe, tues))

    def _fill(self, albe: dict, tues: dict):
        self.name_field.text  = albe.get("name", "")
        self.bio_field.text   = albe.get("bio", "")
        self.rules_field.text = tues.get("behavior_rules", "")

    def _save(self):
        cfg = self.app.memory.load_config()
        cfg.setdefault("albe_profile",    {})["name"]           = self.name_field.text.strip()
        cfg.setdefault("albe_profile",    {})["bio"]            = self.bio_field.text.strip()
        cfg.setdefault("tuesday_settings",{})["behavior_rules"] = self.rules_field.text.strip()
        self.app.memory.save_config(cfg)
        self.status_lbl.text = "✓ Saved to memory."
        Clock.schedule_once(lambda *_: setattr(self.status_lbl, "text", ""), 3)
