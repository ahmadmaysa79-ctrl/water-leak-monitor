"""
مراقبة تسريب المياه — Splash، صلاحيات، بدء المراقبة، Edge AI، تنبيه، إجراءات.
"""

from __future__ import annotations

import os
import random
import threading
import time
from pathlib import Path
from urllib.parse import quote

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.metrics import dp
from kivy.uix.screenmanager import FadeTransition, ScreenManager
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from database.events_db import init_db, log_event
from inference import run_inference

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
LOGO_PATH = ASSETS / "logo.png"
ALARM_WAV = ASSETS / "alarm.wav"
LIVE_FRAME = ASSETS / "_live_frame.png"

# رقم لرسالة SMS للأهل (اتركه فارغاً لفتح واجهة الرسائل بدون رقم محدد على أندرويد)
FAMILY_SMS_NUMBER = ""

CAMERA_AI_INTERVAL = 2.8
CONFIDENCE_ALERT = 0.55


def request_runtime_permissions() -> None:
    """طلب الكاميرا والميكروفون والتخزين على أندرويد."""
    if platform != "android":
        return
    try:
        from android.permissions import Permission, request_permissions

        request_permissions(
            [
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ]
        )
    except Exception:
        pass


class LeakSensorSimulator(threading.Thread):
    """محاكاة شريحة/حساس تسريب — يعمل فقط عند تفعيل المراقبة."""

    def __init__(self, app: "WaterMonitorApp"):
        super().__init__(daemon=True)
        self.app = app
        self.value = 18.0
        self.enabled = False
        self._stop = threading.Event()
        self.alert_latched = False

    def run(self) -> None:
        while not self._stop.is_set():
            time.sleep(0.45)
            if not self.enabled:
                continue
            self.value += random.uniform(-2.0, 4.2)
            self.value = max(0.0, min(100.0, self.value))
            if self.value >= 78.0 and not self.alert_latched:
                self.alert_latched = True
                Clock.schedule_once(lambda _dt: self.app.on_leak_detected("sensor_chip"), 0)

    def stop_thread(self) -> None:
        self._stop.set()

    def reset_after_alert(self) -> None:
        self.alert_latched = False
        self.value = random.uniform(12.0, 28.0)


class SplashScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(name="splash", **kwargs)
        self.md_bg_color = (0.06, 0.11, 0.17, 1)
        box = MDBoxLayout(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(16),
            size_hint=(1, 1),
        )
        if LOGO_PATH.is_file():
            from kivy.uix.image import Image

            box.add_widget(
                Image(
                    source=str(LOGO_PATH),
                    size_hint=(1, 0.38),
                    allow_stretch=True,
                    keep_ratio=True,
                )
            )
        else:
            box.add_widget(
                MDLabel(
                    text="شعار المشروع\n(ضع ملف assets/logo.png)",
                    halign="center",
                    theme_text_color="Custom",
                    text_color=(0.85, 0.9, 1, 1),
                    font_style="H5",
                )
            )
        box.add_widget(
            MDLabel(
                text="مراقب التسريب والرطوبة",
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                font_style="H4",
            )
        )
        box.add_widget(
            MDLabel(
                text="جاري التحميل…",
                halign="center",
                theme_text_color="Custom",
                text_color=(0.75, 0.85, 0.95, 1),
            )
        )
        self.add_widget(box)

    def on_enter(self, *args):
        Clock.schedule_once(self._go_permissions, 3.0)

    def _go_permissions(self, _dt):
        self.manager.transition = FadeTransition(duration=0.35)
        self.manager.current = "permissions"


class PermissionsScreen(MDScreen):
    """شرح الأذونات ثم طلبها قبل لوحة التحكم."""

    def __init__(self, **kwargs):
        super().__init__(name="permissions", **kwargs)
        self.md_bg_color = (0.96, 0.97, 0.98, 1)
        box = MDBoxLayout(
            orientation="vertical",
            padding=dp(20),
            spacing=dp(14),
            size_hint=(1, 1),
        )
        box.add_widget(
            MDLabel(
                text="الأذونات",
                halign="right",
                font_style="H5",
            )
        )
        box.add_widget(
            MDLabel(
                text=(
                    "يحتاج التطبيق إلى:\n"
                    "• الكاميرا — لمراقبة الجدران لحظياً عبر نموذج الذكاء الاصطناعي على الجهاز.\n"
                    "• الميكروفون — جاهز لاحقاً لاكتشاف أصوات تسريب (Edge AI).\n"
                    "• التخزين — لقراءة الصور عند الحاجة."
                ),
                halign="right",
                theme_text_color="Secondary",
            )
        )
        box.add_widget(
            MDRaisedButton(
                text="السماح والمتابعة",
                pos_hint={"center_x": 0.5},
                on_release=lambda *_: self._continue(),
            )
        )
        self.add_widget(box)

    def _continue(self):
        request_runtime_permissions()
        self.manager.transition = FadeTransition(duration=0.3)
        self.manager.current = "main"


