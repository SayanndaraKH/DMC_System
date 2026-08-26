def dms_context(request):
    if request.user.is_authenticated:
        try:
            profile = getattr(request.user, 'profile', None)
        except Exception:
            profile = None
            
        unread_notifications_count = request.user.notifications.filter(is_read=False).count()
        recent_notifications = request.user.notifications.filter(is_read=False)[:5]
        
        pending_users_count = 0
        from .models import UserProfile
        from django.contrib.auth.models import User
        from django.conf import settings

        is_impersonating = 'original_admin_id' in request.session
        is_admin_or_impersonating = (
            request.user.is_superuser or 
            request.user.username.upper() == 'ADMIN' or 
            is_impersonating
        )

        from django.db.models import Q
        all_dev_users = []
        if is_admin_or_impersonating or settings.DEBUG:
            all_dev_users = (
                User.objects.filter(is_active=True)
                .filter(
                    Q(profile__is_approved=True) |
                    Q(username__iexact='ADMIN')
                )
                .filter(profile__isnull=False)
                .select_related('profile', 'profile__department')
                .order_by('id')
            )

        if request.user.is_superuser or request.user.username.upper() == 'ADMIN' or is_impersonating:
            pending_users_count = UserProfile.objects.filter(is_approved=False).exclude(user__is_superuser=True).exclude(user__username__iexact='ADMIN').count()

        # Contract Officer module menu permission
        from .models import ContractOfficer
        is_lead_or_admin = (
            request.user.is_superuser or 
            request.user.username.upper() == 'ADMIN' or 
            getattr(profile, 'is_leadership', False) or 
            getattr(profile, 'is_admin', False)
        )
        if not is_lead_or_admin and profile and profile.department:
            dept_name = (profile.department.name_kh or '').strip().lower()
            dept_code = (profile.department.code or '').strip().upper()
            if not (dept_code.startswith('CANTON') or dept_name.startswith('ខណ្ឌ') or 'ខណ្ឌ' in dept_name):
                if dept_code in ['ADMIN', 'ADMIN_PERS', 'GEN_AFFAIRS', 'GENERAL_AFFAIRS', 'GAD', 'ADMIN_DEPT', 'LEAD']:
                    is_lead_or_admin = True
                elif 'កិច្ចការទូទៅ' in dept_name or 'កិច្ចការរដ្ឋបាលទូទៅ' in dept_name:
                    is_lead_or_admin = True
                elif ('រដ្ឋបាល' in dept_name and 'បុគ្គលិក' in dept_name) or ('រដ្ឋបាល' in dept_name and 'ទូទៅ' in dept_name):
                    is_lead_or_admin = True
                elif dept_name in ['ការិយាល័យរដ្ឋបាល បុគ្គលិក', 'ការិយាល័យរដ្ឋបាល-បុគ្គលិក', 'ការិយាល័យរដ្ឋបាល', 'ការិយាល័យកិច្ចការរដ្ឋបាលទូទៅ', 'ការិយាល័យកិច្ចការទូទៅ']:
                    is_lead_or_admin = True

        can_view_contract_officers_menu = is_lead_or_admin or (
            profile and profile.department and 
            ContractOfficer.objects.filter(department=profile.department, is_active=True).exists()
        )

        # Vehicle requests count
        from .models import VehicleRequest
        if is_lead_or_admin:
            pending_vehicle_requests_count = VehicleRequest.objects.filter(status='PENDING').count()
        elif profile and profile.department:
            pending_vehicle_requests_count = VehicleRequest.objects.filter(applicant_department=profile.department, status='PENDING').count()
        else:
            pending_vehicle_requests_count = 0

        # Leadership Attendance (Attendend B) permission:
        # Strictly for ADMIN or Administration & Personnel Office (ការិយាល័យរដ្ឋបាល-បុគ្គលិក)
        is_admin_user = request.user.is_superuser or request.user.username.upper() == 'ADMIN'
        is_admin_personnel_office = False
        if profile and profile.department:
            dept_code = (profile.department.code or '').strip().upper()
            dept_name = (profile.department.name_kh or '').strip()
            if dept_code in ['ADMIN_PERS', 'ADMIN_PERSONNEL'] or ('រដ្ឋបាល' in dept_name and 'បុគ្គលិក' in dept_name):
                is_admin_personnel_office = True

        can_manage_leadership_attendance = is_admin_user or is_admin_personnel_office

        return {
            'user_profile': profile,
            'unread_notifications_count': unread_notifications_count,
            'recent_notifications': recent_notifications,
            'pending_users_count': pending_users_count,
            'pending_vehicle_requests_count': pending_vehicle_requests_count,
            'is_impersonating': is_impersonating,
            'all_dev_users': all_dev_users,
            'is_dev_mode': settings.DEBUG,
            'can_view_contract_officers_menu': can_view_contract_officers_menu,
            'can_manage_leadership_attendance': can_manage_leadership_attendance,
        }
    return {
        'user_profile': None,
        'unread_notifications_count': 0,
        'recent_notifications': [],
        'pending_users_count': 0,
        'is_impersonating': False,
        'all_dev_users': [],
        'is_dev_mode': True,
    }
