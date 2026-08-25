from django import forms
from .models import Document, DocumentVersion, LeadershipAnnotation, DocumentRouting, Department, ChatMessage

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name_kh', 'code', 'name_en', 'structure_type', 'is_active', 'order_index', 'description']
        labels = {
            'name_kh': 'ឈ្មោះការិយាល័យ / អង្គភាព (ខ្មែរ) *',
            'code': 'កូដសម្គាល់ (Code) *',
            'name_en': 'English Name',
            'structure_type': 'ប្រភេទរចនាសម្ព័ន្ធ',
            'is_active': 'បើកដំណើរការ (Active)',
            'order_index': 'លំដាប់លំដោយ (Order Index)',
            'description': 'ការពណ៌នា / បរិយាយ',
        }
        widgets = {
            'name_kh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឧ. ការិយាល័យផែនការ និងស្ថិតិ', 'required': True}),
            'code': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'ឧ. PLAN ឬ STAT', 'required': True}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឧ. Planning and Statistics Office'}),
            'structure_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order_index': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ព័ត៌មានបន្ថែមអំពីការិយាល័យ ឬតួនាទី...'}),
        }

class DocumentForm(forms.ModelForm):
    initial_route_dept = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        label="បញ្ជូនទៅកាន់ការិយាល័យណា (Auto Route - មិនបាច់ជ្រើសក៏បាន)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    initial_send_to_all = forms.BooleanField(
        required=False,
        label="បញ្ជូនទៅគ្រប់ការិយាល័យទាំងអស់ (Broadcast to All)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Document
        fields = [
            'doc_type', 'registry_number', 'title', 'summary',
            'origin_org', 'destination_org', 'urgency', 'secrecy',
            'issue_date', 'received_date'
        ]
        widgets = {
            'doc_type': forms.Select(attrs={'class': 'form-select'}),
            'registry_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ឧទាហរណ៍៖ 001/26/ADMIN (ទុកទំនេរដើម្បីចុះស្វ័យប្រវត្តិ)'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'បញ្ចូលកម្មវត្ថុ ឬចំណងជើងលិខិត...'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'សង្ខេបខ្លឹមសារលិខិត...'}),
            'origin_org': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឧ. ក្រសួងសេដ្ឋកិច្ច និងហិរញ្ញវត្ថុ (មិនបាច់ដាក់ក៏បាន)'}),
            'destination_org': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឧ. មន្ទីររដ្ឋបាល និងហិរញ្ញវត្ថុ (មិនបាច់ដាក់ក៏បាន)'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'secrecy': forms.Select(attrs={'class': 'form-select'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, user=None, profile=None, doc_type_mode=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registry_number'].required = False
        self.fields['origin_org'].required = False
        self.fields['destination_org'].required = False

        # Check if user is Admin / General Affairs / Leadership
        is_general_affairs = False
        if user:
            if user.is_superuser or (user.username or '').upper() == 'ADMIN':
                is_general_affairs = True
            elif profile:
                if profile.is_admin or profile.is_leadership:
                    is_general_affairs = True
                elif profile.department:
                    dept = profile.department
                    dept_name = (dept.name_kh or '').strip().lower()
                    dept_code = (dept.code or '').strip().upper()
                    if not (dept_code.startswith('CANTON') or dept_name.startswith('ខណ្ឌ') or 'ខណ្ឌ' in dept_name):
                        if dept_code in ['ADMIN', 'ADMIN_PERS', 'LEAD', 'GEN_AFFAIRS', 'GENERAL_AFFAIRS', 'GAD', 'ADMIN_DEPT']:
                            is_general_affairs = True
                        elif 'កិច្ចការទូទៅ' in dept_name or 'កិច្ចការរដ្ឋបាលទូទៅ' in dept_name:
                            is_general_affairs = True
                        elif ('រដ្ឋបាល' in dept_name and 'បុគ្គលិក' in dept_name) or ('រដ្ឋបាល' in dept_name and 'ទូទៅ' in dept_name):
                            is_general_affairs = True
                        elif dept_name in ['ការិយាល័យរដ្ឋបាល បុគ្គលិក', 'ការិយាល័យរដ្ឋបាល-បុគ្គលិក', 'ការិយាល័យរដ្ឋបាល', 'ការិយាល័យកិច្ចការរដ្ឋបាលទូទៅ', 'ការិយាល័យកិច្ចការទូទៅ']:
                            is_general_affairs = True

        # Dynamic doc_type choices
        mode = (doc_type_mode or '').upper()
        if mode == 'INBOUND':
            if is_general_affairs:
                # General Affairs and Admin can choose Inbound or Internal Inbound
                self.fields['doc_type'].choices = [
                    ('INBOUND', 'លិខិតចូល (Inbound)'),
                    ('INTERNAL', 'លិខិតផ្ទៃក្នុង (Internal)'),
                ]
                self.fields['doc_type'].initial = 'INBOUND'
            else:
                self.fields['doc_type'].choices = [
                    ('INBOUND', 'លិខិតចូល (Inbound)'),
                ]
                self.fields['doc_type'].initial = 'INBOUND'
        else:
            # Outbound / New Registry
            if is_general_affairs:
                # General Affairs and Admin can choose between Outbound and Internal
                self.fields['doc_type'].choices = [
                    ('OUTBOUND', 'លិខិតចេញ (Outbound)'),
                    ('INTERNAL', 'លិខិតផ្ទៃក្នុង (Internal)'),
                ]
                self.fields['doc_type'].initial = 'OUTBOUND'
            else:
                # Specialized offices only see Outbound
                self.fields['doc_type'].choices = [
                    ('OUTBOUND', 'លិខិតចេញ (Outbound)'),
                ]
                self.fields['doc_type'].initial = 'OUTBOUND'

        # Department routing choices:
        # For Specialized Offices: Leadership (LEAD) is excluded completely
        if is_general_affairs:
            self.fields['initial_route_dept'].queryset = Department.objects.filter(is_active=True)
        else:
            self.fields['initial_route_dept'].queryset = Department.objects.filter(is_active=True).exclude(code='LEAD')

    file = forms.FileField(
        required=False,
        label="ឯកសារភ្ជាប់ (PDF, រូបភាព, Docx)",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.png,.jpeg,.doc,.docx'})
    )


