رابط النموذج على Teachable Machine (للمرجع):
https://teachablemachine.withgoogle.com/models/neW9W26ME/

خطوات الربط بالتطبيق:
1) افتح الرابط من متصفح Chrome أو Safari على الكمبيوتر (ليس من معاينة داخل التطبيقات).
2) من مشروع الصور (Image Project): القائمة أو زر التصدير → Download model → اختر TensorFlow Lite.
3) انسخ ملف الـ .tflite من المجلد المضغوط إلى هذا المجلد وسمّه:
   humidity_model.tflite
4) صدّر التسميات (labels) بنفس ترتيب الفئات في Teachable Machine — غالباً ملف labels.txt أو داخل metadata.json.
   انسخ أسماء الفئات سطراً بسطر إلى labels.txt هنا بنفس الترتيب تماماً (الترتيب يحدد تفسير مخرجات النموذج).

ملاحظة: إن كان التصدير يعطي نموذجاً مكمّماً (quantized) فقط، استخدمه كما هو؛ كود inference.py يحاول دعم float و uint8 حسب تفاصيل المدخلات.

بدون humidity_model.tflite و labels.txt المتطابقة، لن يعمل تحليل الصور بشكل صحيح.
