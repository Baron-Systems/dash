# 🚀 Quick Start Guide

## بعد التثبيت - تشغيل الخدمات

### الطريقة 1: تشغيل جميع الخدمات معاً (موصى به)

```bash
cd /opt/dash
bash start-all.sh
```

هذا سيشغل:
- ✅ Agent Service (port 9100)
- ✅ Dashboard Service (port 8000)

**ملاحظة:** اضغط `Ctrl+C` لإيقاف الخدمات

---

### الطريقة 2: تشغيل كل خدمة في terminal منفصل

**Terminal 1 - Agent:**
```bash
cd /opt/dash
bash start-agent.sh
```

**Terminal 2 - Dashboard:**
```bash
cd /opt/dash
bash start-dashboard.sh
```

---

### الطريقة 3: تشغيل يدوي (للتطوير)

**Terminal 1:**
```bash
cd /opt/dash
source venv/bin/activate
python agent/main.py
```

**Terminal 2:**
```bash
cd /opt/dash
source venv/bin/activate
python dashboard/main.py
```

---

## ✅ التحقق من أن الخدمات تعمل

### 1. تحقق من الـ Ports

```bash
# يجب أن ترى:
# - 127.0.0.1:9100 (Agent)
# - 0.0.0.0:8000 (Dashboard)
sudo netstat -tulpn | grep -E ":(8000|9100)"
```

### 2. تحقق من الـ Processes

```bash
# يجب أن ترى عمليتين python
ps aux | grep "python.*main.py"
```

### 3. اختبار الاتصال

```bash
# اختبار Agent (يجب أن يعيد JSON)
curl http://127.0.0.1:9100/

# اختبار Dashboard (يجب أن يعيد HTML)
curl http://localhost:8000/
```

---

## 🌐 الوصول إلى Dashboard

بعد تشغيل الخدمات:

1. **من نفس الجهاز:**
   ```
   http://localhost:8000
   ```

2. **من جهاز آخر على نفس الشبكة:**
   ```
   http://192.168.1.99:8000
   ```
   (استبدل IP بآي بي جهازك)

---

## 🔧 استكشاف الأخطاء

### المشكلة: لا يمكن الوصول للـ Dashboard

**الحل 1: تحقق من Firewall**
```bash
# السماح للـ port 8000
sudo ufw allow 8000
sudo ufw status
```

**الحل 2: تحقق من أن الخدمات تعمل**
```bash
# يجب أن ترى عمليتين
ps aux | grep python
```

**الحل 3: تحقق من الـ Logs**
```bash
cd /opt/dash
source venv/bin/activate

# شغل Dashboard وسترى الأخطاء إن وجدت
python dashboard/main.py
```

**الحل 4: تحقق من IP**
```bash
# تأكد من IP الصحيح
hostname -I
```

---

### المشكلة: Agent لا يعمل

```bash
cd /opt/dash
source venv/bin/activate
python agent/main.py
# سترى الأخطاء إن وجدت
```

---

### المشكلة: Port 8000 مستخدم

```bash
# تحقق من ماذا يستخدم الـ port
sudo lsof -i :8000

# أو قتل العملية
sudo kill -9 <PID>
```

---

## 📝 تثبيت كـ Systemd Services (للإنتاج)

للتشغيل التلقائي عند بدء النظام:

```bash
cd /opt/dash
sudo bash scripts/install-services.sh
```

ثم:
```bash
sudo systemctl start fm-agent fm-dashboard
sudo systemctl status fm-agent fm-dashboard
```

---

## 🎯 الخطوات السريعة

```bash
# 1. تشغيل الخدمات
cd /opt/dash
bash start-all.sh

# 2. في متصفح آخر، افتح:
# http://192.168.1.99:8000

# 3. سجل دخول بـ:
# Username: admin
# Password: (الذي أدخلته أثناء التثبيت)
```

---

**ملاحظة:** إذا كنت تريد تشغيل الخدمات في الخلفية بشكل دائم، استخدم systemd services.

