from django.contrib import admin
from .models import Department, UserProfile, Document, DocumentVersion, LeadershipAnnotation, DocumentRouting, Notification

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('order_index', 'name_kh', 'code', 'structure_type', 'is_active', 'name_en')
    list_display_links = ('name_kh', 'code')
    list_filter = ('structure_type', 'is_active')
    search_fields = ('name_kh', 'code', 'name_en')
    list_editable = ('is_active', 'order_index')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department', 'position_title', 'phone', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'role', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position_title', 'phone')
    list_editable = ('is_approved',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('registry_number', 'title', 'doc_type', 'urgency', 'status', 'current_department', 'received_date')
    list_filter = ('doc_type', 'urgency', 'secrecy', 'status', 'current_department')
    search_fields = ('registry_number', 'title', 'origin_org', 'destination_org')
    date_hierarchy = 'received_date'

@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'uploaded_by', 'uploaded_at')

@admin.register(LeadershipAnnotation)
class LeadershipAnnotationAdmin(admin.ModelAdmin):
    list_display = ('document', 'leader', 'decision', 'signed_at')
    list_filter = ('decision',)

@admin.register(DocumentRouting)
class DocumentRoutingAdmin(admin.ModelAdmin):
    list_display = ('document', 'from_user', 'from_dept', 'to_dept', 'action_taken', 'routed_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)


from .models import OTPVerification

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'otp_code', 'purpose', 'created_at', 'expires_at', 'is_used')
    list_filter = ('purpose', 'is_used')
    search_fields = ('identifier', 'otp_code')


from .models import CivilServantProfile, OfficerAttachment, OfficerAuditLog, OfficerEditWindowSetting

@admin.register(CivilServantProfile)
class CivilServantProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name_kh', 'full_name_latin', 'officer_id_number', 'department', 'current_position_title', 'current_rank_and_step', 'phone')
    list_filter = ('department', 'gender', 'marital_status')
    search_fields = ('khmer_last_name', 'khmer_first_name', 'latin_last_name', 'latin_first_name', 'officer_id_number', 'national_id_number', 'phone')


@admin.register(OfficerAttachment)
class OfficerAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'officer', 'doc_number', 'file_size', 'uploaded_by', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'doc_number', 'officer__khmer_last_name', 'officer__khmer_first_name', 'officer__officer_id_number')


@admin.register(OfficerAuditLog)
class OfficerAuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'officer', 'user', 'action_type', 'attachment_title', 'category', 'ip_address')
    list_filter = ('action_type', 'category', 'timestamp')
    search_fields = ('officer__khmer_last_name', 'officer__khmer_first_name', 'attachment_title', 'user__username', 'details')
    date_hierarchy = 'timestamp'


@admin.register(OfficerEditWindowSetting)
class OfficerEditWindowSettingAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'allow_specialized_edit', 'start_datetime', 'end_datetime', 'status_label_kh', 'updated_at', 'updated_by')
    list_filter = ('is_active', 'allow_specialized_edit')


from .models import (
    ContractOfficer, ContractOfficerAttachment, ContractOfficerRenewalHistory,
    ContractOfficerTransferHistory, OfficerDepartmentTransferHistory,
    Vehicle, VehicleRequest, VehicleRequestAttachment
)

@admin.register(OfficerDepartmentTransferHistory)
class OfficerDepartmentTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('officer', 'from_department', 'to_department', 'transfer_date', 'reference_letter_number', 'transferred_by', 'created_at')
    list_filter = ('to_department', 'from_department', 'transfer_date')
    search_fields = ('officer__khmer_last_name', 'officer__khmer_first_name', 'reference_letter_number', 'remarks')


@admin.register(ContractOfficer)
class ContractOfficerAdmin(admin.ModelAdmin):
    list_display = ('full_name_kh', 'contract_year', 'latin_name', 'gender', 'position_title', 'department', 'working_unit', 'contract_status', 'contract_count_years', 'phone')
    list_filter = ('contract_year', 'gender', 'contract_status', 'department', 'id_type')
    search_fields = ('khmer_last_name', 'khmer_first_name', 'latin_name', 'id_number', 'phone', 'position_title', 'working_unit')


@admin.register(ContractOfficerRenewalHistory)
class ContractOfficerRenewalHistoryAdmin(admin.ModelAdmin):
    list_display = ('contract_officer', 'from_year', 'to_year', 'contract_number', 'salary', 'approved_by', 'approved_at')
    list_filter = ('to_year', 'from_year', 'approved_at')
    search_fields = ('contract_officer__khmer_last_name', 'contract_officer__khmer_first_name', 'contract_number')


@admin.register(ContractOfficerTransferHistory)
class ContractOfficerTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('contract_officer', 'from_department', 'to_department', 'transfer_date', 'reference_letter_number', 'transferred_by', 'created_at')
    list_filter = ('to_department', 'from_department', 'transfer_date')
    search_fields = ('contract_officer__khmer_last_name', 'contract_officer__khmer_first_name', 'reference_letter_number', 'remarks')


@admin.register(ContractOfficerAttachment)
class ContractOfficerAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'contract_officer', 'file_type', 'uploaded_by', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('title', 'contract_officer__khmer_last_name', 'contract_officer__khmer_first_name')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('brand', 'plate_number', 'vehicle_type', 'model_year', 'color', 'status', 'department', 'current_user_name')
    list_filter = ('vehicle_type', 'status', 'department')
    search_fields = ('name', 'brand', 'plate_number', 'chassis_number', 'engine_number', 'current_user_name')


@admin.register(VehicleRequest)
class VehicleRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'applicant_name', 'applicant_department', 'display_vehicle_type_kh', 'vehicle_brand', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'vehicle_type', 'applicant_department', 'created_at')
    search_fields = ('request_number', 'applicant_name', 'applicant_id_number', 'applicant_phone', 'vehicle_brand', 'vehicle_plate_number')
    date_hierarchy = 'created_at'


@admin.register(VehicleRequestAttachment)
class VehicleRequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'vehicle_request', 'file_type', 'uploaded_by', 'created_at')
    list_filter = ('file_type', 'created_at')
    search_fields = ('title', 'vehicle_request__applicant_name', 'vehicle_request__request_number')


from .models import AttendanceRecord

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'person_name', 'person_type', 'department',
        'display_position', 'status', 'morning_in', 'morning_out',
        'afternoon_in', 'afternoon_out', 'is_late', 'is_early_out',
        'leave_type', 'recorded_by'
    )
    list_filter = ('date', 'status', 'person_type', 'department', 'leave_type', 'is_late', 'is_early_out')
    search_fields = (
        'officer__khmer_last_name', 'officer__khmer_first_name',
        'contract_officer__khmer_last_name', 'contract_officer__khmer_first_name',
        'position_title', 'reference_doc', 'remarks'
    )
    date_hierarchy = 'date'


