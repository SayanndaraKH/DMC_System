# ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMS / DCM System)

ប្រព័ន្ធគ្រប់គ្រងឯកសារចូល-ចេញ (Document Management System), គ្រប់គ្រងព័ត៌មានមន្ត្រីរាជការស៊ីវិល, មន្ត្រីជាប់កិច្ចសន្យា, សំណើសុំគ្រឿងឥស្សរិយយស, ការតម្លើងថ្នាក់/ឋានន្តរស័ក្តិ និងគ្រប់គ្រងយានយន្តរដ្ឋ។

---

## 🚀 ការដាក់ឱ្យដំណើរការនៅលើ Railway.com (Deploy to Railway)

### ជំហានទី ១៖ បង្កើតគម្រោងលើ Railway
1. ចូលទៅកាន់ [Railway.com](https://railway.com/) ហើយចុះឈ្មោះ/ចូលដោយប្រើគណនី GitHub
2. ចុច **New Project** -> ជ្រើសរើស **Deploy from GitHub repo**
3. ជ្រើសរើស Repository: `DMC_System`

### ជំហានទី ២៖ បន្ថែម Database (PostgreSQL)
1. ក្នុង Project Dashboard ចុច **Create** -> ជ្រើសរើស **Database** -> **Add PostgreSQL**
2. Railway នឹងភ្ជាប់ `DATABASE_URL` ដោយស្វ័យប្រវត្តិទៅកាន់ Django Web Service

### ជំហានទី ៣៖ កំណត់ Environment Variables (លើ Railway Web Service)
ចូលទៅកាន់ Service របស់ Django -> ផ្ទាំង **Variables** ហើយបន្ថែម៖
- `DEBUG` = `False`
- `SECRET_KEY` = `(បង្កើត Secret Key វែងមួយ ឬប្រើអក្សរចម្រុះ)`
- `ALLOWED_HOSTS` = `*`
- `CSRF_TRUSTED_ORIGINS` = `https://*.railway.app,https://*.up.railway.app`
- `EMAIL_HOST_USER` = `(Gmail របស់អ្នកសម្រាប់ផ្ញើ OTP)`
- `EMAIL_HOST_PASSWORD` = `(Google App Password ១៦ ខ្ទង់)`

---

## 💻 ដំណើរការក្នុងកុំព្យូទ័រ (Local Development)

```bash
# ១. បង្កើត និងបើក Virtual Environment
python -m venv venv
venv\Scripts\activate

# ២. ដំឡើង Dependencies
pip install -r requirements.txt

# ៣. Run Database Migrations
python manage.py migrate

# ៤. បង្កើត Superuser (Admin)
python manage.py createsuperuser

# ៥. Start Server
python manage.py runserver
```

---

## 🔒 សុវត្ថិភាព និងឯកសារដែលត្រូវរក្សាការសម្ងាត់
- ឯកសារ `.env` និង `db.sqlite3` ត្រូវបានកំណត់ក្នុង `.gitignore` មិនអនុញ្ញាតឱ្យ upload ឡើង GitHub ជាសាធារណៈឡើយ។
- រាល់ការកំណត់ Password ឬ Secret ត្រូវបញ្ចូលក្នុង Railway Environment Variables ផ្ទាល់។
