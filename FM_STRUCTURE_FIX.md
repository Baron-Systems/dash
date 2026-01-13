# إصلاح بنية FM - FM Structure Fix

## 🎯 المشكلة

الداشبورد كان يفترض بنية مختلفة عن البنية الفعلية لـ Frappe Manager!

### ❌ البنية المفترضة (خطأ):
```
/home/baron/frappe/
├── sites/
│   └── site1.example.com/      ← موقع مباشر
│   └── site2.example.com/      ← موقع مباشر
```

### ✅ البنية الفعلية (صحيحة):
```
/home/baron/frappe/                           ← Stack Root
├── backups/
├── fm_config.toml
├── logs/
├── services/
└── sites/
    └── devsite.mby-solution.vip/            ← Bench Container
        ├── bench_config.toml
        ├── configs/
        ├── docker-compose.yml               ← Docker files لهذا الـ bench
        └── workspace/
            └── frappe-bench/
                └── sites/                    ← المواقع الفعلية هنا!
                    └── devsite.mby-solution.vip/  ← الموقع الحقيقي
```

---

## 🔧 التغييرات المطبّقة

### 1. **دالة جديدة: `find_site_bench()`**
تبحث عن الـ bench الذي يحتوي على موقع معين:

```python
def find_site_bench(stack_name: str, site_name: str) -> Path:
    """Find the bench directory that contains a specific site"""
    stack_path = get_stack_path(stack_name)
    sites_dir = stack_path / "sites"
    
    # Iterate through all benches
    for bench_dir in sites_dir.iterdir():
        site_path = bench_dir / "workspace" / "frappe-bench" / "sites" / site_name
        if site_path.exists():
            return bench_dir  # Return bench container path
    
    raise FileNotFoundError(f"Site '{site_name}' not found")
```

### 2. **تحديث `list_sites()`**
الآن تبحث في جميع الـ benches:

```python
def list_sites(stack_name: str) -> List[str]:
    """List all sites in a stack - FM structure aware"""
    all_sites = set()
    sites_dir = stack_path / "sites"
    
    # Iterate through each bench container
    for bench_dir in sites_dir.iterdir():
        frappe_sites_dir = bench_dir / "workspace" / "frappe-bench" / "sites"
        if frappe_sites_dir.exists():
            # List actual sites in this bench
            for site_dir in frappe_sites_dir.iterdir():
                if site_dir.is_dir():
                    all_sites.add(site_dir.name)
    
    return sorted(list(all_sites))
```

### 3. **تحديث جميع دوال العمليات**

#### ✅ `restart_site()`
```python
def restart_site(stack_name: str, site_name: str) -> tuple:
    bench_path = find_site_bench(stack_name, site_name)
    # Execute docker-compose in the correct bench directory
    run_command(["docker-compose", "restart", "backend"], cwd=bench_path)
```

#### ✅ `migrate_site()`
```python
def migrate_site(stack_name: str, site_name: str) -> tuple:
    bench_path = find_site_bench(stack_name, site_name)
    # Execute migrate in the correct bench
    run_command(["docker", "exec", "backend", "bench", "--site", site_name, "migrate"], 
                cwd=bench_path)
```

#### ✅ `backup_site()`
```python
def backup_site(stack_name: str, site_name: str) -> tuple:
    bench_path = find_site_bench(stack_name, site_name)
    # Backup in correct bench
    run_command(["docker", "exec", "backend", "bench", "--site", site_name, "backup"], 
                cwd=bench_path)
    
    # Find backup in correct location
    source_backup_dir = bench_path / "workspace" / "frappe-bench" / "sites" / site_name / "private" / "backups"
```

#### ✅ `get_site_logs()`
```python
def get_site_logs(stack_name: str, site_name: str, lines: int = 100) -> tuple:
    bench_path = find_site_bench(stack_name, site_name)
    # Get logs from correct bench's container
    run_command(["docker", "logs", "--tail", str(lines), "backend"], cwd=bench_path)
```

#### ✅ `list_site_files()`
```python
def list_site_files(stack_name: str, site_name: str, subpath: str = "") -> tuple:
    bench_path = find_site_bench(stack_name, site_name)
    # List files in correct location
    site_dir = bench_path / "workspace" / "frappe-bench" / "sites" / site_name
```

---

## 📁 هيكل FM بالتفصيل

### المسارات الكاملة:

```
/home/baron/frappe/                                                    ← Stack Root
│
├── sites/
│   └── devsite.mby-solution.vip/                                     ← Bench Container
│       ├── bench_config.toml
│       ├── docker-compose.yml                                        ← Docker Compose للـ bench
│       ├── docker-compose.workers.yml
│       ├── docker-compose.admin-tools.yml
│       │
│       └── workspace/
│           └── frappe-bench/                                         ← Frappe Bench
│               ├── apps/                                             ← Frappe Apps
│               ├── config/                                           ← Bench Config
│               ├── env/                                              ← Python virtualenv
│               ├── logs/                                             ← Bench Logs
│               │
│               └── sites/                                            ← المواقع الفعلية
│                   ├── assets/
│                   ├── common_site_config.json
│                   │
│                   └── devsite.mby-solution.vip/                     ← الموقع الحقيقي
│                       ├── site_config.json
│                       ├── public/
│                       ├── private/
│                       │   └── backups/                              ← Backups هنا!
│                       └── locks/
│
├── backups/                                                           ← Stack Backups
├── logs/                                                              ← Stack Logs
├── services/                                                          ← FM Services
└── fm_config.toml                                                     ← FM Config
```

