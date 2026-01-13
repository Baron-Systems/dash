# ميزة عارض السجلات - Logs Viewer Feature

## ✨ الميزة الجديدة

تم إضافة **صفحة Logs Viewer** في القائمة الرئيسية لعرض سجلات المواقع في الوقت الفعلي!

## 🎯 المميزات:

### 1. **موقع في القائمة الرئيسية** 📍
```
Dashboard | Logs | Scheduler
```

الآن يمكن الوصول للـ Logs من أي مكان في التطبيق!

### 2. **اختيار ديناميكي** 🎛️
- ✅ اختيار Stack من قائمة منسدلة
- ✅ اختيار Site من القائمة (يتم تحديثها تلقائياً)
- ✅ اختيار عدد الأسطر (50, 100, 200, 500, 1000)

### 3. **عرض متقدم** 📋
- ✅ خلفية سوداء مع نص أخضر (terminal style)
- ✅ تمرير تلقائي للأسفل
- ✅ عرض الوقت الحالي
- ✅ إحصائيات (Stack, Site, Lines)

### 4. **Auto Refresh** 🔄
- ✅ زر لتفعيل/إيقاف التحديث التلقائي
- ✅ يحدث كل 5 ثوانٍ
- ✅ مؤشر واضح (ON/OFF)

### 5. **تحميل Logs** 💾
- ✅ زر Download لحفظ Logs كملف نصي
- ✅ اسم الملف يحتوي على: Stack, Site, وقت التحميل
- ✅ إشعار نجاح بعد التحميل

---

## 📁 الملفات المضافة/المعدّلة:

### 1. **`dashboard/templates/base.html`** (معدّل)
أضيف لينك Logs في الـ Navigation:

```html
<a href="/logs-viewer" class="...">
    <i class="fas fa-file-alt mr-2"></i> Logs
</a>
```

### 2. **`dashboard/templates/logs_viewer.html`** (جديد)
Template كامل للـ Logs Viewer مع:
- نماذج اختيار Stack/Site/Lines
- عرض Logs
- Auto Refresh
- Download functionality

### 3. **`dashboard/main.py`** (معدّل)
أضيف Route جديد:

```python
@app.get("/logs-viewer")
async def logs_viewer_page(
    stack: str = None,
    site: str = None,
    lines: int = 100,
    ...
):
    # Get stacks
    # Get sites for selected stack
    # Get logs if both selected
    ...
```

---

## 🎨 واجهة المستخدم:

### الشاشة الرئيسية:
```
┌─────────────────────────────────────────────┐
│ 🗂️ Select Site                             │
├─────────────────────────────────────────────┤
│ Stack: [frappe ▼]                          │
│ Site:  [devsite.mby-solution.vip ▼]       │
│ Lines: [100 ▼]                              │
│                                             │
│ [🔄 Refresh Logs] [▶️ Auto Refresh (OFF)]  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 💻 Container Logs         Last: 14:30:25   │
│                                 [⬇️ Download]│
├─────────────────────────────────────────────┤
│ [Black Background]                          │
│ 2026-01-13 14:30:20 INFO Starting server... │
│ 2026-01-13 14:30:21 INFO Database connected │
│ 2026-01-13 14:30:22 INFO Ready!            │
│ ...                                         │
│                                             │
│ Showing last 100 lines                      │
│ Stack: frappe | Site: devsite.mby-solution │
└─────────────────────────────────────────────┘
```

---

## 🔄 كيف يعمل:

### 1. **اختيار Stack**
```javascript
User selects Stack → Form submits → 
  Dashboard calls /stacks/{stack} → 
    Sites list updates
```

### 2. **اختيار Site**
```javascript
User selects Site → Form submits →
  Dashboard calls /site/{stack}/{site}/logs →
    Logs display
```

### 3. **Auto Refresh**
```javascript
User clicks "Auto Refresh" →
  Interval set (5 seconds) →
    Page reloads automatically →
      Fresh logs displayed
```

### 4. **Download Logs**
```javascript
User clicks "Download" →
  Logs extracted from page →
    Blob created →
      File downloaded
```

---

## 🚀 التطبيق:

### نسخ الملفات المحدثة:

```bash
# من جهازك المحلي
scp /home/manager-pc/Desktop/dash/dashboard/main.py \
    baron@192.168.1.99:/opt/dash/dashboard/

scp /home/manager-pc/Desktop/dash/dashboard/templates/base.html \
    baron@192.168.1.99:/opt/dash/dashboard/templates/

scp /home/manager-pc/Desktop/dash/dashboard/templates/logs_viewer.html \
    baron@192.168.1.99:/opt/dash/dashboard/templates/
```

