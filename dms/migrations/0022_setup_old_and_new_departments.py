from django.db import migrations

def setup_old_and_new_departments(apps, schema_editor):
    Department = apps.get_model('dms', 'Department')
    UserProfile = apps.get_model('dms', 'UserProfile')
    CivilServantProfile = apps.get_model('dms', 'CivilServantProfile')

    # Step 1: Map/Rename existing new structure departments to NEW and is_active=False
    code_rename_map = {
        'ADMIN': 'ADMIN_NEW',
        'AGRO': 'AGRO_NEW',
        'AHVP': 'AHVP_NEW',
        'FISH': 'FISH_NEW',
        'FOREST': 'FOREST_NEW',
        'ENG': 'ENG_NEW',
    }

    for old_c, new_c in code_rename_map.items():
        dept = Department.objects.filter(code=old_c).first()
        if dept:
            dept.code = new_c
            dept.structure_type = 'NEW'
            dept.is_active = False
            dept.order_index = 200
            dept.save()

    # Step 2: Ensure Leadership Department (CORE)
    lead_dept = Department.objects.filter(code='LEAD').first()
    if not lead_dept:
        lead_dept = Department.objects.filter(name_kh='ថ្នាក់ដឹកនាំមន្ទីរ').first()
    if lead_dept:
        lead_dept.code = 'LEAD'
        lead_dept.name_kh = 'ថ្នាក់ដឹកនាំមន្ទីរ'
        lead_dept.name_en = 'Provincial Department Leadership'
        lead_dept.description = 'ថ្នាក់ដឹកនាំ និងប្រធានមន្ទីរ'
        lead_dept.structure_type = 'CORE'
        lead_dept.is_active = True
        lead_dept.order_index = 0
        lead_dept.save()
    else:
        lead_dept = Department.objects.create(
            code='LEAD',
            name_kh='ថ្នាក់ដឹកនាំមន្ទីរ',
            name_en='Provincial Department Leadership',
            description='ថ្នាក់ដឹកនាំ និងប្រធានមន្ទីរ',
            structure_type='CORE',
            is_active=True,
            order_index=0
        )

    # Step 3: Populate the 10 Old Structure Offices + 2 Cantons
    old_departments = [
        {
            'code': 'ADMIN_PERS',
            'name_kh': 'ការិយាល័យរដ្ឋបាល បុគ្គលិក',
            'name_en': 'Administration and Personnel Office',
            'description': 'កិច្ចការរដ្ឋបាល ទូទៅ និងគ្រប់គ្រងបុគ្គលិក មន្ត្រីរាជការ',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 1,
        },
        {
            'code': 'PLAN_ACC',
            'name_kh': 'ការិយាល័យផែនការ គណនេយ្យ',
            'name_en': 'Planning and Accounting Office',
            'description': 'កិច្ចការរៀបចំផែនការ ស្ថិតិ គណនេយ្យ និងហិរញ្ញវត្ថុ',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 2,
        },
        {
            'code': 'AGRI_LEG',
            'name_kh': 'ការិយាល័យនីតិកម្មកសិកម្ម',
            'name_en': 'Agricultural Legislation Office',
            'description': 'កិច្ចការនីតិកម្ម បទប្បញ្ញត្តិ និងអនុវត្តច្បាប់កសិកម្ម',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 3,
        },
        {
            'code': 'PROD_VET',
            'name_kh': 'ការិយាល័យផលិតកម្មនិងបសុព្យាបាល',
            'name_en': 'Animal Production and Veterinary Office',
            'description': 'កិច្ចការផលិតកម្មសត្វ សុខភាពសត្វ និងបសុព្យាបាល',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 4,
        },
        {
            'code': 'AGRO_PROD',
            'name_kh': 'ការិយាល័យក្សេត្រសាស្ត្រនិងផលិតភាពកសិកម្ម',
            'name_en': 'Agronomy and Agricultural Productivity Office',
            'description': 'កិច្ចការក្សេត្រសាស្ត្រ ដីកសិកម្ម ដំណាំ និងផលិតភាពកសិកម្ម',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 5,
        },
        {
            'code': 'AGRI_EXT',
            'name_kh': 'ការិយាល័យផ្សព្វផ្សាយកសិកម្ម',
            'name_en': 'Agricultural Extension Office',
            'description': 'ការងារបណ្តុះបណ្តាល និងផ្សព្វផ្សាយបច្ចេកទេសកសិកម្ម',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 6,
        },
        {
            'code': 'AGRI_MACH',
            'name_kh': 'ការិយាល័យគ្រឿងយន្តកសិកម្ម',
            'name_en': 'Agricultural Machinery Office',
            'description': 'កិច្ចការគ្រឿងយន្តកសិកម្ម និងបច្ចេកវិទ្យាកសិកម្ម',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 7,
        },
        {
            'code': 'AGRI_COMM',
            'name_kh': 'ការិយាល័យអភិវឌ្ឍន៍សហគមន៍កសិកម្ម',
            'name_en': 'Agricultural Community Development Office',
            'description': 'លើកកម្ពស់និងអភិវឌ្ឍន៍សហគមន៍កសិកម្ម និងសហករណ៍',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 8,
        },
        {
            'code': 'AGRO_IND',
            'name_kh': 'ការិយាល័យកសិឧស្សាហកម្ម',
            'name_en': 'Agro-Industry Office',
            'description': 'កិច្ចការកែច្នៃ និងអភិវឌ្ឍន៍ផលិតផលកសិឧស្សាហកម្ម',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 9,
        },
        {
            'code': 'RUBBER',
            'name_kh': 'ការិយាល័យកៅស៊ូ',
            'name_en': 'Rubber Office',
            'description': 'កិច្ចការអភិវឌ្ឍន៍ និងគ្រប់គ្រងដំណាំកៅស៊ូ',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 10,
        },
        {
            'code': 'CANTON_FOREST',
            'name_kh': 'ខណ្ឌរដ្ឋបាលព្រៃឈើ',
            'name_en': 'Forestry Administration Canton',
            'description': 'គ្រប់គ្រង ថែរក្សា ការពារ និងអភិរក្សធនធានព្រៃឈើ និងសត្វព្រៃ',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 11,
        },
        {
            'code': 'CANTON_FISH',
            'name_kh': 'ខណ្ឌរដ្ឋបាលជលផល',
            'name_en': 'Fisheries Administration Canton',
            'description': 'គ្រប់គ្រង ថែរក្សា អភិវឌ្ឍន៍ និងអភិរក្សធនធានជលផល និងវារីវប្បកម្ម',
            'structure_type': 'OLD',
            'is_active': True,
            'order_index': 12,
        },
    ]

    created_map = {}
    for d_data in old_departments:
        code = d_data['code']
        dept = Department.objects.filter(code=code).first()
        if not dept:
            dept = Department.objects.filter(name_kh=d_data['name_kh']).first()
        if dept:
            dept.code = code
            dept.name_kh = d_data['name_kh']
            dept.name_en = d_data['name_en']
            dept.description = d_data['description']
            dept.structure_type = d_data['structure_type']
            dept.is_active = d_data['is_active']
            dept.order_index = d_data['order_index']
            dept.save()
        else:
            dept = Department.objects.create(**d_data)
        created_map[code] = dept

    # Step 4: Reassign user profiles and civil servants to new active old-structure offices
    admin_pers = created_map.get('ADMIN_PERS')
    agro_prod = created_map.get('AGRO_PROD')
    canton_fish = created_map.get('CANTON_FISH')
    canton_forest = created_map.get('CANTON_FOREST')
    agri_comm = created_map.get('AGRI_COMM')

    # ADMIN_NEW users & officers -> ADMIN_PERS
    dept_admin_new = Department.objects.filter(code='ADMIN_NEW').first()
    if dept_admin_new and admin_pers:
        UserProfile.objects.filter(department=dept_admin_new).update(department=admin_pers)
        CivilServantProfile.objects.filter(department=dept_admin_new).update(department=admin_pers)

    # AGRO_NEW users & officers -> AGRO_PROD
    dept_agro_new = Department.objects.filter(code='AGRO_NEW').first()
    if dept_agro_new and agro_prod:
        UserProfile.objects.filter(department=dept_agro_new).update(department=agro_prod)
        CivilServantProfile.objects.filter(department=dept_agro_new).update(department=agro_prod)

    # FISH_NEW users & officers -> CANTON_FISH
    dept_fish_new = Department.objects.filter(code='FISH_NEW').first()
    if dept_fish_new and canton_fish:
        UserProfile.objects.filter(department=dept_fish_new).update(department=canton_fish)
        CivilServantProfile.objects.filter(department=dept_fish_new).update(department=canton_fish)

    # FOREST_NEW officers -> CANTON_FOREST
    dept_forest_new = Department.objects.filter(code='FOREST_NEW').first()
    if dept_forest_new and canton_forest:
        UserProfile.objects.filter(department=dept_forest_new).update(department=canton_forest)
        CivilServantProfile.objects.filter(department=dept_forest_new).update(department=canton_forest)

    # ACD (old code) officers -> AGRI_COMM
    dept_acd_old = Department.objects.filter(code='ACD').first()
    if dept_acd_old and dept_acd_old.id != agri_comm.id and agri_comm:
        UserProfile.objects.filter(department=dept_acd_old).update(department=agri_comm)
        CivilServantProfile.objects.filter(department=dept_acd_old).update(department=agri_comm)
        dept_acd_old.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dms', '0021_alter_department_options_department_is_active_and_more'),
    ]

    operations = [
        migrations.RunPython(setup_old_and_new_departments, reverse_code=migrations.RunPython.noop),
    ]
