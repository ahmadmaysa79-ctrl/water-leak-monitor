# water-leak-monitor

**منظومة طيف الماء الذكية** — تطبيق KivyMD للأمن المائي: كاميرا + نموذج TensorFlow Lite (شرائح/تحليل صور)، تنبيهات، وسجل أحداث.

## ما هو جاهز في الكود

- واجهات: ترحيب، أذونات، مراقبة بالكاميرا، تحليل صورة يدوي، شاشة إنذار.
- `inference.py` يحمّل TFLite من مجلد `model/` ويقرأ `labels.txt` بنفس ترتيب التدريب.
- `buildozer.spec` مضبوط لبناء **APK** (أندرويد 7+ تقريباً، `minapi` 24، `arm64-v8a`).
- بناء تلقائي على GitHub: `.github/workflows/android-apk.yml` (تشغيل يدوي من تبويب Actions).

## ما تحتاجه لإكمال عمل زميلتك وتحويله لتطبيق أندرويد

### 1) نموذج Teachable Machine (خطوة حاسمة)

- من مشروع **الصور** في Teachable Machine: **Export → Download model → TensorFlow Lite** (ليس TensorFlow.js فقط).
- ضع الملف في المستودع تحت `model/` باسم **`water_quality_model.tflite`** أو **`humidity_model.tflite`**.
- تأكد أن **`model/labels.txt`** يطابق **ترتيب** الفئات في التصدير حرفياً (سطر لكل فئة).

بدون `.tflite` و`labels.txt` المتطابقين، يعمل التطبيق لكن **تحليل الصور** لن يعطي نتائج صحيحة.

### 2) أصول اختيارية

- `assets/logo.png` — شعار شاشة الترحيب (بدونها يظهر نص بديل).
- `assets/alarm.wav` — صوت الإنذار (راجع `assets/README.txt`).

### 3) بناء APK

| الطريقة | الملاحظات |
|--------|-----------|
| **GitHub Actions** | ادفع التغييرات → **Actions** → **Build Android APK** → **Run workflow** → بعد النجاح نزّل الـ APK من **Artifacts**. |
| **جهازك** | Buildozer مُختبر جيداً على **Linux** (أوبنتو أو VM). على macOS/Windows غالباً تحتاج حاوية أو CI. |

تفاصيل إضافية واستكشاف أخطاء البناء: **`BUILD_ANDROID.txt`**.

### 4) تثبيت على الهاتف

- فعّل «مصادر غير معروفة» أو ثبّت عبر `adb install -r bin/*.apk`.

---

Edge AI + تنبيهات؛ رقم SMS للأهل يُضبط من `FAMILY_SMS_NUMBER` في `main.py`.
