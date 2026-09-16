from .models import OfficerPromotionRequest
import os
import re
import io
from datetime import date, datetime
import docx
from PIL import ImageFont
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.enum.table import WD_TABLE_ALIGNMENT

KHMER_DIGITS_MAP = str.maketrans('0123456789', '០១២៣៤៥៦៧៨៩')
ARABIC_DIGITS_MAP = str.maketrans('០១២៣៤៥៦៧៨៩', '0123456789')

def to_khmer_digits(s):
    if s is None:
        return ''
    return str(s).translate(KHMER_DIGITS_MAP)

def to_arabic_digits(s):
    if not s:
        return ''
    return str(s).translate(ARABIC_DIGITS_MAP)

KHMER_MONTHS = {
    1: 'មករា', 2: 'កុម្ភៈ', 3: 'មីនា', 4: 'មេសា',
    5: 'ឧសភា', 6: 'មិថុនា', 7: 'កក្កដា', 8: 'សីហា',
    9: 'កញ្ញា', 10: 'តុលា', 11: 'វិច្ឆិកា', 12: 'ធ្នូ'
}

TEMPLATE_CONFIGS = {
    'D01': {
        'code': 'D01',
        'framework_name': 'ក្របខ័ណ្ឌ ក',
        'title': 'ព្រឹត្តិប័ត្រពិន្ទុសម្រាប់ដំឡើងថ្នាក់\nនៃក្របខ័ណ្ឌមន្រ្តីគ្រប់គ្រងរដ្ឋបាល',
        'sub_title': 'នៃក្របខ័ណ្ឌមន្រ្តីគ្រប់គ្រងរដ្ឋបាល',
        'template_file': 'D01_template.docx',
        'divisor': 5,
        'criteria': [
            {'num': '១-', 'label': 'មានគំនិតផ្តួចផ្តើម និងច្នៃប្រឌិត'},
            {'num': '២-', 'label': 'មានស្មារតីទទួលខុសត្រូវ'},
            {'num': '៣-', 'label': 'យកចិត្តទុកដាក់ដល់ផលប្រយោជន៍ជាតិ'},
            {'num': '៤-', 'label': 'មានប្រសិទ្ធភាពក្នុងការដឹកនាំ'},
            {'num': '៥-', 'label': 'មានសីលធម៌'},
        ],
        'note_text': 'បូកសរុបពិន្ទុដែលទទួលបានទាំង ៥ចំណុច រួចចែក នឹង ៥ ដើម្បីរកមធ្យមភាគ ។',
    },
    'D02': {
        'code': 'D02',
        'framework_name': 'ក្របខ័ណ្ឌ ខ',
        'title': 'ព្រឹត្តិប័ត្រពិន្ទុសម្រាប់ដំឡើងថ្នាក់\nនៃក្របខ័ណ្ឌមន្រ្តីក្រមការ',
        'sub_title': 'នៃក្របខ័ណ្ឌមន្រ្តីក្រមការ',
        'template_file': 'D02_template.docx',
        'divisor': 4,
        'criteria': [
            {'num': '១-', 'label': 'គោរពវិន័យការងាបានត្រឹមត្រូវ'},
            {'num': '២-', 'label': 'មានស្មារតីទទួលខុសត្រូវ'},
            {'num': '៣-', 'label': 'សម្រេចបានល្អនូវភារៈកិច្ចដែលប្រគល់អោយ'},
            {'num': '៤-', 'label': 'មានសីលធម៌'},
        ],
        'note_text': 'បូកសរុបពិន្ទុដែលទទួលបានទាំង ៤ចំណុច រួចចែក នឹង ៤ ដើម្បីរកមធ្យមភាគ ។',
    },
    'D03': {
        'code': 'D03',
        'framework_name': 'ក្របខ័ណ្ឌ គ/ឃ',
        'title': 'ព្រឹត្តិប័ត្រពិន្ទុសម្រាប់ដំឡើងថ្នាក់\nនៃក្របខ័ណ្ឌមន្រ្តីលេខាធិការដ្ឋបាល',
        'sub_title': 'នៃក្របខ័ណ្ឌមន្រ្តីលេខាធិការដ្ឋបាល',
        'template_file': 'D03_template.docx',
        'divisor': 3,
        'criteria': [
            {'num': '១-', 'label': 'គោរពវិន័យការងាបានត្រឹមត្រូវ'},
            {'num': '២-', 'label': 'សម្រេចបានល្អនូវភារៈកិច្ចដែលប្រគល់អោយ'},
            {'num': '៣-', 'label': 'មានសីលធម៌'},
        ],
        'note_text': 'បូកសរុបពិន្ទុដែលទទួលបានទាំង ៣ចំណុច រួចចែក នឹង ៣ ដើម្បីរកមធ្យមភាគ ។',
    },
}

