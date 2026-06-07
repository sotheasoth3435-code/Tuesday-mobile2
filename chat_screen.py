"""
screens/chat_screen.py — TUESDAY Mobile
========================================
Voice + text chat screen. Mirrors dashboard.py Mission Hub
but touch-optimised for Android.
"""
import asyncio
import threading
import time
import re
import random

from kivy.clock          import Clock
from kivy.uix.scrollview import ScrollView
from kivy.metrics        import dp
from kivymd.app          import MDApp
from kivymd.uix.screen   import MDScreen
from kivymd.uix.boxlayout    import MDBoxLayout
from kivymd.uix.textfield    import MDTextField
from kivymd.uix.button       import MDIconButton, MDRaisedButton, MDFlatButton
from kivymd.uix.label        import MDLabel
from kivymd.uix.card         import MDCard
from kivymd.uix.progressindicator import MDCircularProgressIndicator

# Android speech (graceful fallback on desktop)
try:
    from android.permissions import request_permissions, Permission
    from jnius import autoclass
    ANDROID = True
except ImportError:
    ANDROID = False

ACCENT_HEX  = "#14B8A6"
TEXT_SEC    = "#8B949E"
BG_INPUT    = "#16191F"
BG_MSG      = "#12141A"


class MessageCard(MDCard):
    def __init__(self, sender: str, body: str, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(4),
            md_bg_color=(18/255, 20/255, 26/255, 1),
            radius=[dp(10)],
            **kwargs
        )
        color = ACCENT_HEX if "Tuesday" in sender else TEXT_SEC
        self.add_widget(MDLabel(
            text=sender,
            font_style="Body2",
            theme_text_color="Custom",
            text_color=color,
            bold=True,
            size_hint_y=None,
            height=dp(22),
        ))
        self.add_widget(MDLabel(
            text=body,
            font_style="Body1",
            theme_text_color="Primary",
            size_hint_y=None,
            text_size=(None, None),
            halign="left",
        ))
        self.bind(width=self._update_text_width)

    def _update_text_width(self, *_):
        for child in self.children:
            if isinstance(child, MDLabel) and child.font_style == "Body1":
                child.text_size = (self.width - dp(24), None)
                child.texture_update()
                child.height = child.texture_size[1] + dp(8)
        self.height = sum(c.height for c in self.children) + dp(28)


