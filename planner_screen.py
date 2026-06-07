"""
screens/planner_screen.py — TUESDAY Mobile
===========================================
Calendar-aware planner. TUESDAY reads your tasks and
can summarise your day, set reminders, and plan ahead.
"""
import asyncio
from datetime import datetime

from kivy.clock        import Clock
from kivy.metrics      import dp
from kivy.uix.scrollview import ScrollView
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout  import MDBoxLayout
from kivymd.uix.textfield  import MDTextField
from kivymd.uix.button     import MDRaisedButton, MDIconButton
from kivymd.uix.label      import MDLabel
from kivymd.uix.card       import MDCard
from kivymd.uix.selectioncontrol import MDCheckbox

ACCENT_HEX = "#14B8A6"
TEXT_SEC   = "#8B949E"

# Android calendar access (graceful fallback)
try:
    from android.permissions import request_permissions, Permission
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False


def _get_calendar_events() -> list[dict]:
    """Pull today's events from Android Calendar provider."""
    if not ANDROID:
        return []
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri            = autoclass("android.net.Uri")
        context        = PythonActivity.mActivity

        now     = int(datetime.now().timestamp() * 1000)
        end_day = now + 86_400_000  # +24 h

        uri    = Uri.parse("content://com.android.calendar/events")
        cursor = context.getContentResolver().query(
            uri,
            ["title", "dtstart", "dtend", "description"],
            f"dtstart >= {now} AND dtstart <= {end_day}",
            None, "dtstart ASC"
        )
        events = []
        if cursor:
            while cursor.moveToNext():
                ts    = cursor.getLong(1)
                dt    = datetime.fromtimestamp(ts / 1000)
                events.append({
                    "title": cursor.getString(0) or "(no title)",
                    "time":  dt.strftime("%H:%M"),
                    "desc":  cursor.getString(3) or "",
                })
            cursor.close()
        return events
    except Exception:
        return []


class TaskCard(MDCard):
    def __init__(self, task_text: str, on_delete, **kwargs):
        super().__init__(
            orientation="horizontal",
            padding=dp(8),
            spacing=dp(8),
            md_bg_color=(18/255, 20/255, 26/255, 1),
            radius=[dp(8)],
            size_hint_y=None,
            height=dp(52),
            **kwargs
        )
        self.checkbox = MDCheckbox(size_hint=(None, None), size=(dp(32), dp(32)))
        self.add_widget(self.checkbox)

        self.task_lbl = MDLabel(
            text=task_text,
            font_style="Body2",
            theme_text_color="Primary",
        )
        self.add_widget(self.task_lbl)

        del_btn = MDIconButton(
            icon="delete-outline",
            theme_icon_color="Custom",
            icon_color=(0.97, 0.44, 0.44, 1),
            size_hint_x=None,
            width=dp(36),
            on_release=lambda *_: on_delete(self),
        )
        self.add_widget(del_btn)