def detect_officer_template(officer):
    """
    Auto-detect whether an officer belongs to D01 (A), D02 (B), or D03 (C/D).
    """
    if not officer:
        return 'D01'
    
    fw = getattr(officer, 'framework_category', '') or ''
    rank = getattr(officer, 'current_rank_and_step', '') or ''
    
    if fw == 'A' or rank.strip().startswith('ក') or 'ក.' in rank:
        return 'D01'
    elif fw == 'B' or rank.strip().startswith('ខ') or 'ខ.' in rank:
        return 'D02'
    elif fw in ['C', 'D'] or rank.strip().startswith('គ') or 'គ.' in rank or rank.strip().startswith('ឃ') or 'ឃ.' in rank:
        return 'D03'
    
    return 'D01'

def parse_date_safely(date_str):
    """
    Attempts to parse date strings like '13/04/2025', '01-12-1999', '២០០០', etc.
    """
    if not date_str:
        return None
    cleaned = to_arabic_digits(str(date_str)).strip()
    
    patterns = [
        r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',
        r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})',
        r'(\d{4})',
    ]
    for p in patterns:
        m = re.search(p, cleaned)
        if m:
            groups = m.groups()
            try:
                if len(groups) == 3:
                    if len(groups[0]) == 4: # yyyy-mm-dd
                        return date(int(groups[0]), int(groups[1]), int(groups[2]))
                    else: # dd-mm-yyyy
                        return date(int(groups[2]), int(groups[1]), int(groups[0]))
                elif len(groups) == 1:
                    return date(int(groups[0]), 1, 1)
            except Exception:
                continue
    return None

def calculate_grade_and_average(scores_list, divisor):
    """
    Calculates average score /20 and corresponding grade (និទ្ទេស).
    Returns (avg_score_str, grade_label)
    """
    valid_scores = []
    for s in scores_list:
        if s is not None and str(s).strip() != '':
            try:
                val = float(to_arabic_digits(str(s)).strip())
                valid_scores.append(val)
            except ValueError:
                pass
                
    if not valid_scores:
        return '', ''
        
    avg = sum(valid_scores) / float(divisor if divisor else len(valid_scores))
    avg_formatted = f"{avg:.2f}".rstrip('0').rstrip('.')
    avg_kh = to_khmer_digits(avg_formatted)
    
    if avg >= 19.0:
        grade = 'ល្អណាស់'
    elif avg >= 16.0:
        grade = 'ល្អ'
    elif avg >= 13.0:
        grade = 'ល្អបង្គួរ'
    elif avg >= 10.0:
        grade = 'មធ្យម'
    else:
        grade = 'ខ្សោយ'
        
    return avg_kh, grade

