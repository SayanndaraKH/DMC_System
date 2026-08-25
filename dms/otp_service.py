import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import OTPVerification

logger = logging.getLogger(__name__)

def send_otp_notification(identifier, otp_code, purpose='REGISTER', full_name=''):
    """
    Send OTP code via Email or log for SMS/other channels.
    """
    subject = f"លេខកូដផ្ទៀងផ្ទាត់ OTP (DMS): {otp_code}"
    
    purpose_label = "ចុះឈ្មោះគណនីថ្មី" if purpose == 'REGISTER' else "ចូលប្រើប្រាស់ប្រព័ន្ធ"
    
    message_text = f"""
សួស្តី {full_name or 'លោក-លោកស្រី'},

លេខកូដផ្ទៀងផ្ទាត់ ៦ ខ្ទង់ (OTP) របស់អ្នកសម្រាប់ {purpose_label} ក្នុង «ប្រព័ន្ធគ្រប់គ្រងឯកសាររដ្ឋបាល (DMS)» គឺ៖

==========================
   កូដ OTP:  {otp_code}
==========================

* លេខកូដនេះមានសុពលភាពរយៈពេល ១០ នាទី។
* សូមកុំចែករំលែកលេខកូដនេះទៅកាន់អ្នកដទៃជាដាច់ខាត។

ដោយក្តីគោរព,
ប្រព័ន្ធគ្រប់គ្រងឯកសាររដ្ឋបាល (Government Document Management System)
"""

    html_message = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 520px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div style="background-color: #1a4d2e; color: #ffffff; padding: 24px; text-align: center;">
            <h2 style="margin: 0; font-size: 20px;">ប្រព័ន្ធគ្រប់គ្រងឯកសាររដ្ឋបាល</h2>
            <p style="margin: 4px 0 0 0; opacity: 0.85; font-size: 13px;">Government Document Management System (DMS)</p>
        </div>
        <div style="padding: 28px 24px; background-color: #ffffff;">
            <p style="font-size: 15px; color: #333333; margin-top: 0;">
                សួស្តី <strong>{full_name or 'លោក-លោកស្រី'}</strong>,
            </p>
            <p style="font-size: 14px; color: #555555; line-height: 1.6;">
                អ្នកបានស្នើសុំលេខកូដផ្ទៀងផ្ទាត់ ៦ ខ្ទង់សម្រាប់ <strong>{purpose_label}</strong>។ សូមប្រើប្រាស់លេខកូដខាងក្រោមដើម្បីបន្ត៖
            </p>
            
            <div style="background: #f0f7f2; border: 2px dashed #2e7d32; border-radius: 10px; padding: 18px; text-align: center; margin: 24px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1a4d2e; display: inline-block;">{otp_code}</span>
            </div>
            
            <p style="font-size: 13px; color: #888888; line-height: 1.5; margin-bottom: 0;">
                ⏱️ លេខកូដនេះមានសុពលភាពរយៈពេល <strong>១០ នាទី</strong>។<br>
                🔒 សូមកុំចែករំលែកលេខកូដនេះទៅកាន់អ្នកដទៃដើម្បីសុវត្ថិភាពគណនី។
            </p>
        </div>
        <div style="background-color: #f9f9f9; padding: 16px; text-align: center; font-size: 12px; color: #888888; border-top: 1px solid #eeeeee;">
            © 2026 Government Document Management System - Cambodia
        </div>
    </div>
    """

    if '@' in identifier:
        try:
            send_mail(
                subject=subject,
                message=message_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[identifier],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"OTP Email sent successfully to {identifier}")
            return True, "Email Sent"
        except Exception as e:
            logger.warning(f"Could not send email directly: {e}")
            return True, f"Logged OTP (Mail host error: {e})"
    else:
        # Phone / SMS placeholder
        logger.info(f"OTP for phone {identifier}: {otp_code}")
        return True, "SMS Simulated"
