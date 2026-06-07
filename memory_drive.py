"""
memory_drive.py  —  Tuesday's Persistent Memory Core
=====================================================
Handles:
  - config.json load/save
  - Chat session archiving
  - Pinned memories with AI-assigned labels, timestamps, and manual unpin
  - File reading  (txt, pdf, docx, csv, json, md, py, etc.)
  - Image reading (returns base64 + mime for vision API)
"""

import json
import os
import base64
import mimetypes
from datetime import datetime
from pathlib import Path

CONFIG_FILE = "config.json"
CHAT_DIR    = "chats"

# ── Label taxonomy Tuesday can assign ────────────────────────────────────────
VALID_LABELS = ["TASK", "PLAN", "GOAL", "REMINDER", "REFERENCE", "DEADLINE", "MEETING", "NOTE"]


class MemoryDrive:

    def __init__(self):
        Path(CHAT_DIR).mkdir(exist_ok=True)
        self._ensure_config_exists()

    # ── Config ────────────────────────────────────────────────────────────────

    def _ensure_config_exists(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config({
                "albe_profile": {
                    "name": "Albe (Soth Sothea)",
                    "bio": "",
                    "profile_picture_path": ""
                },
                "tuesday_settings": {
                    "greeting": "Online.",
                    "behavior_rules": "",
                    "voice_rate": "+10%"
                },
                "pinned_memories": [],
                "memory_slots": []
            })

    def load_config(self) -> dict:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, data: dict):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # ── Pinned Memories ───────────────────────────────────────────────────────

    def get_pinned_memories(self) -> list[dict]:
        """
        Returns all pinned memory objects.
        Each object: {id, text, label, pinned_at, source}
        """
        cfg = self.load_config()
        return cfg.get("memory_slots", [])

    def add_pinned_memory(self, text: str, label: str, source: str = "manual") -> dict:
        """
        Pins a new memory. label must be one of VALID_LABELS.
        Returns the new memory object so the UI can display it immediately.
        """
        label = label.upper().strip()
        if label not in VALID_LABELS:
            label = "NOTE"

        cfg = self.load_config()
        if "memory_slots" not in cfg:
            cfg["memory_slots"] = []

        mem = {
            "id":        f"mem_{int(datetime.now().timestamp())}",
            "text":      text.strip(),
            "label":     label,
            "pinned_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source":    source           # "manual" | "ai" | "file" | "image"
        }
        cfg["memory_slots"].append(mem)
        self.save_config(cfg)
        return mem

    def remove_pinned_memory(self, mem_id: str) -> bool:
        """Unpins a memory by its id. Returns True if found and removed."""
        cfg = self.load_config()
        before = len(cfg.get("memory_slots", []))
        cfg["memory_slots"] = [m for m in cfg.get("memory_slots", []) if m["id"] != mem_id]
        self.save_config(cfg)
        return len(cfg["memory_slots"]) < before

    def update_memory_label(self, mem_id: str, new_label: str) -> bool:
        """Lets the UI or Tuesday reassign a label."""
        new_label = new_label.upper().strip()
        if new_label not in VALID_LABELS:
            return False
        cfg = self.load_config()
        for m in cfg.get("memory_slots", []):
            if m["id"] == mem_id:
                m["label"] = new_label
                self.save_config(cfg)
                return True
        return False

    def format_memories_for_prompt(self) -> str:
        """
        Returns a compact string injected into Tuesday's system prompt
        so she is always aware of pinned items.
        """
        mems = self.get_pinned_memories()
        if not mems:
            return ""
        lines = ["PINNED MEMORY BANK (always prioritise these):"]
        for m in mems:
            lines.append(f"  [{m['label']}] {m['text']}  (pinned {m['pinned_at']})")
        return "\n".join(lines)

    # ── Chat archiving ────────────────────────────────────────────────────────

    def archive_chat_session(self, chat_history_list: list):
        if len(chat_history_list) <= 1:
            return
        ts       = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(CHAT_DIR, f"Session_{ts}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            for msg in chat_history_list:
                role    = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                if isinstance(content, list):
                    # multi-part content (vision messages) — extract text only
                    content = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                f.write(f"[{role}]\n{content}\n\n")

    # ── File reading ──────────────────────────────────────────────────────────

    @staticmethod
    def read_file(filepath: str) -> dict:
        """
        Reads any supported file and returns:
          {"type": "text", "content": "...", "filename": "..."}
          {"type": "image", "base64": "...", "mime": "image/png", "filename": "..."}
          {"type": "error", "message": "..."}
        """
        path = Path(filepath)
        if not path.exists():
            return {"type": "error", "message": f"File not found: {filepath}"}

        suffix = path.suffix.lower()
        name   = path.name

        # ── Images ───────────────────────────────────────────────────────────
        if suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
            mime = mimetypes.guess_type(filepath)[0] or "image/png"
            with open(filepath, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return {"type": "image", "base64": b64, "mime": mime, "filename": name}

        # ── PDF ──────────────────────────────────────────────────────────────
        if suffix == ".pdf":
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(filepath) as pdf:
                    for pg in pdf.pages:
                        t = pg.extract_text()
                        if t:
                            text_parts.append(t)
                return {"type": "text", "content": "\n\n".join(text_parts)[:15000], "filename": name}
            except ImportError:
                return {"type": "error", "message": "pdfplumber not installed. Run: pip install pdfplumber"}
            except Exception as e:
                return {"type": "error", "message": f"PDF read error: {e}"}

        # ── DOCX ─────────────────────────────────────────────────────────────
        if suffix == ".docx":
            try:
                import docx
                doc   = docx.Document(filepath)
                text  = "\n".join(p.text for p in doc.paragraphs)
                return {"type": "text", "content": text[:15000], "filename": name}
            except ImportError:
                return {"type": "error", "message": "python-docx not installed. Run: pip install python-docx"}
            except Exception as e:
                return {"type": "error", "message": f"DOCX read error: {e}"}

        # ── Plain text variants ───────────────────────────────────────────────
        if suffix in (".txt", ".md", ".py", ".js", ".html", ".css",
                      ".json", ".csv", ".xml", ".yaml", ".yml", ".log",
                      ".ini", ".env", ".bat", ".sh", ".ts", ".jsx"):
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                return {"type": "text", "content": content[:15000], "filename": name}
            except Exception as e:
                return {"type": "error", "message": f"Read error: {e}"}

        # ── Fallback: try raw text ────────────────────────────────────────────
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return {"type": "text", "content": content[:15000], "filename": name}
        except Exception as e:
            return {"type": "error",
                    "message": f"Unsupported file type '{suffix}'. Error: {e}"}