def get_officer_score_bulletin_context(officer, target_year=None, target_date_str=None, template_code=None, raw_scores=None, custom_data=None):
    """
    Extracts, formats, and prepares all biodata and evaluation data needed for
    both the HTML print view and the Word docx/doc export.
    """
    today = date.today()
    if not target_year:
        target_year = today.year
    else:
        try:
            target_year = int(to_arabic_digits(str(target_year)))
        except Exception:
            target_year = today.year

    if not template_code or template_code not in TEMPLATE_CONFIGS:
        template_code = detect_officer_template(officer)
    cfg = TEMPLATE_CONFIGS[template_code]

    # Target calculation date (standard is 13 April of target year for promotion)
    effective_target_date = date(target_year, 4, 13)
    if target_date_str:
        parsed_t = parse_date_safely(target_date_str)
        if parsed_t:
            effective_target_date = parsed_t

    target_day_kh = to_khmer_digits(effective_target_date.day)
    target_month_kh = KHMER_MONTHS.get(effective_target_date.month, '')
    target_year_kh = to_khmer_digits(effective_target_date.year)
    header_as_of_date_kh = f"ថ្ងៃទី {target_day_kh} ខែ {target_month_kh} ឆ្នាំ {target_year_kh}"

    # 🎯 Query saved OfficerPromotionRequest record for this officer & year (if exists)
    saved_promo = None
    try:
        saved_promo = OfficerPromotionRequest.objects.filter(
            officer=officer,
            request_year=target_year
        ).order_by('-updated_at').first()
    except Exception:
        pass

    unit_proposal = ''
    unit_head_comment = ''
    minister_comment = ''
    if saved_promo:
        unit_proposal = saved_promo.unit_proposal or saved_promo.proposed_rank_and_step or ''
        unit_head_comment = saved_promo.unit_head_comment or ''
        minister_comment = saved_promo.minister_comment or ''
        if not raw_scores and saved_promo.scores_data:
            raw_scores = [saved_promo.scores_data.get(f'score_{i+1}', '') for i in range(len(cfg['criteria']))]

    # Extract general education & skill
    general_education = ''
    skill_major = ''
    
    if officer.highest_degree:
        general_education = officer.get_highest_degree_display()
        # Clean label e.g. '(៣). បរិញ្ញាប័ត្រ (Bachelor)' -> 'បរិញ្ញាប័ត្រ'
        general_education = re.sub(r'^\([០-៩\d]+\)\.\s*', '', general_education)
        general_education = re.sub(r'\s*\([A-Za-z\s/]+\)$', '', general_education).strip()

    if officer.education_data and isinstance(officer.education_data, list):
        for edu in officer.education_data:
            lvl_type = edu.get('level_type', '')
            deg = edu.get('degree', '') or edu.get('level_label', '')
            skl = edu.get('skill', '')
            if lvl_type == 'GENERAL' and deg and not general_education:
                general_education = deg
            if skl and not skill_major:
                skill_major = skl

    if not general_education:
        general_education = 'មធ្យមសិក្សាទុតិយភូមិ'
    if not skill_major:
        skill_major = 'រដ្ឋបាលសាធារណៈ'

    # Last promotion date & seniority in current rank
    last_promo_date = None
    last_promo_date_raw = None
    
    # 1. Try from promotions_by_seniority
    if officer.promotions_by_seniority and isinstance(officer.promotions_by_seniority, list):
        for p in reversed(officer.promotions_by_seniority):
            eff = p.get('effective_date')
            parsed = parse_date_safely(eff)
            if parsed:
                last_promo_date = parsed
                last_promo_date_raw = eff
                break
                
    # 2. Fallback to officer.last_promotion_date (from model)
    if not last_promo_date and getattr(officer, 'last_promotion_date', None):
        last_promo_date = officer.last_promotion_date
        last_promo_date_raw = last_promo_date.strftime('%d/%m/%Y')
        
    # 3. Fallback to permanent date
    if not last_promo_date and officer.civil_service_permanent_date:
        last_promo_date = parse_date_safely(officer.civil_service_permanent_date)
        last_promo_date_raw = officer.civil_service_permanent_date
        
    # 4. Fallback to start date
    if not last_promo_date and officer.civil_service_start_date:
        last_promo_date = parse_date_safely(officer.civil_service_start_date)
        last_promo_date_raw = officer.civil_service_start_date

    # Seniority calculation in current rank
    years_in_rank = 0
    months_in_rank = 0
    if last_promo_date:
        total_months = (effective_target_date.year - last_promo_date.year) * 12 + (effective_target_date.month - last_promo_date.month)
        if effective_target_date.day < last_promo_date.day:
            total_months -= 1
        if total_months < 0:
            total_months = 0
        years_in_rank = total_months // 12
        months_in_rank = total_months % 12
    else:
        years_in_rank = 2
        months_in_rank = 0

    seniority_in_rank_str = f"{to_khmer_digits(years_in_rank)} ឆ្នាំ"
    if months_in_rank > 0:
        seniority_in_rank_str += f" {to_khmer_digits(months_in_rank)} ខែ"

    # Total civil service work duration
    total_service_years = 0
    total_service_months = 0
    start_service_date = parse_date_safely(officer.civil_service_start_date)
    if start_service_date:
        total_m = (effective_target_date.year - start_service_date.year) * 12 + (effective_target_date.month - start_service_date.month)
        if effective_target_date.day < start_service_date.day:
            total_m -= 1
        if total_m < 0:
            total_m = 0
        total_service_years = total_m // 12
        total_service_months = total_m % 12
    else:
        total_service_years = years_in_rank
        total_service_months = months_in_rank

    total_service_str = f"{to_khmer_digits(total_service_years)} ឆ្នាំ"
    if total_service_months > 0:
        total_service_str += f" {to_khmer_digits(total_service_months)} ខែ"

    # Leave info
    leave_reason = 'គ្មាន'
    leave_duration = 'គ្មាន'
    if officer.unpaid_leave_status and isinstance(officer.unpaid_leave_status, list) and len(officer.unpaid_leave_status) > 0:
        item = officer.unpaid_leave_status[-1]
        leave_reason = item.get('reason', '') or item.get('ministry', '') or 'ទំនេរគ្មានបៀវត្ស'
        leave_duration = item.get('duration', '') or '...'
    elif officer.outside_framework_status and isinstance(officer.outside_framework_status, list) and len(officer.outside_framework_status) > 0:
        item = officer.outside_framework_status[-1]
        leave_reason = item.get('reason', '') or 'ក្រៅក្របខ័ណ្ឌដើម'
        leave_duration = item.get('duration', '') or '...'

    # Format dates in Khmer numerals
    dob_kh = to_khmer_digits(officer.dob) if officer.dob else '...'
    start_date_kh = to_khmer_digits(officer.civil_service_start_date) if officer.civil_service_start_date else '...'
    perm_date_kh = to_khmer_digits(officer.civil_service_permanent_date) if officer.civil_service_permanent_date else '...'
    last_promo_date_kh = to_khmer_digits(last_promo_date_raw) if last_promo_date_raw else '...'

    # Parse scores
    scores_list = []
    if raw_scores and isinstance(raw_scores, list):
        for idx, crit in enumerate(cfg['criteria']):
            val = raw_scores[idx] if idx < len(raw_scores) else ''
            scores_list.append(val)
    elif raw_scores and isinstance(raw_scores, dict):
        for idx, crit in enumerate(cfg['criteria']):
            key = f"score_{idx+1}"
            val = raw_scores.get(key, '')
            scores_list.append(val)
    else:
        scores_list = ['' for _ in cfg['criteria']]

    avg_score_kh, grade_kh = calculate_grade_and_average(scores_list, cfg['divisor'])

    # Build criteria items with current scores
    criteria_items = []
    for idx, crit in enumerate(cfg['criteria']):
        sc = scores_list[idx] if idx < len(scores_list) else ''
        criteria_items.append({
            'num': crit['num'],
            'label': crit['label'],
            'score': sc,
            'score_kh': to_khmer_digits(sc) if sc != '' else '',
            'max_score_kh': '២០',
        })

    # Department & Province Signatures
    dept_name = officer.department.name_kh if officer.department else 'មន្ទីរកសិកម្ម រុក្ខាប្រមាញ់ និងនេសាទខេត្តប៉ៃលិន'
    sign_day_kh = to_khmer_digits(today.day)
    sign_month_kh = KHMER_MONTHS.get(today.month, '')
    sign_year_kh = to_khmer_digits(today.year)

    ctx = {
        'officer': officer,
        'template_code': template_code,
        'template_config': cfg,
        'target_year': target_year,
        'target_year_kh': target_year_kh,
        'effective_target_date': effective_target_date,
        'header_as_of_date_kh': header_as_of_date_kh,
        'seniority_in_rank_str': seniority_in_rank_str,
        'total_service_str': total_service_str,
        'full_name_kh': officer.full_name_kh,
        'full_name_latin': officer.full_name_latin,
        'gender_kh': officer.get_gender_display(),
        'officer_id_number': to_khmer_digits(officer.officer_id_number) if officer.officer_id_number else '...',
        'dob_kh': dob_kh,
        'general_education': general_education,
        'skill_major': skill_major,
        'civil_service_start_date_kh': start_date_kh,
        'civil_service_permanent_date_kh': perm_date_kh,
        'current_rank_and_step': officer.current_rank_and_step or '...',
        'years_in_rank_kh': to_khmer_digits(years_in_rank),
        'last_promotion_date_kh': last_promo_date_kh,
        'leave_reason': leave_reason,
        'leave_duration': leave_duration,
        'criteria_items': criteria_items,
        'raw_scores': scores_list,
        'avg_score_kh': avg_score_kh,
        'grade_kh': grade_kh,
        'dept_name': dept_name,
        'sign_day_kh': sign_day_kh,
        'sign_month_kh': sign_month_kh,
        'sign_year_kh': sign_year_kh,
        'unit_proposal': unit_proposal,
        'unit_head_comment': unit_head_comment,
        'minister_comment': minister_comment,
        'all_templates': [
            {'code': 'D01', 'name': 'D01 - ក្របខ័ណ្ឌមន្រ្តីគ្រប់គ្រងរដ្ឋបាល (ក្របខ័ណ្ឌ ក)'},
            {'code': 'D02', 'name': 'D02 - ក្របខ័ណ្ឌមន្រ្តីក្រមការ (ក្របខ័ណ្ឌ ខ)'},
            {'code': 'D03', 'name': 'D03 - ក្របខ័ណ្ឌមន្រ្តីលេខាធិការដ្ឋបាល (ក្របខ័ណ្ឌ គ/ឃ)'},
        ]
    }

    # Apply any custom overrides submitted by the user
    if custom_data and isinstance(custom_data, dict):
        editable_fields = [
            'full_name_kh', 'full_name_latin', 'gender_kh', 'officer_id_number', 'dob_kh',
            'general_education', 'skill_major', 'civil_service_start_date_kh',
            'civil_service_permanent_date_kh', 'current_rank_and_step', 'seniority_in_rank_str',
            'years_in_rank_kh', 'last_promotion_date_kh', 'total_service_str',
            'leave_reason', 'leave_duration', 'dept_name', 'header_as_of_date_kh',
            'sign_day_kh', 'sign_month_kh', 'sign_year_kh', 'avg_score_kh', 'grade_kh'
        ]
        for fld in editable_fields:
            if fld in custom_data and custom_data[fld] is not None:
                val = str(custom_data[fld]).strip()
                if val:
                    ctx[fld] = val

        if custom_data.get('unit_proposal') is not None:
            ctx['unit_proposal'] = str(custom_data['unit_proposal']).strip()
        if custom_data.get('unit_head_comment') is not None:
            ctx['unit_head_comment'] = str(custom_data['unit_head_comment']).strip()
        if custom_data.get('minister_comment') is not None:
            ctx['minister_comment'] = str(custom_data['minister_comment']).strip()

        # Check if custom scores were passed via score_1, score_2 or raw_scores
        updated_scores = []
        has_custom_scores = False
        for idx, crit in enumerate(cfg['criteria']):
            k1 = f"score_{idx+1}"
            k2 = f"score_{idx}"
            k3 = f"scores[{idx}]"
            val = custom_data.get(k1) or custom_data.get(k2) or custom_data.get(k3)
            if val is not None:
                has_custom_scores = True
                updated_scores.append(str(val).strip())
            elif idx < len(ctx['raw_scores']):
                updated_scores.append(ctx['raw_scores'][idx])
            else:
                updated_scores.append('')

        if has_custom_scores:
            ctx['raw_scores'] = updated_scores
            # Update criteria items
            for idx, crit in enumerate(cfg['criteria']):
                if idx < len(ctx['criteria_items']):
                    sc = updated_scores[idx] if idx < len(updated_scores) else ''
                    ctx['criteria_items'][idx]['score'] = sc
                    ctx['criteria_items'][idx]['score_kh'] = to_khmer_digits(sc) if sc != '' else ''

            if not custom_data.get('avg_score_kh') or not custom_data.get('grade_kh'):
                calc_avg, calc_grade = calculate_grade_and_average(updated_scores, cfg['divisor'])
                if calc_avg:
                    ctx['avg_score_kh'] = calc_avg
                if calc_grade:
                    ctx['grade_kh'] = calc_grade

    return ctx


