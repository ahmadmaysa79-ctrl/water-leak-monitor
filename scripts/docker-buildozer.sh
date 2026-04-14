#!/usr/bin/env bash
# محاولة بناء APK داخل حاوية (يتطلب Docker مثبتاً).
# الصورة قد تحتاج تحديثاً حسب توثيق Kivy الحالي.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Using project root: $ROOT"
echo "If this image fails, use Ubuntu 22.04 + pip install buildozer (see BUILD_ANDROID.txt)"

docker run --rm \
  -e BUILDOZER_WARN_ON_ROOT=0 \
  -v "$ROOT:/home/user/hostcwd" \
  -w /home/user/hostcwd \
  kivy/buildozer:latest \
  buildozer android debug
