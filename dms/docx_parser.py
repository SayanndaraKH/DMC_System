import re
import zipfile
import xml.etree.ElementTree as ET

KHMER_DIGITS_MAP = str.maketrans('០១២៣៤៥៦៧៨៩', '0123456789')

def to_arabic_digits(text):
    """
    Converts Khmer digits (០១២៣៤៥៦៧៨៩) to Arabic/French numerals (0123456789).
    Example: ១៨០០៣០០១០៦ -> 1800300106
    """
    if not text:
        return ""
    return str(text).translate(KHMER_DIGITS_MAP).strip()

def clean_khmer_text(text):
    if not text:
        return ""
    text = text.replace('\u200b', '').replace('\xa0', ' ')
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

def parse_docx_officer(file_path_or_file):
    """
    Parses any Cambodian Civil Servant Biography .docx file and returns a structured dictionary
    ready to populate CivilServantProfile.
    """
    with zipfile.ZipFile(file_path_or_file) as z:
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

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

    # Table 1: Personal Info
    if len(tables) > 1:
        t1 = tables[1]
        for row in t1:
            if len(row) < 2: continue
            label, val = row[0], row[1]
            if 'ឈ្មោះជាភាសាខ្មែរ' in label:
                m_last = re.search(r'គោត្តនាម\s*[:\.\-]?\s*(.*?)(?=\s*នាមខ្លួន|\s*ភេទ|$)', val)
                if m_last: data['khmer_last_name'] = clean_noise(m_last.group(1))
                m_first = re.search(r'នាមខ្លួន\s*[:\.\-]?\s*(.*?)(?=\s*ភេទ|$)', val)
                if m_first: data['khmer_first_name'] = clean_noise(m_first.group(1))
                m_g = re.search(r'ភេទ\s*[:\.\-]?\s*(\S+)', val)
                if m_g and 'ស្រី' in m_g.group(1):
                    data['gender'] = 'FEMALE'
                else:
                    data['gender'] = 'MALE'

            elif 'ឈ្មោះជាអក្សរពុម្ព' in label or 'ទ្បាតាំង' in label or 'ឡាតាំង' in label:
                m_lat_last = re.search(r'គោត្តនាម\s*[:\.\-]?\s*([A-Za-z\s]+?)(?=\s*នាមខ្លួន|$)', val)
                if m_lat_last: data['latin_last_name'] = clean_noise(m_lat_last.group(1))
                m_lat_first = re.search(r'នាមខ្លួន\s*[:\.\-]?\s*([A-Za-z\s]+)', val)
                if m_lat_first: data['latin_first_name'] = clean_noise(m_lat_first.group(1))

            elif 'ថ្ងៃខែឆ្នាំកំណើត' in label:
                m_dob = re.search(r'^(.*?)(?=\s*ជនជាតិ|\s*សញ្ជាតិ|$)', val)
                if m_dob: data['dob'] = clean_noise(m_dob.group(1))
                m_eth = re.search(r'ជនជាតិ\s*[:\.\-]?\s*(.*?)(?=\s*សញ្ជាតិ|$)', val)
                if m_eth: data['ethnicity'] = clean_noise(m_eth.group(1)) or 'ខ្មែរ'
                m_nat = re.search(r'សញ្ជាតិ\s*[:\.\-]?\s*(.*)', val)
                if m_nat: data['nationality'] = clean_noise(m_nat.group(1)) or 'ខ្មែរ'

            elif 'ទីកន្លែងកំណើត' in label:
                m_v = re.search(r'ភូមិ\s*(.*?)(?=\s*ឃុំ|\s*សង្កាត់|\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_v: data['pob_village'] = clean_noise(m_v.group(1))
                m_c = re.search(r'(?:ឃុំ/សង្កាត់|ឃុំ|សង្កាត់)\s*(.*?)(?=\s*ស្រុក|\s*ខណ្ឌ|\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_c: data['pob_commune'] = clean_noise(m_c.group(1))
                m_d = re.search(r'(?:ស្រុក/ខណ្ឌ|ស្រុក|ខណ្ឌ)\s*(.*?)(?=\s*រាជធានី|\s*ខេត្ត|$)', val)
                if m_d: data['pob_district'] = clean_noise(m_d.group(1))
                m_p = re.search(r'(?:រាជធានី/ខេត្ត|រាជធានី|ខេត្ត)\s*(.*)', val)
                if m_p: data['pob_province'] = clean_province(m_p.group(1))

            elif 'អាសយដ្ឋានបច្ចុប្បន្ន' in label:
                m_h = re.search(r'[#​\s]*([^ផ្លភ]+?)(?=\s*ផ្លូវ|\s*ភូមិ|\s*ឃុំ|\s*សង្កាត់|$)', val)
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

            elif 'លេខទូរស័ព្ទ' in label:
                m_ph = re.search(r'^(.*?)(?=\s*អ៊ីម៉ែល|$)', val)
                if m_ph: data['phone'] = to_arabic_digits(clean_noise(m_ph.group(1)))
                m_em = re.search(r'អ៊ីម៉ែល\s*[:\.\-]?\s*(.*)', val)
                if m_em:
                    em_val = clean_noise(m_em.group(1))
                    if '@' in em_val: data['email'] = em_val

            elif 'អត្តលេខ' in label or 'អត្ដលេខ' in label:
                data['officer_id_number'] = to_arabic_digits(clean_noise(val))

            elif 'លេខអត្តសញ្ញាណប័ណ្ណ' in label:
                m_id = re.search(r'([0-9០-៩]+)', val)
                if m_id: data['national_id_number'] = to_arabic_digits(m_id.group(1))
                m_vfrom = re.search(r'សុពលភាព\s*[:\.\-]?\s*([^\sដល់]+)', val)
                if m_vfrom: data['national_id_valid_from'] = clean_noise(m_vfrom.group(1))
                m_vto = re.search(r'ដល់ថ្ងៃ\s*[:\.\-]?\s*(.*)', val)
                if m_vto: data['national_id_valid_to'] = clean_noise(m_vto.group(1))

            elif 'កាយសម្បទា' in label:
                if 'ពិការ' in val and 'គ្រប់គ្រាន់' not in val:
                    data['physical_condition'] = 'ពិការ'

    # Table 2: Spouse Info
    if len(tables) > 2:
        t2 = tables[2]
        for row in t2:
            if len(row) < 2: continue
            lbl, val = row[0], row[1]
            if 'សំបុត្រអាពាហ៏ពិពាហ៏' in lbl or 'សំបុត្រអាពាហ៍ពិពាហ៍' in lbl:
                data['spouse_marriage_cert_no'] = clean_noise(val)
            elif 'ឈ្មោះប្រពន្ធ' in lbl or 'ឈ្មោះប្តី' in lbl:
                data['spouse_name_kh'] = clean_noise(val.replace('រស់', '').replace('ស្លាប់', ''))
                data['spouse_is_alive'] = 'ស្លាប់' not in val
            elif 'ឡាតាំង' in lbl or 'ទ្បាតាំង' in lbl:
                data['spouse_name_latin'] = clean_noise(val)
            elif 'ថ្ងៃខែឆ្នាំកំណើត' in lbl:
                data['spouse_dob'] = clean_noise(val)
            elif 'លេខអត្តសញ្ញាណប័ណ្ណ' in lbl:
                data['spouse_national_id'] = to_arabic_digits(clean_noise(val))
            elif 'ទីកន្លែងកំណើត' in lbl:
                data['spouse_pob'] = clean_noise(val)
            elif 'មុខរបរ' in lbl:
                data['spouse_occupation'] = clean_noise(val.replace('ៈ', ''))
            elif 'អាសយដ្ឋាន' in lbl:
                data['spouse_current_address'] = clean_noise(val.replace('#', '').strip())
            elif 'អង្គភាព' in lbl:
                sp_org = clean_noise(val)
                if sp_org != 'គ្មាន': data['spouse_organization'] = sp_org

    # Table 3: Children
    if len(tables) > 3:
        t3 = tables[3]
        for row in t3:
            row_str = ' '.join(row)
            if 'គោត្តនាម' in row_str and len(row) >= 6:
                name_idx = 1
                child_name = clean_noise(row[name_idx])
                child_gender = 'ប្រុស'
                child_dob = ''
                child_occ = 'ក្នុងបន្ទុក'
                for c in row:
                    if c in ['ប្រុស', 'ស្រី']: child_gender = c
                    elif 'ថ្ងៃ' in c or 'ឆ្នាំ' in c or '/' in c or '-' in c: child_dob = clean_noise(c)
                    elif c in ['ក្នុងបន្ទុក', 'សិស្ស', 'និស្សិត', 'មន្ត្រី', 'អាជីវករ', 'មេផ្ទះ', 'លក់ដូរ', 'លក់ដូ']: child_occ = clean_noise(c)
                if child_name:
                    data['children_data'].append({
                        'name': child_name,
                        'gender': child_gender,
                        'dob': child_dob,
                        'occupation': child_occ
                    })

    # Table 4: Parents & Emergency
    if len(tables) > 4:
        t4 = tables[4]
        for row in t4:
            if len(row) < 2: continue
            lbl, val = row[0], row[1]
            if 'ឪពុកឈ្មោះ' in lbl:
                data['father_name'] = clean_noise(val.replace('រស់', '').replace('ស្លាប់', ''))
                data['father_is_alive'] = 'ស្លាប់' not in val
            elif 'ទីកន្លែងកំណើត' in lbl and not data['mother_name']:
                data['father_pob'] = clean_noise(val)
            elif 'មុខរបរ' in lbl and not data['mother_name']:
                data['father_occupation'] = clean_noise(val)
            elif 'ម្ដាយឈ្មោះ' in lbl or 'ម្តាយឈ្មោះ' in lbl:
                data['mother_name'] = clean_noise(val.replace('រស់', '').replace('ស្លាប់', ''))
                data['mother_is_alive'] = 'ស្លាប់' not in val
            elif 'ទីកន្លែងកំណើត' in lbl and data['mother_name']:
                data['mother_pob'] = clean_noise(val)
            elif 'មុខរបរ' in lbl and data['mother_name']:
                data['mother_occupation'] = clean_noise(val)
            elif 'ឈ្មោះជាភាសាខ្មែរ' in lbl and 'គោត្តនាម' in val:
                m_em_last = re.search(r'គោត្តនាម\s*[:\.\-]?\s*(.*?)(?=\s*នាមខ្លួន|\s*ភេទ|$)', val)
                if m_em_last: data['emergency_last_name'] = clean_noise(m_em_last.group(1))
                m_em_first = re.search(r'នាមខ្លួន\s*[:\.\-]?\s*(.*?)(?=\s*ភេទ|$)', val)
                if m_em_first: data['emergency_first_name'] = clean_noise(m_em_first.group(1))
                m_em_g = re.search(r'ភេទ\s*[:\.\-]?\s*(\S+)', val)
                if m_em_g and 'ស្រី' in m_em_g.group(1): data['emergency_gender'] = 'FEMALE'
            elif 'ទំនាក់ទំនងត្រូវជា' in lbl:
                m_rel = re.search(r'^(.*?)(?=\s*មុខរបរ|$)', val)
                if m_rel: data['emergency_relationship'] = clean_noise(m_rel.group(1))
                m_rocc = re.search(r'មុខរបរ\s*[:\.\-]?\s*(.*)', val)
                if m_rocc: data['emergency_occupation'] = clean_noise(m_rocc.group(1))
            elif 'អាសយដ្ឋាន' in lbl and data['emergency_last_name']:
                data['emergency_address'] = clean_noise(val.replace('#', '').strip())
            elif 'លេខទូរស័ព្ទ' in lbl and data['emergency_last_name']:
                m_eph = re.search(r'^(.*?)(?=\s*អ៊ីម៉ែល|$)', val)
                if m_eph: data['emergency_phone'] = to_arabic_digits(clean_noise(m_eph.group(1)))
                m_eem = re.search(r'អ៊ីម៉ែល\s*[:\.\-]?\s*(.*)', val)
                if m_eem and '@' in m_eem.group(1): data['emergency_email'] = clean_noise(m_eem.group(1))

    # Table 5: Education & Training
    if len(tables) > 5:
        t5 = tables[5]
        curr_section = 'GENERAL'
        for row in t5:
            if not row or not any(row): continue
            row_str = ' '.join(row)
            if '១-កម្រិតវប្បធម៌ទូទៅ' in row_str:
                curr_section = 'GENERAL'
                continue
            elif '២-កម្រិតបណ្ដុះបណ្ដាលវិជ្ជាជីវៈ' in row_str:
                curr_section = 'VOCATIONAL'
                continue
            elif '៣-វគ្គបណ្ដុះបណ្ដាលបន្ត' in row_str:
                curr_section = 'CONTINUOUS'
                continue
            elif 'វគ្គ' in row_str and 'គ្រឹះស្ថាន' in row_str:
                continue

            if len(row) >= 5:
                lvl = clean_noise(row[0])
                sch = clean_noise(row[1]) if len(row) > 1 else ''
                loc = clean_noise(row[2]) if len(row) > 2 else ''
                deg = clean_noise(row[3]) if len(row) > 3 else ''
                skl = clean_noise(row[4]) if len(row) > 4 else ''
                s_dt = clean_noise(row[5]) if len(row) > 5 else ''
                e_dt = clean_noise(row[6]) if len(row) > 6 else ''
                if (sch or lvl) and lvl != 'គ្មាន' and sch != 'គ្មាន':
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

    # Table 6: Foreign Languages
    if len(tables) > 6:
        t6 = tables[6]
        for row in t6:
            if 'ភាសាបរទេស' in ' '.join(row) and 'ការអាន' in ' '.join(row): continue
            if len(row) >= 4:
                lang = clean_noise(row[0])
                r = clean_noise(row[1])
                s = clean_noise(row[2])
                w = clean_noise(row[3])
                if lang and lang != 'គ្មាន':
                    data['languages_data'].append({
                        'language': lang,
                        'reading': r,
                        'speaking': s,
                        'writing': w
                    })

    # Table 7: Framework
    if len(tables) > 7:
        t7 = tables[7]
        for row in t7:
            for idx, c in enumerate(row):
                if 'ចូលបម្រើក្របខ័ណ្ឌរដ្ឋ' in c and idx + 1 < len(row):
                    data['civil_service_start_date'] = clean_noise(row[idx+1])
                elif 'តាំងស៊ប់' in c and idx + 1 < len(row):
                    data['civil_service_permanent_date'] = clean_noise(row[idx+1])
                elif 'ឈ្មោះក្របខណ្ឌ' in c and idx + 1 < len(row):
                    data['framework_name'] = clean_noise(row[idx+1])
                elif 'ឋានន្តរស័ក្ដ' in c and idx + 1 < len(row):
                    data['current_rank_and_step'] = clean_noise(row[idx+1])

    # Table 8: Public Sector History
    if len(tables) > 8:
        t8 = tables[8]
        for row in t8:
            if 'ថ្ងៃខែឆ្នាំ' in ' '.join(row) and 'ក្រសួង' in ' '.join(row): continue
            if len(row) >= 5:
                pos = clean_noise(row[4]) if len(row) > 4 else ''
                if pos and pos != 'គ្មាន':
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

    # Table 9: Private Sector History
    if len(tables) > 9:
        t9 = tables[9]
        for row in t9:
            if 'ថ្ងៃខែឆ្នាំ' in ' '.join(row) and 'តួនាទី' in ' '.join(row): continue
            if len(row) >= 4:
                role = clean_noise(row[3]) if len(row) > 3 else ''
                if role and role != 'គ្មាន':
                    data['history_private_sector'].append({
                        'start_date': clean_noise(row[0]),
                        'end_date': clean_noise(row[1]) if len(row) > 1 else '',
                        'org': clean_noise(row[2]) if len(row) > 2 else '',
                        'role': role,
                        'skill': clean_noise(row[4]) if len(row) > 4 else ''
                    })

    # Table 10: Promotions by Seniority
    if len(tables) > 10:
        t10 = tables[10]
        for row in t10:
            if 'ថ្ងៃខែឆ្នាំ' in ' '.join(row) and 'ក្រសួង' in ' '.join(row): continue
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

    # Table 11: Promotions by Degree
    if len(tables) > 11:
        t11 = tables[11]
        for row in t11:
            if 'ថ្ងៃខែឆ្នាំ' in ' '.join(row) and 'គ្រឺះស្ថាន' in ' '.join(row): continue
            if len(row) >= 6:
                sch = clean_noise(row[1]) if len(row) > 1 else ''
                if sch and sch != 'គ្មាន' and '(គ្មាន)' not in sch:
                    data['promotions_by_degree'].append({
                        'effective_date': clean_noise(row[0]),
                        'school': sch,
                        'location': clean_noise(row[2]) if len(row) > 2 else '',
                        'degree': clean_noise(row[3]) if len(row) > 3 else '',
                        'old_rank_step': clean_noise(row[4]) if len(row) > 4 else '',
                        'new_rank_step': clean_noise(row[5]) if len(row) > 5 else ''
                    })

    # Table 14: Awards
    if len(tables) > 14:
        t14 = tables[14]
        for row in t14:
            if 'លេខលិខិត' in ' '.join(row) and 'កាលបរិច្ឆេទ' in ' '.join(row): continue
            if len(row) >= 4:
                doc_no = clean_noise(row[0])
                if doc_no and doc_no != 'គ្មាន' and '(គ្មាន)' not in doc_no:
                    data['awards_data'].append({
                        'doc_number': doc_no,
                        'date': clean_noise(row[1]) if len(row) > 1 else '',
                        'ministry': clean_noise(row[2]) if len(row) > 2 else '',
                        'description': clean_noise(row[3]) if len(row) > 3 else '',
                        'type': clean_noise(row[4]) if len(row) > 4 else ''
                    })

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

def parse_docx_contract_officer(file_path_or_file):
    """
    Parses a Contract Civil Servant Summary Biography (ជីវប្រវត្តិរូបសង្ខេប) from a .docx file.
    Extracts all fields (Items 1 through 11) and any embedded 4x6 photo.
    """
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
        # 1. Extract embedded photo if present in word/media/
        media_files = [f for f in z.namelist() if f.startswith('word/media/') and not f.endswith('/')]
        # Prefer image1 or the largest image file
        if media_files:
            # Sort to find suitable photo
            image_candidates = []
            for mf in media_files:
                ext = mf.split('.')[-1].lower()
                if ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp']:
                    size = z.getinfo(mf).file_size
                    image_candidates.append((size, mf))
            if image_candidates:
                image_candidates.sort(reverse=True) # Largest image
                best_photo_path = image_candidates[0][1]
                data['photo_bytes'] = z.read(best_photo_path)
                data['photo_filename'] = best_photo_path.split('/')[-1]

        # 2. Extract Document XML
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        # Collect text from both tables and paragraphs
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
    # Flatten paragraphs
    all_lines.extend(paragraphs)
    # Flatten tables
    for tbl in tables:
        for row in tbl:
            row_combined = " ".join([c for c in row if c])
            if row_combined:
                all_lines.append(row_combined)
            for cell in row:
                if cell and cell not in all_lines:
                    all_lines.append(cell)

    full_document_text = "\n".join(all_lines)

    # =========================================================================
    # PARSE FIELDS USING ROBUST PATTERN MATCHING
    # =========================================================================

    for line in all_lines:
        # ១- គោត្តនាម និងនាមខ្លួន
        if 'គោត្តនាម និងនាមខ្លួន' in line or 'គោត្តនាមនិងនាមខ្លួន' in line or ('គោត្តនាម' in line and 'នាមខ្លួន' in line and '១' in line):
            m_full = re.search(r'(?:គោត្តនាម\s*(?:និង\s*)?នាមខ្លួន|១\s*[\-\.\:៖]?\s*គោត្តនាម.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ភេទ|\s*សញ្ជាតិ|$)', line)
            if m_full:
                raw_name = clean_noise(m_full.group(1)).strip()
                # Split first and last name if space exists
                parts = raw_name.split()
                if len(parts) >= 2:
                    data['khmer_last_name'] = parts[0]
                    data['khmer_first_name'] = " ".join(parts[1:])
                elif len(parts) == 1:
                    data['khmer_first_name'] = parts[0]

            m_g = re.search(r'ភេទ\s*[:៖\.\-]?\s*(\S+)', line)
            if m_g:
                if 'ស្រី' in m_g.group(1):
                    data['gender'] = 'FEMALE'
                else:
                    data['gender'] = 'MALE'

            m_nat = re.search(r'សញ្ជាតិ\s*[:៖\.\-]?\s*([^\s,]+)', line)
            if m_nat:
                data['nationality'] = clean_noise(m_nat.group(1)) or 'ខ្មែរ'

        # ២- អក្សរពុម្ពឡាតាំង
        elif 'អក្សរពុម្ពឡាតាំង' in line or 'អក្សរឡាតាំង' in line or '២-អក្សរ' in line or ('២' in line and 'ឡាតាំង' in line):
            m_lat = re.search(r'(?:អក្សរពុម្ពឡាតាំង|អក្សរឡាតាំង|២\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([A-Za-z\s]+)', line)
            if m_lat:
                data['latin_name'] = clean_noise(m_lat.group(1)).strip().upper()

        # ៣- ថ្ងៃខែឆ្នាំកំណើត
        elif 'ថ្ងៃខែឆ្នាំកំណើត' in line or '៣-ថ្ងៃ' in line or ('៣' in line and 'កំណើត' in line and 'កន្លែង' not in line):
            m_dob = re.search(r'(?:ថ្ងៃខែឆ្នាំកំណើត|៣\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ជនជាតិ|\s*សញ្ជាតិ|\s*ទីកន្លែង|$)', line)
            if m_dob:
                data['dob'] = clean_noise(m_dob.group(1)).strip()

        # ៤- ទីកន្លែងកំណើត
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

        # ៥- កម្រិតវប្បធម៌ទូទៅ
        elif 'កម្រិតវប្បធម៌ទូទៅ' in line or 'កម្រិតវប្បធម៌' in line or '៥-កម្រិត' in line:
            m_edu = re.search(r'(?:កម្រិតវប្បធម៌ទូទៅ|កម្រិតវប្បធម៌|៥\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_edu:
                data['general_education'] = clean_noise(m_edu.group(1)).strip()

        # ៦- កម្រិតបណ្តុះបណ្តាល & ជំនាញ/ឯកទេស
        elif 'កម្រិតបណ្តុះបណ្តាល' in line or 'ជំនាញ/ឯកទេស' in line or '៦-កម្រិត' in line:
            m_train = re.search(r'(?:កម្រិតបណ្តុះបណ្តាល|៦\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ជំនាញ|\s*ឯកទេស|$)', line)
            if m_train:
                data['training_level'] = clean_noise(m_train.group(1)).strip()
            m_sk = re.search(r'(?:ជំនាញ/ឯកទេស|ជំនាញ|ឯកទេស)\s*[:៖\.\-]?\s*(.*)', line)
            if m_sk:
                data['skill_specialization'] = clean_noise(m_sk.group(1)).strip()

        # ៧- លេខអត្តសញ្ញាណប័ណ្ណសញ្ជាតិខ្មែរ ឬលិខិតឆ្លងដែន
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
                if m_dig:
                    data['id_number'] = to_arabic_digits(m_dig.group(1))

        # ៨- អង្គភាព/ការិយាល័យបំពេញការងារ
        elif 'អង្គភាព/ការិយាល័យបំពេញការងារ' in line or 'អង្គភាព/ការិយាល័យ' in line or '៨-អង្គភាព' in line:
            m_unit = re.search(r'(?:អង្គភាព/ការិយាល័យបំពេញការងារ|អង្គភាព/ការិយាល័យ|៨\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_unit:
                data['working_unit'] = clean_noise(m_unit.group(1)).strip()

        # ៩- អាសយដ្ឋានបច្ចុប្បន្ន
        elif 'អាសយដ្ឋានបច្ចុប្បន្ន' in line or '៩-អាសយដ្ឋាន' in line:
            m_addr = re.search(r'(?:អាសយដ្ឋានបច្ចុប្បន្ន|៩\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line)
            if m_addr:
                val = clean_noise(m_addr.group(1))
                data['current_address'] = val
                m_h = re.search(r'[#​\s]*([^ផ្លភ]+?)(?=\s*ផ្លូវ|\s*ភូមិ|\s*ឃុំ|\s*សង្កាត់|$)', val)
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

        # ១០- លេខទូរស័ព្ទ
        elif 'លេខទូរស័ព្ទ' in line or 'ទូរស័ព្ទ' in line or '១០-លេខ' in line:
            m_ph = re.search(r'(?:លេខទូរស័ព្ទ|១០\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([0-9០-៩\s\-\/\+]+)', line)
            if m_ph:
                data['phone'] = to_arabic_digits(clean_noise(m_ph.group(1)))

        # ១១- អ៊ីម៉ែល
        elif 'អ៊ីម៉ែល' in line or 'email' in line.lower() or '១១-អ៊ីម៉ែល' in line:
            m_em = re.search(r'(?:អ៊ីម៉ែល.*?|១១\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([A-Za-z0-9\.\_\-]+@[A-Za-z0-9\.\_\-]+)', line)
            if m_em:
                data['email'] = clean_noise(m_em.group(1)).strip()

    # Fallbacks if name wasn't captured by line parser
    if not data['khmer_last_name'] and not data['khmer_first_name']:
        m_fallback = re.search(r'(?:ឈ្មោះ|គោត្តនាម.*?នាមខ្លួន)\s*[:\.\-]?\s*([\u1780-\u17FF\s]+)', full_document_text)
        if m_fallback:
            parts = clean_noise(m_fallback.group(1)).split()
            if len(parts) >= 2:
                data['khmer_last_name'] = parts[0]
                data['khmer_first_name'] = " ".join(parts[1:])
            elif len(parts) == 1:
                data['khmer_first_name'] = parts[0]

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

