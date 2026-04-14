مشروع كشف مكوّنات/جودة المياه (شرائح + كاميرا) — ليس اعتماداً على Teachable Machine كتطبيق ويب؛ التصدير للهاتف يكون TensorFlow Lite فقط.

1) من Teachable Machine (مشروع صور): القائمة → Download model → TensorFlow Lite (وليس TensorFlow.js فقط).
   إن كان عندك حالياً model.json + model.weights.bin فهذا تنسيق الويب؛ حوّله عبر إعادة التصدير كـ TFLite من نفس المشروع أو استخدم سكربت تحويل (TensorFlow) من نفس الأوزان.

2) انسخ ملف .tflite إلى هذا المجلد وسمّه أحد الاسمين:
   - water_quality_model.tflite (مفضّل)
   - humidity_model.tflite (اسم قديم للتوافق)

3) labels.txt يجب أن يطابق ترتيب الفئات في metadata.json / Teachable Machine حرفياً (سطر لكل فئة).
   أي خطأ في الترتيب يفسّر النتائج بشكل خاطئ.

4) حجم الإدخال في النموذج الحالي 224×224؛ الكود يقرأ الأبعاد من ملف TFLite تلقائياً.

بدون ملف .tflite و labels.txt المتطابقين، لن يعمل التحليل في التطبيق.