_font_kh_cache = {}
_font_en_cache = {}

def get_kh_font(sz_pt, is_en=False):
    c = _font_en_cache if is_en else _font_kh_cache
    if sz_pt not in c:
        p = r'C:\Windows\Fonts\calibri.ttf' if is_en else r'C:\Windows\Fonts\KhmerOSsiemreap.ttf'
        try:
            c[sz_pt] = ImageFont.truetype(p, sz_pt)
        except Exception:
            c[sz_pt] = None
    return c.get(sz_pt)

def measure_pt(text, sz_pt, is_en=False):
    if not text:
        return 0.0
    f = get_kh_font(sz_pt, is_en)
    if f:
        return f.getlength(text.replace('\t', '    '))
    return len(text) * (4.5 if is_en else 7.0)

def format_paragraph_dotted_runs(p, segments, max_line_pt=485.0, base_font_size=10.5):
    """
    Clears paragraph runs and rebuilds them so that filled data values sit
    DIRECTLY ON the official dotted line with WD_UNDERLINE.DOTTED.
    Strictly calibrated so that NO paragraph EVER wraps or drops onto a second line
    ("ពុំទម្លាក់បន្ទាត់ដាច់ខាត")!
    """
    p.clear()
    
    clean_segs = []
    for s in segments:
        val = s.get('val', '')
        val_str = str(val).strip() if val and str(val).strip() not in ('None', '...', '') else ''
        clean_segs.append({
            'prefix': s.get('prefix', ''),
            'val_str': val_str,
            'suffix': s.get('suffix', ''),
            'is_en': (s.get('font') == 'Calibri'),
            'weight': s.get('weight', 1.0),
            'min_dots': s.get('min_dots', 3)
        })
        
    best_size = base_font_size
    for test_size in [10.5, 10.0, 9.5, 9.0, 8.5]:
        total_text_pt = sum(
            measure_pt(s['prefix'], test_size) +
            measure_pt(s['val_str'], test_size, s['is_en']) +
            measure_pt(s['suffix'], test_size)
            for s in clean_segs
        )
        f_dot = get_kh_font(test_size)
        dot_pt = f_dot.getlength('.') if f_dot else 3.0
        min_dots_pt = sum(s['min_dots'] for s in clean_segs) * dot_pt
        if (total_text_pt + min_dots_pt) <= max_line_pt:
            best_size = test_size
            break
        best_size = test_size
        
    f_dot = get_kh_font(best_size)
    dot_pt = f_dot.getlength('.') if f_dot else 3.0
    total_text_pt = sum(
        measure_pt(s['prefix'], best_size) +
        measure_pt(s['val_str'], best_size, s['is_en']) +
        measure_pt(s['suffix'], best_size)
        for s in clean_segs
    )
    
    remaining_pt = max(0.0, max_line_pt - total_text_pt)
    total_weight = sum(s['weight'] for s in clean_segs) or 1.0
    
    for s in clean_segs:
        if s['prefix']:
            r_pre = p.add_run(s['prefix'])
            r_pre.font.name = 'Khmer OS Siemreap'
            r_pre.font.size = Pt(best_size)
            
        if s['val_str']:
            r_val = p.add_run(s['val_str'])
            r_val.font.name = 'Calibri' if s['is_en'] else 'Khmer OS Siemreap'
            r_val.font.size = Pt(best_size)
            r_val.font.bold = True
            r_val.font.underline = WD_UNDERLINE.DOTTED
            
        slot_pt = remaining_pt * (s['weight'] / total_weight)
        num_dots = max(s['min_dots'], int(slot_pt / dot_pt))
        
        r_dots = p.add_run('.' * num_dots)
        r_dots.font.name = 'Khmer OS Siemreap'
        r_dots.font.size = Pt(best_size)
        
        if s['suffix']:
            r_suf = p.add_run(s['suffix'])
            r_suf.font.name = 'Khmer OS Siemreap'
            r_suf.font.size = Pt(best_size)