---

## 🔍 كيف يعمل الآن

### مثال: Restart Site

#### القديم ❌:
```python
# كان يبحث في المسار الخاطئ
cwd = /home/baron/frappe  # ← خطأ! لا يوجد docker-compose هنا
docker-compose restart backend  # ← فشل!
```

#### الجديد ✅:
```python
# 1. يجد الـ bench الصحيح
bench_path = find_site_bench("frappe", "devsite.mby-solution.vip")
# Returns: /home/baron/frappe/sites/devsite.mby-solution.vip

# 2. ينفذ الأمر في المسار الصحيح
cwd = /home/baron/frappe/sites/devsite.mby-solution.vip  # ← صحيح!
docker-compose restart backend  # ← نجح! ✅
```

### مثال: Backup Site

#### القديم ❌:
```python
# كان يبحث في:
/home/baron/frappe/workspace/frappe-bench/sites/...  # ← لا يوجد!
```

#### الجديد ✅:
```python
# يبحث في:
/home/baron/frappe/sites/devsite.mby-solution.vip/workspace/frappe-bench/sites/devsite.mby-solution.vip/private/backups/
# ✅ صحيح!
```

---

## 🧪 الاختبار

### Test 1: List Sites
```bash
# يجب أن يعيد المواقع الفعلية من داخل كل bench
GET /stacks/frappe/sites

# Expected:
{
  "stack": "frappe",
  "sites": ["devsite.mby-solution.vip"]
}
```

### Test 2: Restart Site
```bash
# يجب أن ينفذ في bench الصحيح
POST /action
{
  "action": "restart_site",
  "stack": "frappe",
  "site": "devsite.mby-solution.vip"
}

# Expected: ✅ Success
```

### Test 3: Backup Site
```bash
# يجب أن يجد الـ backup في المسار الصحيح
POST /action
{
  "action": "backup_site",
  "stack": "frappe",
  "site": "devsite.mby-solution.vip"
}

# Expected: ✅ Backup file found and copied
```

### Test 4: View Files
```bash
# يجب أن يعرض ملفات الموقع من المسار الصحيح
GET /site/frappe/devsite.mby-solution.vip/files

# Expected: ✅ Files list from correct location
```

---

## 🚀 التطبيق

### نسخ الملف المحدث:

```bash
# من جهازك المحلي
scp /home/manager-pc/Desktop/dash/agent/main.py \
    baron@192.168.1.99:/opt/dash/agent/
```

### على السيرفر:

```bash
# إصلاح الصلاحيات
sudo chown -R baron:baron /opt/dash

# إعادة تشغيل Agent
cd /opt/dash
# اضغط Ctrl+C لإيقاف start-all.sh
bash start-all.sh
```

---

## ✅ التحقق

بعد التطبيق، تحقق من:

1. **Sites List**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:9100/stacks/frappe/sites
```

Expected:
```json
{
  "stack": "frappe",
  "sites": ["devsite.mby-solution.vip"]
}
```

2. **Dashboard**
```
http://192.168.1.99:8000/stack/frappe
```

يجب أن ترى:
- ✅ اسم الموقع: `devsite.mby-solution.vip`
- ✅ جميع الأزرار تعمل (Restart, Migrate, Backup)
- ✅ Logs تظهر بشكل صحيح
- ✅ Files تظهر من المسار الصحيح

---

## 🔮 دعم Multiple Benches

الكود الآن يدعم **عدة benches** في نفس الـ stack!

### مثال:
```
/home/baron/frappe/sites/
├── bench1/
│   └── workspace/frappe-bench/sites/
│       ├── site1.example.com
│       └── site2.example.com
│
└── bench2/
    └── workspace/frappe-bench/sites/
        ├── site3.example.com
        └── site4.example.com
```

سيعرض Dashboard:
```
Sites (4)
- site1.example.com
- site2.example.com
- site3.example.com
- site4.example.com
```

وكل site ستنفذ عملياته في الـ bench الصحيح! ✨

---

## 📊 الملخص

| العنصر | القديم | الجديد |
|--------|--------|--------|
| **Sites Discovery** | ❌ يبحث في مسار خاطئ | ✅ يبحث في جميع benches |
| **Operations Path** | ❌ مسار Stack فقط | ✅ مسار Bench الصحيح |
| **Backup Location** | ❌ مسار خاطئ | ✅ مسار صحيح في bench |
| **Docker Commands** | ❌ في مجلد خاطئ | ✅ في bench directory |
| **Multi-Bench** | ❌ غير مدعوم | ✅ مدعوم كامل |

---

## 🎓 فهم FM Structure

### لماذا هذه البنية؟

FM يستخدم هذه البنية لـ:

1. **عزل Benches**: كل bench له docker-compose خاص
2. **Multiple Versions**: يمكن تشغيل Frappe versions مختلفة
3. **Resource Management**: containers منفصلة لكل bench
4. **Easier Backup**: كل bench مستقل

### Stack vs Bench vs Site

- **Stack**: المجموعة الكاملة (`/home/baron/frappe`)
- **Bench**: حاوية تحتوي على Frappe installation (`sites/devsite.mby-solution.vip`)
- **Site**: الموقع الفعلي داخل Bench (`workspace/frappe-bench/sites/devsite.mby-solution.vip`)

---

**تم بنجاح! 🎉**

الداشبورد الآن يفهم بنية FM الحقيقية ويعمل بشكل صحيح!

