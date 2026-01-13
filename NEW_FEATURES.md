# الميزات الجديدة - New Features

## ✨ ما تم إضافته

### 1. **إصلاح عرض أسماء المواقع** ✅
- تم إصلاح parsing أسماء المواقع من `fm list`
- الآن تظهر الأسماء الحقيقية بدلاً من الأحرف الرسومية
- استخدام fallback متعدد لضمان اكتشاف المواقع

### 2. **عرض Logs** 📋
- **URL**: `/site/{stack}/{site}/logs`
- عرض آخر 100 سطر من logs الخاصة بالموقع
- زر Refresh لتحديث الـ logs
- عرض بخلفية سوداء مع نص أخضر (terminal style)

### 3. **متصفح الملفات** 📁
- **URL**: `/site/{stack}/{site}/files`
- عرض جميع الملفات والمجلدات في الموقع
- إمكانية التصفح بين المجلدات
- عرض حجم الملفات وتاريخ التعديل
- أيقونات مميزة للمجلدات والملفات

### 4. **Console / Shell** 💻
- **URL**: `/site/{stack}/{site}/console`
- عرض الأوامر المطلوبة للوصول للـ console
- زر نسخ سريع للأوامر
- عرض 3 طرق مختلفة للوصول:
  - Frappe Console
  - Python Shell
  - MariaDB Console
- جدول بالأوامر الشائعة

### 5. **أزرار جديدة في صفحة Stack**
تم إضافة 3 أزرار جديدة لكل موقع:
- 🗒️ **Logs** - عرض سجلات الموقع
- 📁 **Files** - تصفح ملفات الموقع
- 💻 **Console** - الوصول للـ console

---

## 🔄 كيفية التحديث على الخادم

### الطريقة 1: نسخ يدوي

```bash
# نسخ الملفات المحدثة
sudo cp /home/manager-pc/Desktop/dash/agent/main.py /opt/dash/agent/
sudo cp /home/manager-pc/Desktop/dash/dashboard/main.py /opt/dash/dashboard/
sudo cp /home/manager-pc/Desktop/dash/dashboard/templates/stack_detail.html /opt/dash/dashboard/templates/
sudo cp /home/manager-pc/Desktop/dash/dashboard/templates/site_logs.html /opt/dash/dashboard/templates/
sudo cp /home/manager-pc/Desktop/dash/dashboard/templates/site_files.html /opt/dash/dashboard/templates/
sudo cp /home/manager-pc/Desktop/dash/dashboard/templates/site_console.html /opt/dash/dashboard/templates/

# إصلاح الصلاحيات
sudo chown -R baron:baron /opt/dash

# إعادة تشغيل الخدمات
cd /opt/dash
# أوقف الخدمات الحالية (Ctrl+C)
# ثم شغّل:
bash start-all.sh
```

### الطريقة 2: عبر Git (بعد رفع التحديثات)

```bash
cd /opt/dash
git pull
bash start-all.sh
```

---

## 📸 ما ستراه الآن

### صفحة Stack Detail
```
Sites (1)
┌─────────────────────────────────────────────┐
│ 🌐 devsite.mby-solution.vip                │
│                                             │
│ [Restart] [Migrate] [Backup Now]           │
│ [View Backups] [Logs] [Files] [Console]    │
└─────────────────────────────────────────────┘
```

### صفحة Logs
- خلفية سوداء مع نص أخضر
- آخر 100 سطر من logs
- زر Refresh

### صفحة Files
- جدول بالملفات والمجلدات
- حجم الملفات
- تاريخ التعديل
- إمكانية التصفح

### صفحة Console
- أوامر جاهزة للنسخ
- 3 طرق مختلفة للوصول
- أوامر شائعة

---

## 🧪 اختبار الميزات

```bash
# 1. تأكد أن الخدمات تعمل
cd /opt/dash
bash start-all.sh

# 2. افتح المتصفح
http://192.168.1.99:8000

# 3. اذهب إلى Stack
# 4. يجب أن ترى اسم الموقع (devsite.mby-solution.vip)
# 5. جرّب الأزرار الجديدة:
#    - Logs
#    - Files
#    - Console
```

---

## 📋 API Endpoints الجديدة

### Agent (Port 9100)
```
GET  /site/{stack}/{site}/logs          # Get logs
GET  /site/{stack}/{site}/files         # List files
GET  /site/{stack}/{site}/console       # Get console command
```

### Dashboard (Port 8000)
```
GET  /site/{stack}/{site}/logs          # Logs page
GET  /site/{stack}/{site}/files         # Files browser
GET  /site/{stack}/{site}/console       # Console page
```

---

## 🔧 ملاحظات تقنية

### list_sites() تحسينات:
1. يبحث أولاً في `/sites/` directory (الأكثر موثوقية)
2. يحاول parsing output `fm list`
3. fallback إلى `workspace/frappe-bench/sites`

### Files Browser:
- يعرض الملفات من: `stack_path/sites/site_name/`
- يدعم التصفح في المجلدات الفرعية
- يعرض معلومات تفصيلية عن كل ملف

### Logs:
- يستخدم `docker logs backend`
- آخر 100 سطر
- يمكن زيادة العدد من الكود

---

## 🚀 رفع التحديثات إلى GitHub

```bash
cd /home/manager-pc/Desktop/dash

git add agent/main.py dashboard/main.py
git add dashboard/templates/stack_detail.html
git add dashboard/templates/site_logs.html
git add dashboard/templates/site_files.html
git add dashboard/templates/site_console.html

git commit -m "feat: Add site logs, files browser, and console access

- Fix site name parsing from fm list output
- Add logs viewer with 100 lines display
- Add file browser for site directories
- Add console access instructions
- Add new buttons to stack detail page
- Create new templates for all features"

git push origin main
```

---

## ✅ التحقق من نجاح التحديث

بعد إعادة تشغيل الخدمات:

1. ✅ أسماء المواقع تظهر بشكل صحيح
2. ✅ زر "Logs" يعمل ويعرض السجلات
3. ✅ زر "Files" يعرض الملفات والمجلدات
4. ✅ زر "Console" يعرض الأوامر
5. ✅ لا توجد أحرف غريبة في URLs

---

**تم بنجاح! 🎉**

