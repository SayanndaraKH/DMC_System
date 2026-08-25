from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import os

from dms.models import (
    Department, UserProfile, Document, DocumentVersion,
    LeadershipAnnotation, DocumentRouting, Notification
)

class Command(BaseCommand):
    help = 'Seeds initial departments, users, and sample government documents for DMS testing.'

    def handle(self, *args, **options):
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')

        self.stdout.write(self.style.SUCCESS("=== Starting DMS Seed Data Generation ==="))


        # 1. Create Departments (8 Official Departments)
        departments_data = [
            {'code': 'LEAD', 'name_kh': 'ថ្នាក់ដឹកនាំមន្ទីរ', 'name_en': 'Provincial Department Leadership', 'desc': 'ថ្នាក់ដឹកនាំ និងប្រធានមន្ទីរ'},
            {'code': 'ADMIN', 'name_kh': 'ការិយាល័យកិច្ចការទូទៅ', 'name_en': 'General Affairs Office', 'desc': 'កិច្ចការរដ្ឋបាល បុគ្គលិក ហិរញ្ញវត្ថុ និងកិច្ចការទូទៅ'},
            {'code': 'AGRO', 'name_kh': 'ការិយាល័យក្សេត្រសាស្ត្រ', 'name_en': 'Agronomy and Agricultural Land Office', 'desc': 'គ្រប់គ្រងការងារក្សេត្រសាស្ត្រ ដំណាំកសិកម្ម និងដីកសិកម្ម'},
            {'code': 'AHVP', 'name_kh': 'ការិយាល័យសុខភាពសត្វនិងផលិតកម្មសត្វ', 'name_en': 'Animal Health and Veterinary Production Office', 'desc': 'គ្រប់គ្រងសុខភាពសត្វ ការចាក់វ៉ាក់សាំង និងផលិតកម្មសត្វ'},
            {'code': 'FISH', 'name_kh': 'ការិយាល័យជលផល', 'name_en': 'Fisheries Administration Office', 'desc': 'គ្រប់គ្រងធនធានជលផល វារីវប្បកម្ម និងការនេសាទ'},
            {'code': 'FOREST', 'name_kh': 'ការិយាល័យព្រៃឈើនិងសត្វព្រៃ', 'name_en': 'Forestry and Wildlife Office', 'desc': 'គ្រប់គ្រងធនធានព្រៃឈើ ដាំដើមឈើ និងអភិរក្សសត្វព្រៃ'},
            {'code': 'ACD', 'name_kh': 'ការិយាល័យអភិវឌ្ឍន៍សហគមន៍កសិកម្ម', 'name_en': 'Agricultural Community Development Office', 'desc': 'លើកកម្ពស់និងបង្កើតសហគមន៍កសិកម្ម និងសហករណ៍'},
            {'code': 'ENG', 'name_kh': 'ការិយាល័យវិស្វកម្មកសិកម្មនិងកសិឧស្សាហកម្ម', 'name_en': 'Agricultural Engineering and Agro-Industry Office', 'desc': 'គ្រឿងយន្តកសិកម្ម ប្រព័ន្ធស្រោចស្រព និងកែច្នៃកសិឧស្សាហកម្ម'},
        ]

        depts = {}
        for d in departments_data:
            dept_obj, _ = Department.objects.get_or_create(
                code=d['code'],
                defaults={'name_kh': d['name_kh'], 'name_en': d['name_en'], 'description': d['desc']}
            )
            depts[d['code']] = dept_obj
            self.stdout.write(f" -> Created department: {dept_obj.code}")


        # 2. Create Users & Profiles
        users_data = [
            {
                'username': 'leader_user',
                'first_name': 'ឯកឧត្តម',
                'last_name': 'ប្រធានមន្ទីរ',
                'role': 'LEADERSHIP',
                'dept': depts['LEAD'],
                'position': 'ប្រធានមន្ទីរ'
            },
            {
                'username': 'admin_user',
                'first_name': 'សុខ',
                'last_name': 'ចំរើន',
                'role': 'ADMIN',
                'dept': depts['ADMIN'],
                'position': 'ប្រធានការិយាល័យរដ្ឋបាល'
            },
            {
                'username': 'acc_user',
                'first_name': 'ចាន់',
                'last_name': 'ធីរ៉ា',
                'role': 'SPECIALIZED',
                'dept': depts['ACC'],
                'position': 'ប្រធានការិយាល័យគណនេយ្យ'
            },
            {
                'username': 'hr_user',
                'first_name': 'មាស',
                'last_name': 'សុផល',
                'role': 'SPECIALIZED',
                'dept': depts['HR'],
                'position': 'ប្រធានការិយាល័យបុគ្គលិក'
            },
            {
                'username': 'it_user',
                'first_name': 'ហ៊ុយ',
                'last_name': 'វិបុល',
                'role': 'SPECIALIZED',
                'dept': depts['IT'],
                'position': 'ប្រធានការិយាល័យព័ត៌មានវិទ្យា'
            },
        ]

        user_objs = {}
        for u in users_data:
            user_inst, created = User.objects.get_or_create(
                username=u['username'],
                defaults={
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'email': f"{u['username']}@gov.kh",
                    'is_staff': True,
                }
            )
            if created or not user_inst.check_password('pass123'):
                user_inst.set_password('pass123')
                user_inst.save()

            profile, _ = UserProfile.objects.get_or_create(
                user=user_inst,
                defaults={
                    'department': u['dept'],
                    'role': u['role'],
                    'position_title': u['position'],
                    'phone': '012 345 678'
                }
            )
            user_objs[u['username']] = user_inst
            self.stdout.write(f" -> Created user: {user_inst.username}")

        # Create Superuser admin/admin123
        su, created_su = User.objects.get_or_create(username='admin', defaults={'is_superuser': True, 'is_staff': True})
        if created_su:
            su.set_password('admin123')
            su.save()
            UserProfile.objects.create(user=su, department=depts['ADMIN'], role='ADMIN', position_title='Super Admin')

        # 3. Create Sample Documents
        today = timezone.now().date()


        docs_data = [
            {
                'doc_type': 'INBOUND',
                'registry_number': '001/26/ADMIN',
                'title': 'សំណើសុំអនុម័តកញ្ចប់ថវិកាបំពាក់ឧបករណ៍បច្ចេកវិទ្យាព័ត៌មានប្រចាំឆ្នាំ២០២៦',
                'summary': 'ស្នើសុំការពិនិត្យ និងសម្រេចលើកញ្ចប់ថវិកាសម្រាប់ការទិញម៉ាស៊ីនកុំព្យូទ័រ និង Server ថ្មីសម្រាប់មន្ទីរ',
                'origin_org': 'ក្រសួងសេដ្ឋកិច្ច និងហិរញ្ញវត្ថុ',
                'destination_org': 'មន្ទីររដ្ឋបាល និងហិរញ្ញវត្ថុ',
                'urgency': 'MOST_URGENT',
                'secrecy': 'NORMAL',
                'status': 'PENDING_LEADERSHIP',
                'created_by': user_objs['admin_user'],
                'origin_dept': depts['ADMIN'],
                'current_dept': depts['LEAD'],
            },
            {
                'doc_type': 'INBOUND',
                'registry_number': '002/26/ACC',
                'title': 'លិខិតអញ្ជើញចូលរួមវគ្គបណ្តុះបណ្តាលស្តីពីការគ្រប់គ្រងហិរញ្ញវត្ថុសាធារណៈ',
                'summary': 'អញ្ជើញមន្ត្រីជំនាញផ្នែកគណនេយ្យចំនួន ០២ រូប ចូលរួមវគ្គបណ្តុះបណ្តាលនៅសាលាជាតិហិរញ្ញវត្ថុ',
                'origin_org': 'អគ្គនាយកដ្ឋានហិរញ្ញវត្ថុសាធារណៈ',
                'destination_org': 'ការិយាល័យគណនេយ្យ និងហិរញ្ញវត្ថុ',
                'urgency': 'URGENT',
                'secrecy': 'NORMAL',
                'status': 'ROUTED',
                'created_by': user_objs['admin_user'],
                'origin_dept': depts['ADMIN'],
                'current_dept': depts['ACC'],
            },
            {
                'doc_type': 'OUTBOUND',
                'registry_number': '003/26/HR',
                'title': 'របាយការណ៍បូកសរុបវាយតម្លៃការងារមន្ត្រីរាជការប្រចាំឆមាសទី១ ឆ្នាំ២០២៦',
                'summary': 'របាយការណ៍ស្ដីពីការវាយតម្លៃលទ្ធផលការងារ និងការលើកសរសើរមន្ត្រីរាជការមានស្នាដៃ',
                'origin_org': 'ការិយាល័យគ្រប់គ្រងបុគ្គលិក',
                'destination_org': 'ក្រសួងមុខងារសាធារណៈ',
                'urgency': 'NORMAL',
                'secrecy': 'CONFIDENTIAL',
                'status': 'COMPLETED',
                'created_by': user_objs['hr_user'],
                'origin_dept': depts['HR'],
                'current_dept': depts['HR'],
            },
            {
                'doc_type': 'OUTBOUND',
                'registry_number': '004/26/IT',
                'title': 'គម្រោងរៀបចំប្រព័ន្ធគ្រប់គ្រងឯកសារអេឡិចត្រូនិក (DMS) សម្រាប់មន្ទីរ',
                'summary': 'ផែនការសកម្មភាពកាត់បន្ថយការប្រើប្រាស់ក្រដាស និងការផ្លាស់ប្តូរទៅជាការិយាល័យឌីជីថល',
                'origin_org': 'ការិយាល័យព័ត៌មានវិទ្យា',
                'destination_org': 'រដ្ឋបាលមន្ទីរ',
                'urgency': 'URGENT',
                'secrecy': 'NORMAL',
                'status': 'PENDING_ADMIN',
                'created_by': user_objs['it_user'],
                'origin_dept': depts['IT'],
                'current_dept': depts['ADMIN'],
            },
        ]

        for d in docs_data:
            doc_inst, created_doc = Document.objects.get_or_create(
                registry_number=d['registry_number'],
                defaults={
                    'doc_type': d['doc_type'],
                    'title': d['title'],
                    'summary': d['summary'],
                    'origin_org': d['origin_org'],
                    'destination_org': d['destination_org'],
                    'urgency': d['urgency'],
                    'secrecy': d['secrecy'],
                    'status': d['status'],
                    'created_by': d['created_by'],
                    'origin_department': d['origin_dept'],
                    'current_department': d['current_dept'],
                    'issue_date': today - timedelta(days=2),
                    'received_date': today,
                }
            )
            if created_doc:
                self.stdout.write(f" -> Created document: [{doc_inst.registry_number}]")


                # Create initial Version
                DocumentVersion.objects.create(
                    document=doc_inst,
                    version_number='1.0',
                    uploaded_by=d['created_by'],
                    change_summary='ឯកសារចម្បង Upload លើកដំបូង'
                )

                # Create initial Routing record
                DocumentRouting.objects.create(
                    document=doc_inst,
                    from_user=d['created_by'],
                    from_dept=d['origin_dept'],
                    to_dept=d['current_dept'],
                    action_taken="បង្កើត និងចុះបញ្ជីឯកសារ",
                    notes="ចុះលេខចូលប្រព័ន្ធរដ្ឋបាល"
                )

                # Add sample annotation for routed document 002/26/ACC
                if d['registry_number'] == '002/26/ACC':
                    annot = LeadershipAnnotation.objects.create(
                        document=doc_inst,
                        leader=user_objs['leader_user'],
                        decision='ACTION_REQUIRED',
                        annotation_text='ឯកភាព - ជូនការិយាល័យគណនេយ្យ ជ្រើសរើសមន្ត្រី ០២រូប ចូលរួមវគ្គបណ្តុះបណ្តាលនេះ និងធ្វើរបាយការណ៍ជូនខ្ញុំ។'
                    )
                    annot.target_departments.add(depts['ACC'])

                    DocumentRouting.objects.create(
                        document=doc_inst,
                        from_user=user_objs['leader_user'],
                        from_dept=depts['LEAD'],
                        to_dept=depts['ACC'],
                        action_taken="ធ្វើចំណារថ្នាក់ដឹកនាំ",
                        notes="ចាត់ចែងជូនការិយាល័យគណនេយ្យ"
                    )

                # Notification for leader
                Notification.objects.create(
                    recipient=user_objs['leader_user'],
                    document=doc_inst,
                    title=f"ឯកសារថ្មី៖ {doc_inst.registry_number}",
                    message=f"ឯកសារកម្រិត {doc_inst.get_urgency_display()} ត្រូវបានបញ្ជូនមកកាន់តុលោកអ្នក"
                )

        self.stdout.write(self.style.SUCCESS("=== Successfully Seeded DMS Sample Data! ==="))

