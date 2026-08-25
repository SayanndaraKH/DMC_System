import re
import os
import zipfile
import xml.etree.ElementTree as ET

KHMER_DIGITS_MAP = str.maketrans('០១២៣៤៥៦៧៨៩', '0123456789')

def to_arabic_digits(text):
    """
    Converts Khmer digits (០១២៣៤៥៦៧៨៩) to Arabic numerals (0123456789).
    Example: ១៨០០៣០០១០៦ -> 1800300106
    """
    if not text:
        return ""
    return str(text).translate(KHMER_DIGITS_MAP).strip()

def clean_khmer_text(text):
    if not text:
        return ""
    text = text.replace('\u200b', '').replace('\u200c', '').replace('\xa0', ' ')
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text

def clean_province(p):
    p = clean_khmer_text(p)
    p = re.sub(r'^(?:រាជធានី|ខេត្ត|រាជធានី/ខេត្ត|/ខេត្ត|/រាជធានី)\s*', '', p)
    return p.strip()

def clean_noise(text):
    if not text:
        return ""
    text = clean_khmer_text(text)
    text = re.sub(r'\.{2,}', '', text).strip()
    return text

def parse_docx_officer(file_path_or_file, original_filename=None):
    """
    Parses any Cambodian Civil Servant Biography .docx file and returns a structured dictionary
    ready to populate CivilServantProfile.
    Uses dynamic table discovery, multi-cell regex, paragraph extraction, and filename fallback
    to guarantee high resilience on all docx formats.
    """
    if hasattr(file_path_or_file, 'name') and not original_filename:
        original_filename = file_path_or_file.name
    elif isinstance(file_path_or_file, str) and not original_filename:
        original_filename = os.path.basename(file_path_or_file)

    tables = []
    paragraphs = []

    with zipfile.ZipFile(file_path_or_file) as z:
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        # Extract all paragraphs for text fallback
        for p in tree.findall('.//w:p', ns):
            p_text = clean_khmer_text(''.join([t.text for t in p.findall('.//w:t', ns) if t.text]))
            if p_text:
                paragraphs.append(p_text)

        # Extract all tables
        for tbl in tree.findall('.//w:tbl', ns):
            tbl_rows = []
            for tr in tbl.findall('.//w:tr', ns):
                row_cells = []
                for tc in tr.findall('.//w:tc', ns):
                    tc_texts = [t.text for t in tc.findall('.//w:t', ns) if t.text]
                    cell_text = clean_khmer_text(''.join(tc_texts))
                    row_cells.append(cell_text)
                if any(row_cells):
                    tbl_rows.append(row_cells)
            if tbl_rows:
                tables.append(tbl_rows)

    data = {
        'khmer_last_name': '',
        'khmer_first_name': '',
        'latin_last_name': '',
        'latin_first_name': '',
        'gender': 'MALE',
        'dob': '',
        'ethnicity': 'ខ្មែរ',
        'nationality': 'ខ្មែរ',
        'pob_village': '',
        'pob_commune': '',
        'pob_district': '',
        'pob_province': '',
        'current_house_no': '',
        'current_street': '',
        'current_village': '',
        'current_commune': '',
        'current_district': '',
        'current_province': '',
        'perm_same_as_current': True,
        'perm_house_no': '',
        'perm_street': '',
        'perm_village': '',
        'perm_commune': '',
        'perm_district': '',
        'perm_province': '',
        'phone': '',
        'email': '',
        'officer_id_number': '',
        'national_id_number': '',
        'national_id_valid_from': '',
        'national_id_valid_to': '',
        'physical_condition': 'គ្រប់គ្រាន់',
        'disability_detail': '',
        'marital_status': 'MARRIED',
        'spouse_marriage_cert_no': '',
        'spouse_name_kh': '',
        'spouse_is_alive': True,
        'spouse_name_latin': '',
        'spouse_dob': '',
        'spouse_national_id': '',
        'spouse_pob': '',
        'spouse_occupation': '',
        'spouse_current_address': '',
        'spouse_organization': '',
        'children_data': [],
        'father_name': '',
        'father_is_alive': True,
        'father_pob': '',
        'father_occupation': '',
        'mother_name': '',
        'mother_is_alive': True,
        'mother_pob': '',
        'mother_occupation': '',
        'emergency_last_name': '',
        'emergency_first_name': '',
        'emergency_gender': 'FEMALE',
        'emergency_relationship': '',
        'emergency_occupation': '',
        'emergency_address': '',
        'emergency_phone': '',
        'emergency_email': '',
        'education_data': [],
        'languages_data': [],
        'civil_service_start_date': '',
        'civil_service_permanent_date': '',
        'framework_name': '',
        'current_rank_and_step': '',
        'current_position_title': 'មន្ត្រី',
        'history_public_sector': [],
        'history_private_sector': [],
        'promotions_by_seniority': [],
        'promotions_by_degree': [],
        'outside_framework_status': [],
        'unpaid_leave_status': [],
        'awards_data': [],
        'sanctions_data': [],
    }

    # =========================================================================
    # 1. SCAN ALL TABLES FOR PERSONAL INFO (Section ក)
    # =========================================================================
    for tbl in tables:
        for row in tbl:
            row_str = ' '.join(row)

            # --- Name (Khmer) ---
            if not data['khmer_last_name'] or not data['khmer_first_name']:
                if 'ឈ្មោះជាភាសាខ្មែរ' in row_str or 'គោត្តនាម' in row_str or 'នាមខ្លួន' in row_str or 'គោត្តនាម/នាម' in row_str or 'គោត្តនាម និងនាម' in row_str:
                    for cell in row:
                        m_both = re.search(r'(?:គោត្តនាម/នាម|គោត្តនាម និងនាម|គោត្តនាមនិងនាម|ឈ្មោះ|នាម)\s*[:\.\-]?\s*([\u1780-\u17F9\s]+)', cell)
                        if m_both:
                            parts = [p.strip() for p in m_both.group(1).split() if p.strip()]
                            if len(parts) >= 2 and not data['khmer_last_name']:
                                data['khmer_last_name'] = parts[0]
                                data['khmer_first_name'] = ' '.join(parts[1:])
                        m_last = re.search(r'គោត្តនាម\s*[:\.\-]?\s*([\u1780-\u17F9\s]+?)(?=\s*នាមខ្លួន|\s*នាម|\s*ភេទ|$)', cell)
                        if m_last and m_last.group(1).strip():
                            data['khmer_last_name'] = clean_noise(m_last.group(1))
                        m_first = re.search(r'(?:នាមខ្លួន|នាម)\s*[:\.\-]?\s*([\u1780-\u17F9\s]+?)(?=\s*ភេទ|$)', cell)
                        if m_first and m_first.group(1).strip():
                            data['khmer_first_name'] = clean_noise(m_first.group(1))
                        if 'ភេទ' in cell:
                            if 'ស្រី' in cell: data['gender'] = 'FEMALE'
                            elif 'ប្រុស' in cell: data['gender'] = 'MALE'

            # --- Name (Latin) ---
            if not data['latin_last_name'] or not data['latin_first_name']:
                if 'ឈ្មោះជាអក្សរពុម្ព' in row_str or 'ទ្បាតាំង' in row_str or 'ឡាតាំង' in row_str or 'Latin' in row_str or 'Nom et' in row_str:
                    for cell in row:
                        m_lat_last = re.search(r'គោត្តនាម\s*[:\.\-]?\s*([A-Za-z\s]+?)(?=\s*នាមខ្លួន|\s*First|$)', cell, re.IGNORECASE)
                        if m_lat_last: data['latin_last_name'] = clean_noise(m_lat_last.group(1))
                        m_lat_first = re.search(r'នាមខ្លួន\s*[:\.\-]?\s*([A-Za-z\s]+)', cell, re.IGNORECASE)
                        if m_lat_first: data['latin_first_name'] = clean_noise(m_lat_first.group(1))
                        if not data['latin_last_name']:
                            m_lat_all = re.search(r'(?:ឡាតាំង|ទ្បាតាំង|Latin|Name)\s*[:\.\-]?\s*([A-Za-z\s]{3,})', cell, re.IGNORECASE)
                            if m_lat_all:
                                lparts = [p.strip() for p in m_lat_all.group(1).split() if p.strip()]
                                if len(lparts) >= 2:
                                    data['latin_last_name'] = lparts[0]
                                    data['latin_first_name'] = ' '.join(lparts[1:])
                                elif len(lparts) == 1:
                                    data['latin_last_name'] = lparts[0]

            # --- DOB & Nationality ---
            if not data['dob'] and 'ថ្ងៃខែឆ្នាំកំណើត' in row_str:
                for idx, cell in enumerate(row):
                    if 'ថ្ងៃខែឆ្នាំកំណើត' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        m_dob = re.search(r'([0-9០-៩]+[\.\-\/\s]+(?:[0-9០-៩]+|[^\s]+)[\.\-\/\s]+[0-9០-៩]+|[0-9០-៩]{4})', val)
                        if m_dob: data['dob'] = clean_noise(m_dob.group(1))
                        if 'ជនជាតិ' in val:
                            m_eth = re.search(r'ជនជាតិ\s*[:\.\-]?\s*(.*?)(?=\s*សញ្ជាតិ|$)', val)
                            if m_eth: data['ethnicity'] = clean_noise(m_eth.group(1)) or 'ខ្មែរ'
                        if 'សញ្ជាតិ' in val:
                            m_nat = re.search(r'សញ្ជាតិ\s*[:\.\-]?\s*(.*)', val)
                            if m_nat: data['nationality'] = clean_noise(m_nat.group(1)) or 'ខ្មែរ'

            # --- Officer ID Number ---
            if not data['officer_id_number'] and ('អត្តលេខ' in row_str or 'អត្ដលេខ' in row_str):
                for idx, cell in enumerate(row):
                    if 'អត្តលេខ' in cell or 'អត្ដលេខ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        m_num = re.search(r'([0-9០-៩]{6,12})', val)
                        if m_num: data['officer_id_number'] = to_arabic_digits(m_num.group(1))

            # --- POB ---
            if not data['pob_province'] and 'ទីកន្លែងកំណើត' in row_str and 'ប្តី' not in row_str and 'ប្រពន្ធ' not in row_str and 'ឪពុក' not in row_str and 'ម្តាយ' not in row_str:
                for cell in row:
                    m_v = re.search(r'ភូមិ\s*(.*?)(?=\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', cell)
                    if m_v: data['pob_village'] = clean_noise(m_v.group(1))
                    m_c = re.search(r'(?:ឃុំ/សង្កាត់|ឃុំ|សង្កាត់)\s*(.*?)(?=\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', cell)
                    if m_c: data['pob_commune'] = clean_noise(m_c.group(1))
                    m_d = re.search(r'(?:ស្រុក/ខណ្ឌ|ស្រុក|ខណ្ឌ)\s*(.*?)(?=\s*រាជធានី|\s*ខេត្ត|$)', cell)
                    if m_d: data['pob_district'] = clean_noise(m_d.group(1))
                    m_p = re.search(r'(?:រាជធានី/ខេត្ត|រាជធានី|ខេត្ត)\s*(.*)', cell)
                    if m_p: data['pob_province'] = clean_province(m_p.group(1))

            # --- Current Address ---
            if not data['current_province'] and 'អាសយដ្ឋានបច្ចុប្បន្ន' in row_str and 'ប្តី' not in row_str and 'ប្រពន្ធ' not in row_str and 'អាសន្ន' not in row_str:
                for cell in row:
                    m_h = re.search(r'[#\s]*([^ផ្លភ]+?)(?=\s*ផ្លូវ|\s*ភូមិ|\s*ឃុំ|\s*សង្កាត់|$)', cell)
                    if m_h: data['current_house_no'] = clean_noise(m_h.group(1)).replace('#', '').strip()
                    m_st = re.search(r'ផ្លូវ\s*([^ភឃស្រ]+?)(?=\s*ភូមិ|\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|$)', cell)
                    if m_st: data['current_street'] = clean_noise(m_st.group(1))
                    m_v = re.search(r'ភូមិ\s*(.*?)(?=\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', cell)
                    if m_v: data['current_village'] = clean_noise(m_v.group(1))
                    m_c = re.search(r'(?:ឃុំ/សង្កាត់|ឃុំ|សង្កាត់)\s*(.*?)(?=\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', cell)
                    if m_c: data['current_commune'] = clean_noise(m_c.group(1))
                    m_d = re.search(r'(?:ស្រុក/ខណ្ឌ|ស្រុក|ខណ្ឌ)\s*(.*?)(?=\s*រាជធានី|\s*ខេត្ត|$)', cell)
                    if m_d: data['current_district'] = clean_noise(m_d.group(1))
                    m_p = re.search(r'(?:រាជធានី/ខេត្ត|រាជធានី|ខេត្ត)\s*(.*)', cell)
                    if m_p: data['current_province'] = clean_province(m_p.group(1))

            # --- Phone & Email ---
            if not data['phone'] and 'លេខទូរស័ព្ទ' in row_str and 'អាសន្ន' not in row_str and 'ប្តី' not in row_str:
                for cell in row:
                    m_ph = re.search(r'([0-9០-៩\s\-\.\/]{8,15})', cell)
                    if m_ph: data['phone'] = to_arabic_digits(m_ph.group(1)).replace(' ', '').replace('-', '')
                    if '@' in cell:
                        m_em = re.search(r'([\w\.-]+@[\w\.-]+)', cell)
                        if m_em: data['email'] = m_em.group(1)

            # --- National ID ---
            if not data['national_id_number'] and 'លេខអត្តសញ្ញាណប័ណ្ណ' in row_str and 'ប្តី' not in row_str and 'ប្រពន្ធ' not in row_str:
                for cell in row:
                    m_id = re.search(r'([0-9០-៩]{9,12})', cell)
                    if m_id: data['national_id_number'] = to_arabic_digits(m_id.group(1))

            # --- Physical Condition ---
            if 'កាយសម្បទា' in row_str:
                if 'ពិការ' in row_str and 'គ្រប់គ្រាន់' not in row_str:
                    data['physical_condition'] = 'ពិការ'

            # --- Spouse Info ---
            if 'សំបុត្រអាពាហ៏ពិពាហ៏' in row_str or 'សំបុត្រអាពាហ៍ពិពាហ៍' in row_str:
                for idx, cell in enumerate(row):
                    if 'សំបុត្រ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        data['spouse_marriage_cert_no'] = clean_noise(val)
            if ('ឈ្មោះប្រពន្ធ' in row_str or 'ឈ្មោះប្តី' in row_str) and not data['spouse_name_kh']:
                for idx, cell in enumerate(row):
                    if 'ឈ្មោះប្រពន្ធ' in cell or 'ឈ្មោះប្តី' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        data['spouse_name_kh'] = clean_noise(val.replace('រស់', '').replace('ស្លាប់', ''))
                        data['spouse_is_alive'] = 'ស្លាប់' not in val

            # --- Parents ---
            if 'ឪពុកឈ្មោះ' in row_str and not data['father_name']:
                for idx, cell in enumerate(row):
                    if 'ឪពុកឈ្មោះ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        data['father_name'] = clean_noise(val.replace('រស់', '').replace('ស្លាប់', ''))
                        data['father_is_alive'] = 'ស្លាប់' not in val
            if ('ម្ដាយឈ្មោះ' in row_str or 'ម្តាយឈ្មោះ' in row_str) and not data['mother_name']:
                for idx, cell in enumerate(row):
                    if 'ម្ដាយឈ្មោះ' in cell or 'ម្តាយឈ្មោះ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        data['mother_name'] = clean_noise(val.replace('រស់', '').replace('ស្លាប់', ''))
                        data['mother_is_alive'] = 'ស្លាប់' not in val

            # --- Framework & Rank ---
            if not data['current_rank_and_step'] and ('ឋានន្តរស័ក្ដ' in row_str or 'ឋានន្តរស័ក្តិ' in row_str or 'ក្របខ័ណ្ឌ ឋានន្តរស័ក្តិ' in row_str):
                for idx, cell in enumerate(row):
                    if 'ឋានន្តរស័ក្ដ' in cell or 'ឋានន្តរស័ក្តិ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        if not any(h in val for h in ['ក្រសួង', 'ស្ថាប័ន', 'អង្គភាព', 'ថ្ងៃខែ', 'ល.រ']):
                            m_rk = re.search(r'([ក-ឃ]\.[១-៤1-4]\.[១-៩1-9]+|[ក-ឃ]\.[១-៩1-9]+|[ក-ឃ]\s*[១-៩1-9])', val)
                            if m_rk: data['current_rank_and_step'] = clean_noise(m_rk.group(1))
                            elif val and len(val) < 20: data['current_rank_and_step'] = clean_noise(val)

            if 'ឈ្មោះក្របខណ្ឌ' in row_str or 'ឈ្មោះក្របខ័ណ្ឌ' in row_str:
                for idx, cell in enumerate(row):
                    if 'ឈ្មោះក្របខណ្ឌ' in cell or 'ឈ្មោះក្របខ័ណ្ឌ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        if not any(h in val for h in ['ក្រសួង', 'ស្ថាប័ន', 'អង្គភាព', 'ថ្ងៃខែ']):
                            data['framework_name'] = clean_noise(val)

            if 'ចូលបម្រើក្របខ័ណ្ឌរដ្ឋ' in row_str:
                for idx, cell in enumerate(row):
                    if 'ចូលបម្រើក្របខ័ណ្ឌរដ្ឋ' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        if not any(h in val for h in ['បញ្ចប់', 'ក្រសួង', 'ស្ថាប័ន', 'អង្គភាព', 'មុខតំណែង']):
                            data['civil_service_start_date'] = clean_noise(val)

            if 'តាំងស៊ប់' in row_str:
                for idx, cell in enumerate(row):
                    if 'តាំងស៊ប់' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        if not any(h in val for h in ['បញ្ចប់', 'ក្រសួង', 'ស្ថាប័ន', 'អង្គភាព', 'មុខតំណែង']):
                            data['civil_service_permanent_date'] = clean_noise(val)

            # --- Position Title ---
            if 'មុខតំណែង' in row_str and data['current_position_title'] == 'មន្ត្រី':
                for idx, cell in enumerate(row):
                    if 'មុខតំណែង' in cell:
                        val = row[idx+1] if idx + 1 < len(row) else cell
                        p_val = clean_noise(val)
                        if p_val and p_val not in ['មុខតំណែង', 'ជំនាញ', 'បច្ចុប្បន្ន', 'គ្មាន']:
                            data['current_position_title'] = p_val

    # =========================================================================
    # 2. SCAN SPECIFIC SUB-TABLES (Children, Education, Languages, History, Promotions, Awards)
    # =========================================================================
    for tbl in tables:
        tbl_str = ' '.join([' '.join(r) for r in tbl])

        # --- Children Table ---
        if 'កូន' in tbl_str and len(tbl) > 1 and not data['children_data']:
            for row in tbl:
                row_str = ' '.join(row)
                if 'ឈ្មោះ' in row_str and 'អក្សរឡាតាំង' in row_str: continue
                if len(row) >= 4:
                    c_name = clean_noise(row[0] if len(row) <= 5 else row[1])
                    if c_name and c_name not in ['ឈ្មោះ', 'ល.រ', 'គ្មាន', '(គ្មាន)']:
                        c_gender = 'ប្រុស'
                        c_dob = ''
                        c_occ = 'ក្នុងបន្ទុក'
                        for c in row:
                            if c in ['ប្រុស', 'ស្រី', 'ប', 'ស']:
                                c_gender = 'ស្រី' if c in ['ស្រី', 'ស'] else 'ប្រុស'
                            elif 'ថ្ងៃ' in c or 'ឆ្នាំ' in c or '/' in c or '-' in c or '.' in c:
                                if re.search(r'[0-9០-៩]{2,}', c): c_dob = clean_noise(c)
                            elif c in ['ក្នុងបន្ទុក', 'សិស្ស', 'និស្សិត', 'មន្ត្រី', 'អាជីវករ', 'មេផ្ទះ', 'លក់ដូរ']:
                                c_occ = clean_noise(c)
                        data['children_data'].append({
                            'name': c_name,
                            'gender': c_gender,
                            'dob': c_dob,
                            'occupation': c_occ
                        })

        # --- Education & Training Table ---
        if ('កម្រិតវប្បធម៌' in tbl_str or 'បណ្ដុះបណ្ដាល' in tbl_str) and not data['education_data']:
            curr_section = 'GENERAL'
            for row in tbl:
                row_str = ' '.join(row)
                if '១-កម្រិតវប្បធម៌ទូទៅ' in row_str or 'វប្បធម៌ទូទៅ' in row_str:
                    curr_section = 'GENERAL'
                    continue
                elif '២-កម្រិតបណ្ដុះបណ្ដាលវិជ្ជាជីវៈ' in row_str or 'វិជ្ជាជីវៈ' in row_str:
                    curr_section = 'VOCATIONAL'
                    continue
                elif '៣-វគ្គបណ្ដុះបណ្ដាលបន្ត' in row_str or 'បណ្ដុះបណ្ដាលបន្ត' in row_str:
                    curr_section = 'CONTINUOUS'
                    continue
                if 'វគ្គ' in row_str and 'គ្រឹះស្ថាន' in row_str: continue

                if len(row) >= 4:
                    lvl = clean_noise(row[0])
                    sch = clean_noise(row[1]) if len(row) > 1 else ''
                    loc = clean_noise(row[2]) if len(row) > 2 else ''
                    deg = clean_noise(row[3]) if len(row) > 3 else ''
                    skl = clean_noise(row[4]) if len(row) > 4 else ''
                    s_dt = clean_noise(row[5]) if len(row) > 5 else ''
                    e_dt = clean_noise(row[6]) if len(row) > 6 else ''
                    if (sch or lvl) and lvl not in ['គ្មាន', '(គ្មាន)', 'កម្រិត', 'ល.រ'] and sch not in ['គ្មាន', '(គ្មាន)']:
                        data['education_data'].append({
                            'level_type': curr_section,
                            'level_label': lvl,
                            'school': sch,
                            'location': loc,
                            'degree': deg,
                            'skill': skl,
                            'start_date': s_dt,
                            'end_date': e_dt
                        })

        # --- Foreign Languages Table ---
        if 'ភាសាបរទេស' in tbl_str and not data['languages_data']:
            for row in tbl:
                row_str = ' '.join(row)
                if 'ភាសាបរទេស' in row_str and 'ការអាន' in row_str: continue
                if len(row) >= 4:
                    lang = clean_noise(row[0])
                    r = clean_noise(row[1])
                    s = clean_noise(row[2])
                    w = clean_noise(row[3])
                    if lang and lang not in ['គ្មាន', '(គ្មាន)', 'ភាសា', 'ល.រ']:
                        data['languages_data'].append({
                            'language': lang,
                            'reading': r,
                            'speaking': s,
                            'writing': w
                        })

        # --- Public Sector Work History ---
        if ('ក្រសួង-ស្ថាប័ន' in tbl_str or 'នាយកដ្ឋាន-អង្គភាព' in tbl_str) and not data['history_public_sector']:
            for row in tbl:
                row_str = ' '.join(row)
                if 'ថ្ងៃខែឆ្នាំ' in row_str and 'ក្រសួង' in row_str: continue
                if len(row) >= 5:
                    pos = clean_noise(row[4]) if len(row) > 4 else ''
                    if pos and pos not in ['គ្មាន', '(គ្មាន)', 'មុខតំណែង', 'ជំនាញ']:
                        data['history_public_sector'].append({
                            'start_date': clean_noise(row[0]),
                            'end_date': clean_noise(row[1]) if len(row) > 1 else '',
                            'ministry': clean_noise(row[2]) if len(row) > 2 else '',
                            'department': clean_noise(row[3]) if len(row) > 3 else '',
                            'position': pos,
                            'skill': clean_noise(row[5]) if len(row) > 5 else ''
                        })
            if data['history_public_sector']:
                data['current_position_title'] = data['history_public_sector'][0]['position']

        # --- Seniority Promotions ---
        if ('ក្របខណ្ឌ ឋានន្តរស័ក្តិ និងថ្នាក់ចាស់' in tbl_str or 'ដំឡើងថ្នាក់' in tbl_str or 'វេនជ្រើសរើស' in tbl_str) and not data['promotions_by_seniority']:
            for row in tbl:
                row_str = ' '.join(row)
                if 'ថ្ងៃខែឆ្នាំ' in row_str and 'ក្រសួង' in row_str: continue
                if len(row) >= 6:
                    old_r = clean_noise(row[4]) if len(row) > 4 else ''
                    new_r = clean_noise(row[5]) if len(row) > 5 else ''
                    if old_r or new_r:
                        data['promotions_by_seniority'].append({
                            'effective_date': clean_noise(row[0]),
                            'ministry': clean_noise(row[1]) if len(row) > 1 else '',
                            'department': clean_noise(row[2]) if len(row) > 2 else '',
                            'office': clean_noise(row[3]) if len(row) > 3 else '',
                            'old_rank_step': old_r,
                            'new_rank_step': new_r,
                            'promo_type': clean_noise(row[6]) if len(row) > 6 else 'វេនជ្រើសរើស'
                        })

        # --- Awards / Medals ---
        if ('គ្រឿងឥស្សរិយយស' in tbl_str or 'មេដាយ' in tbl_str) and not data['awards_data']:
            for row in tbl:
                row_str = ' '.join(row)
                if 'លេខលិខិត' in row_str and 'កាលបរិច្ឆេទ' in row_str: continue
                if len(row) >= 4:
                    doc_no = clean_noise(row[0])
                    if doc_no and doc_no not in ['គ្មាន', '(គ្មាន)', 'ល.រ', 'ប្រភេទ']:
                        data['awards_data'].append({
                            'doc_number': doc_no,
                            'date': clean_noise(row[1]) if len(row) > 1 else '',
                            'ministry': clean_noise(row[2]) if len(row) > 2 else '',
                            'description': clean_noise(row[3]) if len(row) > 3 else '',
                            'type': clean_noise(row[4]) if len(row) > 4 else ''
                        })

    # =========================================================================
    # 3. FALLBACK TO PARAGRAPHS IF NAME OR ID STILL MISSING
    # =========================================================================
    if not data['khmer_last_name'] or not data['khmer_first_name'] or not data['officer_id_number']:
        for p in paragraphs:
            if not data['officer_id_number'] and ('អត្តលេខ' in p or 'អត្ដលេខ' in p):
                m_num = re.search(r'([0-9០-៩]{6,12})', p)
                if m_num: data['officer_id_number'] = to_arabic_digits(m_num.group(1))
            if not data['khmer_last_name'] and ('ឈ្មោះ' in p or 'គោត្តនាម' in p):
                m = re.search(r'(?:គោត្តនាម\s*[:\.\-]?\s*([\u1780-\u17F9]+)\s*នាមខ្លួន\s*[:\.\-]?\s*([\u1780-\u17F9]+)|(?:ឈ្មោះ|គោត្តនាម/នាម)\s*[:\.\-]?\s*([\u1780-\u17F9]+\s+[\u1780-\u17F9]+))', p)
                if m:
                    if m.group(1) and m.group(2):
                        data['khmer_last_name'] = clean_noise(m.group(1))
                        data['khmer_first_name'] = clean_noise(m.group(2))
                    elif m.group(3):
                        p_parts = m.group(3).split()
                        data['khmer_last_name'] = p_parts[0]
                        data['khmer_first_name'] = ' '.join(p_parts[1:])

    # =========================================================================
    # 4. FALLBACK TO FILENAME (e.g. 1791400328_សាន_ហុកលីម OK.docx)
    # =========================================================================
    if original_filename:
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        # Extract ID from filename if missing
        if not data['officer_id_number']:
            m_fn_id = re.search(r'([0-9]{6,12})', base_name)
            if m_fn_id:
                data['officer_id_number'] = m_fn_id.group(1)
        # Extract Khmer Name from filename if missing
        if not data['khmer_last_name'] or not data['khmer_first_name']:
            clean_fn = re.sub(r'[0-9_\-\.\(\)\s]+', ' ', base_name).strip()
            kh_words = re.findall(r'[\u1780-\u17F9]+', clean_fn)
            stop_words = {'ប្រវត្តិរូប', 'ជីវប្រវត្តិ', 'មន្ត្រី', 'មន្ត្រីរាជការ', 'ព័ត៌មាន', 'សង្ខេប', 'កែប្រែ', 'ជូនក្រសួង', 'ក្រសួង', 'មន្ទីរ', 'ក្សេត្រសាស្ត្រ', 'ក្សេត្រសាស្រ្ត', 'រដ្ឋបាល'}
            kh_name_words = [w for w in kh_words if w not in stop_words and len(w) >= 2]
            if len(kh_name_words) >= 2:
                data['khmer_last_name'] = kh_name_words[0]
                data['khmer_first_name'] = ' '.join(kh_name_words[1:])
            elif len(kh_name_words) == 1:
                data['khmer_last_name'] = kh_name_words[0]
                data['khmer_first_name'] = kh_name_words[0]

    return data