class DocumentVersionForm(forms.ModelForm):
    class Meta:
        model = DocumentVersion
        fields = ['version_number', 'file', 'change_summary']
        widgets = {
            'version_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឧ. 1.1'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'change_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ព័ត៌មានអំពីការកែប្រែជំនាន់នេះ...'}),
        }


class LeadershipAnnotationForm(forms.ModelForm):
    target_departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.filter(is_active=True).exclude(code='LEAD'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'dept-checkbox-list'}),
        label="ចាត់ចែងបញ្ជូនទៅការិយាល័យជំនាញ"
    )

    class Meta:
        model = LeadershipAnnotation
        fields = ['decision', 'annotation_text', 'target_departments']
        widgets = {
            'decision': forms.Select(attrs={'class': 'form-select'}),
            'annotation_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'វាយបញ្ចូលចំណារទីនេះ (ឧ. ឯកភាព - ជូនការិយាល័យគណនេយ្យ រៀបចំផែនការថវិកា)...'}),
        }


class DocumentRoutingForm(forms.Form):
    to_dept = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_to_dept'}),
        label="បញ្ជូនទៅការិយាល័យជាក់លាក់",
        required=False
    )
    send_to_all = forms.BooleanField(
        required=False,
        label="បញ្ជូនទៅគ្រប់ការិយាល័យទាំងអស់ (Broadcast to All Offices)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_send_to_all'})
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'កំណត់ចំណាំ ឬការណែនាំនៃការបញ្ជូន...'}),
        required=False,
        label="កត់សម្គាល់/ចំណាំ"
    )

    def __init__(self, *args, user=None, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        is_general_affairs = False
        if user:
            if user.is_superuser or (user.username or '').upper() == 'ADMIN':
                is_general_affairs = True
            elif profile:
                if profile.is_admin or profile.is_leadership:
                    is_general_affairs = True
                elif profile.department:
                    dept = profile.department
                    dept_name = (dept.name_kh or '').strip().lower()
                    dept_code = (dept.code or '').strip().upper()
                    if not (dept_code.startswith('CANTON') or dept_name.startswith('ខណ្ឌ') or 'ខណ្ឌ' in dept_name):
                        if dept_code in ['ADMIN', 'ADMIN_PERS', 'LEAD', 'GEN_AFFAIRS', 'GENERAL_AFFAIRS', 'GAD', 'ADMIN_DEPT']:
                            is_general_affairs = True
                        elif 'កិច្ចការទូទៅ' in dept_name or 'កិច្ចការរដ្ឋបាលទូទៅ' in dept_name:
                            is_general_affairs = True
                        elif ('រដ្ឋបាល' in dept_name and 'បុគ្គលិក' in dept_name) or ('រដ្ឋបាល' in dept_name and 'ទូទៅ' in dept_name):
                            is_general_affairs = True
                        elif dept_name in ['ការិយាល័យរដ្ឋបាល បុគ្គលិក', 'ការិយាល័យរដ្ឋបាល-បុគ្គលិក', 'ការិយាល័យរដ្ឋបាល', 'ការិយាល័យកិច្ចការរដ្ឋបាលទូទៅ', 'ការិយាល័យកិច្ចការទូទៅ']:
                            is_general_affairs = True

        if not is_general_affairs:
            self.fields['to_dept'].queryset = Department.objects.filter(is_active=True).exclude(code='LEAD')
        else:
            self.fields['to_dept'].queryset = Department.objects.filter(is_active=True)



class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ['message', 'attachment', 'target_department', 'related_document']
        widgets = {
            'message': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-3',
                'placeholder': 'វាយបញ្ចូលសារទីនេះ...',
                'autocomplete': 'off',
            }),
            'target_department': forms.HiddenInput(),
            'related_document': forms.HiddenInput(),
        }


