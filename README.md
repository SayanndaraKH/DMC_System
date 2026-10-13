# ប្រព័ន្ធគ្រប់គ្រងឯកសារ និងព័ត៌មានមន្ត្រី (DMS / DCM System)

ប្រព័ន្ធគ្រប់គ្រងឯកសារចូល-ចេញ (Document Management System), គ្រប់គ្រងព័ត៌មានមន្ត្រីរាជការស៊ីវិល, មន្ត្រីជាប់កិច្ចសន្យា, សំណើសុំគ្រឿងឥស្សរិយយស, ការតម្លើងថ្នាក់/ឋានន្តរស័ក្តិ និងគ្រប់គ្រងយានយន្តរដ្ឋ។

---

## 🚀 ការដាក់ឱ្យដំណើរការលើ Netlify + Neon PostgreSQL (Deploy to Netlify)

### ជំហានទី ១៖ រៀបចំ Database លើ Neon.tech
1. ចូលទៅកាន់ [Neon Console](https://console.neon.tech/) ហើយ Copy យក **Connection String** (`DATABASE_URL`)
   - ទម្រង់: `postgresql://neondb_owner:***@ep-xyz-pooler.region.aws.neon.tech/neondb?sslmode=require`
2. ដំណើរការឯកសារ `INIT_NEON_DATABASE.bat` ក្នុងកុំព្យូទ័ររបស់អ្នក ហើយ Paste `DATABASE_URL` ចូល ដើម្បីបង្កើត Tables និងទិន្នន័យភូមិសាស្រ្តកម្ពុជាដោយស្វ័យប្រវត្តិ។

### ជំហានទី ២៖ ភ្ជាប់គម្រោងលើ Netlify
1. ចូលទៅកាន់ [Netlify Dashboard](https://app.netlify.com/)
2. ចុច **Add new site** -> ជ្រើសរើស **Import an existing project**
3. ជ្រើសរើស GitHub និងជ្រើសរើស Repository: `DMC_System`

### ជំហានទី ៣៖ កំណត់ Environment Variables (លើ Netlify)
ចូលទៅកាន់ **Site configuration** -> **Environment variables** ហើយបន្ថែម៖
- `DATABASE_URL` = `(Connection String ពី Neon Console របស់អ្នក)`
- `DEBUG` = `False`
- `SECRET_KEY` = `(បង្កើត Secret Key វែងមួយ ឬប្រើអក្សរចម្រុះ)`
- `ALLOWED_HOSTS` = `*`
- `CSRF_TRUSTED_ORIGINS` = `https://*.netlify.app`
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
- រាល់ការកំណត់ Password ឬ Secret ត្រូវបញ្ចូលក្នុង Environment Variables ផ្ទាល់។
