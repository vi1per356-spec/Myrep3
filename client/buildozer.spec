[app]
title = Ukraine Threat Tracker
package.name = uatracker
package.domain = org.utt
source.dir = .
source.include_exts = py,png,jpg,svg,json,kv
version = 1.0
requirements = python3,kivy==2.3.0,kivy_garden.mapview,requests,websocket-client,plyer,certifi,urllib3,chardet,idna
orientation = portrait
fullscreen = 0

# Internet + read storage for the training-image upload picker.
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = 1

[buildozer]
log_level = 2
warn_on_root = 0