from django.contrib.auth.models import User
from .models import UserProfile

class FlexibleLoginForm(forms.Form):
    identifier = forms.CharField(
        label="ឈ្មោះគណនី / Email / លេខទូរស័ព្ទ",
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-light fs-7',
            'placeholder': 'បញ្ចូល Username, Email ឬ លេខទូរស័ព្ទ...',
            'autocomplete': 'username',
            'required': True,
        })
    )
    password = forms.CharField(
        label="ពាក្យសម្ងាត់ (Password)",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control bg-light fs-7',
            'placeholder': 'បញ្ចូលពាក្យសម្ងាត់...',
            'autocomplete': 'current-password',
            'required': True,
        })
    )


class UserRegistrationForm(forms.Form):
    full_name = forms.CharField(
        label="ឈ្មោះពេញ (Full Name)",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control bg-light fs-7', 'placeholder': 'ឧ. ចាន់ សុខា'})
    )
    email = forms.EmailField(
        label="អ៊ីមែលពិត (Email)",
        widget=forms.EmailInput(attrs={'class': 'form-control bg-light fs-7', 'placeholder': 'ឧ. name@gov.kh'})
    )
    phone = forms.CharField(
        label="លេខទូរស័ព្ទ (Phone Number)",
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control bg-light fs-7', 'placeholder': 'ឧ. 012 345 678'})
    )
    department = forms.ModelChoiceField(
        label="ឈ្មោះអង្គភាព / ការិយាល័យ",
        queryset=Department.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select bg-light fs-7'})
    )
    position_title = forms.ChoiceField(
        label="មុខតំណែង (Position)",
        choices=UserProfile.POSITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select bg-light fs-7'})
    )
    username = forms.CharField(
        label="ឈ្មោះគណនី (Username)",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control bg-light fs-7', 'placeholder': 'ឧ. chan_sokha'})
    )
    password = forms.CharField(
        label="ពាក្យសម្ងាត់ (Password)",
        min_length=8,
        error_messages={
            'min_length': "ពាក្យសម្ងាត់ត្រូវតែមានយ៉ាងតិច ៨ ខ្ទង់ឡើងទៅ ដាច់ខាត (ក្រោម ៨ ខ្ទង់ប្រព័ន្ធមិនទទួលយកឡើយ)!",
            'required': "សូមបញ្ចូលពាក្យសម្ងាត់!"
        },
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-light fs-7', 'placeholder': 'យ៉ាងតិច ៨ តួអក្សរឡើងទៅ...'})
    )
    confirm_password = forms.CharField(
        label="ផ្ទៀងផ្ទាត់ពាក្យសម្ងាត់ (Confirm Password)",
        min_length=8,
        error_messages={
            'min_length': "ពាក្យសម្ងាត់ផ្ទៀងផ្ទាត់ត្រូវតែមានយ៉ាងតិច ៨ ខ្ទង់ឡើងទៅ!",
            'required': "សូមផ្ទៀងផ្ទាត់ពាក្យសម្ងាត់ម្តងទៀត!"
        },
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-light fs-7', 'placeholder': 'វាយពាក្យសម្ងាត់ម្តងទៀត...'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("ឈ្មោះគណនី (Username) នេះមានអ្នកប្រើប្រាស់រួចហើយ!")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("អ៊ីមែលនេះមានចុះឈ្មោះរួចហើយ! សូមប្រើអ៊ីមែលផ្សេង ឬចូលប្រព័ន្ធ។")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip().replace(' ', '')
        if UserProfile.objects.filter(phone=phone).exists():
            raise forms.ValidationError("លេខទូរស័ព្ទនេះមានចុះឈ្មោះរួចហើយ!")
        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise forms.ValidationError("ពាក្យសម្ងាត់ត្រូវតែមានយ៉ាងតិច ៨ ខ្ទង់ឡើងទៅ ដាច់ខាត (ក្រោម ៨ ខ្ទង់មិនទទួលយកឡើយ)!")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and len(password) < 8:
            self.add_error('password', "ពាក្យសម្ងាត់ត្រូវតែមានយ៉ាងតិច ៨ ខ្ទង់ឡើងទៅ ដាច់ខាត (ក្រោម ៨ ខ្ទង់មិនទទួលយកឡើយ)!")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "ពាក្យសម្ងាត់ទាំងពីរមិនដូចគ្នាទេ!")

        return cleaned_data


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        label="លេខកូដសម្ងាត់ ៦ ខ្ទង់",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center fs-3 fw-bold tracking-wider py-2',
            'placeholder': '• • • • • •',
            'autocomplete': 'off',
            'autofocus': True,
        })
    )