def compare_officer_data(existing_officer, new_data):
    """
    Compares an existing CivilServantProfile instance with new_data extracted from docx.
    Returns a list of dicts describing each detected difference.
    """
    diffs = []

    field_map = [
        ('khmer_last_name', 'គោត្តនាម (ខ្មែរ)'),
        ('khmer_first_name', 'នាមខ្លួន (ខ្មែរ)'),
        ('latin_last_name', 'គោត្តនាម (ឡាតាំង)'),
        ('latin_first_name', 'នាមខ្លួន (ឡាតាំង)'),
        ('gender', 'ភេទ'),
        ('dob', 'ថ្ងៃខែឆ្នាំកំណើត'),
        ('phone', 'លេខទូរស័ព្ទ'),
        ('email', 'អ៊ីម៉ែល'),
        ('current_position_title', 'មុខតំណែងបច្ចុប្បន្ន'),
        ('current_rank_and_step', 'ឋានន្តរស័ក្តិ និងថ្នាក់'),
        ('framework_name', 'ឈ្មោះក្របខណ្ឌ'),
        ('civil_service_start_date', 'ថ្ងៃចូលបម្រើការងារ'),
        ('civil_service_permanent_date', 'ថ្ងៃតាំងស៊ប់ក្នុងក្របខ័ណ្ឌ'),
        ('pob_village', 'ទីកន្លែងកំណើត-ភូមិ'),
        ('pob_commune', 'ទីកន្លែងកំណើត-ឃុំ/សង្កាត់'),
        ('pob_district', 'ទីកន្លែងកំណើត-ស្រុក/ខណ្ឌ'),
        ('pob_province', 'ទីកន្លែងកំណើត-រាជធានី/ខេត្ត'),
        ('current_village', 'អាសយដ្ឋានបច្ចុប្បន្ន-ភូមិ'),
        ('current_commune', 'អាសយដ្ឋានបច្ចុប្បន្ន-ឃុំ/សង្កាត់'),
        ('current_district', 'អាសយដ្ឋានបច្ចុប្បន្ន-ស្រុក/ខណ្ឌ'),
        ('current_province', 'អាសយដ្ឋានបច្ចុប្បន្ន-រាជធានី/ខេត្ត'),
        ('spouse_name_kh', 'ឈ្មោះប្តី/ប្រពន្ធ'),
        ('spouse_occupation', 'មុខរបរប្តី/ប្រពន្ធ'),
        ('father_name', 'ឈ្មោះឪពុក'),
        ('mother_name', 'ឈ្មោះម្តាយ'),
        ('emergency_last_name', 'អ្នកទំនាក់ទំនងអាសន្ន-គោត្តនាម'),
        ('emergency_first_name', 'អ្នកទំនាក់ទំនងអាសន្ន-នាមខ្លួន'),
        ('emergency_phone', 'អ្នកទំនាក់ទំនងអាសន្ន-លេខទូរស័ព្ទ'),
    ]

    for field, label in field_map:
        old_val = getattr(existing_officer, field, '') or ''
        new_val = new_data.get(field, '') or ''

        old_clean = re.sub(r'\s+', ' ', str(old_val)).strip()
        new_clean = re.sub(r'\s+', ' ', str(new_val)).strip()

        if new_clean and old_clean != new_clean:
            diffs.append({
                'field': field,
                'label': label,
                'old_val': old_clean or '(គ្មាន/ទទេ)',
                'new_val': new_clean
            })

    # Array comparisons
    array_fields = [
        ('children_data', 'ព័ត៌មានកូន', 'នាក់'),
        ('education_data', 'ប្រវត្តិការសិក្សា/វគ្គបណ្តុះបណ្តាល', 'វគ្គ/កម្រិត'),
        ('history_public_sector', 'ប្រវត្តិការងារក្នុងរដ្ឋ', 'កន្លែង'),
        ('promotions_by_seniority', 'ការឡើងថ្នាក់/ឋានន្តរស័ក្តិ', 'លើក'),
        ('awards_data', 'គ្រឿងឥស្សរិយយស/មេដាយ', 'មេដាយ'),
    ]

    for field, label, unit in array_fields:
        old_arr = getattr(existing_officer, field, []) or []
        new_arr = new_data.get(field, []) or []
        if len(old_arr) != len(new_arr):
            diff_num = len(new_arr) - len(old_arr)
            sign = '+' if diff_num > 0 else ''
            diffs.append({
                'field': field,
                'label': label,
                'old_val': f"{len(old_arr)} {unit}",
                'new_val': f"{len(new_arr)} {unit} ({sign}{diff_num})"
            })

    return diffs