class MainScreen(MDScreen):
    def __init__(self, app: "WaterMonitorApp", **kwargs):
        super().__init__(name="main", **kwargs)
        self.app = app
        self._cam_ev = None
        self._cam = None

        self.md_bg_color = (0.96, 0.97, 0.98, 1)
        root = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
            size_hint=(1, 1),
        )

        root.add_widget(
            MDLabel(text="لوحة التحكم", halign="right", font_style="H5")
        )

        self.status_label = MDLabel(
            text="المُراقبة متوقفة — اضغط «بدء المراقبة»",
            halign="right",
            theme_text_color="Primary",
            font_style="H6",
        )
        root.add_widget(self.status_label)

        self.detail_label = MDLabel(
            text="",
            halign="right",
            theme_text_color="Secondary",
        )
        root.add_widget(self.detail_label)

        self.monitor_btn = MDRaisedButton(
            text="بدء المراقبة",
            size_hint_y=None,
            height=dp(52),
            md_bg_color=(0.12, 0.45, 0.35, 1),
            on_release=lambda *_: self._toggle_monitoring(),
        )
        root.add_widget(self.monitor_btn)

        preview = MDBoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint=(1, 0.42),
        )
        preview.add_widget(
            MDLabel(text="معاينة الكاميرا (Edge AI)", halign="right", font_style="Caption")
        )
        cam_box = MDBoxLayout(size_hint=(1, 1))
        try:
            from kivy.uix.camera import Camera

            self._cam = Camera(
                play=False,
                resolution=(640, 480),
                size_hint=(1, 1),
            )
            cam_box.add_widget(self._cam)
        except Exception:
            cam_box.add_widget(
                MDLabel(
                    text="الكاميرا غير متاحة على هذا الجهاز (طبيعي على محاكٍ بعض الأحيان).",
                    halign="center",
                )
            )
        preview.add_widget(cam_box)
        root.add_widget(preview)

        extra = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(48),
        )
        extra.add_widget(
            MDRaisedButton(
                text="تحليل صورة يدوي",
                md_bg_color=(0.35, 0.4, 0.55, 1),
                on_release=lambda *_: setattr(self.manager, "current", "analysis"),
            )
        )
        root.add_widget(extra)

        self.add_widget(root)
        Clock.schedule_interval(self._refresh_ui, 0.25)

    def _toggle_monitoring(self):
        if self.app.monitoring_active:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        self.app.monitoring_active = True
        if self.app.sensor:
            self.app.sensor.enabled = True
        self.monitor_btn.text = "إيقاف المراقبة"
        self.monitor_btn.md_bg_color = (0.65, 0.2, 0.15, 1)
        if self._cam:
            self._cam.play = True
        if self._cam_ev:
            self._cam_ev.cancel()
        self._cam_ev = Clock.schedule_interval(self._camera_ai_tick, CAMERA_AI_INTERVAL)

    def _stop_monitoring(self):
        self.app.monitoring_active = False
        if self.app.sensor:
            self.app.sensor.enabled = False
        self.monitor_btn.text = "بدء المراقبة"
        self.monitor_btn.md_bg_color = (0.12, 0.45, 0.35, 1)
        if self._cam:
            self._cam.play = False
        if self._cam_ev:
            self._cam_ev.cancel()
            self._cam_ev = None

    def _camera_ai_tick(self, _dt):
        if not self.app.monitoring_active or not self._cam:
            return
        try:
            self._cam.export_to_png(str(LIVE_FRAME))
        except Exception:
            return
        res = run_inference(str(LIVE_FRAME))
        if not res.get("ok"):
            return
        if (
            res.get("high_humidity")
            and float(res.get("confidence") or 0) >= CONFIDENCE_ALERT
        ):
            log_event("camera_edge", f"{res.get('label')} conf={res.get('confidence')}")
            Clock.schedule_once(
                lambda _dt: self.app.on_leak_detected("camera_ai"),
                0,
            )

    def _refresh_ui(self, _dt):
        if not self.app.monitoring_active:
            self.status_label.text = "المُراقبة متوقفة — اضغط «بدء المراقبة»"
            self.detail_label.text = ""
            return
        self.status_label.text = "الحالة: آمن"
        if self.app.sensor:
            v = self.app.sensor.value
            self.detail_label.text = (
                f"الحساس (محاكاة): {v:.1f}% — الميكروفون: جاهز للتوسع لاحقاً"
            )


