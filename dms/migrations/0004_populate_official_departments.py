from django.db import migrations

def populate_official_departments(apps, schema_editor):
    Department = apps.get_model('dms', 'Department')
    
    official_departments = [
        {
            'code': 'LEAD',
            'name_kh': 'ថ្នាក់ដឹកនាំមន្ទីរ',
            'name_en': 'Provincial Department Leadership',
            'description': 'ថ្នាក់ដឹកនាំ និងប្រធានមន្ទីរ'
        },
        {
            'code': 'AGRO',
            'name_kh': 'ការិយាល័យក្សេត្រសាស្ត្រ',
            'name_en': 'Agronomy and Agricultural Land Office',
            'description': 'គ្រប់គ្រងការងារក្សេត្រសាស្ត្រ ដំណាំកសិកម្ម និងដីកសិកម្ម'
        },
        {
            'code': 'AHVP',
            'name_kh': 'ការិយាល័យសុខភាពសត្វនិងផលិតកម្មសត្វ',
            'name_en': 'Animal Health and Veterinary Production Office',
            'description': 'គ្រប់គ្រងសុខភាពសត្វ ការចាក់វ៉ាក់សាំង និងផលិតកម្មសត្វ'
        },
        {
            'code': 'FISH',
            'name_kh': 'ការិយាល័យជលផល',
            'name_en': 'Fisheries Administration Office',
            'description': 'គ្រប់គ្រងធនធានជលផល វារីវប្បកម្ម និងការអភិរក្ស'
        },
        {
            'code': 'FOREST',
            'name_kh': 'ការិយាល័យព្រៃឈើនិងសត្វព្រៃ',
            'name_en': 'Forestry and Wildlife Office',
            'description': 'គ្រប់គ្រងធនធានព្រៃឈើ ដាំដើមឈើ និងអភិរក្សសត្វព្រៃ'
        },
        {
            'code': 'ACD',
            'name_kh': 'ការិយាល័យអភិវឌ្ឍន៍សហគមន៍កសិកម្ម',
            'name_en': 'Agricultural Community Development Office',
            'description': 'លើកកម្ពស់និងអភិវឌ្ឍន៍សហគមន៍កសិកម្ម និងសហករណ៍'
        },
        {
            'code': 'ENG',
            'name_kh': 'ការិយាល័យវិស្វកម្មកសិកម្មនិងកសិឧស្សាហកម្ម',
            'name_en': 'Agricultural Engineering and Agro-Industry Office',
            'description': 'គ្រឿងយន្តកសិកម្ម ប្រព័ន្ធស្រោចស្រព និងកែច្នៃកសិឧស្សាហកម្ម'
        },
        {
            'code': 'ADMIN',
            'name_kh': 'ការិយាល័យកិច្ចការទូទៅ',
            'name_en': 'General Affairs Office',
            'description': 'កិច្ចការរដ្ឋបាល បុគ្គលិក ហិរញ្ញវត្ថុ និងកិច្ចការទូទៅ'
        },
    ]

    for data in official_departments:
        dept = Department.objects.filter(code=data['code']).first()
        if not dept:
            dept = Department.objects.filter(name_kh=data['name_kh']).first()
        
        if dept:
            dept.code = data['code']
            dept.name_kh = data['name_kh']
            dept.name_en = data['name_en']
            dept.description = data['description']
            dept.save()
        else:
            Department.objects.create(**data)


class Migration(migrations.Migration):

    dependencies = [
        ('dms', '0003_userprofile_created_at_userprofile_is_approved'),
    ]

    operations = [
        migrations.RunPython(populate_official_departments, reverse_code=migrations.RunPython.noop),
    ]