class UserManagementEditForm(forms.Form):
    full_name = forms.CharField(
        label="ឈ្មោះពេញ (Full Name)",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឈ្មោះពេញ...'})
    )
    username = forms.CharField(
        label="ឈ្មោះគណនី (Username)",
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ឈ្មោះគណនី...'})
    )
    email = forms.EmailField(
        label="អ៊ីមែល (Email)",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@gov.kh'})
    )
    phone = forms.CharField(
        label="លេខទូរស័ព្ទ (Phone)",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '012 345 678'})
    )
    department = forms.ModelChoiceField(
        label="ការិយាល័យ / អង្គភាព",
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    position_title = forms.ChoiceField(
        label="មុខតំណែងជាក់ស្តែង (Position)",
        choices=UserProfile.POSITION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ChoiceField(
        label="តួនាទីសិទ្ធិ (Role)",
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_approved = forms.BooleanField(
        label="អនុម័តឱ្យប្រើប្រាស់ (Approved)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    new_password = forms.CharField(
        label="កំណត់ពាក្យសម្ងាត់ថ្មី (ទុកទំនេរបើមិនចង់ប្តូរ)",
        required=False,
        min_length=8,
        error_messages={
            'min_length': "ពាក្យសម្ងាត់ថ្មីត្រូវតែមានយ៉ាងតិច ៨ ខ្ទង់ឡើងទៅ ដាច់ខាត!"
        },
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'បញ្ចូលពាក្យសម្ងាត់ថ្មី (យ៉ាងតិច ៨ ខ្ទង់)...'})
    )

    # Granular Feature Permissions
    can_create_document = forms.BooleanField(
        label="សិទ្ធិចុះបញ្ជីលិខិតចូល/ចេញ (Create Doc)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_edit_document = forms.BooleanField(
        label="សិទ្ធិកែប្រែ/បន្ថែម Version ឯកសារ (Edit Doc)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_route_document = forms.BooleanField(
        label="សិទ្ធិបញ្ជូន/ចាត់ចែងលំហូរលិខិត (Route Doc)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_annotate = forms.BooleanField(
        label="សិទ្ធិផ្តល់ចំណារថ្នាក់ដឹកនាំ (Leadership Annotation)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_complete_document = forms.BooleanField(
        label="សិទ្ធិបិទបញ្ចប់លិខិត (Complete/Close Doc)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_delete_document = forms.BooleanField(
        label="សិទ្ធិលុបលិខិត (Delete Doc)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_view_reports = forms.BooleanField(
        label="សិទ្ធិមើលរបាយការណ៍ & Export Excel",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    can_print = forms.BooleanField(
        label="សិទ្ធិបោះពុម្ពប័ណ្ណតាមដាន (Print)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