class AlertScreen(MDScreen):
    def __init__(self, app: "WaterMonitorApp", **kwargs):
        super().__init__(name="alert", **kwargs)
        self.app = app
        self._anim: Animation | None = None
        self._alarm_sound = None
        self._vib_ev = None

        self.box = MDBoxLayout(
            orientation="vertical",
            padding=dp(22),
            spacing=dp(16),
            md_bg_color=(0.75, 0.0, 0.0, 1),
            size_hint=(1, 1),
        )

        self.box.add_widget(
            MDLabel(
                text="تحذير: تم كشف تسريب!",
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                font_style="H4",
            )
        )
        self.box.add_widget(
            MDLabel(
                text="تنبيه مرئي وصوتي وحركي — أوقف الإنذار يدوياً.",
                halign="center",
                theme_text_color="Custom",
                text_color=(1, 0.92, 0.92, 1),
            )
        )

        self.box.add_widget(
            MDRaisedButton(
                text="إيقاف الإنذار",
                md_bg_color=(0.25, 0.05, 0.05, 1),
                size_hint_y=None,
                height=dp(48),
                on_release=lambda *_: self._dismiss(),
            )
        )

        row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(48),
        )
        row.add_widget(
            MDRaisedButton(
                text="اتصال بالطوارئ",
                md_bg_color=(0.2, 0.2, 0.22, 1),
                on_release=lambda *_: self.app.open_emergency_dialer(),
            )
        )
        row.add_widget(
            MDRaisedButton(
                text="إرسال رسالة للأهل",
                md_bg_color=(0.15, 0.35, 0.55, 1),
                on_release=lambda *_: self.app.open_sms_to_family(),
            )
        )
        self.box.add_widget(row)
        self.add_widget(self.box)

    def on_enter(self, *args):
        self._start_blink()
        self._play_alarm()
        self._vibrate_once()
        self._vib_ev = Clock.schedule_interval(self._vibrate_pulse, 2.0)

    def on_pre_leave(self, *args):
        self._stop_blink()
        self._stop_alarm()
        if self._vib_ev:
            self._vib_ev.cancel()
            self._vib_ev = None

    def _start_blink(self):
        self._stop_blink()
        anim = (
            Animation(md_bg_color=(1.0, 0.05, 0.05, 1), d=0.35)
            + Animation(md_bg_color=(0.45, 0.0, 0.0, 1), d=0.35)
        )
        anim.repeat = True
        anim.start(self.box)
        self._anim = anim

    def _stop_blink(self):
        if self._anim:
            self._anim.cancel(self.box)
            self._anim = None
        self.box.md_bg_color = (0.75, 0.0, 0.0, 1)

    def _play_alarm(self):
        if ALARM_WAV.is_file():
            s = SoundLoader.load(str(ALARM_WAV))
            if s:
                s.loop = True
                s.play()
                self._alarm_sound = s

    def _stop_alarm(self):
        if self._alarm_sound:
            self._alarm_sound.stop()
            self._alarm_sound = None

    def _vibrate_once(self):
        try:
            from plyer import vibrator

            vibrator.vibrate(1.2)
        except Exception:
            pass

    def _vibrate_pulse(self, _dt):
        try:
            from plyer import vibrator

            vibrator.vibrate(0.55)
        except Exception:
            pass

    def _dismiss(self):
        if self.app.sensor:
            self.app.sensor.reset_after_alert()
        self.manager.transition = FadeTransition(duration=0.3)
        self.manager.current = "main"


