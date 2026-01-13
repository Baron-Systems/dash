# إضافة FM Stacks يدوياً

إذا لم يتم اكتشاف stacks تلقائياً، يمكنك إضافتها يدوياً.

## 🔍 اكتشاف مسار Stack الخاص بك

### الطريقة 1: استخدام `fm list`

```bash
fm list
```

مثال Output:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Site                     ┃ Status   ┃ Path                                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ devsite.mby-solution.vip │ Inactive │ /home/baron/frappe/sites/devsite.mby-solution.vip │
└──────────────────────────┴──────────┴───────────────────────────────────────────────────┘
```

**المسار الذي تحتاجه:**
- Site path: `/home/baron/frappe/sites/devsite.mby-solution.vip`
- **Stack path**: `/home/baron/frappe` (المجلد الأب لـ sites)

---

## ✏️ تعديل config.yaml

```bash
cd /opt/dash
nano config.yaml
```

### قبل:
```yaml
stacks:
  example:
    path: /home/baron/frappe-bench
    type: fm
```

### بعد:
```yaml
stacks:
  production:
    path: /home/baron/frappe
    type: fm
  # يمكنك إضافة المزيد
  # dev:
  #   path: /home/baron/frappe-dev
  #   type: fm
```

---

## 📝 أمثلة على هياكل FM المختلفة

### النمط 1: FM Standard
```yaml
stacks:
  main:
    path: /home/baron/frappe
    type: fm
```

الهيكل:
```
/home/baron/frappe/
├── sites/
│   ├── site1.example.com/
│   └── site2.example.com/
└── ...
```

---

### النمط 2: FM Workspace
```yaml
stacks:
  prod:
    path: /home/baron/.frappe/prod
    type: fm
```

الهيكل:
```
/home/baron/.frappe/prod/
├── workspace/
│   └── frappe-bench/
│       └── sites/
└── docker-compose.yml
```

---

### النمط 3: Multiple Stacks
```yaml
stacks:
  production:
    path: /home/baron/frappe
    type: fm
  staging:
    path: /home/baron/frappe-staging
    type: fm
  development:
    path: /home/baron/frappe-dev
    type: fm
```

---

## 🔄 بعد التعديل

```bash
# إعادة تشغيل الخدمات
cd /opt/dash

# إيقاف الخدمات الحالية (إذا كانت تعمل)
# اضغط Ctrl+C في الـ terminals

# إعادة التشغيل
bash start-all.sh
```

---

## ✅ التحقق من التكوين

```bash
cd /opt/dash
source venv/bin/activate

# اختبار Agent - يجب أن يعرض stacks
python3 << 'EOF'
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
    print("Configured stacks:")
    for name, details in config['stacks'].items():
        print(f"  - {name}: {details['path']}")
EOF
```

---

## 🎯 مثال كامل

بناءً على output `fm list` الخاص بك:

```yaml
agent:
  name: stage
  listen: 127.0.0.1
  port: 9100

security:
  token: YOUR_TOKEN_HERE

stacks:
  production:
    path: /home/baron/frappe
    type: fm

backups:
  base_path: /backups
  retention_days: 30

dashboard:
  listen: 0.0.0.0
  port: 8000
  secret_key: YOUR_SECRET_HERE
  admin_username: admin
  admin_password: YOUR_PASSWORD
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: Stack لا يظهر في Dashboard

**الحل:**
```bash
# 1. تحقق من المسار موجود
ls -la /home/baron/frappe

# 2. تحقق من أن المستخدم يستطيع الوصول للمسار
test -r /home/baron/frappe && echo "OK" || echo "No access"

# 3. تحقق من التكوين
cd /opt/dash
cat config.yaml | grep -A 3 "stacks:"
```

---

### المشكلة: عدة sites في نفس المجلد

إذا كان لديك:
```
/home/baron/frappe/sites/
  ├── site1.example.com/
  ├── site2.example.com/
  └── site3.example.com/
```

**الحل:** استخدم مسار واحد:
```yaml
stacks:
  main:
    path: /home/baron/frappe
    type: fm
```

Dashboard سيعرض كل المواقع في `/home/baron/frappe/sites/`

---

## 📚 مزيد من المعلومات

- [README.md](README.md) - وثائق كاملة
- [README.ar.md](README.ar.md) - دليل عربي
- [DEPLOYMENT.md](DEPLOYMENT.md) - نشر للإنتاج

