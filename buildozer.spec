[app]

title = مراقب التسريب
package.name = watermonitor
package.domain = org.example.watermonitor

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,tflite,txt,wav,webp

version = 0.1.0

# tflite-runtime: وصفة p4a موجودة لكن قد تفشل حسب إصدار NDK — راجع BUILD_ANDROID.txt
requirements = python3,kivy,kivymd,pillow,numpy,plyer,tflite-runtime

orientation = portrait
fullscreen = 0

[buildozer]

log_level = 2
warn_on_root = 1

[android]

android.api = 33
android.minapi = 24
android.ndk = 25b
# يطابق حزمة build-tools في CI (يحتوي aidl)
android.build_tools = 33.0.2
android.accept_sdk_license = True

# تسريع البناء: هاتف حديث arm64 فقط (أضف armeabi-v7a إن احتجت أجهزة قديمة)
android.archs = arm64-v8a

android.permissions = INTERNET,CAMERA,RECORD_AUDIO,VIBRATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS

# أندرويد 10+: مسار ملفات التطبيق
android.allow_backup = True