### على السيرفر:

```bash
# إصلاح الصلاحيات
sudo chown -R baron:baron /opt/dash

# إعادة تشغيل Dashboard
cd /opt/dash
# اضغط Ctrl+C ثم:
bash start-all.sh
```

---

## 🧪 الاختبار:

### Test 1: الوصول للصفحة
```
1. افتح Dashboard
2. اضغط على "Logs" في القائمة العلوية
3. Expected: ✅ صفحة Logs Viewer تفتح
```

### Test 2: اختيار Site
```
1. اختر Stack: frappe
2. اختر Site: devsite.mby-solution.vip
3. Expected: ✅ Logs تظهر فوراً
```

### Test 3: تغيير عدد الأسطر
```
1. غيّر Lines من 100 إلى 500
2. Expected: ✅ تحديث تلقائي وعرض 500 سطر
```

### Test 4: Auto Refresh
```
1. اضغط "Auto Refresh (OFF)"
2. انتظر 5 ثوانٍ
3. Expected: ✅ الصفحة تتحدث تلقائياً
4. اضغط "Auto Refresh (ON)" لإيقافها
5. Expected: ✅ التحديث يتوقف
```

### Test 5: Download
```
1. اضغط زر "Download"
2. Expected: ✅ ملف نصي يُحمّل
3. تحقق من اسم الملف:
   logs-frappe-devsite.mby-solution.vip-2026-01-13_14-30-25.txt
```

---

## 💡 حالات الاستخدام:

### 1. **مراقبة الأخطاء في الوقت الفعلي**
```
- فعّل Auto Refresh
- راقب Logs أثناء اختبار ميزة جديدة
- الأخطاء تظهر فوراً
```

### 2. **تصدير Logs للفريق**
```
- اختر الموقع
- غيّر Lines إلى 1000
- اضغط Download
- أرسل الملف للفريق
```

### 3. **مقارنة سلوك المواقع**
```
- افتح Tab 1: Site A logs
- افتح Tab 2: Site B logs
- قارن السلوك
```

### 4. **تتبع Deployment**
```
- أثناء deployment
- راقب Logs بـ Auto Refresh
- تأكد من نجاح التحديث
```

---

## 🎯 الفوائد:

| الميزة | الفائدة |
|--------|---------|
| **Centralized** | جميع logs في مكان واحد |
| **Real-time** | مراقبة مباشرة مع Auto Refresh |
| **Flexible** | اختيار عدد الأسطر حسب الحاجة |
| **Exportable** | تحميل وحفظ للرجوع إليها |
| **User-friendly** | واجهة سهلة وواضحة |
| **Fast** | لا حاجة للـ SSH |

---

## 🔮 تحسينات مستقبلية محتملة:

### 1. **Live Streaming**
```javascript
// WebSocket للـ logs الحية
ws://dashboard/logs/stream
```

### 2. **Search in Logs**
```html
<input type="text" placeholder="Search logs...">
```

### 3. **Filter by Level**
```html
☑️ INFO  ☑️ WARNING  ☑️ ERROR  ☐ DEBUG
```

### 4. **Multiple Sites**
```html
<!-- عرض logs من عدة مواقع في نفس الوقت -->
<div class="grid grid-cols-2">
  <div>Site A Logs</div>
  <div>Site B Logs</div>
</div>
```

### 5. **Color Coding**
```css
/* تلوين حسب نوع الرسالة */
.error { color: red; }
.warning { color: yellow; }
.info { color: green; }
```

---

## 📊 الملخص:

| العنصر | القيمة |
|--------|--------|
| **Files Added** | 1 (logs_viewer.html) |
| **Files Modified** | 2 (main.py, base.html) |
| **New Routes** | 1 (/logs-viewer) |
| **Features** | 5 (Select, View, Refresh, Auto, Download) |
| **UX Impact** | 🌟🌟🌟🌟🌟 |

---

## ✅ Checklist:

بعد التطبيق تأكد من:

- [ ] لينك "Logs" يظهر في القائمة العلوية
- [ ] صفحة Logs تفتح بدون أخطاء
- [ ] قوائم Stack و Site تعمل
- [ ] Logs تظهر عند الاختيار
- [ ] زر Refresh يحدث الـ logs
- [ ] Auto Refresh يعمل (كل 5 ثوانٍ)
- [ ] زر Download يحمّل ملف نصي
- [ ] التصميم متناسق مع باقي Dashboard

---

**تم بنجاح! 🎉**

الآن لديك صفحة Logs احترافية في القائمة الرئيسية مع جميع الميزات المتقدمة!

