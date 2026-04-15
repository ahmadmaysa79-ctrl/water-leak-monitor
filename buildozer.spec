[app]

title = منظومة طيف الماء الذكية
package.name = watermonitor
package.domain = org.example.watermonitor

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,tflite,txt,wav,webp

version = 0.1.0

requirements = python3,kivy==2.3.0,pillow,numpy,plyer,cython==0.29.33

orientation = portrait
fullscreen = 0

[buildozer]

log_level = 2
warn_on_root = 1

[android]

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

android.permissions = INTERNET,CAMERA,RECORD_AUDIO,VIBRATE,POST_NOTIFICATIONS

android.allow_backup = True
