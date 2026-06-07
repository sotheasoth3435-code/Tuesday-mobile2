"""
screens/memory_screen.py — TUESDAY Mobile
==========================================
Pin, view and unpin memories. Syncs with the same
memory.json used by the desktop app.
"""
import asyncio

from kivy.clock        import Clock
from kivy.metrics      import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout  import MDBoxLayout
from kivymd.uix.textfield  import MDTextField
from kivymd.uix.button     import MDRaisedButton, MDIconButton
from kivymd.uix.label      import MDLabel
from kivymd.uix.card       import MDCard
from kivymd.uix.menu       import MDDropdownMenu

ACCENT_HEX = "#14B8A6"
TEXT_SEC   = "#8B949E"

LABEL_COLORS = {
    "TASK":      "#F59E0B",
    "PLAN":      "#3B82F6",
    "GOAL":      "#8B5CF6",
    "REMINDER":  "#EC4899",
    "REFERENCE": "#6B7280",
    "DEADLINE":  "#EF4444",
    "MEETING":   "#10B981",
    "NOTE":      "#9CA3AF",
}


class MemoryScreen(MDScreen):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app           = app
        self._selected_label = "Let Tuesday decide"
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        root = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        # Title
        root.add_widget(MDLabel(
            text="Memory Panel",
            font_style="H5",
            theme_text_color="Custom",
            text_color=ACCENT_HEX,
            size_hint_y=None,
            height=dp(40),
        ))

        # Input box
        self.mem_input = MDTextField(
            hint_text="Paste a note, task, or meeting summary...",
            mode="fill",
            multiline=True,
            max_height=dp(120),
            fill_color_normal=(22/255, 25/255, 31/255, 1),
            line_color_focus=ACCENT_HEX,
        )
        root.add_widget(self.mem_input)

        # Label selector + Pin button row
        action_row = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))

        self.label_btn = MDRaisedButton(
            text="Let Tuesday decide",
            md_bg_color=(30/255, 34/255, 42/255, 1),
            on_release=self._open_label_menu,
        )
        action_row.add_widget(self.label_btn)

        pin_btn = MDRaisedButton(
            text="Pin",
            md_bg_color=(20/255, 184/255, 166/255, 1),
            on_release=lambda *_: self._pin(),
        )
        action_row.add_widget(pin_btn)
        root.add_widget(action_row)

        # Status label
        self.status_lbl = MDLabel(
            text="",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=TEXT_SEC,
            size_hint_y=None,
            height=dp(20),
        )
        root.add_widget(self.status_lbl)

        # Pinned memories list
        root.add_widget(MDLabel(
            text="Pinned Memories",
            font_style="Subtitle1",
            theme_text_color="Primary",
            size_hint_y=None,
            height=dp(30),
        ))

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.mem_list = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[dp(2), dp(2)],
            size_hint_y=None,
        )
        self.mem_list.bind(minimum_height=self.mem_list.setter("height"))
        self.scroll.add_widget(self.mem_list)
        root.add_widget(self.scroll)

        self.add_widget(root)

        # Dropdown menu
        items = [{"text": l, "on_release": lambda x=l: self._set_label(x)}
                 for l in ["Let Tuesday decide","TASK","PLAN","GOAL",
                            "REMINDER","REFERENCE","DEADLINE","MEETING","NOTE"]]
        self.menu = MDDropdownMenu(caller=self.label_btn, items=items, width_mult=4)

    def _open_label_menu(self, *_):
        self.menu.open()

    def _set_label(self, label: str):
        self._selected_label = label
        self.label_btn.text  = label
        self.menu.dismiss()

    def _pin(self):
        text = self.mem_input.text.strip()
        if not text:
            return
        self.mem_input.text = ""
        if self._selected_label == "Let Tuesday decide":
            self.status_lbl.text = "Tuesday is labelling..."
            asyncio.run_coroutine_threadsafe(
                self._ai_pin(text), self.app.loop
            )
        else:
            self.app.memory.add_pinned_memory(text, self._selected_label, source="mobile")
            self.status_lbl.text = f"Pinned as [{self._selected_label}]"
            self._refresh()

    async def _ai_pin(self, text: str):
        try:
            mem = await self.app.brain.pin_memory_from_text(text)
            Clock.schedule_once(lambda *_: setattr(
                self.status_lbl, "text", f"Pinned as [{mem['label']}]"))
        except Exception as e:
            self.app.memory.add_pinned_memory(text, "NOTE", source="mobile")
            Clock.schedule_once(lambda *_: setattr(
                self.status_lbl, "text", "Pinned as [NOTE]"))
        Clock.schedule_once(lambda *_: self._refresh())

    def _refresh(self):
        self.mem_list.clear_widgets()
        mems = self.app.memory.get_pinned_memories()
        if not mems:
            self.mem_list.add_widget(MDLabel(
                text="No pinned memories yet.",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(40),
            ))
            return
        for mem in reversed(mems):
            self._add_card(mem)

    def _add_card(self, mem: dict):
        color = LABEL_COLORS.get(mem.get("label", "NOTE"), "#9CA3AF")
        card  = MDCard(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(4),
            md_bg_color=(18/255, 20/255, 26/255, 1),
            radius=[dp(8)],
            size_hint_y=None,
        )
        # Label badge + unpin row
        top_row = MDBoxLayout(size_hint_y=None, height=dp(28))
        top_row.add_widget(MDLabel(
            text=mem.get("label","NOTE"),
            font_style="Caption",
            theme_text_color="Custom",
            text_color=color,
            bold=True,
        ))
        mem_id = mem["id"]
        unpin = MDIconButton(
            icon="pin-off",
            theme_icon_color="Custom",
            icon_color=(0.97, 0.44, 0.44, 1),
            size_hint_x=None,
            width=dp(36),
            on_release=lambda *_, mid=mem_id: self._unpin(mid),
        )
        top_row.add_widget(unpin)
        card.add_widget(top_row)

        body_lbl = MDLabel(
            text=mem.get("text",""),
            font_style="Body2",
            theme_text_color="Primary",
            size_hint_y=None,
            text_size=(None, None),
            halign="left",
        )
        card.add_widget(body_lbl)

        meta = MDLabel(
            text=f"Pinned {mem.get('pinned_at','')}  •  {mem.get('source','?')}",
            font_style="Caption",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(20),
        )
        card.add_widget(meta)

        # Force height after bind
        def _set_height(*_):
            body_lbl.text_size = (card.width - dp(20), None)
            body_lbl.texture_update()
            body_lbl.height = body_lbl.texture_size[1] + dp(6)
            card.height = dp(28) + body_lbl.height + dp(20) + dp(24)
        card.bind(width=_set_height)
        Clock.schedule_once(lambda *_: _set_height())
        self.mem_list.add_widget(card)

    def _unpin(self, mem_id: str):
        self.app.memory.remove_pinned_memory(mem_id)
        self._refresh()