class ChatScreen(MDScreen):

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app          = app
        self.voice_active = False
        self._build_ui()
        if ANDROID:
            request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET])

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = MDBoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))

        # Header
        header = MDBoxLayout(size_hint_y=None, height=dp(44), padding=[dp(8), 0])
        header.add_widget(MDLabel(
            text="⚡ TUESDAY",
            font_style="H6",
            theme_text_color="Custom",
            text_color=ACCENT_HEX,
        ))
        # Mic status indicator (spinner or tick)
        self.mic_status = MDLabel(
            text="",
            size_hint_x=None,
            width=dp(28),
            theme_text_color="Custom",
            text_color=TEXT_SEC,
            font_style="H6",
            halign="center",
        )
        header.add_widget(self.mic_status)
        root.add_widget(header)

        # Chat scroll area
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.msg_list = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=[dp(4), dp(4)],
            size_hint_y=None,
        )
        self.msg_list.bind(minimum_height=self.msg_list.setter("height"))
        self.scroll.add_widget(self.msg_list)
        root.add_widget(self.scroll)

        # Input row
        input_row = MDBoxLayout(
            size_hint_y=None,
            height=dp(56),
            spacing=dp(6),
            padding=[dp(4), dp(4)],
            md_bg_color=(22/255, 25/255, 31/255, 1),
            radius=[dp(14)],
        )

        self.text_input = MDTextField(
            hint_text="Ask anything...",
            mode="fill",
            fill_color_normal=(22/255, 25/255, 31/255, 1),
            line_color_focus=ACCENT_HEX,
            size_hint_x=1,
        )
        self.text_input.bind(on_text_validate=lambda *_: self._send_text())
        input_row.add_widget(self.text_input)

        # Voice button
        self.voice_btn = MDIconButton(
            icon="microphone",
            theme_icon_color="Custom",
            icon_color=ACCENT_HEX,
            on_release=lambda *_: self._toggle_voice(),
        )
        input_row.add_widget(self.voice_btn)

        # Send button
        send_btn = MDIconButton(
            icon="send",
            theme_icon_color="Custom",
            icon_color=ACCENT_HEX,
            on_release=lambda *_: self._send_text(),
        )
        input_row.add_widget(send_btn)
        root.add_widget(input_row)

        self.add_widget(root)
        self._append("System", "Memory Drive initialized. Ready.")

    # ── Message helpers ───────────────────────────────────────────────────────
    def _append(self, sender: str, body: str):
        def _do(*_):
            card = MessageCard(sender=sender, body=body, size_hint_y=None)
            self.msg_list.add_widget(card)
            Clock.schedule_once(lambda *_: setattr(
                self.scroll, "scroll_y", 0), 0.1)
        Clock.schedule_once(_do)

    # ── Text send ─────────────────────────────────────────────────────────────
    def _send_text(self):
        text = self.text_input.text.strip()
        if not text:
            return
        self.text_input.text = ""
        self._append("[Mobile] Boss", text)
        asyncio.run_coroutine_threadsafe(
            self._get_reply(text), self.app.loop
        )

    async def _get_reply(self, text: str):
        try:
            reply = await self.app.brain.run_prompt(
                f"MOBILE MODE. Be concise. User said: {text}"
            )
        except Exception as e:
            reply = f"Error: {e}"
        self._append("Tuesday", reply)

    # ── Voice toggle ──────────────────────────────────────────────────────────
    def _toggle_voice(self):
        if not self.voice_active:
            self.voice_active = True
            self.voice_btn.icon       = "microphone-off"
            self.voice_btn.icon_color = (1, 0.3, 0.3, 1)
            self._start_mic_spinner()
            threading.Thread(target=self._voice_loop, daemon=True).start()
        else:
            self.voice_active = False
            self.voice_btn.icon       = "microphone"
            self.voice_btn.icon_color = (20/255, 184/255, 166/255, 1)
            Clock.schedule_once(lambda *_: setattr(self.mic_status, "text", ""))

    def _start_mic_spinner(self):
        self._spin_chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        self._spin_idx   = 0
        self._spin_event = Clock.schedule_interval(self._tick_spinner, 0.1)

    def _tick_spinner(self, *_):
        if not self.voice_active:
            self._spin_event.cancel()
            return
        if self.mic_status.text == "✓":
            self._spin_event.cancel()
            return
        self.mic_status.text = self._spin_chars[self._spin_idx % len(self._spin_chars)]
        self._spin_idx += 1

    def _mic_ready(self):
        if hasattr(self, "_spin_event"):
            self._spin_event.cancel()
        Clock.schedule_once(lambda *_: setattr(self.mic_status, "text", "✓"))

    # ── Voice loop (Android SpeechRecognizer or desktop sr fallback) ──────────
    def _voice_loop(self):
        if ANDROID:
            self._voice_loop_android()
        else:
            self._voice_loop_desktop()

    def _voice_loop_android(self):
        """
        Uses Android's built-in SpeechRecognizer via pyjnius.
        No internet latency — runs on-device.
        """
        try:
            SpeechRecognizer  = autoclass("android.speech.SpeechRecognizer")
            RecognizerIntent  = autoclass("android.speech.RecognizerIntent")
            Intent            = autoclass("android.content.Intent")
            Locale            = autoclass("java.util.Locale")

            Clock.schedule_once(lambda *_: self._mic_ready())

            while self.voice_active:
                # Android STT is callback-based; we use a threading.Event to block
                result_event  = threading.Event()
                result_holder = [None]

                def on_results(bundle):
                    results = bundle.getStringArrayList(
                        SpeechRecognizer.RESULTS_RECOGNITION
                    )
                    if results and results.size() > 0:
                        result_holder[0] = results.get(0)
                    result_event.set()

                def on_error(error):
                    result_event.set()

                intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE,
                                Locale.getDefault())
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)

                sr_instance = SpeechRecognizer.createSpeechRecognizer(
                    autoclass("org.kivy.android.PythonActivity").mActivity
                )
                sr_instance.setRecognitionListener(type(
                    "RL", (), {
                        "onResults":          lambda self, b: on_results(b),
                        "onError":            lambda self, e: on_error(e),
                        "onBeginningOfSpeech":lambda self: None,
                        "onEndOfSpeech":      lambda self: None,
                        "onReadyForSpeech":   lambda self, p: None,
                        "onRmsChanged":       lambda self, r: None,
                        "onBufferReceived":   lambda self, b: None,
                        "onPartialResults":   lambda self, b: None,
                        "onEvent":            lambda self, t, b: None,
                    }
                )())
                sr_instance.startListening(intent)
                result_event.wait(timeout=8)
                sr_instance.destroy()

                text = result_holder[0]
                if not text or not text.strip():
                    continue

                self._append("[Voice] Boss", text)
                asyncio.run_coroutine_threadsafe(
                    self._get_reply(text), self.app.loop
                )
                time.sleep(0.3)

        except Exception as e:
            self._append("System", f"Voice error: {e}")
            Clock.schedule_once(lambda *_: self._toggle_voice())

    def _voice_loop_desktop(self):
        """Fallback for testing on PC (uses speech_recognition library)."""
        try:
            import speech_recognition as sr_lib
            recognizer = sr_lib.Recognizer()
            recognizer.pause_threshold    = 0.8
            recognizer.non_speaking_duration = 0.3
            mic = sr_lib.Microphone()
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                Clock.schedule_once(lambda *_: self._mic_ready())
                while self.voice_active:
                    try:
                        audio = recognizer.listen(source, timeout=3, phrase_time_limit=12)
                    except sr_lib.WaitTimeoutError:
                        continue
                    try:
                        text = recognizer.recognize_google(audio)
                    except sr_lib.UnknownValueError:
                        continue
                    if not text.strip():
                        continue
                    self._append("[Voice] Boss", text)
                    asyncio.run_coroutine_threadsafe(
                        self._get_reply(text), self.app.loop
                    )
                    time.sleep(0.3)
        except Exception as e:
            self._append("System", f"Voice error: {e}")