class PlannerScreen(MDScreen):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app   = app
        self._tasks: list[str] = []
        self._build_ui()
        if ANDROID:
            request_permissions([
                Permission.READ_CALENDAR,
                Permission.WRITE_CALENDAR,
            ])
        Clock.schedule_once(lambda *_: self._load_calendar(), 0.5)

    def _build_ui(self):
        root = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        root.add_widget(MDLabel(
            text="Planner",
            font_style="H5",
            theme_text_color="Custom",
            text_color=ACCENT_HEX,
            size_hint_y=None,
            height=dp(40),
        ))

        # "Ask TUESDAY to plan" button
        plan_btn = MDRaisedButton(
            text="⚡  Summarise my day with TUESDAY",
            md_bg_color=(20/255, 184/255, 166/255, 1),
            size_hint_y=None,
            height=dp(44),
            on_release=lambda *_: self._ai_plan(),
        )
        root.add_widget(plan_btn)

        # TUESDAY response box
        self.ai_card = MDCard(
            padding=dp(12),
            md_bg_color=(18/255, 20/255, 26/255, 1),
            radius=[dp(10)],
            size_hint_y=None,
            height=dp(60),
        )
        self.ai_lbl = MDLabel(
            text="Tap above to have TUESDAY plan your day.",
            font_style="Body2",
            theme_text_color="Secondary",
            text_size=(None, None),
            halign="left",
        )
        self.ai_card.add_widget(self.ai_lbl)
        root.add_widget(self.ai_card)

        # Today's calendar events
        root.add_widget(MDLabel(
            text="Today's Calendar",
            font_style="Subtitle1",
            theme_text_color="Primary",
            size_hint_y=None,
            height=dp(30),
        ))
        self.cal_scroll = ScrollView(size_hint=(1, None), height=dp(160), do_scroll_x=False)
        self.cal_list   = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
        )
        self.cal_list.bind(minimum_height=self.cal_list.setter("height"))
        self.cal_scroll.add_widget(self.cal_list)
        root.add_widget(self.cal_scroll)

        # Task list
        root.add_widget(MDLabel(
            text="Tasks",
            font_style="Subtitle1",
            theme_text_color="Primary",
            size_hint_y=None,
            height=dp(30),
        ))

        add_row = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.task_input = MDTextField(
            hint_text="Add a task...",
            mode="fill",
            fill_color_normal=(22/255, 25/255, 31/255, 1),
            line_color_focus=ACCENT_HEX,
        )
        self.task_input.bind(on_text_validate=lambda *_: self._add_task())
        add_row.add_widget(self.task_input)
        add_btn = MDIconButton(
            icon="plus-circle",
            theme_icon_color="Custom",
            icon_color=ACCENT_HEX,
            on_release=lambda *_: self._add_task(),
        )
        add_row.add_widget(add_btn)
        root.add_widget(add_row)

        self.task_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.task_list   = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
        )
        self.task_list.bind(minimum_height=self.task_list.setter("height"))
        self.task_scroll.add_widget(self.task_list)
        root.add_widget(self.task_scroll)

        self.add_widget(root)

    # ── Calendar ──────────────────────────────────────────────────────────────
    def _load_calendar(self):
        events = _get_calendar_events()
        self.cal_list.clear_widgets()
        if not events:
            self.cal_list.add_widget(MDLabel(
                text="No events today.",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(30),
            ))
            return
        for ev in events:
            card = MDCard(
                padding=dp(8),
                md_bg_color=(22/255, 25/255, 31/255, 1),
                radius=[dp(6)],
                size_hint_y=None,
                height=dp(48),
            )
            row = MDBoxLayout(spacing=dp(8))
            row.add_widget(MDLabel(
                text=ev["time"],
                font_style="Caption",
                theme_text_color="Custom",
                text_color=ACCENT_HEX,
                size_hint_x=None,
                width=dp(44),
            ))
            row.add_widget(MDLabel(
                text=ev["title"],
                font_style="Body2",
                theme_text_color="Primary",
            ))
            card.add_widget(row)
            self.cal_list.add_widget(card)

    # ── AI planner ────────────────────────────────────────────────────────────
    def _ai_plan(self):
        events   = _get_calendar_events()
        tasks    = self._tasks
        ev_text  = "\n".join(f"- {e['time']} {e['title']}" for e in events) or "No calendar events."
        task_text= "\n".join(f"- {t}" for t in tasks) or "No tasks."
        prompt   = (
            f"MOBILE PLANNER MODE. Be concise, no markdown.\n"
            f"My calendar today:\n{ev_text}\n\n"
            f"My task list:\n{task_text}\n\n"
            f"Give me a brief daily plan and any suggestions."
        )
        self.ai_lbl.text = "Planning your day..."
        asyncio.run_coroutine_threadsafe(
            self._run_plan(prompt), self.app.loop
        )

    async def _run_plan(self, prompt: str):
        try:
            reply = await self.app.brain.run_prompt(prompt)
        except Exception as e:
            reply = f"Error: {e}"
        def _update(*_):
            self.ai_lbl.text = reply
            self.ai_lbl.texture_update()
            self.ai_card.height = self.ai_lbl.texture_size[1] + dp(28)
        Clock.schedule_once(_update)

    # ── Tasks ─────────────────────────────────────────────────────────────────
    def _add_task(self):
        text = self.task_input.text.strip()
        if not text:
            return
        self.task_input.text = ""
        self._tasks.append(text)
        card = TaskCard(task_text=text, on_delete=self._remove_task)
        self.task_list.add_widget(card)

    def _remove_task(self, card: TaskCard):
        text = card.task_lbl.text
        if text in self._tasks:
            self._tasks.remove(text)
        self.task_list.remove_widget(card)