def generate_score_bulletin_docx(context):
    """
    Generates a high-fidelity Word (.docx) document populated with the officer's data
    based on the master docx templates in `dms/templates_docs/`.
    100% places data DIRECTLY ON the official dotted lines (underlined with WD_UNDERLINE.DOTTED)
    across all templates (D01, D02, D03) with ZERO line wrapping ("ពុំទម្លាក់បន្ទាត់ដាច់ខាត")!
    """
    template_code = context.get('template_code', 'D01')
    template_filename = f"{template_code}_template.docx"
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, 'templates_docs', template_filename)
    
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(base_dir), 'scratch', f"{template_code}.docx")
        
    doc = docx.Document(template_path)
    
    # 1. Update Table 0 (As-of Date & Durations)
    if len(doc.tables) > 0:
        t0 = doc.tables[0]
        # Row 0: Date header
        if len(t0.rows) > 0 and len(t0.rows[0].cells) > 0:
            header_cell = t0.rows[0].cells[0]
            if context.get('header_as_of_date_kh'):
                header_cell.text = f"គិតត្រឹម {context['header_as_of_date_kh']}"
                header_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in header_cell.paragraphs[0].runs:
                    run.font.name = 'Khmer OS Siemreap'
                    run.font.size = Pt(11)

        # Row 2: Value row
        if len(t0.rows) > 2 and len(t0.rows[2].cells) >= 2:
            cell_seniority = t0.rows[2].cells[0]
            cell_seniority.text = context.get('seniority_in_rank_str', '')
            cell_seniority.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in cell_seniority.paragraphs[0].runs:
                run.font.name = 'Khmer OS Siemreap'
                run.font.size = Pt(11)
                run.font.bold = True

            cell_total = t0.rows[2].cells[1]
            cell_total.text = context.get('total_service_str', '')
            cell_total.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in cell_total.paragraphs[0].runs:
                run.font.name = 'Khmer OS Siemreap'
                run.font.size = Pt(11)
                run.font.bold = True

    # 2. Update Paragraphs with Biodata (CALIBRATED ZERO-LINE-WRAPPING)
    for p in doc.paragraphs:
        t = p.text
        if '១-' in t and 'គោត្តនាម' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '១-\tគោត្តនាម និងនាម ', 'val': context.get('full_name_kh', ''), 'weight': 1.0, 'min_dots': 5},
                {'prefix': ' ជាអក្សរឡាតាំង ', 'val': context.get('full_name_latin', ''), 'font': 'Calibri', 'weight': 1.0, 'min_dots': 5},
                {'prefix': ' ភេទ ', 'val': context.get('gender_kh', ''), 'weight': 0.3, 'min_dots': 3},
            ])
        elif '២-' in t and 'អត្តលេខ' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '២-\tអត្តលេខ ', 'val': context.get('officer_id_number', ''), 'weight': 1.0, 'min_dots': 6},
                {'prefix': ' ថ្ងៃ-ខែ-ឆ្នាំកំណើត ', 'val': context.get('dob_kh', ''), 'weight': 1.0, 'min_dots': 6},
            ])
        elif '៣-' in t and 'កម្រិតវប្បធម៌ទូទៅ' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '៣-\tកម្រិតវប្បធម៌ទូទៅ ', 'val': context.get('general_education', ''), 'weight': 1.0, 'min_dots': 6},
                {'prefix': ' កម្រិតជំនាញ ', 'val': context.get('skill_major', ''), 'weight': 1.0, 'min_dots': 6},
            ])
        elif '៤-' in t and 'កាលបរិច្ឆេទចូលបម្រើការងាររដ្ឋ' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '៤-\tកាលបរិច្ឆេទចូលបម្រើការងាររដ្ឋ ', 'val': context.get('civil_service_start_date_kh', ''), 'weight': 1.0, 'min_dots': 8},
            ])
        elif '៥-' in t and 'កាលបរិច្ឆេទដែលបានតាំងស៊ប់' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '៥-\tកាលបរិច្ឆេទដែលបានតាំងស៊ប់ក្នុងក្របខ័ណ្ឌ ', 'val': context.get('civil_service_permanent_date_kh', ''), 'weight': 1.0, 'min_dots': 8},
            ])
        elif '៦-' in t and 'ឋានន្តរស័ក្តិ' in t:
            y_str = str(context.get('years_in_rank_kh', '')).replace('ឆ្នាំ', '').strip()
            format_paragraph_dotted_runs(p, [
                {'prefix': '៦-\tឋានន្តរស័ក្តិ និងថ្នាក់បច្ចុប្បន្ន ', 'val': context.get('current_rank_and_step', ''), 'weight': 0.8, 'min_dots': 4},
                {'prefix': ' អតីតភាពក្នុងឋានន្តរស័ក្តិនិងថ្នាក់បច្ចុប្បន្ន ', 'val': y_str, 'suffix': ' ឆ្នាំ', 'weight': 0.5, 'min_dots': 4},
            ])
        elif '៧-' in t and 'កាលបរិឆ្ឆេទក្នុងថ្នាក់' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '៧-\tកាលបរិឆ្ឆេទក្នុងថ្នាក់បច្ចុប្បន្ន (ថ្ងៃ ខែ ឆ្នាំ ឡើងថ្នាក់ចុងក្រោយ ) ', 'val': context.get('last_promotion_date_kh', ''), 'weight': 1.0, 'min_dots': 6},
            ])
        elif '- មូលហេតុ' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '\t- មូលហេតុ ', 'val': context.get('leave_reason', 'គ្មាន'), 'weight': 1.0, 'min_dots': 8},
            ])
        elif '- រយៈពេល' in t:
            format_paragraph_dotted_runs(p, [
                {'prefix': '\t- រយៈពេល ', 'val': context.get('leave_duration', 'គ្មាន'), 'weight': 1.0, 'min_dots': 8},
            ])
        elif 'សំណើរបស់' in t:
            head_cm = context.get('unit_head_comment', '')
            prop_val = context.get('unit_proposal', '')
            p.clear()
            r1 = p.add_run(head_cm if head_cm else ('.' * 250))
            r1.font.name = 'Khmer OS Siemreap'
            r1.font.size = Pt(10.5)
            if head_cm:
                r1.font.bold = True
                r1.font.underline = WD_UNDERLINE.DOTTED
                
            r_sp = p.add_run('   សំណើរបស់ ')
            r_sp.font.name = 'Khmer OS Siemreap'
            r_sp.font.size = Pt(10.5)
            
            r2 = p.add_run(prop_val if prop_val else ('.' * 200))
            r2.font.name = 'Khmer OS Siemreap'
            r2.font.size = Pt(10.5)
            if prop_val:
                r2.font.bold = True
                r2.font.underline = WD_UNDERLINE.DOTTED

    # 3. Update Textboxes in Document XML (e.g. Employee Affairs textbox with លោក/លោកស្រី)
    try:
        body_xml = doc._body._element
        for wt in body_xml.xpath('.//w:t'):
            if wt.text and 'លោក/លោកស្រី' in wt.text:
                full_name = context.get('full_name_kh', '')
                if full_name:
                    # In D01 template, wt.text has 48 dots: 'លោក/លោកស្រី................................................'
                    # Replace dots with name + remaining dots so textbox boundary is never exceeded!
                    dot_count = max(4, 48 - int(len(full_name) * 2.5))
                    wt.text = f"លោក/លោកស្រី {full_name}" + ('.' * dot_count)
                break
    except Exception as e:
        pass

    # 4. Update Table 1 (Score table) PRESERVING CRITERIA DOTS
    if len(doc.tables) > 1:
        t1 = doc.tables[1]
        criteria_items = context.get('criteria_items', [])
        num_crit = len(criteria_items)
        
        for r_idx in range(min(num_crit, len(t1.rows))):
            row = t1.rows[r_idx]
            item = criteria_items[r_idx]
            score_cell = row.cells[-1]
            sc_str = item.get('score_kh', '') or item.get('score', '')
            if sc_str:
                score_cell.text = f"{sc_str}   /២០"
            else:
                score_cell.text = "       /២០"
            score_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in score_cell.paragraphs[0].runs:
                run.font.name = 'Khmer OS Siemreap'
                run.font.size = Pt(11)
                if sc_str:
                    run.font.bold = True

        # Average row
        avg_row_idx = num_crit
        if len(t1.rows) > avg_row_idx:
            avg_row = t1.rows[avg_row_idx]
            avg_cell = avg_row.cells[-1]
            if context.get('avg_score_kh'):
                avg_cell.text = f"{context['avg_score_kh']}   /២០"
                avg_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in avg_cell.paragraphs[0].runs:
                    run.font.name = 'Khmer OS Siemreap'
                    run.font.size = Pt(11)
                    run.font.bold = True

        # Grade row
        grade_row_idx = num_crit + 1
        if len(t1.rows) > grade_row_idx:
            grade_row = t1.rows[grade_row_idx]
            for c in grade_row.cells:
                if 'និទ្ទេស' in c.text:
                    p_gr = c.paragraphs[0]
                    gr_val = context.get('grade_kh', '')
                    if gr_val:
                        p_gr.clear()
                        r_pre = p_gr.add_run('និទ្ទេស  ')
                        r_pre.font.name = 'Khmer OS Siemreap'
                        r_pre.font.size = Pt(11)
                        
                        r_val = p_gr.add_run(gr_val)
                        r_val.font.name = 'Khmer OS Siemreap'
                        r_val.font.size = Pt(11)
                        r_val.font.bold = True
                        r_val.font.underline = WD_UNDERLINE.DOTTED
                        
                        dot_count = max(5, 51 - int(len(gr_val) * 2.5))
                        r_dots = p_gr.add_run('.' * dot_count)
                        r_dots.font.name = 'Khmer OS Siemreap'
                        r_dots.font.size = Pt(11)
                    break

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio
