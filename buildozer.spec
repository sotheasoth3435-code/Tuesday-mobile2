[app]
title           = TUESDAY
package.name    = tuesday
package.domain  = com.albe

source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,json,env

version         = 1.0.0

requirements    = python3,kivy==2.3.0,kivymd,openai,python-dotenv,requests,pillow,jnius,android

# Orientation
orientation     = portrait

# Android permissions
android.permissions = INTERNET,RECORD_AUDIO,READ_CONTACTS,SEND_SMS,\
                      READ_CALENDAR,WRITE_CALENDAR,RECEIVE_SMS,\
                      CHANGE_WIFI_STATE,ACCESS_WIFI_STATE,\
                      MODIFY_AUDIO_SETTINGS,READ_CLIPBOARD,\
                      VIBRATE,RECEIVE_BOOT_COMPLETED

android.api             = 35
android.minapi          = 31
android.ndk             = 25b
android.sdk             = 34
android.ndk_api         = 21

android.archs           = arm64-v8a

# Enable AndroidX
android.enable_androidx = True
android.gradle_dependencies = com.google.android.material:material:1.11.0

# App icon (place a tuesday_icon.png in your project root)
# icon.filename = %(source.dir)s/tuesday_icon.png

[buildozer]
log_level = 2
warn_on_root = 1
