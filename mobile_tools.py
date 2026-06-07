"""
tools/mobile_tools.py — TUESDAY Mobile
=======================================
Android-native tools registered alongside the desktop tool registry.
Each function is a plain callable — the orchestrator picks them up
via get_mobile_tools() which mirrors get_gemini_tools().
"""
import os
import re

# ── Android imports (graceful fallback on desktop) ────────────────────────────
try:
    from jnius import autoclass
    from android.permissions import request_permissions, Permission
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    ANDROID = True
except ImportError:
    ANDROID = False


# ── 1. Send SMS ───────────────────────────────────────────────────────────────
def send_sms(phone_number: str, message: str) -> str:
    """Send an SMS message to a phone number."""
    if not ANDROID:
        return f"[Desktop stub] Would send SMS to {phone_number}: {message}"
    try:
        SmsManager = autoclass("android.telephony.SmsManager")
        manager    = SmsManager.getDefault()
        manager.sendTextMessage(phone_number, None, message, None, None)
        return f"SMS sent to {phone_number}."
    except Exception as e:
        return f"SMS failed: {e}"


# ── 2. Open phone app ─────────────────────────────────────────────────────────
def open_phone_app(app_name: str) -> str:
    """Open an installed app on the Android phone by name."""
    if not ANDROID:
        return f"[Desktop stub] Would open {app_name}"
    APP_PACKAGES = {
        "whatsapp":   "com.whatsapp",
        "youtube":    "com.google.android.youtube",
        "chrome":     "com.android.chrome",
        "gmail":      "com.google.android.gm",
        "maps":       "com.google.android.apps.maps",
        "camera":     "com.android.camera2",
        "settings":   "com.android.settings",
        "spotify":    "com.spotify.music",
        "telegram":   "org.telegram.messenger",
        "instagram":  "com.instagram.android",
        "facebook":   "com.facebook.katana",
        "twitter":    "com.twitter.android",
        "calculator": "com.android.calculator2",
        "clock":      "com.android.deskclock",
        "files":      "com.android.documentsui",
    }
    key = app_name.lower().strip()
    package = APP_PACKAGES.get(key, None)

    # Fuzzy match if exact not found
    if not package:
        for k, v in APP_PACKAGES.items():
            if k in key or key in k:
                package = v
                break

    if not package:
        return f"Don't know the package for '{app_name}'. Try being more specific."

    try:
        context = PythonActivity.mActivity
        Intent  = autoclass("android.content.Intent")
        pm      = context.getPackageManager()
        intent  = pm.getLaunchIntentForPackage(package)
        if intent:
            context.startActivity(intent)
            return f"Opened {app_name}."
        return f"{app_name} is not installed."
    except Exception as e:
        return f"Failed to open {app_name}: {e}"


# ── 3. Set volume ─────────────────────────────────────────────────────────────
def set_volume(level: int) -> str:
    """Set the media volume on the phone. Level is 0–15."""
    if not ANDROID:
        return f"[Desktop stub] Would set volume to {level}"
    try:
        context      = PythonActivity.mActivity
        AudioManager = autoclass("android.media.AudioManager")
        audio_mgr    = context.getSystemService("audio")
        level        = max(0, min(15, int(level)))
        audio_mgr.setStreamVolume(
            AudioManager.STREAM_MUSIC, level,
            AudioManager.FLAG_SHOW_UI
        )
        return f"Volume set to {level}."
    except Exception as e:
        return f"Volume change failed: {e}"


# ── 4. Toggle Wi-Fi ───────────────────────────────────────────────────────────
def set_wifi(enabled: bool) -> str:
    """Enable or disable Wi-Fi on the phone."""
    if not ANDROID:
        return f"[Desktop stub] Would set wifi={'on' if enabled else 'off'}"
    try:
        context     = PythonActivity.mActivity
        WifiManager = autoclass("android.net.wifi.WifiManager")
        wifi_mgr    = context.getSystemService("wifi")
        wifi_mgr.setWifiEnabled(bool(enabled))
        return f"Wi-Fi {'enabled' if enabled else 'disabled'}."
    except Exception as e:
        return f"Wi-Fi toggle failed: {e}"


# ── 5. Read clipboard / summarise text ────────────────────────────────────────
def get_clipboard_text() -> str:
    """Read the current clipboard text from the phone."""
    if not ANDROID:
        try:
            import pyperclip
            return pyperclip.paste() or "(clipboard empty)"
        except Exception:
            return "[Desktop stub] Clipboard text"
    try:
        context   = PythonActivity.mActivity
        ClipMgr   = autoclass("android.content.ClipboardManager")
        clip_mgr  = context.getSystemService("clipboard")
        clip_data = clip_mgr.getPrimaryClip()
        if clip_data and clip_data.getItemCount() > 0:
            return str(clip_data.getItemAt(0).coerceToText(context))
        return "(clipboard empty)"
    except Exception as e:
        return f"Clipboard read failed: {e}"


# ── 6. Get battery level ──────────────────────────────────────────────────────
def get_battery_level() -> str:
    """Check the current battery percentage of the phone."""
    if not ANDROID:
        return "[Desktop stub] Battery: 85%"
    try:
        context          = PythonActivity.mActivity
        IntentFilter     = autoclass("android.content.IntentFilter")
        BatteryManager   = autoclass("android.os.BatteryManager")
        ifilter          = IntentFilter(
            autoclass("android.content.Intent").ACTION_BATTERY_CHANGED
        )
        intent = context.registerReceiver(None, ifilter)
        level  = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        scale  = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        pct    = int(level * 100 / scale) if scale > 0 else -1
        return f"Battery is at {pct}%."
    except Exception as e:
        return f"Battery check failed: {e}"


# ── 7. Send WhatsApp message ──────────────────────────────────────────────────
def send_whatsapp(phone_number: str, message: str) -> str:
    """Send a WhatsApp message to a contact (opens WhatsApp with pre-filled message)."""
    if not ANDROID:
        return f"[Desktop stub] Would WhatsApp {phone_number}: {message}"
    try:
        import urllib.parse
        context = PythonActivity.mActivity
        Intent  = autoclass("android.content.Intent")
        Uri     = autoclass("android.net.Uri")
        encoded = urllib.parse.quote(message)
        # Strip + and spaces from number
        number  = re.sub(r"[^\d]", "", phone_number)
        uri     = Uri.parse(f"https://api.whatsapp.com/send?phone={number}&text={encoded}")
        intent  = Intent(Intent.ACTION_VIEW, uri)
        context.startActivity(intent)
        return f"Opened WhatsApp chat with {phone_number}."
    except Exception as e:
        return f"WhatsApp failed: {e}"


# ── 8. Get current time & date ────────────────────────────────────────────────
def get_datetime() -> str:
    """Get the current date and time on the phone."""
    from datetime import datetime
    return datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")


# ── Registry ──────────────────────────────────────────────────────────────────
MOBILE_TOOLS = [
    send_sms,
    open_phone_app,
    set_volume,
    set_wifi,
    get_clipboard_text,
    get_battery_level,
    send_whatsapp,
    get_datetime,
]


def get_mobile_tools() -> list:
    """Return all mobile tool callables for registration in the orchestrator."""
    return MOBILE_TOOLS
