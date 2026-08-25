from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Department(models.Model):
    STRUCTURE_CHOICES = [
        ('OLD', 'រចនាសម្ព័ន្ធចាស់ (ការិយាល័យទាំង១០ + ខណ្ឌទាំង២)'),
        ('NEW', 'រចនាសម្ព័ន្ធថ្មី'),
        ('CORE', 'ថ្នាក់ដឹកនាំ/រចនាសម្ព័ន្ធស្នូល'),
    ]

    name_kh = models.CharField(max_length=200, verbose_name="ឈ្មោះការិយាល័យ/អង្គភាព (ខ្មែរ)")
    name_en = models.CharField(max_length=200, blank=True, verbose_name="English Name")
    code = models.CharField(max_length=50, unique=True, verbose_name="កូដលិខិត/លេខកូដ (Dept Code)")
    description = models.TextField(blank=True, verbose_name="ការពណ៌នា")
    structure_type = models.CharField(max_length=20, choices=STRUCTURE_CHOICES, default='OLD', verbose_name="ប្រភេទរចនាសម្ព័ន្ធ")
    is_active = models.BooleanField(default=True, verbose_name="ស្ថានភាពដំណើរការ")
    order_index = models.IntegerField(default=100, verbose_name="លំដាប់លំដោយ")

    class Meta:
        verbose_name = "ការិយាល័យ/អង្គភាព"
        verbose_name_plural = "បញ្ជីការិយាល័យ/អង្គភាព"
        ordering = ['order_index', 'name_kh']

    def __str__(self):
        status_str = "" if self.is_active else " [បិទបណ្ដោះអាសន្ន]"
        return f"{self.name_kh} ({self.code}){status_str}"



class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('LEADERSHIP', 'ថ្នាក់ដឹកនាំ (Leadership)'),
        ('ADMIN', 'ការិយាល័យរដ្ឋបាល (Admin Office)'),
        ('SPECIALIZED', 'ការិយាល័យជំនាញ (Specialized Office)'),
    ]

    POSITION_CHOICES = [
        ('ប្រធានមន្ទីរ', 'ប្រធានមន្ទីរ'),
        ('អនុប្រធានមន្ទីរ', 'អនុប្រធានមន្ទីរ'),
        ('នាយខណ្ឌ', 'នាយខណ្ឌ'),
        ('នាយរងខណ្ឌ', 'នាយរងខណ្ឌ'),
        ('ប្រធានការិយាល័យ', 'ប្រធានការិយាល័យ'),
        ('អនុប្រធានការិយាល័យ', 'អនុប្រធានការិយាល័យ'),
        ('នាយផ្នែក', 'នាយផ្នែក'),
        ('នាយរងផ្នែក', 'នាយរងផ្នែក'),
        ('មន្ត្រី', 'មន្ត្រី'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users', verbose_name="ការិយាល័យ/អង្គភាព")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='SPECIALIZED', verbose_name="តួនាទីសិទ្ធិ")
    position_title = models.CharField(max_length=150, choices=POSITION_CHOICES, default='មន្ត្រី', blank=True, verbose_name="មុខតំណែង")
    phone = models.CharField(max_length=50, blank=True, verbose_name="លេខទូរស័ព្ទ")
    raw_password_display = models.CharField(max_length=255, blank=True, null=True, verbose_name="ពាក្យសម្ងាត់ (សម្រាប់ Admin ពិនិត្យ)")
    is_approved = models.BooleanField(default=False, verbose_name="បានអនុម័តដោយ Admin")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # Granular Feature Permissions (Controlled strictly by ADMIN)
    can_create_document = models.BooleanField(default=True, verbose_name="សិទ្ធិចុះបញ្ជីលិខិត (Create Doc)")
    can_edit_document = models.BooleanField(default=True, verbose_name="សិទ្ធិកែប្រែ/បន្ថែម Version ឯកសារ")
    can_route_document = models.BooleanField(default=True, verbose_name="សិទ្ធិបញ្ជូន/ចាត់ចែងលិខិត (Route Doc)")
    can_annotate = models.BooleanField(default=False, verbose_name="សិទ្ធិផ្តល់ចំណារថ្នាក់ដឹកនាំ (Leadership Annotation)")
    can_complete_document = models.BooleanField(default=False, verbose_name="សិទ្ធិបញ្ចប់លិខិត (Complete Doc)")
    can_delete_document = models.BooleanField(default=False, verbose_name="សិទ្ធិលុបលិខិត (Delete Doc)")
    can_view_reports = models.BooleanField(default=True, verbose_name="សិទ្ធិមើលរបាយការណ៍ & Export Excel")
    can_print = models.BooleanField(default=True, verbose_name="សិទ្ធិបោះពុម្ពប័ណ្ណតាមដាន (Print)")

    class Meta:
        verbose_name = "ព័ត៌មានអ្នកប្រើប្រាស់"
        verbose_name_plural = "បញ្ជីព័ត៌មានអ្នកប្រើប្រាស់"

    def __str__(self):
        dept_str = self.department.code if self.department else 'គ្មាន'
        return f"{self.user.get_full_name() or self.user.username} [{self.get_role_display()}] - {dept_str}"

    @property
    def is_leadership(self):
        return self.role == 'LEADERSHIP'

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_specialized(self):
        return self.role == 'SPECIALIZED'

    def save(self, *args, **kwargs):
        if self.position_title in ['ប្រធានមន្ទីរ', 'អនុប្រធានមន្ទីរ']:
            lead_dept = Department.objects.filter(models.Q(code='LEAD') | models.Q(name_kh='ថ្នាក់ដឹកនាំមន្ទីរ')).first()
            if lead_dept:
                self.department = lead_dept
            self.role = 'LEADERSHIP'
            self.can_annotate = True
        super().save(*args, **kwargs)



class Document(models.Model):
    DOC_TYPE_CHOICES = [
        ('INBOUND', 'លិខិតចូល (Inbound)'),
        ('OUTBOUND', 'លិខិតចេញ (Outbound)'),
        ('INTERNAL', 'លិខិតផ្ទៃក្នុង (Internal)'),
    ]

    URGENCY_CHOICES = [
        ('NORMAL', 'ធម្មតា (Normal)'),
        ('URGENT', 'ប្រញាប់ (Urgent)'),
        ('MOST_URGENT', 'ប្រញាប់បំផុត (Most Urgent)'),
    ]

    SECRECY_CHOICES = [
        ('NORMAL', 'ធម្មតា'),
        ('CONFIDENTIAL', 'សម្ងាត់'),
        ('MOST_CONFIDENTIAL', 'សម្ងាត់បំផុត'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'ព្រាងឯកសារ (Draft)'),
        ('PENDING_ADMIN', 'រង់ចាំរដ្ឋបាលពិនិត្យ (Pending Admin)'),
        ('PENDING_LEADERSHIP', 'រង់ចាំថ្នាក់ដឹកនាំពិនិត្យ/ធ្វើចំណារ (Pending Leadership)'),
        ('ANNOTATED', 'បានធ្វើចំណាររួច (Annotated)'),
        ('ROUTED', 'បានបញ្ជូនទៅការិយាល័យជំនាញ (Routed)'),
        ('IN_PROGRESS', 'កំពុងចាត់ចែង (In Progress)'),
        ('COMPLETED', 'បានចាត់ចែងរួចរាល់ (Completed)'),
        ('REJECTED', 'បដិសេធ/បញ្ជូនត្រឡប់ (Rejected)'),
    ]

    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='OUTBOUND', verbose_name="ប្រភេទលិខិត")
    registry_number = models.CharField(max_length=100, unique=True, verbose_name="លេខចុះលិខិត (Registry Code)")
    title = models.CharField(max_length=500, verbose_name="កម្មវត្ថុ (ចំណងជើងលិខិត)")
    summary = models.TextField(blank=True, verbose_name="សង្ខេបខ្លឹមសារ/បរិយាយ")
    origin_org = models.CharField(max_length=250, blank=True, default='', verbose_name="ប្រភពលិខិត/ផ្ញើមកពីណា")
    destination_org = models.CharField(max_length=250, blank=True, default='', verbose_name="អ្នកទទួល/ផ្ញើទៅណា")
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='NORMAL', verbose_name="កម្រិតប្រញាប់")
    secrecy = models.CharField(max_length=20, choices=SECRECY_CHOICES, default='NORMAL', verbose_name="កម្រិតសម្ងាត់")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='DRAFT', verbose_name="ស្ថានភាពលំហូរ")
    
    issue_date = models.DateField(default=timezone.now, verbose_name="ថ្ងៃខែឆ្នាំលើលិខិត")
    received_date = models.DateField(default=timezone.now, verbose_name="ថ្ងៃខែឆ្នាំ ចុះចូលប្រព័ន្ធ")
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_documents', verbose_name="អ្នកបង្កើត")
    origin_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='originating_documents', verbose_name="ការិយាល័យដើម")
    current_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_documents', verbose_name="កំពុងស្ថិតនៅការិយាល័យ")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_documents', verbose_name="អ្នកទទួលបន្ទុកចាត់ចែង")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ឯកសារ"
        verbose_name_plural = "បញ្ជីឯកសារ"
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.registry_number}] {self.title}"

    @property
    def latest_version(self):
        return self.versions.order_by('-uploaded_at').first()

    @property
    def latest_annotation(self):
        return self.annotations.order_by('-signed_at').first()


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions', verbose_name="ឯកសារ")
    version_number = models.CharField(max_length=20, default='1.0', verbose_name="ជំនាន់ (Version)")
    file = models.FileField(upload_to='documents/%Y/%m/', verbose_name="ឯកសារភ្ជាប់ (PDF/Image)")
    file_name = models.CharField(max_length=255, blank=True, verbose_name="ឈ្មោះស្រាប់")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="អ្នក Upload")
    change_summary = models.TextField(blank=True, verbose_name="ចំណាំនៃការកែប្រែ")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ជំនាន់ឯកសារ"
        verbose_name_plural = "បញ្ជីជំនាន់ឯកសារ"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document.registry_number} - V{self.version_number}"


class LeadershipAnnotation(models.Model):
    DECISION_CHOICES = [
        ('APPROVED', 'ឯកភាព (Approved)'),
        ('ACTION_REQUIRED', 'សូមចាត់ចែង (Please Action)'),
        ('REVIEW', 'សូមពិនិត្យ និងផ្តល់យោបល់ (Please Review)'),
        ('REJECTED', 'បដិសេធ (Rejected)'),
        ('CUSTOM', 'ចំណារផ្សេងៗ (Custom Note)'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='annotations', verbose_name="ឯកសារ")
    leader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ថ្នាក់ដឹកនាំធ្វើចំណារ")
    decision = models.CharField(max_length=30, choices=DECISION_CHOICES, default='ACTION_REQUIRED', verbose_name="ការសម្រេច/ប្រភេទចំណារ")
    annotation_text = models.TextField(verbose_name="ខ្លឹមសារចំណារ")
    target_departments = models.ManyToManyField(Department, related_name='received_annotations', verbose_name="ចាត់ចែងជូនការិយាល័យ")
    signed_at = models.DateTimeField(default=timezone.now, verbose_name="កាលបរិច្ឆេទធ្វើចំណារ")

    class Meta:
        verbose_name = "ចំណារថ្នាក់ដឹកនាំ"
        verbose_name_plural = "បញ្ជីចំណារថ្នាក់ដឹកនាំ"

    def __str__(self):
        return f"ចំណារលើ {self.document.registry_number} ដោយ {self.leader.get_full_name() or self.leader.username}"


class DocumentRouting(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='routings', verbose_name="ឯកសារ")
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_routings', verbose_name="អ្នកបញ្ជូន")
    from_dept = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_dept_routings', verbose_name="ពីការិយាល័យ")
    to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_routings', verbose_name="ទៅកាន់អ្នកទទួល")
    to_dept = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_dept_routings', verbose_name="ទៅកាន់ការិយាល័យ")
    action_taken = models.CharField(max_length=250, verbose_name="សកម្មភាពបញ្ជូន")
    notes = models.TextField(blank=True, verbose_name="ចំណាំ/កត់សម្គាល់")
    is_broadcast = models.BooleanField(default=False, verbose_name="បញ្ជូនទៅគ្រប់ការិយាល័យទាំងអស់ (Broadcast)")
    is_cancelled = models.BooleanField(default=False, verbose_name="បានលុបចោលការបញ្ជូន (Cancelled)")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទលុបចោល")
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_routings', verbose_name="អ្នកលុបចោល")
    cancellation_reason = models.TextField(blank=True, verbose_name="មូលហេតុលុបចោល")
    routed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ប្រវត្តិបញ្ជូនឯកសារ"
        verbose_name_plural = "ប្រវត្តិបញ្ជូនឯកសារ"
        ordering = ['-routed_at']

    def __str__(self):
        return f"{self.document.registry_number}: {self.from_dept} -> {self.to_dept} ({self.action_taken})"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="អ្នកទទួល")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True, verbose_name="ឯកសារពាក់ព័ន្ធ")
    title = models.CharField(max_length=250, verbose_name="ចំណងជើងជូនដំណឹង")
    message = models.TextField(verbose_name="សារ")
    is_read = models.BooleanField(default=False, verbose_name="បានអានរួច")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "សារជូនដំណឹង"
        verbose_name_plural = "បញ្ជីសារជូនដំណឹង"
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"


