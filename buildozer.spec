[buildozer]
log_level = 2
warn_on_root = 1

[app]
title = منظومة طيف الماء الذكية
package.name = watermonitor
package.domain = org.example.watermonitor

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1.0

requirements = python3,kivy==2.2.1,kivymd==1.2.0,numpy,pillow,plyer,pyjnius==1.6.1

log_level = 2
warn_on_root = 1

[android]
android.ndk_api = 24
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

android.permissions = CAMERA,INTERNET,VIBRATE
android.allow_backup = True