# ==============================================================================
# 📝 PARSER FOR CONTRACT CIVIL SERVANT BIOGRAPHY (ជីវប្រវត្តិរូបសង្ខេបមន្ត្រីជាប់កិច្ចសន្យា)
# ==============================================================================

def parse_docx_contract_officer(file_path_or_file, original_filename=None):
    """
    Parses a Contract Civil Servant Summary Biography (ជីវប្រវត្តិរូបសង្ខេប) from a .docx file.
    Extracts all fields (Items 1 through 11) and any embedded 4x6 photo.
    """
    if hasattr(file_path_or_file, 'name') and not original_filename:
        original_filename = file_path_or_file.name
    elif isinstance(file_path_or_file, str) and not original_filename:
        original_filename = os.path.basename(file_path_or_file)

    data = {
        'khmer_last_name': '',
        'khmer_first_name': '',
        'latin_name': '',
        'gender': 'MALE',
        'nationality': 'ខ្មែរ',
        'ethnicity': 'ខ្មែរ',
        'dob': '',
        'pob_village': '',
        'pob_commune': '',
        'pob_district': '',
        'pob_province': '',
        'place_of_birth': '',
        'general_education': '',
        'training_level': '',
        'skill_specialization': '',
        'id_type': 'NATIONAL_ID',
        'id_number': '',
        'working_unit': '',
        'current_house_no': '',
        'current_street': '',
        'current_village': '',
        'current_commune': '',
        'current_district': '',
        'current_province': '',
        'current_address': '',
        'phone': '',
        'email': '',
        'position_title': 'មន្ត្រីជាប់កិច្ចសន្យា',
        'contract_number': '',
        'contract_status': 'ACTIVE',
        'photo_bytes': None,
        'photo_filename': '',
    }

    with zipfile.ZipFile(file_path_or_file) as z:
        # Extract embedded photo if present
        media_files = [f for f in z.namelist() if f.startswith('word/media/') and not f.endswith('/')]
        if media_files:
            image_candidates = []
            for mf in media_files:
                ext = mf.split('.')[-1].lower()
                if ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp']:
                    size = z.getinfo(mf).file_size
                    image_candidates.append((size, mf))
            if image_candidates:
                image_candidates.sort(reverse=True)
                best_photo_path = image_candidates[0][1]
                data['photo_bytes'] = z.read(best_photo_path)
                data['photo_filename'] = best_photo_path.split('/')[-1]

        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        paragraphs = []
        for p in tree.findall('.//w:p', ns):
            p_texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
            p_str = clean_khmer_text(''.join(p_texts))
            if p_str:
                paragraphs.append(p_str)

        tables = []
        for tbl in tree.findall('.//w:tbl', ns):
            tbl_rows = []
            for tr in tbl.findall('.//w:tr', ns):
                row_cells = []
                for tc in tr.findall('.//w:tc', ns):
                    tc_texts = [t.text for t in tc.findall('.//w:t', ns) if t.text]
                    cell_text = clean_khmer_text(''.join(tc_texts))
                    row_cells.append(cell_text)
                tbl_rows.append(row_cells)
            tables.append(tbl_rows)

    all_lines = []
    all_lines.extend(paragraphs)
    for tbl in tables:
        for row in tbl:
            row_combined = " ".join([c for c in row if c])
            if row_combined:
                all_lines.append(row_combined)
            for cell in row:
                if cell and cell not in all_lines:
                    all_lines.append(cell)

    full_document_text = "\n".join(all_lines)

    for line in all_lines:
        if 'គោត្តនាម និងនាមខ្លួន' in line or 'គោត្តនាមនិងនាមខ្លួន' in line or ('គោត្តនាម' in line and 'នាមខ្លួន' in line and '១' in line):
            m_full = re.search(r'(?:គោត្តនាម\s*(?:និង\s*)?នាមខ្លួន|១\s*[\-\.\:៖]?\s*គោត្តនាម.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ភេទ|\s*សញ្ជាតិ|$)', line)
            if m_full:
                raw_name = clean_noise(m_full.group(1)).strip()
                parts = raw_name.split()
                if len(parts) >= 2:
                    data['khmer_last_name'] = parts[0]
                    data['khmer_first_name'] = " ".join(parts[1:])
                elif len(parts) == 1:
                    data['khmer_first_name'] = parts[0]

            m_g = re.search(r'ភេទ\s*[:៖\.\-]?\s*(\S+)', line)
            if m_g:
                if 'ស្រី' in m_g.group(1): data['gender'] = 'FEMALE'
                else: data['gender'] = 'MALE'

            m_nat = re.search(r'សញ្ជាតិ\s*[:៖\.\-]?\s*([^\s,]+)', line)
            if m_nat: data['nationality'] = clean_noise(m_nat.group(1)) or 'ខ្មែរ'

        elif 'អក្សរពុម្ពឡាតាំង' in line or 'អក្សរឡាតាំង' in line or '២-អក្សរ' in line or ('២' in line and 'ឡាតាំង' in line):
            m_lat = re.search(r'(?:អក្សរពុម្ពឡាតាំង|អក្សរឡាតាំង|២\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([A-Za-z\s]+)', line)
            if m_lat: data['latin_name'] = clean_noise(m_lat.group(1)).strip().upper()

        elif 'ថ្ងៃខែឆ្នាំកំណើត' in line or '៣-ថ្ងៃ' in line or ('៣' in line and 'កំណើត' in line and 'កន្លែង' not in line):
            m_dob = re.search(r'(?:ថ្ងៃខែឆ្នាំកំណើត|៣\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ជនជាតិ|\s*សញ្ជាតិ|\s*ទីកន្លែង|$)', line)
            if m_dob: data['dob'] = clean_noise(m_dob.group(1)).strip()

        elif 'ទីកន្លែងកំណើត' in line or '៤-ទី' in line:
            m_pob = re.search(r'(?:ទីកន្លែងកំណើត|៤\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_pob:
                val = clean_noise(m_pob.group(1))
                data['place_of_birth'] = val
                m_v = re.search(r'ភូមិ\s*(.*?)(?=\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_v: data['pob_village'] = clean_noise(m_v.group(1))
                m_c = re.search(r'(?:ឃុំ/សង្កាត់|ឃុំ|សង្កាត់)\s*(.*?)(?=\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_c: data['pob_commune'] = clean_noise(m_c.group(1))
                m_d = re.search(r'(?:ស្រុក/ខណ្ឌ|ស្រុក|ខណ្ឌ)\s*(.*?)(?=\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_d: data['pob_district'] = clean_noise(m_d.group(1))
                m_p = re.search(r'(?:រាជធានី/ខេត្ត|រាជធានី|ខេត្ត)\s*(.*)', val)
                if m_p: data['pob_province'] = clean_province(m_p.group(1))

        elif 'កម្រិតវប្បធម៌ទូទៅ' in line or 'កម្រិតវប្បធម៌' in line or '៥-កម្រិត' in line:
            m_edu = re.search(r'(?:កម្រិតវប្បធម៌ទូទៅ|កម្រិតវប្បធម៌|៥\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_edu: data['general_education'] = clean_noise(m_edu.group(1)).strip()

        elif 'កម្រិតបណ្តុះបណ្តាល' in line or 'ជំនាញ/ឯកទេស' in line or '៦-កម្រិត' in line:
            m_train = re.search(r'(?:កម្រិតបណ្តុះបណ្តាល|៦\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ជំនាញ|\s*ឯកទេស|$)', line)
            if m_train: data['training_level'] = clean_noise(m_train.group(1)).strip()
            m_sk = re.search(r'(?:ជំនាញ/ឯកទេស|ជំនាញ|ឯកទេស)\s*[:៖\.\-]?\s*(.*)', line)
            if m_sk: data['skill_specialization'] = clean_noise(m_sk.group(1)).strip()

        elif 'អត្តសញ្ញាណប័ណ្ណ' in line or 'លិខិតឆ្លងដែន' in line or '៧-លេខ' in line:
            if 'លិខិតឆ្លងដែន' in line and ('[✓]' in line or '[x]' in line or '✓' in line or 'passport' in line.lower()):
                data['id_type'] = 'PASSPORT'
            else:
                data['id_type'] = 'NATIONAL_ID'
            m_num = re.search(r'(?:៖|:|\.|\-)\s*([0-9០-៩A-Za-z]+)', line)
            if m_num:
                data['id_number'] = to_arabic_digits(clean_noise(m_num.group(1)))
            else:
                m_dig = re.search(r'([0-9០-៩]{6,})', line)
                if m_dig: data['id_number'] = to_arabic_digits(m_dig.group(1))

        elif 'អង្គភាព/ការិយាល័យបំពេញការងារ' in line or 'អង្គភាព/ការិយាល័យ' in line or '៨-អង្គភាព' in line:
            m_unit = re.search(r'(?:អង្គភាព/ការិយាល័យបំពេញការងារ|អង្គភាព/ការិយាល័យ|៨\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_unit: data['working_unit'] = clean_noise(m_unit.group(1)).strip()

        elif 'អាសយដ្ឋានបច្ចុប្បន្ន' in line or '៩-អាសយដ្ឋាន' in line:
            m_addr = re.search(r'(?:អាសយដ្ឋានបច្ចុប្បន្ន|៩\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_addr:
                val = clean_noise(m_addr.group(1))
                data['current_address'] = val
                m_h = re.search(r'[#\s]*([^ផ្លភ]+?)(?=\s*ផ្លូវ|\s*ភូមិ|\s*ឃុំ|\s*សង្កាត់|$)', val)
                if m_h: data['current_house_no'] = clean_noise(m_h.group(1)).replace('#', '').strip()
                m_st = re.search(r'ផ្លូវ\s*([^ភឃស្រ]+?)(?=\s*ភូមិ|\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|$)', val)
                if m_st: data['current_street'] = clean_noise(m_st.group(1))
                m_v = re.search(r'ភូមិ\s*(.*?)(?=\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_v: data['current_village'] = clean_noise(m_v.group(1))
                m_c = re.search(r'(?:ឃុំ/សង្កាត់|ឃុំ|សង្កាត់)\s*(.*?)(?=\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_c: data['current_commune'] = clean_noise(m_c.group(1))
                m_d = re.search(r'(?:ស្រុក/ខណ្ឌ|ស្រុក|ខណ្ឌ)\s*(.*?)(?=\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_d: data['current_district'] = clean_noise(m_d.group(1))
                m_p = re.search(r'(?:រាជធានី/ខេត្ត|រាជធានី|ខេត្ត)\s*(.*)', val)
                if m_p: data['current_province'] = clean_province(m_p.group(1))

        elif 'លេខទូរស័ព្ទ' in line or 'ទូរស័ព្ទ' in line or '១០-លេខ' in line:
            m_ph = re.search(r'(?:លេខទូរស័ព្ទ|១០\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([0-9០-៩\s\-\/\+]+)', line)
            if m_ph: data['phone'] = to_arabic_digits(clean_noise(m_ph.group(1)))

        elif 'អ៊ីម៉ែល' in line or 'email' in line.lower() or '១១-អ៊ីម៉ែល' in line:
            m_em = re.search(r'(?:អ៊ីម៉ែល.*?|១១\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([A-Za-z0-9\.\_\-]+@[A-Za-z0-9\.\_\-]+)', line)
            if m_em: data['email'] = clean_noise(m_em.group(1)).strip()

    if not data['khmer_last_name'] and not data['khmer_first_name']:
        m_fallback = re.search(r'(?:ឈ្មោះ|គោត្តនាម.*?នាមខ្លួន)\s*[:\.\-]?\s*([\u1780-\u17FF\s]+)', full_document_text)
        if m_fallback:
            parts = clean_noise(m_fallback.group(1)).split()
            if len(parts) >= 2:
                data['khmer_last_name'] = parts[0]
                data['khmer_first_name'] = " ".join(parts[1:])
            elif len(parts) == 1:
                data['khmer_first_name'] = parts[0]

    # Filename fallback
    if original_filename and (not data['khmer_last_name'] or not data['khmer_first_name']):
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        clean_fn = re.sub(r'[0-9_\-\.\(\)\s]+', ' ', base_name).strip()
        kh_words = re.findall(r'[\u1780-\u17F9]+', clean_fn)
        if len(kh_words) >= 2:
            data['khmer_last_name'] = kh_words[0]
            data['khmer_first_name'] = ' '.join(kh_words[1:])
        elif len(kh_words) == 1:
            data['khmer_first_name'] = kh_words[0]

    return data


def compare_contract_officer_data(existing_officer, new_data):
    """
    Compares existing ContractOfficer record with parsed new data from Word file.
    Returns list of differences for review.
    """
    diffs = []
    field_map = [
        ('khmer_last_name', 'គោត្តនាម (ខ្មែរ)'),
        ('khmer_first_name', 'នាមខ្លួន (ខ្មែរ)'),
        ('latin_name', 'អក្សរឡាតាំង'),
        ('gender', 'ភេទ'),
        ('dob', 'ថ្ងៃខែឆ្នាំកំណើត'),
        ('nationality', 'សញ្ជាតិ'),
        ('id_type', 'ប្រភេទឯកសារសម្គាល់ខ្លួន'),
        ('id_number', 'លេខអត្តសញ្ញាណ/លិខិតឆ្លងដែន'),
        ('phone', 'លេខទូរស័ព្ទ'),
        ('email', 'អ៊ីម៉ែល'),
        ('position_title', 'មុខតំណែង/តួនាទី'),
        ('general_education', 'កម្រិតវប្បធម៌ទូទៅ'),
        ('training_level', 'កម្រិតបណ្តុះបណ្តាល'),
        ('skill_specialization', 'ជំនាញ/ឯកទេស'),
        ('working_unit', 'អង្គភាពបំពេញការងារ'),
        ('place_of_birth', 'ទីកន្លែងកំណើត'),
        ('current_address', 'អាសយដ្ឋានបច្ចុប្បន្ន'),
    ]

    for field, label in field_map:
        old_val = getattr(existing_officer, field, '') or ''
        new_val = new_data.get(field, '') or ''

        old_clean = re.sub(r'\s+', ' ', str(old_val)).strip()
        new_clean = re.sub(r'\s+', ' ', str(new_val)).strip()

        if new_clean and old_clean != new_clean:
            diffs.append({
                'field': field,
                'label': label,
                'old_val': old_clean or '(គ្មាន/ទទេ)',
                'new_val': new_clean
            })

    return diffs