class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name="អ្នកផ្ញើ")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_messages', verbose_name="ការិយាល័យអ្នកផ្ញើ")
    target_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='incoming_chats', verbose_name="ការិយាល័យគោលដៅ (ទុកទំនេរបើសាធារណៈ)")
    message = models.TextField(verbose_name="ខ្លឹមសារសារ")
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True, verbose_name="ឯកសារភ្ជាប់")
    related_document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_chats', verbose_name="លិខិតពាក់ព័ន្ធ")
    is_edited = models.BooleanField(default=False, verbose_name="បានកែប្រែ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "សារជជែក (Live Chat)"
        verbose_name_plural = "សារជជែកទាំងអស់ (Live Chat)"
        ordering = ['created_at']

    def __str__(self):
        target = self.target_department.name_kh if self.target_department else "បន្ទប់ទូទៅ (All)"
        return f"[{self.created_at.strftime('%H:%M')}] {self.sender.username} -> {target}: {self.message[:30]}"


import random
from datetime import timedelta

class OTPVerification(models.Model):
    PURPOSE_CHOICES = [
        ('REGISTER', 'ចុះឈ្មោះថ្មី (Registration)'),
        ('LOGIN', 'ចូលប្រព័ន្ធ (Login)'),
        ('RESET_PASSWORD', 'ផ្លាស់ប្តូរពាក្យសម្ងាត់ (Reset Password)'),
    ]

    identifier = models.CharField(max_length=150, verbose_name="Email ឬ លេខទូរស័ព្ទ")
    otp_code = models.CharField(max_length=6, verbose_name="លេខកូដ ៦ខ្ទង់")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='REGISTER', verbose_name="គោលបំណង")
    payload_data = models.JSONField(null=True, blank=True, verbose_name="ទិន្នន័យបណ្តោះអាសន្ន")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="ផុតកំណត់នៅពេល")
    is_used = models.BooleanField(default=False, verbose_name="បានប្រើប្រាស់រួច")

    class Meta:
        verbose_name = "ការផ្ទៀងផ្ទាត់ OTP"
        verbose_name_plural = "បញ្ជីផ្ទៀងផ្ទាត់ OTP"
        ordering = ['-created_at']

    def is_valid(self):
        return (not self.is_used) and (timezone.now() <= self.expires_at)

    @classmethod
    def generate_otp(cls, identifier, purpose='REGISTER', payload_data=None, expiry_minutes=10):
        code = f"{random.randint(100000, 999999):06d}"
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        cls.objects.filter(identifier=identifier, purpose=purpose, is_used=False).update(is_used=True)
        return cls.objects.create(
            identifier=identifier,
            otp_code=code,
            purpose=purpose,
            payload_data=payload_data,
            expires_at=expires_at
        )

    def __str__(self):
        return f"OTP {self.otp_code} for {self.identifier} ({self.purpose})"


# =========================================================================
# 👤 ម៉ូឌុលគ្រប់គ្រងជីវប្រវត្តិមន្ត្រីរាជការ (Civil Servant Profile / HR)
# រៀបចំតាមស្តង់ដារផ្លូវការ ក- ព័ត៌មានផ្ទាល់ខ្លួន ដល់ ឆ/ជ- ការលើកសរសើរ/ពិន័យ
# =========================================================================
KHMER_DIGITS_MAP = str.maketrans('០១២៣៤៥៦៧៨៩', '0123456789')

def to_arabic_digits(text):
    """
    Converts Khmer digits (០១២៣៤៥៦៧៨៩) to Arabic/French numerals (0123456789).
    Example: ១៨០០៣០០១០៦ -> 1800300106
    """
    if not text:
        return ""
    return str(text).translate(KHMER_DIGITS_MAP).strip()

def normalize_khmer_role(role_text):
    if not role_text:
        return ""
    t = str(role_text).strip()
    t = t.replace('មន្រ្តី', 'មន្ត្រី').replace('មន្រ្ដី', 'មន្ត្រី')
    return t

def get_position_sort_weight(title):
    """
    Computes priority weight for Cambodian Civil Service positions (10 = highest to 95 = lowest):
    - 10: ប្រធានមន្ទីរ (Director)
    - 20: អនុប្រធានមន្ទីរ (Deputy Director)
    - 25: នាយក / នាយករង
    - 30: នាយខណ្ឌ / ប្រធានស្ថាប័នប្រតិបត្តិ
    - 35: នាយរងខណ្ឌ / អនុប្រធានប្រតិបត្តិ
    - 40: ប្រធានការិយាល័យ (Head of Office)
    - 50: អនុប្រធានការិយាល័យ (Deputy Head of Office)
    - 60: នាយផ្នែក / ប្រធានផ្នែក / ប្រធានក្រុម (Section/Team Chief)
    - 70: នាយរងផ្នែក / អនុប្រធានផ្នែក / អនុប្រធានក្រុម
    - 80: មន្ត្រី / មន្ត្រីជំនាញ / មន្ត្រីបច្ចេកទេស (Officer)
    - 90: មន្ត្រីជាប់កិច្ចសន្យា / ភ្នាក់ងារ
    - 95: ផ្សេងៗ
    """
    if not title:
        return 99
    t = normalize_khmer_role(title)
    if 'ប្រធានមន្ទីរ' in t and 'អនុ' not in t:
        return 10
    elif 'អនុប្រធានមន្ទីរ' in t:
        return 20
    elif 'នាយក' in t and 'នាយករង' not in t and 'អនុ' not in t:
        return 25
    elif 'នាយករង' in t or 'អនុប្រធាននាយកដ្ឋាន' in t:
        return 26
    elif ('នាយខណ្ឌ' in t or 'នាយកដ្ឋាន' in t) and 'នាយរង' not in t and 'អនុ' not in t:
        return 30
    elif 'នាយរងខណ្ឌ' in t:
        return 35
    elif 'ប្រធានការិយាល័យ' in t and 'អនុ' not in t:
        return 40
    elif 'អនុប្រធានការិយាល័យ' in t:
        return 50
    elif 'នាយផ្នែក' in t or 'ប្រធានផ្នែក' in t or 'ប្រធានក្រុម' in t:
        return 60
    elif 'នាយរងផ្នែក' in t or 'អនុប្រធានផ្នែក' in t or 'អនុប្រធានក្រុម' in t:
        return 70
    elif 'មន្ត្រី' in t:
        return 80
    elif 'កិច្ចសន្យា' in t or 'ភ្នាក់ងារ' in t:
        return 90
    return 95

def get_rank_step_sort_weight(rank_str):
    """
    Computes priority weight for Cambodian Civil Service Ranks & Steps (from Category A down to D, higher step to lower step):
    - Cat A: ក្របខ័ណ្ឌ ក (ឧត្តមមន្ត្រី) -> Weight 1
    - Cat B: ក្របខ័ណ្ឌ ខ (វរមន្ត្រី) -> Weight 2
    - Cat C: ក្របខ័ណ្ឌ គ (អនុមន្ត្រី/នាយ) -> Weight 3
    - Cat D: ក្របខ័ណ្ឌ ឃ (មន្ត្រី/ជំនួយការ) -> Weight 4
    """
    if not rank_str:
        return (99, 99, 99)
    s = str(rank_str).strip()
    cat_w = 99
    if 'ក' in s or 'A' in s.upper() or 'ឧត្តម' in s:
        cat_w = 1
    elif 'ខ' in s or 'B' in s.upper() or 'វរ' in s:
        cat_w = 2
    elif 'គ' in s or 'C' in s.upper() or 'អនុ' in s:
        cat_w = 3
    elif 'ឃ' in s or 'D' in s.upper():
        cat_w = 4

    KHMER_NUM_MAP = str.maketrans('០១២៣៤៥៦៧៨៩', '0123456789')
    s_ar = s.translate(KHMER_NUM_MAP)
    import re
    nums = [int(n) for n in re.findall(r'\d+', s_ar)]
    level = nums[0] if len(nums) > 0 else 99
    step = nums[1] if len(nums) > 1 else 99
    return (cat_w, level, step)

def get_department_sort_weight(dept):
    if not dept:
        return (999, "zzz_គ្មានការិយាល័យ")
    name = dept.name_kh or ""
    order = getattr(dept, 'order_index', 100)
    return (order, name)


def officer_sort_key(o):
    dept_w = get_department_sort_weight(o.department)
    pos_w = get_position_sort_weight(o.current_position_title)
    rank_w = get_rank_step_sort_weight(o.current_rank_and_step)
    name_kh = f"{o.khmer_last_name} {o.khmer_first_name}".strip()
    return (dept_w, pos_w, rank_w, name_kh)


class CivilServantProfile(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'ប្រុស'),
        ('FEMALE', 'ស្រី'),
    ]
    MARITAL_CHOICES = [
        ('SINGLE', 'នៅលីវ'),
        ('MARRIED', 'រៀបការហើយ'),
        ('DIVORCED', 'មេម៉ាយ/ពោះម៉ាយ'),
    ]

    # Links
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='civil_servant_profiles', verbose_name="គណនីប្រព័ន្ធ (ប្រសិនបើមាន)")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='officers', verbose_name="ការិយាល័យ/អង្គភាពបច្ចុប្បន្ន")

    # ==========================================
    # ក- ព័ត៌មានផ្ទាល់ខ្លួន (Personal Information)
    # ==========================================
    photo = models.ImageField(upload_to='officers/photos/%Y/', null=True, blank=True, verbose_name="រូបថត 4x6")
    khmer_last_name = models.CharField(max_length=100, verbose_name="គោត្តនាម (ខ្មែរ)")
    khmer_first_name = models.CharField(max_length=100, verbose_name="នាមខ្លួន (ខ្មែរ)")
    latin_last_name = models.CharField(max_length=100, blank=True, verbose_name="គោត្តនាម (ឡាតាំង)")
    latin_first_name = models.CharField(max_length=100, blank=True, verbose_name="នាមខ្លួន (ឡាតាំង)")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE', verbose_name="ភេទ")
    dob = models.CharField(max_length=150, blank=True, verbose_name="ថ្ងៃខែឆ្នាំកំណើត")
    ethnicity = models.CharField(max_length=50, default='ខ្មែរ', verbose_name="ជនជាតិ")
    nationality = models.CharField(max_length=50, default='ខ្មែរ', verbose_name="សញ្ជាតិ")

    # ទីកន្លែងកំណើត
    pob_province_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដរាជធានី/ខេត្តកំណើត")
    pob_district_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដស្រុក/ខណ្ឌកំណើត")
    pob_commune_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដឃុំ/សង្កាត់កំណើត")
    pob_village_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដភូមិកំណើត")
    pob_village = models.CharField(max_length=100, blank=True, verbose_name="ភូមិកំណើត")
    pob_commune = models.CharField(max_length=100, blank=True, verbose_name="ឃុំ/សង្កាត់កំណើត")
    pob_district = models.CharField(max_length=100, blank=True, verbose_name="ស្រុក/ខណ្ឌកំណើត")
    pob_province = models.CharField(max_length=100, blank=True, verbose_name="រាជធានី/ខេត្តកំណើត")

    # អាសយដ្ឋានបច្ចុប្បន្ន
    current_province_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដរាជធានី/ខេត្តបច្ចុប្បន្ន")
    current_district_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដស្រុក/ខណ្ឌបច្ចុប្បន្ន")
    current_commune_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដឃុំ/សង្កាត់បច្ចុប្បន្ន")
    current_village_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដភូមិបច្ចុប្បន្ន")
    current_house_no = models.CharField(max_length=50, blank=True, verbose_name="ផ្ទះលេខ (បច្ចុប្បន្ន)")
    current_street = models.CharField(max_length=100, blank=True, verbose_name="ផ្លូវ (បច្ចុប្បន្ន)")
    current_village = models.CharField(max_length=100, blank=True, verbose_name="ភូមិ (បច្ចុប្បន្ន)")
    current_commune = models.CharField(max_length=100, blank=True, verbose_name="ឃុំ/សង្កាត់ (បច្ចុប្បន្ន)")
    current_district = models.CharField(max_length=100, blank=True, verbose_name="ស្រុក/ខណ្ឌ (បច្ចុប្បន្ន)")
    current_province = models.CharField(max_length=100, blank=True, verbose_name="រាជធានី/ខេត្ត (បច្ចុប្បន្ន)")

    # អាសយដ្ឋានអចិន្ត្រៃយ៍
    perm_same_as_current = models.BooleanField(default=True, verbose_name="ដូចអាសយដ្ឋានបច្ចុប្បន្ន")
    perm_province_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដរាជធានី/ខេត្តអចិន្ត្រៃយ៍")
    perm_district_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដស្រុក/ខណ្ឌអចិន្ត្រៃយ៍")
    perm_commune_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដឃុំ/សង្កាត់អចិន្ត្រៃយ៍")
    perm_village_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដភូមិអចិន្ត្រៃយ៍")
    perm_house_no = models.CharField(max_length=50, blank=True, verbose_name="ផ្ទះលេខ (អចិន្ត្រៃយ៍)")
    perm_street = models.CharField(max_length=100, blank=True, verbose_name="ផ្លូវ (អចិន្ត្រៃយ៍)")
    perm_village = models.CharField(max_length=100, blank=True, verbose_name="ភូមិ (អចិន្ត្រៃយ៍)")
    perm_commune = models.CharField(max_length=100, blank=True, verbose_name="ឃុំ/សង្កាត់ (អចិន្ត្រៃយ៍)")
    perm_district = models.CharField(max_length=100, blank=True, verbose_name="ស្រុក/ខណ្ឌ (អចិន្ត្រៃយ៍)")
    perm_province = models.CharField(max_length=100, blank=True, verbose_name="រាជធានី/ខេត្ត (អចិន្ត្រៃយ៍)")

    phone = models.CharField(max_length=100, blank=True, verbose_name="លេខទូរស័ព្ទ")
    email = models.EmailField(blank=True, verbose_name="អ៊ីម៉ែល")
    officer_id_number = models.CharField(max_length=50, blank=True, verbose_name="អត្តលេខមន្ត្រីរាជការ")
    national_id_number = models.CharField(max_length=50, blank=True, verbose_name="លេខអត្តសញ្ញាណប័ណ្ណសញ្ជាតិខ្មែរ")
    national_id_valid_from = models.CharField(max_length=100, blank=True, verbose_name="សុពលភាពអត្តសញ្ញាណប័ណ្ណ ចាប់ពីថ្ងៃ")
    national_id_valid_to = models.CharField(max_length=100, blank=True, verbose_name="សុពលភាពអត្តសញ្ញាណប័ណ្ណ ដល់ថ្ងៃ")
    physical_condition = models.CharField(max_length=50, default='គ្រប់គ្រាន់', verbose_name="កាយសម្បទា")
    disability_detail = models.CharField(max_length=200, blank=True, verbose_name="ប្រភេទពិការភាព (ប្រសិនបើមាន)")

    # ==========================================
    # ខ- ព័ត៌មានគ្រួសារ (Family Information)
    # ==========================================
    marital_status = models.CharField(max_length=20, choices=MARITAL_CHOICES, default='SINGLE', verbose_name="ស្ថានភាពគ្រួសារ")

    # ខ.១- ព័ត៌មានប្រពន្ធឬប្តី
    spouse_marriage_cert_no = models.CharField(max_length=100, blank=True, verbose_name="លេខសំបុត្រអាពាហ៍ពិពាហ៍")
    spouse_name_kh = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះប្រពន្ធឬប្តី (ខ្មែរ)")
    spouse_is_alive = models.BooleanField(default=True, verbose_name="ប្តី/ប្រពន្ធ រស់/ស្លាប់")
    spouse_name_latin = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះជាអក្សរពុម្ពឡាតាំង")
    spouse_dob = models.CharField(max_length=150, blank=True, verbose_name="ថ្ងៃខែឆ្នាំកំណើតប្តី/ប្រពន្ធ")
    spouse_national_id = models.CharField(max_length=100, blank=True, verbose_name="លេខអត្តសញ្ញាណប័ណ្ណប្តី/ប្រពន្ធ")
    spouse_pob = models.CharField(max_length=255, blank=True, verbose_name="ទីកន្លែងកំណើតប្តី/ប្រពន្ធ")
    spouse_occupation = models.CharField(max_length=150, blank=True, verbose_name="មុខរបរបច្ចុប្បន្នប្តី/ប្រពន្ធ")
    spouse_current_address = models.CharField(max_length=255, blank=True, verbose_name="អាសយដ្ឋានបច្ចុប្បន្នប្តី/ប្រពន្ធ")
    spouse_organization = models.CharField(max_length=200, blank=True, verbose_name="ឈ្មោះអង្គភាពបម្រើការងារ")

    # ខ.២- ព័ត៌មានកូន (JSON List: [{ 'name': '', 'gender': '', 'dob': '', 'occupation': '' }])
    children_data = models.JSONField(default=list, blank=True, verbose_name="បញ្ជីព័ត៌មានកូនៗ")

    # ខ.៣- ព័ត៌មានឪពុក និងម្តាយបង្កើត
    father_name = models.CharField(max_length=150, blank=True, verbose_name="ឪពុកឈ្មោះ")
    father_is_alive = models.BooleanField(default=True, verbose_name="ឪពុករស់/ស្លាប់")
    father_pob = models.CharField(max_length=255, blank=True, verbose_name="ទីកន្លែងកំណើតឪពុក")
    father_occupation = models.CharField(max_length=150, blank=True, verbose_name="មុខរបរបច្ចុប្បន្នឪពុក")

    mother_name = models.CharField(max_length=150, blank=True, verbose_name="ម្តាយឈ្មោះ")
    mother_is_alive = models.BooleanField(default=True, verbose_name="ម្តាយរស់/ស្លាប់")
    mother_pob = models.CharField(max_length=255, blank=True, verbose_name="ទីកន្លែងកំណើតម្តាយ")
    mother_occupation = models.CharField(max_length=150, blank=True, verbose_name="មុខរបរបច្ចុប្បន្នម្តាយ")

    # ==========================================
    # គ- ព័ត៌មានទំនាក់ទំនងក្នុងករណីមានអាសន្ន
    # ==========================================
    emergency_last_name = models.CharField(max_length=100, blank=True, verbose_name="គោត្តនាមអ្នកទាក់ទងអាសន្ន")
    emergency_first_name = models.CharField(max_length=100, blank=True, verbose_name="នាមខ្លួនអ្នកទាក់ទងអាសន្ន")
    emergency_gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='FEMALE', blank=True, verbose_name="ភេទអ្នកទាក់ទង")
    emergency_relationship = models.CharField(max_length=100, blank=True, verbose_name="ទំនាក់ទំនងត្រូវជា")
    emergency_occupation = models.CharField(max_length=150, blank=True, verbose_name="មុខរបរអ្នកទាក់ទងអាសន្ន")
    emergency_address = models.CharField(max_length=255, blank=True, verbose_name="អាសយដ្ឋានអ្នកទាក់ទងអាសន្ន")
    emergency_phone = models.CharField(max_length=100, blank=True, verbose_name="លេខទូរស័ព្ទអាសន្ន")
    emergency_email = models.CharField(max_length=100, blank=True, verbose_name="អ៊ីម៉ែលអាសន្ន")

    # ==========================================
    # ឃ- កម្រិតវប្បធម៌ ការបណ្តុះបណ្តាលមុខវិជ្ជាជីវៈ និងការបណ្តុះបណ្តាលបន្ត
    # ==========================================
    # JSON List: [{ 'level_type': 'GENERAL|VOCATIONAL|CONTINUOUS', 'level_label': '', 'school': '', 'location': '', 'degree': '', 'skill': '', 'start_date': '', 'end_date': '' }]
    education_data = models.JSONField(default=list, blank=True, verbose_name="ប្រវត្តិការសិក្សា និងបណ្តុះបណ្តាល")

    # ==========================================
    # ង- ភាសាបរទេស
    # ==========================================
    # JSON List: [{ 'language': 'អង់គ្លេស', 'reading': 'ល្អ', 'speaking': 'មធ្យម', 'writing': 'មធ្យម' }]
    languages_data = models.JSONField(default=list, blank=True, verbose_name="កម្រិតភាសាបរទេស")

    # ==========================================
    # ច- ក្របខ័ណ្ឌការងារ
    # ==========================================
    civil_service_start_date = models.CharField(max_length=100, blank=True, verbose_name="ថ្ងៃខែឆ្នាំចូលបម្រើក្របខ័ណ្ឌរដ្ឋ")
    civil_service_permanent_date = models.CharField(max_length=100, blank=True, verbose_name="ថ្ងៃខែឆ្នាំតាំងស៊ប់ក្នុងក្របខ័ណ្ឌរដ្ឋ")
    framework_name = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះក្របខ័ណ្ឌ")
    current_rank_and_step = models.CharField(max_length=150, blank=True, verbose_name="ក្របខណ្ឌ ឋានន្តរស័ក្តិ និងថ្នាក់បច្ចុប្បន្ន")
    current_position_title = models.CharField(max_length=150, blank=True, verbose_name="មុខតំណែងបច្ចុប្បន្ន")
    position_code = models.CharField(max_length=50, blank=True, verbose_name="កូដមុខតំណែង / Code ID")

    POSITION_CODE_MAP = {
        'ប្រធានមន្ទីរ': 'DIR-01',
        'អនុប្រធានមន្ទីរ': 'DDIR-02',
        'នាយខណ្ឌ': 'CANTON-03',
        'នាយរងខណ្ឌ': 'DCANTON-04',
        'ប្រធានការិយាល័យ': 'CHIEF-05',
        'អនុប្រធានការិយាល័យ': 'DCHIEF-06',
        'នាយផ្នែក': 'SEC-07',
        'នាយរងផ្នែក': 'DSEC-08',
        'មន្ត្រី': 'OFF-09',
    }

    def get_auto_position_code(self):
        if self.position_code:
            return self.position_code
        return self.POSITION_CODE_MAP.get(self.current_position_title, '')

    # ==========================================
    # ឆ- មុខតំណែង និងប្រវត្តិការងារ
    # ==========================================
    # ឆ.១.១- ក្នុងវិស័យសាធារណៈ: [{ 'start_date': '', 'end_date': '', 'ministry': '', 'department': '', 'position': '', 'skill': '' }]
    history_public_sector = models.JSONField(default=list, blank=True, verbose_name="ប្រវត្តិការងារក្នុងវិស័យសាធារណៈ")

    # ឆ.១.២- ក្នុងវិស័យឯកជន: [{ 'start_date': '', 'end_date': '', 'org': '', 'role': '', 'skill': '' }]
    history_private_sector = models.JSONField(default=list, blank=True, verbose_name="ប្រវត្តិការងារក្នុងវិស័យឯកជន")

    # ឆ.២- ការដំឡើងឋានន្តរស័ក្តិ និងថ្នាក់តាមវេនជ្រើសរើស/អតីតភាព/ប្រឡង: [{ 'effective_date': '', 'ministry': '', 'department': '', 'office': '', 'old_rank_step': '', 'new_rank_step': '', 'promo_type': '' }]
    promotions_by_seniority = models.JSONField(default=list, blank=True, verbose_name="ការដំឡើងថ្នាក់តាមវេនជ្រើសរើស/អតីតភាព")

    # ឆ.៣- ការដំឡើងឋានន្តរស័ក្តិ និងថ្នាក់តាមសញ្ញាបត្រ: [{ 'effective_date': '', 'school': '', 'location': '', 'degree': '', 'old_rank_step': '', 'new_rank_step': '' }]
    promotions_by_degree = models.JSONField(default=list, blank=True, verbose_name="ការដំឡើងថ្នាក់តាមសញ្ញាបត្រ")

    # ឆ.៤- ស្ថានភាពស្ថិតនៅក្រៅក្របខ័ណ្ឌដើម: [{ 'start_date': '', 'end_date': '', 'ministry': '', 'position': '' }]
    outside_framework_status = models.JSONField(default=list, blank=True, verbose_name="ស្ថានភាពក្រៅក្របខ័ណ្ឌដើម")

    # ឆ.៥- ស្ថានភាពស្ថិតក្នុងភាពទំនេរគ្មានបៀវត្ស: [{ 'start_date': '', 'end_date': '', 'ministry': '', 'duration': '' }]
    unpaid_leave_status = models.JSONField(default=list, blank=True, verbose_name="ភាពទំនេរគ្មានបៀវត្ស")

    # ==========================================
    # ជ- ការលើកសរសើរ ឬទណ្ឌកម្មវិន័យ
    # ==========================================
    # ជ.១- ការលើកសរសើរ: [{ 'doc_number': '', 'date': '', 'ministry': '', 'description': '', 'type': '' }]
    awards_data = models.JSONField(default=list, blank=True, verbose_name="ការលើកសរសើរ (មេដាយ/គ្រឿងឥស្សរិយយស)")

    # ជ.២- ការដាក់ពិន័យ: [{ 'doc_number': '', 'date': '', 'ministry': '', 'description': '', 'type': '' }]
    sanctions_data = models.JSONField(default=list, blank=True, verbose_name="ការដាក់ពិន័យ/ទណ្ឌកម្មវិន័យ")

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_officer_profiles', verbose_name="អ្នកបញ្ចូល")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ជីវប្រវត្តិមន្ត្រីរាជការ"
        verbose_name_plural = "បញ្ជីជីវប្រវត្តិមន្ត្រីរាជការ"
        ordering = ['department', 'khmer_last_name', 'khmer_first_name']

    def __str__(self):
        return f"{self.khmer_last_name} {self.khmer_first_name} ({self.officer_id_number or 'គ្មានអត្តលេខ'}) - {self.department.name_kh if self.department else 'គ្មានការិយាល័យ'}"

    @property
    def full_name_kh(self):
        return f"{self.khmer_last_name} {self.khmer_first_name}".strip()

    @property
    def full_name_latin(self):
        return f"{self.latin_last_name} {self.latin_first_name}".strip().upper()

    @property
    def position_sort_weight(self):
        return get_position_sort_weight(self.current_position_title)

    @property
    def rank_sort_weight(self):
        return get_rank_step_sort_weight(self.current_rank_and_step)

    @property
    def is_leadership_position(self):
        return self.current_position_title in ['ប្រធានមន្ទីរ', 'អនុប្រធានមន្ទីរ']

    @property
    def get_display_department(self):
        if self.is_leadership_position or (self.department and (self.department.code == 'LEAD' or 'ថ្នាក់ដឹកនាំ' in self.department.name_kh)):
            lead_dept = Department.objects.filter(models.Q(code='LEAD') | models.Q(name_kh='ថ្នាក់ដឹកនាំមន្ទីរ')).first()
            return lead_dept or self.department
        return self.department

    @property
    def display_department_name(self):
        dept = self.get_display_department
        if dept and hasattr(dept, 'name_kh') and dept.name_kh:
            return dept.name_kh
        if self.department and hasattr(self.department, 'name_kh') and self.department.name_kh:
            return self.department.name_kh
        return "មិនទាន់ចាត់តាំង"

    def save(self, *args, **kwargs):
        # Auto-convert officer_id_number, national_id_number, phone from Khmer to Arabic numerals
        if self.officer_id_number:
            self.officer_id_number = to_arabic_digits(self.officer_id_number)
        if self.national_id_number:
            self.national_id_number = to_arabic_digits(self.national_id_number)
        if self.phone:
            self.phone = to_arabic_digits(self.phone)

        # Auto-assign 'ថ្នាក់ដឹកនាំមន្ទីរ' for 'ប្រធានមន្ទីរ' and 'អនុប្រធានមន្ទីរ'
        if self.is_leadership_position or (self.department and (self.department.code == 'LEAD' or 'ថ្នាក់ដឹកនាំ' in self.department.name_kh)):
            lead_dept = Department.objects.filter(models.Q(code='LEAD') | models.Q(name_kh='ថ្នាក់ដឹកនាំមន្ទីរ')).first()
            if lead_dept:
                self.department = lead_dept

        super().save(*args, **kwargs)

    @property
    def current_address_full(self):
        parts = []
        if self.current_house_no: parts.append(f"#{self.current_house_no}")
        if self.current_street: parts.append(f"ផ្លូវ {self.current_street}")
        if self.current_village: parts.append(f"ភូមិ {self.current_village}")
        if self.current_commune: parts.append(f"ឃុំ/សង្កាត់ {self.current_commune}")
        if self.current_district: parts.append(f"ស្រុក/ខណ្ឌ {self.current_district}")
        if self.current_province: parts.append(f"រាជធានី/ខេត្ត {self.current_province}")
        return " ".join(parts) or "មិនទាន់បញ្ជាក់"

    @property
    def perm_address_full(self):
        if self.perm_same_as_current:
            return self.current_address_full
        parts = []
        if self.perm_house_no: parts.append(f"#{self.perm_house_no}")
        if self.perm_street: parts.append(f"ផ្លូវ {self.perm_street}")
        if self.perm_village: parts.append(f"ភូមិ {self.perm_village}")
        if self.perm_commune: parts.append(f"ឃុំ/សង្កាត់ {self.perm_commune}")
        if self.perm_district: parts.append(f"ស្រុក/ខណ្ឌ {self.perm_district}")
        if self.perm_province: parts.append(f"រាជធានី/ខេត្ត {self.perm_province}")
        return " ".join(parts) or "មិនទាន់បញ្ជាក់"

    @property
    def pob_full(self):
        parts = []
        if self.pob_village: parts.append(f"ភូមិ {self.pob_village}")
        if self.pob_commune: parts.append(f"ឃុំ/សង្កាត់ {self.pob_commune}")
        if self.pob_district: parts.append(f"ស្រុក/ខណ្ឌ {self.pob_district}")
        if self.pob_province: parts.append(f"រាជធានី/ខេត្ត {self.pob_province}")
        return " ".join(parts) or "មិនទាន់បញ្ជាក់"


class OfficerAttachment(models.Model):
    """
    ឯកសារយោង និងភស្តុតាងភ្ជាប់ជាមួយជីវប្រវត្តិមន្ត្រីរាជការ
    បែងចែកតាមមុខងារ/ផ្នែកនីមួយៗ (ក ដល់ ជ)
    """
    CATEGORY_CHOICES = [
        ('PERSONAL', 'ក- ឯកសារអត្តសញ្ញាណ និងផ្ទាល់ខ្លួន (ID/Birth/Family Book)'),
        ('FAMILY', 'ខ- សំបុត្រអាពាហ៍ពិពាហ៍ និងគ្រួសារ (Marriage/Children)'),
        ('EDUCATION', 'ឃ- សញ្ញាបត្រ និងវិញ្ញាបនបត្របណ្តុះបណ្តាល (Degrees/Certificates)'),
        ('APPOINTMENT', 'ច- ព្រះរាជក្រឹត្យ អនុក្រឹត្យ និងប្រកាសតាំងស៊ប់/តែងតាំង (Decrees/Prakas)'),
        ('PROMOTION', 'ឆ- លិខិតដំឡើងឋានន្តរស័ក្តិ និងថ្នាក់ (Promotions)'),
        ('AWARD', 'ជ- ព្រះរាជក្រឹត្យគ្រឿងឥស្សរិយយស មេដាយ និងប័ណ្ណសរសើរ (Awards/Medals)'),
        ('OTHER', 'ឯកសារយោងផ្សេងៗ (Other Reference Documents)'),
    ]

    officer = models.ForeignKey(CivilServantProfile, on_delete=models.CASCADE, related_name='attachments', verbose_name="មន្ត្រីរាជការ")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='OTHER', verbose_name="ប្រភេទឯកសារយោង")
    title = models.CharField(max_length=255, verbose_name="ចំណងជើង/ឈ្មោះឯកសារ")
    doc_number = models.CharField(max_length=150, blank=True, verbose_name="លេខលិខិត/ឯកសារ")
    issued_date = models.CharField(max_length=100, blank=True, verbose_name="កាលបរិច្ឆេទចេញលិខិត")
    file = models.FileField(upload_to='officer_attachments/%Y/%m/', verbose_name="ឯកសារភ្ជាប់")
    file_size = models.PositiveIntegerField(default=0, verbose_name="ទំហំឯកសារ (Bytes)")
    description = models.TextField(blank=True, verbose_name="ការពិពណ៌នា/កំណត់ចំណាំ")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="អ្នកបញ្ចូល")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ឯកសារយោងមន្ត្រីរាជការ"
        verbose_name_plural = "ឯកសារយោងមន្ត្រីរាជការ"
        ordering = ['category', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()}) - {self.officer.full_name_kh}"

    @property
    def file_extension(self):
        import os
        return os.path.splitext(self.file.name)[1].lower()

    @property
    def is_pdf(self):
        return self.file_extension == '.pdf'

    @property
    def is_image(self):
        return self.file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    @property
    def formatted_file_size(self):
        size = self.file_size or (self.file.size if self.file else 0)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"


class OfficerAuditLog(models.Model):
    """
    កំណត់ត្រាសកម្មភាពលើជីវប្រវត្តិ និងឯកសារយោងមន្ត្រីរាជការ
    គ្រប់ការ បញ្ចូល មើល កែប្រែ និងលុប ត្រូវបាន Record ទុកសម្រាប់ ADMIN ត្រួតពិនិត្យ
    """
    ACTION_CHOICES = [
        ('UPLOAD', 'បញ្ចូលឯកសារយោងថ្មី'),
        ('VIEW', 'មើល/ទាញយកឯកសារយោង'),
        ('EDIT', 'កែប្រែ/ប្តូរឯកសារយោង'),
        ('DELETE', 'លុបឯកសារយោង'),
        ('PROFILE_CREATE', 'បញ្ចូលជីវប្រវត្តិមន្ត្រីថ្មី'),
        ('PROFILE_EDIT', 'កែប្រែជីវប្រវត្តិមន្ត្រី'),
        ('PROFILE_DELETE', 'លុបជីវប្រវត្តិមន្ត្រី'),
        ('PROFILE_BULK_DELETE', 'លុបជីវប្រវត្តិមន្ត្រីជាក្រុម/ទាំងអស់'),
        ('SETTING_UPDATE', 'កែប្រែកាលវិភាគ/ការកំណត់'),
    ]

    officer = models.ForeignKey(CivilServantProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs', verbose_name="មន្ត្រីរាជការ")
    officer_name_cache = models.CharField(max_length=200, blank=True, verbose_name="ឈ្មោះមន្ត្រី (Snapshot)")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="អ្នកធ្វើសកម្មភាព")
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name="ប្រភេទសកម្មភាព")
    attachment_title = models.CharField(max_length=255, blank=True, verbose_name="ឈ្មោះឯកសារ")
    category = models.CharField(max_length=100, blank=True, verbose_name="ផ្នែក/មុខងារ")
    details = models.TextField(blank=True, verbose_name="ព័ត៌មានលម្អិត")
    ip_address = models.CharField(max_length=50, blank=True, verbose_name="IP Address")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទ-ម៉ោង")

    class Meta:
        verbose_name = "កំណត់ត្រាសកម្មភាពមន្ត្រី"
        verbose_name_plural = "កំណត់ត្រាសកម្មភាពមន្ត្រី (Audit Logs)"
        ordering = ['-timestamp']

    def __str__(self):
        user_name = self.user.username if self.user else 'ប្រព័ន្ធ'
        off_name = self.officer.full_name_kh if self.officer else (self.officer_name_cache or 'មន្ត្រីត្រូវបានលុប')
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {user_name} - {self.get_action_type_display()} ({off_name})"


class OfficerDepartmentTransferHistory(models.Model):
    """
    ប្រវត្តិនៃការផ្លាស់ប្តូរការិយាល័យ/ខណ្ឌ របស់មន្ត្រីរាជការ (Civil Servant Department/Canton Transfer History)
    """
    officer = models.ForeignKey(
        CivilServantProfile,
        on_delete=models.CASCADE,
        related_name='department_transfers',
        verbose_name="មន្ត្រីរាជការ"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='officer_transfers_from',
        verbose_name="ពីការិយាល័យ/ខណ្ឌ"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='officer_transfers_to',
        verbose_name="ទៅការិយាល័យ/ខណ្ឌថ្មី"
    )
    from_position_title = models.CharField(max_length=150, blank=True, verbose_name="មុខតំណែងចាស់")
    to_position_title = models.CharField(max_length=150, blank=True, verbose_name="មុខតំណែងថ្មី")
    transfer_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទផ្ទេរ/ចូលកាន់តំណែង")
    reference_letter_number = models.CharField(max_length=150, blank=True, verbose_name="លេខលិខិតផ្ទេរ/ចាត់តាំង")
    transfer_document = models.FileField(
        upload_to='officers/transfers/%Y/',
        null=True,
        blank=True,
        verbose_name="ឯកសារលិខិតផ្ទេរ (PDF/រូបភាព)"
    )
    remarks = models.TextField(blank=True, verbose_name="មូលហេតុ/កំណត់សម្គាល់បន្ថែម")
    transferred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_officer_transfers',
        verbose_name="អ្នកធ្វើការផ្លាស់ប្តូរ (Admin)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទកត់ត្រា")

    class Meta:
        verbose_name = "ប្រវត្តិផ្លាស់ប្តូរការិយាល័យមន្ត្រីរាជការ"
        verbose_name_plural = "បញ្ជីប្រវត្តិផ្លាស់ប្តូរការិយាល័យមន្ត្រីរាជការ"
        ordering = ['-transfer_date', '-created_at']

    def __str__(self):
        from_d = self.from_department.name_kh if self.from_department else "គ្មាន"
        to_d = self.to_department.name_kh if self.to_department else "គ្មាន"
        return f"{self.officer.full_name_kh}: {from_d} ➔ {to_d}"


class OfficerEditWindowSetting(models.Model):
    """
    ការកំណត់កាលវិភាគបើក/បិទការកែប្រែ និងបញ្ចូលជីវប្រវត្តិមន្ត្រីសម្រាប់គ្រប់ការិយាល័យជំនាញ
    (គ្រប់គ្រងផ្ដាច់មុខដោយ ADMIN)
    """
    is_active = models.BooleanField(default=True, verbose_name="បើកដំណើរការកាលវិភាគ (Enable Window)")
    start_datetime = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទ & ម៉ោង ចាប់ផ្តើម")
    end_datetime = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទ & ម៉ោង បញ្ចប់ (Deadline)")
    title = models.CharField(max_length=255, default="កាលវិភាគកែប្រែ និងបញ្ចូលជីវប្រវត្តិមន្ត្រី", verbose_name="ចំណងជើងកាលវិភាគ")
    instruction_note = models.TextField(blank=True, default="សូមគ្រប់ការិយាល័យជំនាញទាំងអស់ មេត្តារួសរាន់បញ្ចូល និងកែសម្រួលព័ត៌មានជីវប្រវត្តិមន្ត្រីឱ្យបានទាន់ពេលវេលាកំណត់។", verbose_name="សេចក្តីណែនាំ/សារជូនដំណឹង")
    allow_specialized_edit = models.BooleanField(default=True, verbose_name="អនុញ្ញាតឱ្យការិយាល័យជំនាញកែប្រែ/បញ្ចូល")
    allowed_departments = models.ManyToManyField(Department, blank=True, related_name='edit_window_settings', verbose_name="ការិយាល័យដែលអនុញ្ញាត (ទុកទទេ = គ្រប់ការិយាល័យទាំងអស់)")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="កែប្រែចុងក្រោយដោយ")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="កាលបរិច្ឆេទកែប្រែចុងក្រោយ")

    class Meta:
        verbose_name = "ការកំណត់កាលវិភាគកែប្រែជីវប្រវត្តិ"
        verbose_name_plural = "ការកំណត់កាលវិភាគកែប្រែជីវប្រវត្តិ"

    def __str__(self):
        return f"{self.title} (Active: {self.is_active}, Status: {self.status_label_kh})"

    @classmethod
    def get_setting(cls):
        setting = cls.objects.first()
        if not setting:
            setting = cls.objects.create(
                is_active=True,
                allow_specialized_edit=True,
                title="កាលវិភាគកែប្រែ និងបញ្ចូលជីវប្រវត្តិមន្ត្រី"
            )
        return setting

    def is_open_for_specialized(self):
        """
        Returns True if the edit window is currently open for specialized offices.
        Returns False if disabled, not started, or deadline expired.
        """
        if not self.is_active or not self.allow_specialized_edit:
            return False
        
        now = timezone.now()
        if self.start_datetime and now < self.start_datetime:
            return False
        if self.end_datetime and now > self.end_datetime:
            return False
        return True

    def is_open_for_department(self, department=None):
        """
        Returns True if the window is open AND the department is allowed (or all are allowed).
        """
        if not self.is_open_for_specialized():
            return False
        if self.allowed_departments.exists():
            if not department:
                return False
            dept_id = department.id if hasattr(department, 'id') else department
            return self.allowed_departments.filter(id=dept_id).exists()
        return True

    @property
    def status_code(self):
        """
        Returns 'OPEN', 'NOT_STARTED', 'EXPIRED', or 'DISABLED'
        """
        if not self.is_active or not self.allow_specialized_edit:
            return 'DISABLED'
        now = timezone.now()
        if self.start_datetime and now < self.start_datetime:
            return 'NOT_STARTED'
        if self.end_datetime and now > self.end_datetime:
            return 'EXPIRED'
        return 'OPEN'

    @property
    def status_label_kh(self):
        code = self.status_code
        if code == 'OPEN':
            return 'កំពុងបើកដំណើរការ (Open)'
        elif code == 'NOT_STARTED':
            return 'មិនទាន់ដល់ពេលបើក (Not Started)'
        elif code == 'EXPIRED':
            return 'ផុតកំណត់កាលបរិច្ឆេទ (Expired/Locked)'
        else:
            return 'បានបិទដោយ ADMIN (Closed)'

    @property
    def is_expired(self):
        return self.status_code == 'EXPIRED'

    @property
    def start_datetime_formatted(self):
        if not self.start_datetime:
            return ""
        local_dt = timezone.localtime(self.start_datetime)
        return f"{local_dt.strftime('%d/%m/%Y')} ម៉ោង {local_dt.strftime('%H:%M')}"

    @property
    def end_datetime_formatted(self):
        if not self.end_datetime:
            return ""
        local_dt = timezone.localtime(self.end_datetime)
        return f"{local_dt.strftime('%d/%m/%Y')} ម៉ោង {local_dt.strftime('%H:%M')}"

    @property
    def start_datetime_input(self):
        if not self.start_datetime:
            return ""
        return timezone.localtime(self.start_datetime).strftime('%Y-%m-%dT%H:%M')

    @property
    def end_datetime_input(self):
        if not self.end_datetime:
            return ""
        return timezone.localtime(self.end_datetime).strftime('%Y-%m-%dT%H:%M')


# ==============================================================================
# CAMBODIA ADMINISTRATIVE GEOGRAPHY MODELS (PROVINCE, DISTRICT, COMMUNE, VILLAGE)
# ==============================================================================

class CambodiaProvince(models.Model):
    code = models.CharField(max_length=10, primary_key=True, verbose_name="កូដរាជធានី/ខេត្ត")
    name_kh = models.CharField(max_length=150, db_index=True, verbose_name="ឈ្មោះរាជធានី/ខេត្ត (ខ្មែរ)")
    name_en = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះរាជធានី/ខេត្ត (ឡាតាំង)")

    class Meta:
        verbose_name = "រាជធានី/ខេត្ត"
        verbose_name_plural = "បញ្ជីរាជធានី/ខេត្ត"
        ordering = ['code']

    def __str__(self):
        return f"{self.name_kh} ({self.code})"


class CambodiaDistrict(models.Model):
    code = models.CharField(max_length=10, primary_key=True, verbose_name="កូដក្រុង/ស្រុក/ខណ្ឌ")
    province = models.ForeignKey(CambodiaProvince, on_delete=models.CASCADE, related_name='districts', verbose_name="រាជធានី/ខេត្ត")
    name_kh = models.CharField(max_length=150, db_index=True, verbose_name="ឈ្មោះក្រុង/ស្រុក/ខណ្ឌ (ខ្មែរ)")
    name_en = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះក្រុង/ស្រុក/ខណ្ឌ (ឡាតាំង)")

    class Meta:
        verbose_name = "ក្រុង/ស្រុក/ខណ្ឌ"
        verbose_name_plural = "បញ្ជីក្រុង/ស្រុក/ខណ្ឌ"
        ordering = ['code']

    def __str__(self):
        return f"{self.name_kh} ({self.code})"


class CambodiaCommune(models.Model):
    code = models.CharField(max_length=10, primary_key=True, verbose_name="កូដឃុំ/សង្កាត់")
    district = models.ForeignKey(CambodiaDistrict, on_delete=models.CASCADE, related_name='communes', verbose_name="ក្រុង/ស្រុក/ខណ្ឌ")
    province = models.ForeignKey(CambodiaProvince, on_delete=models.CASCADE, related_name='communes', verbose_name="រាជធានី/ខេត្ត")
    name_kh = models.CharField(max_length=150, db_index=True, verbose_name="ឈ្មោះឃុំ/សង្កាត់ (ខ្មែរ)")
    name_en = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះឃុំ/សង្កាត់ (ឡាតាំង)")

    class Meta:
        verbose_name = "ឃុំ/សង្កាត់"
        verbose_name_plural = "បញ្ជីឃុំ/សង្កាត់"
        ordering = ['code']

    def __str__(self):
        return f"{self.name_kh} ({self.code})"


class CambodiaVillage(models.Model):
    code = models.CharField(max_length=30, db_index=True, verbose_name="កូដភូមិ")
    commune = models.ForeignKey(CambodiaCommune, on_delete=models.CASCADE, related_name='villages', verbose_name="ឃុំ/សង្កាត់")
    district = models.ForeignKey(CambodiaDistrict, on_delete=models.CASCADE, related_name='villages', verbose_name="ក្រុង/ស្រុក/ខណ្ឌ")
    province = models.ForeignKey(CambodiaProvince, on_delete=models.CASCADE, related_name='villages', verbose_name="រាជធានី/ខេត្ត")
    name_kh = models.CharField(max_length=150, db_index=True, verbose_name="ឈ្មោះភូមិ (ខ្មែរ)")
    name_en = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះភូមិ (ឡាតាំង)")

    class Meta:
        verbose_name = "ភូមិ"
        verbose_name_plural = "បញ្ជីភូមិ"
        ordering = ['code', 'name_kh']

    def __str__(self):
        return f"{self.name_kh} ({self.code})"


# ==============================================================================
# 📝 ONLINE PROMOTION & MEDAL REQUEST MODELS (ការស្នើសុំដំឡើងថ្នាក់ & មេដាយ Online)
# ==============================================================================

class OfficerPromotionRequest(models.Model):
    PROMOTION_TYPE_CHOICES = [
        ('SENIORITY', 'តាមវេនជ្រើសរើស / អតីតភាពការងារ (២ ឆ្នាំ)'),
        ('DEGREE', 'តាមកម្រិតសញ្ញាបត្រ'),
        ('EXAM', 'តាមការប្រឡងប្រជែង'),
        ('SPECIAL', 'ករណីពិសេស / គុណសម្បត្តិការងារ'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '🟡 រង់ចាំពិនិត្យ (Pending)'),
        ('DEPT_APPROVED', '🟢 ថ្នាក់ដឹកនាំមន្ទីរឯកភាព (Dept Approved)'),
        ('DEPT_REJECTED', '🔴 ថ្នាក់ដឹកនាំមន្ទីរមិនឯកភាព (Dept Rejected)'),
        ('SUBMITTED', '🏛️ បានបញ្ជូនទៅក្រសួង (Submitted)'),
        ('MINISTRY_APPROVED', '👑 ក្រសួងអនុម័តផ្លូវការ (Ministry Approved)'),
        ('MINISTRY_REJECTED', '❌ ក្រសួងមិនអនុម័ត/ធ្លាក់ (Ministry Rejected)'),
        ('APPROVED', '🟢 ថ្នាក់ដឹកនាំមន្ទីរឯកភាព (Approved)'),
        ('REJECTED', '🔴 មិនទាន់ឯកភាព (Rejected)'),
    ]

    LEGAL_DOC_TYPE_CHOICES = [
        ('PRAKAS', 'ប្រកាស (ក្រសួង)'),
        ('ANUKRET', 'អនុក្រឹត្យ (រាជរដ្ឋាភិបាល)'),
        ('ROYAL_DECREE', 'ព្រះរាជក្រឹត្យ (ព្រះមហាក្សត្រ)'),
        ('DECISION', 'សេចក្តីសម្រេច / លិខិតផ្លូវការ'),
        ('OTHER', 'លិខិតបទដ្ឋានផ្សេងៗ'),
    ]

    officer = models.ForeignKey(CivilServantProfile, on_delete=models.CASCADE, related_name='promotion_requests', verbose_name="មន្ត្រីស្នើសុំ")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='promotion_requests', verbose_name="ការិយាល័យស្នើសុំ")
    request_year = models.IntegerField(default=2026, verbose_name="សម្រាប់ឆ្នាំ")
    promotion_type = models.CharField(max_length=50, choices=PROMOTION_TYPE_CHOICES, default='SENIORITY', verbose_name="ប្រភេទនៃការដំឡើង")
    
    current_rank_and_step = models.CharField(max_length=150, blank=True, verbose_name="ក្របខ័ណ្ឌ និងថ្នាក់បច្ចុប្បន្ន")
    proposed_rank_and_step = models.CharField(max_length=150, verbose_name="ថ្នាក់ដែលស្នើសុំដំឡើងទៅ")
    
    years_in_current_rank = models.CharField(max_length=100, blank=True, verbose_name="អតីតភាពក្នុងថ្នាក់")
    reason = models.TextField(blank=True, verbose_name="មូលហេតុ និងសមិទ្ធផលការងារ")
    attachment = models.FileField(upload_to='promotions/requests/%Y/', null=True, blank=True, verbose_name="ឯកសារយោងភ្ជាប់")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING', verbose_name="ស្ថានភាពពិនិត្យ")
    admin_notes = models.TextField(blank=True, verbose_name="មតិយោបល់/កំណត់សម្គាល់របស់ Admin")
    
    # 📑 ទិន្នន័យសម្រាប់កិច្ចប្រជុំ & បញ្ជូនទៅក្រសួង
    meeting_decision = models.TextField(blank=True, verbose_name="មតិអង្គប្រជុំ/គណៈកម្មការវាយតម្លៃ")
    is_submitted_to_ministry = models.BooleanField(default=False, verbose_name="បានបញ្ជូនទៅក្រសួងរួច")
    ministry_doc_number = models.CharField(max_length=150, blank=True, verbose_name="លេខលិខិតបញ្ជូនទៅក្រសួង")
    ministry_submission_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទបញ្ជូនទៅក្រសួង")

    # 🏛️ លិខិតបទដ្ឋានគតិយុត្តផ្លូវការពីក្រសួង / រាជរដ្ឋាភិបាល (ពេលក្រសួងអនុម័តជាផ្លូវការ)
    legal_doc_type = models.CharField(max_length=50, choices=LEGAL_DOC_TYPE_CHOICES, blank=True, verbose_name="ប្រភេទលិខិតបទដ្ឋាន")
    legal_doc_number = models.CharField(max_length=150, blank=True, verbose_name="លេខប្រកាស/អនុក្រឹត្យ/ព្រះរាជក្រឹត្យ")
    legal_doc_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចុះហត្ថលេខា")
    effective_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចូលជាធរមាន")
    ministry_decision_notes = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់ការសម្រេចរបស់ក្រសួង")
    is_profile_updated = models.BooleanField(default=False, verbose_name="បាន Update Profile រួច")

    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_promotion_requests', verbose_name="អ្នកស្នើសុំ")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_promotion_requests', verbose_name="អ្នកពិនិត្យ/អនុម័ត")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទពិនិត្យ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទស្នើសុំ")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "សំណើសុំដំឡើងថ្នាក់"
        verbose_name_plural = "បញ្ជីសំណើសុំដំឡើងថ្នាក់"
        ordering = ['-created_at']

    def __str__(self):
        return f"សំណើសុំដំឡើងថ្នាក់: {self.officer.full_name_kh} -> {self.proposed_rank_and_step} ({self.get_status_display()})"


class OfficerMedalRequest(models.Model):
    MEDAL_CHOICES = [
        ('GRAND_OFFICER', '👑 គ្រឿងឥស្សរិយយស ថ្នាក់ មហាសេរីវឌ្ឍន៍ (អតីតភាព ៣០ ឆ្នាំឡើង)'),
        ('THIPADIN', '👑 គ្រឿងឥស្សរិយយស ថ្នាក់ មហាធិបឌិន្ទ (អតីតភាព ៣០ ឆ្នាំឡើង)'),
        ('SENA', '🎖️ គ្រឿងឥស្សរិយយស ថ្នាក់ ធិបឌិន្ទ / សេនា (អតីតភាព ២៥ ឆ្នាំឡើង)'),
        ('MOHANISARAPHORN', '🎖️ គ្រឿងឥស្សរិយយសព្រះរាជាណាចក្រកម្ពុជា / មុនីសារាភ័ណ្ឌ (២៥ ឆ្នាំឡើង)'),
        ('GOLD', '🥇 មេដាយការងារមាស (អតីតភាព ២០ ឆ្នាំឡើង)'),
        ('SILVER', '🥈 មេដាយការងារប្រាក់ (អតីតភាព ១៥ ឆ្នាំឡើង)'),
        ('BRONZE', '🥉 មេដាយការងារសំរឹទ្ធ (អតីតភាព ១០ ឆ្នាំឡើង)'),
        ('OTHER', '🏅 មេដាយ/គ្រឿងឥស្សរិយយសផ្សេងៗ'),
    ]

    STATUS_CHOICES = [
        ('PENDING', '🟡 រង់ចាំពិនិត្យ (Pending)'),
        ('DEPT_APPROVED', '🟢 ថ្នាក់ដឹកនាំមន្ទីរឯកភាព (Dept Approved)'),
        ('DEPT_REJECTED', '🔴 ថ្នាក់ដឹកនាំមន្ទីរមិនឯកភាព (Dept Rejected)'),
        ('SUBMITTED', '🏛️ បានបញ្ជូនទៅក្រសួង (Submitted)'),
        ('MINISTRY_APPROVED', '👑 ក្រសួងអនុម័តផ្លូវការ (Ministry Approved)'),
        ('MINISTRY_REJECTED', '❌ ក្រសួងមិនអនុម័ត/ធ្លាក់ (Ministry Rejected)'),
        ('APPROVED', '🟢 ថ្នាក់ដឹកនាំមន្ទីរឯកភាព (Approved)'),
        ('REJECTED', '🔴 មិនទាន់ឯកភាព (Rejected)'),
    ]

    LEGAL_DOC_TYPE_CHOICES = [
        ('ROYAL_DECREE', 'ព្រះរាជក្រឹត្យ (ព្រះមហាក្សត្រ)'),
        ('ANUKRET', 'អនុក្រឹត្យ (រាជរដ្ឋាភិបាល)'),
        ('PRAKAS', 'ប្រកាស (ក្រសួង)'),
        ('DECISION', 'សេចក្តីសម្រេច / លិខិតផ្លូវការ'),
        ('OTHER', 'លិខិតបទដ្ឋានផ្សេងៗ'),
    ]

    officer = models.ForeignKey(CivilServantProfile, on_delete=models.CASCADE, related_name='medal_requests', verbose_name="មន្ត្រីស្នើសុំ")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='medal_requests', verbose_name="ការិយាល័យស្នើសុំ")
    request_year = models.IntegerField(default=2026, verbose_name="សម្រាប់ឆ្នាំ")
    proposed_medal = models.CharField(max_length=200, verbose_name="មេដាយ/គ្រឿងឥស្សរិយយសដែលស្នើសុំ")
    years_of_service = models.CharField(max_length=100, blank=True, verbose_name="អតីតភាពការងារសរុប (ឆ្នាំ)")
    
    achievements = models.TextField(blank=True, verbose_name="ស្នាដៃ និងគុណសម្បត្តិការងារ")
    attachment = models.FileField(upload_to='medals/requests/%Y/', null=True, blank=True, verbose_name="ឯកសារយោងភ្ជាប់")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING', verbose_name="ស្ថានភាពពិនិត្យ")
    admin_notes = models.TextField(blank=True, verbose_name="មតិយោបល់/កំណត់សម្គាល់របស់ Admin")
    
    # 📑 ទិន្នន័យសម្រាប់កិច្ចប្រជុំ & បញ្ជូនទៅក្រសួង
    meeting_decision = models.TextField(blank=True, verbose_name="មតិអង្គប្រជុំ/គណៈកម្មការវាយតម្លៃ")
    is_submitted_to_ministry = models.BooleanField(default=False, verbose_name="បានបញ្ជូនទៅក្រសួងរួច")
    ministry_doc_number = models.CharField(max_length=150, blank=True, verbose_name="លេខលិខិតបញ្ជូនទៅក្រសួង")
    ministry_submission_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទបញ្ជូនទៅក្រសួង")

    # 🏛️ លិខិតបទដ្ឋានគតិយុត្តផ្លូវការពីក្រសួង / រាជរដ្ឋាភិបាល (ពេលក្រសួងអនុម័តជាផ្លូវការ)
    legal_doc_type = models.CharField(max_length=50, choices=LEGAL_DOC_TYPE_CHOICES, blank=True, verbose_name="ប្រភេទលិខិតបទដ្ឋាន")
    legal_doc_number = models.CharField(max_length=150, blank=True, verbose_name="លេខប្រកាស/អនុក្រឹត្យ/ព្រះរាជក្រឹត្យ")
    legal_doc_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចុះហត្ថលេខា")
    effective_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចូលជាធរមាន")
    ministry_decision_notes = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់ការសម្រេចរបស់ក្រសួង")
    is_profile_updated = models.BooleanField(default=False, verbose_name="បាន Update Profile រួច")

    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_medal_requests', verbose_name="អ្នកស្នើសុំ")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_medal_requests', verbose_name="អ្នកពិនិត្យ/អនុម័ត")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទពិនិត្យ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទស្នើសុំ")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "សំណើសុំមេដាយ"
        verbose_name_plural = "បញ្ជីសំណើសុំមេដាយ"
        ordering = ['-created_at']

    def __str__(self):
        return f"សំណើសុំមេដាយ: {self.officer.full_name_kh} -> {self.proposed_medal} ({self.get_status_display()})"


# ==============================================================================
# 📝 CONTRACT CIVIL SERVANTS / STAFF (មន្ត្រីជាប់កិច្ចសន្យា)
# ==============================================================================

class ContractOfficer(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'ប្រុស'),
        ('FEMALE', 'ស្រី'),
    ]
    ID_TYPE_CHOICES = [
        ('NATIONAL_ID', 'អត្តសញ្ញាណប័ណ្ណសញ្ជាតិខ្មែរ'),
        ('PASSPORT', 'លិខិតឆ្លងដែន'),
    ]
    CONTRACT_STATUS_CHOICES = [
        ('ACTIVE', 'កំពុងបម្រើការ'),
        ('RENEWED', 'បានបន្តកិច្ចសន្យា'),
        ('EXPIRED', 'ផុតកិច្ចសន្យា'),
        ('TERMINATED', 'បានបញ្ឈប់/ឈប់'),
    ]

    # Links
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_officers',
        verbose_name="ការិយាល័យ/អង្គភាពបច្ចុប្បន្ន"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_contract_officers',
        verbose_name="អ្នកបញ្ចូលទិន្នន័យ"
    )

    # ==========================================
    # ក. ព័ត៌មានផ្ទាល់ខ្លួន (Personal Information)
    # ==========================================
    photo = models.ImageField(upload_to='contract_officers/photos/%Y/', null=True, blank=True, verbose_name="រូបថត 4x6")
    khmer_last_name = models.CharField(max_length=100, verbose_name="គោត្តនាម (ខ្មែរ)")
    khmer_first_name = models.CharField(max_length=100, verbose_name="នាមខ្លួន (ខ្មែរ)")
    latin_name = models.CharField(max_length=150, blank=True, verbose_name="អក្សរពុម្ពឡាតាំង (Latin Name)")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE', verbose_name="ភេទ")
    nationality = models.CharField(max_length=50, default='ខ្មែរ', verbose_name="សញ្ជាតិ")
    ethnicity = models.CharField(max_length=50, default='ខ្មែរ', blank=True, verbose_name="ជនជាតិ")
    dob = models.CharField(max_length=150, blank=True, verbose_name="ថ្ងៃខែឆ្នាំកំណើត")

    # ទីកន្លែងកំណើត
    pob_province_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដរាជធានី/ខេត្តកំណើត")
    pob_district_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដស្រុក/ខណ្ឌកំណើត")
    pob_commune_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដឃុំ/សង្កាត់កំណើត")
    pob_village_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដភូមិកំណើត")
    pob_village = models.CharField(max_length=100, blank=True, verbose_name="ភូមិកំណើត")
    pob_commune = models.CharField(max_length=100, blank=True, verbose_name="ឃុំ/សង្កាត់កំណើត")
    pob_district = models.CharField(max_length=100, blank=True, verbose_name="ស្រុក/ខណ្ឌកំណើត")
    pob_province = models.CharField(max_length=100, blank=True, verbose_name="រាជធានី/ខេត្តកំណើត")
    place_of_birth = models.CharField(max_length=255, blank=True, verbose_name="ទីកន្លែងកំណើត (សង្ខេប)")

    # កម្រិតវប្បធម៌ទូទៅ និងការបណ្តុះបណ្តាល
    general_education = models.CharField(max_length=200, blank=True, verbose_name="កម្រិតវប្បធម៌ទូទៅ")
    training_level = models.CharField(max_length=200, blank=True, verbose_name="កម្រិតបណ្តុះបណ្តាល")
    skill_specialization = models.CharField(max_length=200, blank=True, verbose_name="ជំនាញ/ឯកទេស")

    # លេខអត្តសញ្ញាណប័ណ្ណ ឬ លិខិតឆ្លងដែន
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default='NATIONAL_ID', verbose_name="ប្រភេទឯកសារសម្គាល់ខ្លួន")
    id_number = models.CharField(max_length=100, blank=True, verbose_name="លេខអត្តសញ្ញាណប័ណ្ណ ឬ លិខិតឆ្លងដែន")

    # អង្គភាព/ការិយាល័យបំពេញការងារ
    working_unit = models.CharField(max_length=255, blank=True, verbose_name="អង្គភាព/ការិយាល័យបំពេញការងារ")

    # ==========================================
    # ខ. ព័ត៌មានទំនាក់ទំនង (Contact Information)
    # ==========================================
    current_province_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដរាជធានី/ខេត្តបច្ចុប្បន្ន")
    current_district_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដស្រុក/ខណ្ឌបច្ចុប្បន្ន")
    current_commune_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដឃុំ/សង្កាត់បច្ចុប្បន្ន")
    current_village_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="កូដភូមិបច្ចុប្បន្ន")
    current_house_no = models.CharField(max_length=50, blank=True, verbose_name="ផ្ទះលេខ (បច្ចុប្បន្ន)")
    current_street = models.CharField(max_length=100, blank=True, verbose_name="ផ្លូវ (បច្ចុប្បន្ន)")
    current_village = models.CharField(max_length=100, blank=True, verbose_name="ភូមិ (បច្ចុប្បន្ន)")
    current_commune = models.CharField(max_length=100, blank=True, verbose_name="ឃុំ/សង្កាត់ (បច្ចុប្បន្ន)")
    current_district = models.CharField(max_length=100, blank=True, verbose_name="ស្រុក/ខណ្ឌ (បច្ចុប្បន្ន)")
    current_province = models.CharField(max_length=100, blank=True, verbose_name="រាជធានី/ខេត្ត (បច្ចុប្បន្ន)")
    current_address = models.CharField(max_length=255, blank=True, verbose_name="អាសយដ្ឋានបច្ចុប្បន្ន (សង្ខេប)")

    phone = models.CharField(max_length=100, blank=True, verbose_name="លេខទូរស័ព្ទ")
    email = models.EmailField(blank=True, verbose_name="អ៊ីម៉ែល (បើមាន)")

    # ==========================================
    # គ. ព័ត៌មានកិច្ចសន្យាការងារ (Contract Details)
    # ==========================================
    contract_year = models.PositiveIntegerField(default=2026, verbose_name="ឆ្នាំកិច្ចសន្យា")
    original_join_year = models.PositiveIntegerField(null=True, blank=True, verbose_name="ឆ្នាំចាប់ផ្តើមដំបូង")
    contract_count_years = models.PositiveIntegerField(default=1, verbose_name="ចំនួនឆ្នាំដែលបានបម្រើការ/បន្ត")
    position_title = models.CharField(max_length=150, default='មន្ត្រីជាប់កិច្ចសន្យា', verbose_name="មុខតំណែង/តួនាទី")
    contract_number = models.CharField(max_length=100, blank=True, verbose_name="លេខកិច្ចសន្យា/លេខលិខិត")
    contract_start_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចាប់ផ្តើមកិច្ចសន្យា")
    contract_end_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទផុតកំណត់កិច្ចសន្យា")
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="ប្រាក់បៀវត្ស/ប្រាក់ឧបត្ថម្ភ (៛)")
    contract_status = models.CharField(
        max_length=20,
        choices=CONTRACT_STATUS_CHOICES,
        default='ACTIVE',
        verbose_name="ស្ថានភាពកិច្ចសន្យា"
    )
    contract_file = models.FileField(upload_to='contract_officers/contracts/%Y/', null=True, blank=True, verbose_name="ឯកសារកិច្ចសន្យា (PDF/រូបភាព)")
    remarks = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់បន្ថែម")
    is_active = models.BooleanField(default=True, verbose_name="សកម្ម")

    last_renewed_at = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទអនុម័តបន្តចុងក្រោយ")
    last_renewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='renewed_contract_officers', verbose_name="អ្នកអនុម័តបន្ត")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="ថ្ងៃបង្កើត")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="ថ្ងៃកែប្រែចុងក្រោយ")

    class Meta:
        verbose_name = "មន្ត្រីជាប់កិច្ចសន្យា"
        verbose_name_plural = "បញ្ជីមន្ត្រីជាប់កិច្ចសន្យា"
        ordering = ['-contract_year', '-created_at']

    def __str__(self):
        return f"{self.full_name_kh} ({self.position_title} - ឆ្នាំ {self.contract_year})"

    @property
    def full_name_kh(self):
        return f"{self.khmer_last_name} {self.khmer_first_name}".strip()

    @property
    def full_name_latin(self):
        return self.latin_name.strip().upper() if self.latin_name else ""

    @property
    def display_working_unit(self):
        if self.working_unit:
            return self.working_unit
        if self.department:
            return self.department.name_kh
        return "មន្ទីររដ្ឋបាល"

    @property
    def full_pob(self):
        if self.place_of_birth:
            return self.place_of_birth
        parts = []
        if self.pob_village:
            parts.append(f"ភូមិ{self.pob_village}")
        if self.pob_commune:
            parts.append(f"ឃុំ/សង្កាត់{self.pob_commune}")
        if self.pob_district:
            parts.append(f"ស្រុក/ខណ្ឌ{self.pob_district}")
        if self.pob_province:
            parts.append(f"ខេត្ត/រាជធានី{self.pob_province}")
        return " ".join(parts) if parts else "-"

    @property
    def full_current_address(self):
        if self.current_address:
            return self.current_address
        parts = []
        if self.current_house_no:
            parts.append(f"ផ្ទះលេខ{self.current_house_no}")
        if self.current_street:
            parts.append(f"ផ្លូវ{self.current_street}")
        if self.current_village:
            parts.append(f"ភូមិ{self.current_village}")
        if self.current_commune:
            parts.append(f"ឃុំ/សង្កាត់{self.current_commune}")
        if self.current_district:
            parts.append(f"ស្រុក/ខណ្ឌ{self.current_district}")
        if self.current_province:
            parts.append(f"ខេត្ត/រាជធានី{self.current_province}")
        return " ".join(parts) if parts else "-"

    @property
    def is_contract_expired(self):
        if self.contract_end_date:
            return self.contract_end_date < timezone.now().date()
        return False


class ContractOfficerRenewalHistory(models.Model):
    """
    ប្រវត្តិនៃការបន្តកិច្ចសន្យាការងារប្រចាំឆ្នាំរបស់មន្ត្រីជាប់កិច្ចសន្យា (Contract Staff Yearly Renewal Log)
    """
    contract_officer = models.ForeignKey(
        ContractOfficer,
        on_delete=models.CASCADE,
        related_name='renewals',
        verbose_name="មន្ត្រីជាប់កិច្ចសន្យា"
    )
    from_year = models.PositiveIntegerField(verbose_name="ពីឆ្នាំកិច្ចសន្យា")
    to_year = models.PositiveIntegerField(verbose_name="ទៅឆ្នាំកិច្ចសន្យាថ្មី")
    contract_number = models.CharField(max_length=100, blank=True, verbose_name="លេខកិច្ចសន្យាថ្មី")
    contract_start_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចាប់ផ្តើមកិច្ចសន្យាថ្មី")
    contract_end_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទផុតកំណត់កិច្ចសន្យាថ្មី")
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="ប្រាក់បៀវត្ស/ប្រាក់ឧបត្ថម្ភ (៛)")
    position_title = models.CharField(max_length=150, blank=True, verbose_name="មុខតំណែង/តួនាទីថ្មី")
    working_unit = models.CharField(max_length=255, blank=True, verbose_name="អង្គភាព/ការិយាល័យថ្មី")
    renewal_document = models.FileField(upload_to='contract_officers/renewals/%Y/', null=True, blank=True, verbose_name="ឯកសារកិច្ចសន្យាថ្មី (PDF/រូបភាព)")
    remarks = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់បន្ថែម")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="អ្នកអនុម័ត")
    approved_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទអនុម័ត")

    class Meta:
        verbose_name = "ប្រវត្តិបន្តកិច្ចសន្យា"
        verbose_name_plural = "បញ្ជីប្រវត្តិបន្តកិច្ចសន្យា"
        ordering = ['-to_year', '-approved_at']

    def __str__(self):
        return f"{self.contract_officer.full_name_kh} - បន្តពី {self.from_year} ទៅ {self.to_year}"


class ContractOfficerAttachment(models.Model):
    contract_officer = models.ForeignKey(
        ContractOfficer,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="មន្ត្រីជាប់កិច្ចសន្យា"
    )
    title = models.CharField(max_length=255, verbose_name="ឈ្មោះឯកសារ")
    file = models.FileField(upload_to='contract_officers/attachments/%Y/%m/', verbose_name="ឯកសារភ្ជាប់")
    file_type = models.CharField(max_length=50, blank=True, verbose_name="ប្រភេទឯកសារ")
    notes = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="អ្នកបញ្ចូល")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទបញ្ចូល")

    class Meta:
        verbose_name = "ឯកសារភ្ជាប់មន្ត្រីកិច្ចសន្យា"
        verbose_name_plural = "បញ្ជីឯកសារភ្ជាប់មន្ត្រីកិច្ចសន្យា"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.contract_officer.full_name_kh})"


class ContractOfficerTransferHistory(models.Model):
    """
    ប្រវត្តិនៃការផ្លាស់ប្តូរការិយាល័យ/ខណ្ឌ របស់មន្ត្រីជាប់កិច្ចសន្យា (Contract Staff Department/Canton Transfer History)
    """
    contract_officer = models.ForeignKey(
        ContractOfficer,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name="មន្ត្រីជាប់កិច្ចសន្យា"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_transfers_from',
        verbose_name="ពីការិយាល័យ/ខណ្ឌ"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contract_transfers_to',
        verbose_name="ទៅការិយាល័យ/ខណ្ឌថ្មី"
    )
    from_working_unit = models.CharField(max_length=255, blank=True, verbose_name="អង្គភាព/ការិយាល័យចាស់")
    to_working_unit = models.CharField(max_length=255, blank=True, verbose_name="អង្គភាព/ការិយាល័យថ្មី")
    from_position_title = models.CharField(max_length=150, blank=True, verbose_name="មុខតំណែងចាស់")
    to_position_title = models.CharField(max_length=150, blank=True, verbose_name="មុខតំណែងថ្មី")
    transfer_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទផ្ទេរ/ចូលកាន់តំណែង")
    reference_letter_number = models.CharField(max_length=150, blank=True, verbose_name="លេខលិខិតផ្ទេរ/ចាត់តាំង")
    transfer_document = models.FileField(
        upload_to='contract_officers/transfers/%Y/',
        null=True,
        blank=True,
        verbose_name="ឯកសារលិខិតផ្ទេរ (PDF/រូបភាព)"
    )
    remarks = models.TextField(blank=True, verbose_name="មូលហេតុ/កំណត់សម្គាល់បន្ថែម")
    transferred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_contract_transfers',
        verbose_name="អ្នកធ្វើការផ្លាស់ប្តូរ (Admin)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទកត់ត្រា")

    class Meta:
        verbose_name = "ប្រវត្តិផ្លាស់ប្តូរការិយាល័យមន្ត្រីកិច្ចសន្យា"
        verbose_name_plural = "បញ្ជីប្រវត្តិផ្លាស់ប្តូរការិយាល័យមន្ត្រីកិច្ចសន្យា"
        ordering = ['-transfer_date', '-created_at']

    def __str__(self):
        from_d = self.from_department.name_kh if self.from_department else (self.from_working_unit or "គ្មាន")
        to_d = self.to_department.name_kh if self.to_department else (self.to_working_unit or "គ្មាន")
        return f"{self.contract_officer.full_name_kh}: {from_d} ➔ {to_d}"


# ==============================================================================
# 🚗 VEHICLE & ASSET USAGE MANAGEMENT (រថយន្ត និង ម៉ូតូរបស់អង្គភាព)
# ==============================================================================

class Vehicle(models.Model):
    """
    Official Vehicle & Motorbike Registry (បញ្ជីសារពើភណ្ឌយានយន្ត និង ម៉ូតូរបស់អង្គភាព)
    """
    VEHICLE_TYPE_CHOICES = [
        ('MOTORCYCLE', 'ម៉ូតូ (Motorcycle)'),
        ('CAR', 'រថយន្តទេសចរណ៍ (Car / Sedan / SUV)'),
        ('TRUCK', 'រថយន្តដឹកទំនិញ/ភីកអាប់ (Pickup / Truck)'),
        ('VAN', 'រថយន្តវ៉ែន/មីនីបឹស (Van / Minibus)'),
        ('OTHER', 'ផ្សេងៗ (Other)'),
    ]

    STATUS_CHOICES = [
        ('AVAILABLE', 'ទំនេរ / អាចខ្ចីបាន (Available)'),
        ('IN_USE', 'កំពុងប្រើប្រាស់ (In Use)'),
        ('MAINTENANCE', 'កំពុងជួសជុល/ថែទាំ (Maintenance)'),
        ('DISPOSED', 'រំសាយ/ខូចលែងប្រើ (Disposed)'),
    ]

    name = models.CharField(max_length=200, verbose_name="ឈ្មោះយានយន្ត/ម៉ូតូ")
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='MOTORCYCLE', verbose_name="ប្រភេទមធ្យោបាយ")
    brand = models.CharField(max_length=100, verbose_name="ម៉ាក (Brand/Model)")
    model_year = models.CharField(max_length=20, blank=True, verbose_name="ឆ្នាំផលិត")
    color = models.CharField(max_length=50, blank=True, verbose_name="ពណ៌")
    plate_number = models.CharField(max_length=50, verbose_name="ស្លាកលេខ (License Plate)")
    chassis_number = models.CharField(max_length=100, blank=True, verbose_name="លេខតួ (Chassis No)")
    engine_number = models.CharField(max_length=100, blank=True, verbose_name="លេខម៉ាស៊ីន (Engine No)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE', verbose_name="ស្ថានភាព")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='allocated_vehicles', verbose_name="អង្គភាព/ការិយាល័យកាន់កាប់")

    current_user_name = models.CharField(max_length=150, blank=True, verbose_name="អ្នកប្រើប្រាស់បច្ចុប្បន្ន")
    previous_user_name = models.CharField(max_length=150, blank=True, verbose_name="អ្នកប្រើប្រាស់ចុងក្រោយ")

    photo_front = models.ImageField(upload_to='vehicles/photos/%Y/%m/', blank=True, null=True, verbose_name="រូបថតមើលពីមុខ")
    photo_side = models.ImageField(upload_to='vehicles/photos/%Y/%m/', blank=True, null=True, verbose_name="រូបថតមើលពីចំហៀង")
    registration_card_photo = models.ImageField(upload_to='vehicles/cards/%Y/%m/', blank=True, null=True, verbose_name="ប័ណ្ណសម្គាល់យានយន្ត (កាតគ្រី)")

    odometer = models.CharField(max_length=50, blank=True, verbose_name="កុងទ័រគីឡូម៉ែត្របច្ចុប្បន្ន (Km)")
    notes = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់")

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_vehicles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "យានយន្ត/ម៉ូតូរបស់អង្គភាព"
        verbose_name_plural = "បញ្ជីយានយន្ត និងម៉ូតូរបស់អង្គភាព"
        ordering = ['vehicle_type', 'brand', 'plate_number']

    def __str__(self):
        return f"{self.get_vehicle_type_display()} {self.brand} - {self.plate_number}"

    @property
    def display_type_kh(self):
        if self.vehicle_type == 'MOTORCYCLE':
            return 'ម៉ូតូ'
        elif self.vehicle_type in ['CAR', 'TRUCK', 'VAN']:
            return 'រថយន្ត'
        return 'មធ្យោបាយ'

    @property
    def status_badge_class(self):
        badges = {
            'AVAILABLE': 'bg-success text-white',
            'IN_USE': 'bg-primary text-white',
            'MAINTENANCE': 'bg-warning text-dark',
            'DISPOSED': 'bg-secondary text-white',
        }
        return badges.get(self.status, 'bg-secondary text-white')


class VehicleRequest(models.Model):
    """
    Vehicle & Motorbike Borrowing Request & Handover Dossier (ពាក្យសុំខ្ចីទ្រព្យប្រើប្រាស់ & កំណត់ហេតុប្រគល់-ទទួល)
    """
    STATUS_CHOICES = [
        ('PENDING', 'រង់ចាំការពិនិត្យ (Pending)'),
        ('APPROVED', 'បានអនុម័ត (Approved)'),
        ('REJECTED', 'បដិសេធ (Rejected)'),
        ('HANDED_OVER', 'បានប្រគល់-ទទួល (Handed Over / In Use)'),
        ('RETURNED', 'បានប្រគល់ជូនវិញ (Returned)'),
        ('CANCELLED', 'បានបោះបង់ (Cancelled)'),
    ]

    GENDER_CHOICES = [
        ('MALE', 'ប្រុស'),
        ('FEMALE', 'ស្រី'),
    ]

    # Reference info
    request_number = models.CharField(max_length=100, blank=True, verbose_name="លេខលិខិតសុំ")

    # ព័ត៌មានអ្នកស្នើសុំ (Applicant Info)
    applicant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_requests', verbose_name="គណនីអ្នកស្នើសុំ")
    applicant_profile = models.ForeignKey('CivilServantProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_requests', verbose_name="មន្ត្រីរាជការ")
    applicant_contract_officer = models.ForeignKey('ContractOfficer', on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_requests', verbose_name="មន្ត្រីជាប់កិច្ចសន្យា")
    applicant_name = models.CharField(max_length=150, verbose_name="ឈ្មោះអ្នកស្នើសុំ")
    applicant_gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE', verbose_name="ភេទ")
    applicant_position = models.CharField(max_length=150, verbose_name="តួនាទី")
    applicant_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='department_vehicle_requests', verbose_name="អង្គភាព/ការិយាល័យបម្រើការងារ")
    applicant_department_name = models.CharField(max_length=200, blank=True, verbose_name="ឈ្មោះអង្គភាព (បង្ហាញលើទម្រង់)")
    applicant_id_number = models.CharField(max_length=100, blank=True, verbose_name="អត្តលេខមន្ត្រី")
    applicant_phone = models.CharField(max_length=50, blank=True, verbose_name="លេខទូរស័ព្ទ")

    # ព័ត៌មានយានយន្តដែលស្នើសុំ (Vehicle info)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests', verbose_name="ជ្រើសរើសយានយន្តក្នុងប្រព័ន្ធ")
    vehicle_type = models.CharField(max_length=20, default='MOTORCYCLE', verbose_name="ប្រភេទមធ្យោបាយ (រថយន្ត/ម៉ូតូ)")
    vehicle_brand = models.CharField(max_length=100, blank=True, verbose_name="ម៉ាក")
    vehicle_color = models.CharField(max_length=50, blank=True, verbose_name="ពណ៌")
    vehicle_model_year = models.CharField(max_length=20, blank=True, verbose_name="ឆ្នាំផលិត")
    vehicle_chassis_number = models.CharField(max_length=100, blank=True, verbose_name="លេខតួ")
    vehicle_engine_number = models.CharField(max_length=100, blank=True, verbose_name="លេខម៉ាស៊ីន")
    vehicle_plate_number = models.CharField(max_length=50, blank=True, verbose_name="ស្លាកលេខ")

    # កម្មវត្ថុ & រយៈពេលស្នើសុំ (Request details)
    duration_text = models.CharField(max_length=100, default="១ឆ្នាំ", verbose_name="រយៈពេលស្នើសុំ (ឧ. ១ឆ្នាំ)")
    start_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទចាប់ផ្តើម")
    end_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទបញ្ចប់")
    purpose = models.TextField(blank=True, verbose_name="គោលបំណង / កម្មវត្ថុនៃការប្រើប្រាស់")

    # ស្ថានភាព & ការអនុម័ត (Approval)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="ស្ថានភាពសំណើ")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_vehicle_requests', verbose_name="អ្នកអនុម័ត")
    approval_date = models.DateField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទអនុម័ត")
    approval_comments = models.TextField(blank=True, verbose_name="មតិយោបល់ថ្នាក់ដឹកនាំ")

    # កំណត់ហេតុប្រគល់-ទទួល (Handover Info - Page 2)
    handover_datetime = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទ និងវេលាម៉ោងប្រគល់-ទទួល")
    handover_officer_name = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះអ្នកប្រគល់ / មន្ត្រីទទួលបន្ទុក")
    handover_officer_position = models.CharField(max_length=150, blank=True, verbose_name="តួនាទីអ្នកប្រគល់")
    recipient_name = models.CharField(max_length=150, blank=True, verbose_name="ឈ្មោះអ្នកទទួល")
    last_user_name = models.CharField(max_length=150, blank=True, verbose_name="អ្នកប្រើប្រាស់ចុងក្រោយ")
    vehicle_condition_handover = models.TextField(blank=True, verbose_name="ស្ថានភាពជាក់ស្តែងពេលប្រគល់-ទទួល")
    odometer_at_handover = models.CharField(max_length=50, blank=True, verbose_name="កុងទ័រគីឡូម៉ែត្រពេលប្រគល់ (Km)")

    photo_front = models.ImageField(upload_to='vehicle_requests/handover/%Y/%m/', blank=True, null=True, verbose_name="រូបថតមើលពីមុខពេលប្រគល់")
    photo_side = models.ImageField(upload_to='vehicle_requests/handover/%Y/%m/', blank=True, null=True, verbose_name="រូបថតមើលពីចំហៀងពេលប្រគល់")
    registration_card_photo = models.ImageField(upload_to='vehicle_requests/cards/%Y/%m/', blank=True, null=True, verbose_name="រូបភាពប័ណ្ណសម្គាល់យានយន្ត")

    # ការប្រគល់ត្រឡប់មកវិញ (Return Info)
    return_datetime = models.DateTimeField(null=True, blank=True, verbose_name="កាលបរិច្ឆេទ និងវេលាម៉ោងប្រគល់មកវិញ")
    return_condition = models.TextField(blank=True, verbose_name="ស្ថានភាពជាក់ស្តែងពេលប្រគល់មកវិញ")
    odometer_at_return = models.CharField(max_length=50, blank=True, verbose_name="កុងទ័រគីឡូម៉ែត្រពេលប្រគល់មកវិញ (Km)")
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='returned_vehicle_requests', verbose_name="អ្នកទទួលយានយន្តមកវិញ")
    return_notes = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់ពេលប្រគល់ត្រឡប់")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ពាក្យសុំខ្ចីយានយន្ត/ម៉ូតូ"
        verbose_name_plural = "បញ្ជីពាក្យសុំខ្ចីយានយន្ត/ម៉ូតូ"
        ordering = ['-created_at']

    def __str__(self):
        v_name = self.vehicle_brand or (self.vehicle.brand if self.vehicle else '')
        return f"ពាក្យសុំ {self.applicant_name} ({self.display_vehicle_type_kh} {v_name}) - {self.get_status_display()}"

    @property
    def display_vehicle_type_kh(self):
        if self.vehicle_type == 'MOTORCYCLE':
            return 'ម៉ូតូ'
        elif self.vehicle_type in ['CAR', 'TRUCK', 'VAN']:
            return 'រថយន្ត'
        return 'មធ្យោបាយ'

    @property
    def display_brand(self):
        return self.vehicle_brand or (self.vehicle.brand if self.vehicle else '-')

    @property
    def display_color(self):
        return self.vehicle_color or (self.vehicle.color if self.vehicle else '-')

    @property
    def display_model_year(self):
        return self.vehicle_model_year or (self.vehicle.model_year if self.vehicle else '-')

    @property
    def display_chassis_number(self):
        return self.vehicle_chassis_number or (self.vehicle.chassis_number if self.vehicle else '-')

    @property
    def display_engine_number(self):
        return self.vehicle_engine_number or (self.vehicle.engine_number if self.vehicle else '-')

    @property
    def display_plate_number(self):
        return self.vehicle_plate_number or (self.vehicle.plate_number if self.vehicle else '-')

    @property
    def display_photo_front(self):
        if self.photo_front:
            return self.photo_front
        if self.vehicle and self.vehicle.photo_front:
            return self.vehicle.photo_front
        return None

    @property
    def display_photo_side(self):
        if self.photo_side:
            return self.photo_side
        if self.vehicle and self.vehicle.photo_side:
            return self.vehicle.photo_side
        return None

    @property
    def display_registration_card_photo(self):
        if self.registration_card_photo:
            return self.registration_card_photo
        if self.vehicle and self.vehicle.registration_card_photo:
            return self.vehicle.registration_card_photo
        return None

    @property
    def status_badge_class(self):
        badges = {
            'PENDING': 'bg-warning text-dark',
            'APPROVED': 'bg-info text-dark',
            'REJECTED': 'bg-danger text-white',
            'HANDED_OVER': 'bg-primary text-white',
            'RETURNED': 'bg-success text-white',
            'CANCELLED': 'bg-secondary text-white',
        }
        return badges.get(self.status, 'bg-secondary text-white')


class VehicleRequestAttachment(models.Model):
    vehicle_request = models.ForeignKey(
        VehicleRequest,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="ពាក្យសុំខ្ចីយានយន្ត"
    )
    title = models.CharField(max_length=255, verbose_name="ឈ្មោះឯកសារ")
    file = models.FileField(upload_to='vehicle_requests/attachments/%Y/%m/', verbose_name="ឯកសារភ្ជាប់")
    file_type = models.CharField(max_length=50, blank=True, verbose_name="ប្រភេទឯកសារ")
    notes = models.TextField(blank=True, verbose_name="កំណត់សម្គាល់")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="អ្នកបញ្ចូល")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="កាលបរិច្ឆេទបញ្ចូល")

    class Meta:
        verbose_name = "ឯកសារភ្ជាប់ពាក្យសុំខ្ចី"
        verbose_name_plural = "បញ្ជីឯកសារភ្ជាប់ពាក្យសុំខ្ចី"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.vehicle_request.applicant_name})"