class ImageAnalysisScreen(MDScreen):
    def __init__(self, app: "WaterMonitorApp", **kwargs):
        super().__init__(name="analysis", **kwargs)
        self.app = app
        self.file_manager: MDFileManager | None = None

        self.md_bg_color = (0.96, 0.97, 0.98, 1)
        box = MDBoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
            size_hint=(1, 1),
        )
        box.add_widget(MDLabel(text="تحليل صورة (يدوي)", halign="right", font_style="H5"))
        self.result_label = MDLabel(
            text="اختر صورة من المعرض أو الملفات.",
            halign="right",
            theme_text_color="Secondary",
        )
        box.add_widget(self.result_label)

        btn_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            adaptive_height=True,
        )
        btn_row.add_widget(
            MDRaisedButton(
                text="اختيار صورة",
                on_release=lambda *_: self._open_picker(),
            )
        )
        btn_row.add_widget(
            MDRaisedButton(
                text="رجوع",
                md_bg_color=(0.5, 0.5, 0.55, 1),
                on_release=lambda *_: setattr(self.manager, "current", "main"),
            )
        )
        box.add_widget(btn_row)
        self.add_widget(box)

    def _open_picker(self):
        start_path = os.path.expanduser("~")
        if os.path.isdir("/sdcard"):
            start_path = "/sdcard"
        self.file_manager = MDFileManager(
            exit_manager=self._exit_manager,
            select_path=self._select_path,
        )
        self.file_manager.show(start_path)

    def _exit_manager(self, *_args):
        if self.file_manager:
            self.file_manager.close()

    def _select_path(self, path: str):
        self._exit_manager()
        if not path:
            return
        low = path.lower()
        if not any(low.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
            self.result_label.text = "يرجى اختيار ملف صورة."
            return
        self._run(path)

    def _run(self, image_path: str):
        res = run_inference(image_path)
        self.result_label.text = res.get("message", "")
        summary = f"{res.get('label', '')} | conf={res.get('confidence', 0):.3f}"
        log_event("image_analysis", summary)
        dlg = MDDialog(text=res.get("message", ""))
        ok = MDFlatButton(text="حسناً")
        ok.bind(on_release=lambda *_: dlg.dismiss())
        dlg.buttons = [ok]
        dlg.open()


class WaterMonitorApp(MDApp):
    sensor: LeakSensorSimulator | None = None
    monitoring_active: bool = False

    def build(self):
        self.title = "مراقب التسريب"
        self.family_phone = FAMILY_SMS_NUMBER
        init_db()

        sm = ScreenManager(transition=FadeTransition(duration=0.35))
        sm.add_widget(SplashScreen())
        sm.add_widget(PermissionsScreen())
        sm.add_widget(MainScreen(self))
        sm.add_widget(AlertScreen(self))
        sm.add_widget(ImageAnalysisScreen(self))

        self.sensor = LeakSensorSimulator(self)
        self.sensor.start()
        return sm

    def on_stop(self):
        if self.sensor:
            self.sensor.stop_thread()

    def on_leak_detected(self, source: str = "sensor"):
        if self.root.current == "alert":
            return
        log_event("leak_alert", f"src={source} sensor={getattr(self.sensor, 'value', 0):.1f}")
        try:
            from plyer import notification

            notification.notify(
                title="تحذير: تم كشف تسريب!",
                message="راجع التطبيق فوراً.",
                app_name="مراقب التسريب",
                timeout=8,
            )
        except Exception:
            pass

        self.root.current = "alert"

    def open_emergency_dialer(self, number: str = "112"):
        try:
            from jnius import autoclass

            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent(Intent.ACTION_DIAL)
            intent.setData(Uri.parse(f"tel:{number}"))
            PythonActivity.mActivity.startActivity(intent)
            return
        except Exception:
            pass
        try:
            import webbrowser

            webbrowser.open(f"tel:{number}")
        except Exception:
            pass

    def open_sms_to_family(self):
        body = "تحذير: تم رصد تسريب محتمل عبر تطبيق المراقبة. يرجى التحقق من المنزل."
        phone = (self.family_phone or "").strip()
        if platform == "android":
            try:
                from jnius import autoclass

                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                intent = Intent(Intent.ACTION_SENDTO)
                target = f"smsto:{phone}" if phone else "smsto:"
                intent.setData(Uri.parse(target))
                intent.putExtra("sms_body", body)
                PythonActivity.mActivity.startActivity(intent)
                return
            except Exception:
                pass
        try:
            import webbrowser

            q = quote(body)
            if phone:
                webbrowser.open(f"sms:{phone}?body={q}")
            else:
                webbrowser.open(f"sms:&body={q}")
        except Exception:
            pass


def main():
    WaterMonitorApp().run()


if __name__ == "__main__":
    main()
