"""
main.py — TUESDAY Mobile
========================
Kivy entry point. Manages screen routing, async loop,
and the shared AgentOrchestrator instance.
"""
import asyncio
import os
import threading

from dotenv import load_dotenv
load_dotenv()

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivymd.app import MDApp
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem
from kivymd.uix.boxlayout import MDBoxLayout

from screens.chat_screen    import ChatScreen
from screens.memory_screen  import MemoryScreen
from screens.planner_screen import PlannerScreen
from screens.profile_screen import ProfileScreen

# ── Shared brain (imported once, passed to every screen) ─────────────────────
from agent.orchestrator import AgentOrchestrator
from memory_drive       import MemoryDrive

# Dark palette — matches desktop
BG_MAIN    = (15/255, 17/255, 21/255, 1)
BG_SIDEBAR = (9/255, 10/255, 12/255, 1)
ACCENT     = (20/255, 184/255, 166/255, 1)


class TuesdayMobile(MDApp):

    def build(self):
        self.theme_cls.theme_style   = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.title = "TUESDAY"

        # ── Async event loop (runs in background thread) ──────────────────────
        self.loop = asyncio.new_event_loop()
        threading.Thread(
            target=lambda: (
                asyncio.set_event_loop(self.loop),
                self.loop.run_forever()
            ),
            daemon=True
        ).start()

        # ── Shared brain & memory ─────────────────────────────────────────────
        self.memory = MemoryDrive()
        self.brain  = AgentOrchestrator()

        # ── Root layout ───────────────────────────────────────────────────────
        root = MDBoxLayout(orientation="vertical", md_bg_color=BG_MAIN)

        # Screen manager
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(ChatScreen(   app=self, name="chat"))
        self.sm.add_widget(MemoryScreen( app=self, name="memory"))
        self.sm.add_widget(PlannerScreen(app=self, name="planner"))
        self.sm.add_widget(ProfileScreen(app=self, name="profile"))
        root.add_widget(self.sm)

        # Bottom navigation bar
        nav = MDNavigationBar(on_switch_tabs=self._on_tab_switch)
        for icon, screen, label in [
            ("message-text-outline",  "chat",    "Chat"),
            ("brain",                 "memory",  "Memory"),
            ("calendar-check",        "planner", "Planner"),
            ("account-outline",       "profile", "Profile"),
        ]:
            item = MDNavigationItem(icon=icon, text=label)
            nav.add_widget(item)
        root.add_widget(nav)

        return root

    def _on_tab_switch(self, bar, item, item_icon, item_text):
        mapping = {
            "Chat":    "chat",
            "Memory":  "memory",
            "Planner": "planner",
            "Profile": "profile",
        }
        self.sm.current = mapping.get(item_text, "chat")


if __name__ == "__main__":
    TuesdayMobile().run()
