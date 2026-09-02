import io
import os
import re
import json
import base64
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from PIL import Image

# Import existing helpers from docx_parser
from .docx_parser import (
    clean_khmer_text,
    to_arabic_digits,
    clean_province,
    clean_noise,
    parse_docx_contract_officer,
    compare_contract_officer_data,
)

# ==============================================================================
# 🔑 GEMINI API KEY MANAGEMENT
# ==============================================================================

def get_gemini_api_key() -> str:
    """
    Retrieves the Gemini API Key from environment variables, Django settings, or .env file.
    """
    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if key:
        return key

    try:
        from django.conf import settings
        key = getattr(settings, 'GEMINI_API_KEY', '').strip()
        if key:
            return key
    except Exception:
        pass

    # Check .env file directly if not found in os.environ
    try:
        env_path = Path(__file__).resolve().parent.parent / '.env'
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GEMINI_API_KEY=') and not line.startswith('#'):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if key:
                            os.environ['GEMINI_API_KEY'] = key
                            return key
    except Exception:
        pass

    return ""


def save_gemini_api_key(api_key: str) -> bool:
    """
    Saves or updates GEMINI_API_KEY into the .env file and active environment.
    """
    api_key = api_key.strip()
    os.environ['GEMINI_API_KEY'] = api_key

    try:
        env_path = Path(__file__).resolve().parent.parent / '.env'
        lines = []
        key_found = False

        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith('GEMINI_API_KEY=') or line.strip().startswith('# GEMINI_API_KEY='):
                new_lines.append(f'GEMINI_API_KEY={api_key}\n')
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            new_lines.append(f'\n# Gemini AI OCR Key\nGEMINI_API_KEY={api_key}\n')

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"Error saving GEMINI_API_KEY to .env: {e}")
        return False


# ==============================================================================
# 🖼️ IMAGE PREPROCESSING & PHOTO EXTRACTION (OpenCV & PIL)
# ==============================================================================

def enhance_image_for_ocr(image_bytes: bytes) -> Tuple[bytes, bytes]:
    """
    Enhances contrast, sharpens handwritten & printed Khmer strokes, and prepares
    both a high-clarity image for OCR and a visual preview.
    Returns (enhanced_ocr_bytes, preview_jpeg_bytes).
    """
    try:
        import cv2
        import numpy as np

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return image_bytes, image_bytes

        # Limit dimensions if extraordinarily huge to maintain speed while preserving text clarity
        h, w = img.shape[:2]
        max_dim = 2400
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        # 1. Contrast Enhancement via CLAHE on L-channel
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # 2. Subtle Unsharp Masking to sharpen pencil/pen handwritten strokes
        gaussian = cv2.GaussianBlur(enhanced_bgr, (0, 0), 2.0)
        sharpened = cv2.addWeighted(enhanced_bgr, 1.3, gaussian, -0.3, 0)

        # Encode preview and enhanced image
        _, preview_buf = cv2.imencode('.jpg', enhanced_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        _, ocr_buf = cv2.imencode('.jpg', sharpened, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        return ocr_buf.tobytes(), preview_buf.tobytes()
    except Exception:
        # Fallback to PIL if cv2 encounters any error
        try:
            from PIL import ImageEnhance, ImageFilter
            pil_img = Image.open(io.BytesIO(image_bytes))
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            # Enhance contrast and sharpness
            enhancer = ImageEnhance.Contrast(pil_img)
            enhanced = enhancer.enhance(1.2)
            sharpener = ImageEnhance.Sharpness(enhanced)
            sharpened = sharpener.enhance(1.3)

            out_buf = io.BytesIO()
            sharpened.save(out_buf, format='JPEG', quality=92)
            res_bytes = out_buf.getvalue()
            return res_bytes, res_bytes
        except Exception:
            return image_bytes, image_bytes


def extract_officer_photo_from_image(image_bytes: bytes) -> Optional[bytes]:
    """
    Attempts to detect and crop the 4x6 officer portrait photograph located
    within the biography document (usually top-right or top-left area).
    """
    try:
        import cv2
        import numpy as np

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        h, w = img.shape[:2]

        # Check top 45% of document where the 4x6 ID photo resides
        top_h = int(h * 0.45)
        top_crop = img[0:top_h, 0:w]

        # Use OpenCV default face detector if available
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if os.path.exists(cascade_path):
            face_cascade = cv2.CascadeClassifier(cascade_path)
            gray = cv2.cvtColor(top_crop, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))

            if len(faces) > 0:
                # Find face closest to top corners
                fx, fy, fw, fh = faces[0]

                # Expand box to capture full 4x6 portrait (shoulders to head)
                pad_top = int(fh * 0.45)
                pad_bottom = int(fh * 0.85)
                pad_side = int(fw * 0.45)

                x1 = max(0, fx - pad_side)
                y1 = max(0, fy - pad_top)
                x2 = min(w, fx + fw + pad_side)
                y2 = min(top_h, fy + fh + pad_bottom)

                photo_crop = top_crop[y1:y2, x1:x2]
                if photo_crop.shape[0] > 40 and photo_crop.shape[1] > 30:
                    target_w = 280
                    target_h = 360
                    resized = cv2.resize(photo_crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                    _, photo_buf = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                    return photo_buf.tobytes()

        # Fallback 2: Check for distinct 4x6 rectangle contours in the top-right / top-left area
        gray = cv2.cvtColor(top_crop, cv2.COLOR_BGR2GRAY)
        edged = cv2.Canny(gray, 50, 200)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            ratio = ch / float(cw) if cw > 0 else 0
            # Check for 4x6 portrait aspect ratio (approx 1.2 to 1.7) and reasonable size
            if 1.1 <= ratio <= 1.8 and cw > 60 and ch > 80:
                if cx > w * 0.5 or cx < w * 0.3: # Top-right or top-left
                    box_crop = top_crop[cy:cy+ch, cx:cx+cw]
                    resized = cv2.resize(box_crop, (280, 360), interpolation=cv2.INTER_LANCZOS4)
                    _, photo_buf = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                    return photo_buf.tobytes()

        return None
    except Exception:
        return None


def pdf_to_page_images(pdf_bytes: bytes, max_pages: int = 4) -> List[Tuple[bytes, bytes]]:
    """
    Renders PDF pages into images using PyMuPDF (fitz).
    Returns list of tuples (enhanced_ocr_bytes, preview_jpeg_bytes) for each page.
    """
    results = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = min(len(doc), max_pages)

        for page_idx in range(total_pages):
            page = doc.load_page(page_idx)
            # Render at 2.0 scale (144 DPI) for crisp text reading
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("jpeg")

            enhanced_ocr, preview = enhance_image_for_ocr(img_bytes)
            results.append((enhanced_ocr, preview))

        doc.close()
    except Exception as e:
        print(f"Error rendering PDF pages to image: {e}")

    return results


def extract_embedded_images_from_pdf(pdf_bytes: bytes) -> Optional[bytes]:
    """
    Extracts embedded candidate 4x6 photos from the PDF file stream.
    """
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        candidates = []

        for page_idx in range(min(len(doc), 2)):
            page = doc.load_page(page_idx)
            image_list = page.get_images(full=True)

            for img_info in image_list:
                xref = img_info[0]
                base_img = doc.extract_image(xref)
                image_bytes = base_img["image"]
                width = base_img["width"]
                height = base_img["height"]

                # Portrait photo characteristics (aspect ratio height > width, reasonable size)
                if 100 <= width <= 1500 and 120 <= height <= 2000:
                    aspect = height / float(width)
                    if 1.1 <= aspect <= 1.6:
                        candidates.append((width * height, image_bytes))

        doc.close()

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
    except Exception:
        pass
    return None


# ==============================================================================
# 🤖 GEMINI AI VISION OCR ENGINE (State-of-the-Art Khmer OCR & Handwriting)
# ==============================================================================

GEMINI_CONTRACT_OFFICER_PROMPT = """
អ្នកជាអ្នកជំនាញអាន និងស្រង់ទិន្នន័យពីឯកសាររដ្ឋបាលផ្លូវការ «ជីវប្រវត្តិរូបសង្ខេបមន្ត្រីជាប់កិច្ចសន្យា» របស់ព្រះរាជាណាចក្រកម្ពុជា។
សូមពិនិត្យឯកសារដែលបានផ្តល់ជូន (ដែលអាចជា អក្សរពុម្ព ឬ អក្សរសរសេរដៃ - Handwriting) ហើយស្រង់ទិន្នន័យគ្រប់ប្រឡោះទាំងអស់ឱ្យបានសុក្រឹតបំផុត។

ទម្រង់ទិន្នន័យដែលត្រូវស្រង់ (ចំណុច ១ ដល់ ១១)៖
១. គោត្តនាម និងនាមខ្លួន (Khmer Full Name): បំបែកជា `khmer_last_name` (គោត្តនាម) និង `khmer_first_name` (នាមខ្លួន)
២. អក្សរពុម្ពឡាតាំង (Latin Name): `latin_name` (ជាអក្សរធំ UPPERCASE ឧ. SUN VANNA)
   - ភេទ: `gender` (ជ្រើសរើស 'MALE' សម្រាប់ប្រុស, ឬ 'FEMALE' សម្រាប់ស្រី)
   - សញ្ជាតិ: `nationality` (ឧ. 'ខ្មែរ')
   - ជនជាតិ: `ethnicity` (ឧ. 'ខ្មែរ')
៣. ថ្ងៃខែឆ្នាំកំណើត: `dob` (ឧ. 15/05/1990 ឬ 15-05-1990)
៤. ទីកន្លែងកំណើត: `place_of_birth` (អាសយដ្ឋានពេញ)
   - ភូមិកំណើត: `pob_village`
   - ឃុំ/សង្កាត់កំណើត: `pob_commune`
   - ស្រុក/ខណ្ឌកំណើត: `pob_district`
   - រាជធានី/ខេត្តកំណើត: `pob_province` (ដកពាក្យ 'ខេត្ត' ឬ 'រាជធានី' ចេញ ឧ. 'បាត់ដំបង', 'ភ្នំពេញ')
៥. កម្រិតវប្បធម៌ទូទៅ: `general_education` (ឧ. បឋមភូមិ, ទុតិយភូមិ, បរិញ្ញាបត្រ, មធ្យមសិក្សាទុតិយភូមិ...)
៦. កម្រិតបណ្តុះបណ្តាល: `training_level` (ឧ. បរិញ្ញាបត្រ, វិញ្ញាបនបត្រ, អនុបណ្ឌិត...)
   - ជំនាញ/ឯកទេស: `skill_specialization` (ឧ. ក្សេត្រសាស្ត្រ, រដ្ឋបាល, គណនេយ្យ, បសុព្យាបាល...)
៧. ឯកសារសម្គាល់ខ្លួន:
   - ប្រភេទឯកសារ: `id_type` ('NATIONAL_ID' ឬ 'PASSPORT')
   - លេខអត្តសញ្ញាណប័ណ្ណ ឬ លិខិតឆ្លងដែន: `id_number` (បម្លែងជាលេខអារ៉ាប់ 0-9 ឧ. 012345678)
៨. អង្គភាព/ការិយាល័យបំពេញការងារ: `working_unit` (ឧ. ការិយាល័យរដ្ឋបាល-បុគ្គលិក, ខណ្ឌរដ្ឋបាលជលផល...)
៩. អាសយដ្ឋានបច្ចុប្បន្ន: `current_address` (អាសយដ្ឋានពេញ)
   - ផ្ទះលេខ: `current_house_no`
   - ផ្លូវ: `current_street`
   - ភូមិ: `current_village`
   - ឃុំ/សង្កាត់: `current_commune`
   - ស្រុក/ខណ្ឌ: `current_district`
   - រាជធានី/ខេត្ត: `current_province`
១០. លេខទូរស័ព្ទ: `phone` (បម្លែងជាលេខអារ៉ាប់ 0-9 ឧ. 012345678)
១១. អ៊ីម៉ែល: `email` (បើមាន)
- ព័ត៌មានបន្ថែម៖
   - `position_title`: មុខតំណែង/តួនាទី (ឧ. មន្ត្រីជាប់កិច្ចសន្យា, អ្នកបើកបរ, ភ្នាក់ងារកសិកម្ម...)
   - `contract_year`: ឆ្នាំកិច្ចសន្យា (លេខ ឧ. 2026)
   - `contract_number`: លេខកិច្ចសន្យា (បើមាន)
   - `salary`: ប្រាក់បៀវត្ស/ប្រាក់ឧបត្ថម្ភ (ជាលេខ ៛)

ចូរបញ្ជូនលទ្ធផលត្រឡប់មកវិញជា **Valid JSON Object** តែមួយគត់ (ដោយគ្មាន markdown backticks ឬអត្ថបទបន្ថែមក្រៅពី JSON ឡើយ) ដូចទម្រង់ខាងក្រោម៖
{
    "khmer_last_name": "",
    "khmer_first_name": "",
    "latin_name": "",
    "gender": "MALE",
    "nationality": "ខ្មែរ",
    "ethnicity": "ខ្មែរ",
    "dob": "",
    "pob_village": "",
    "pob_commune": "",
    "pob_district": "",
    "pob_province": "",
    "place_of_birth": "",
    "current_house_no": "",
    "current_street": "",
    "current_village": "",
    "current_commune": "",
    "current_district": "",
    "current_province": "",
    "current_address": "",
    "general_education": "",
    "training_level": "",
    "skill_specialization": "",
    "id_type": "NATIONAL_ID",
    "id_number": "",
    "working_unit": "",
    "phone": "",
    "email": "",
    "position_title": "មន្ត្រីជាប់កិច្ចសន្យា",
    "contract_year": 2026,
    "contract_number": "",
    "salary": ""
}
"""


def parse_with_gemini_vision(
    file_bytes: bytes,
    mime_type: str,
    original_filename: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Uses Google Gemini Vision API (`google.genai`) to extract structured Contract Officer data
    from image bytes or PDF bytes with state-of-the-art accuracy on handwritten & printed Khmer.
    """
    key = api_key or get_gemini_api_key()
    if not key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        # Choose model: gemini-2.5-flash or gemini-2.0-flash
        model_name = "gemini-2.5-flash"

        # Prepare content part
        content_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[content_part, GEMINI_CONTRACT_OFFICER_PROMPT],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            )
        )

        response_text = response.text.strip()
        # Strip potential markdown fences if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        parsed_json = json.loads(response_text.strip())

        # Clean and sanitize extracted fields
        clean_data = {}
        for k, v in parsed_json.items():
            if isinstance(v, str):
                clean_data[k] = clean_noise(v)
            else:
                clean_data[k] = v

        # Normalize gender
        if clean_data.get('gender') in ['ស្រី', 'FEMALE', 'F']:
            clean_data['gender'] = 'FEMALE'
        else:
            clean_data['gender'] = 'MALE'

        # Normalize ID Type
        if clean_data.get('id_type') in ['លិខិតឆ្លងដែន', 'PASSPORT']:
            clean_data['id_type'] = 'PASSPORT'
        else:
            clean_data['id_type'] = 'NATIONAL_ID'

        # Normalize numbers
        if clean_data.get('id_number'):
            clean_data['id_number'] = to_arabic_digits(clean_data['id_number'])
        if clean_data.get('phone'):
            clean_data['phone'] = to_arabic_digits(clean_data['phone'])
        if clean_data.get('dob'):
            clean_data['dob'] = to_arabic_digits(clean_data['dob'])
        if clean_data.get('contract_year'):
            try:
                clean_data['contract_year'] = int(to_arabic_digits(str(clean_data['contract_year'])))
            except Exception:
                clean_data['contract_year'] = 2026

        if clean_data.get('pob_province'):
            clean_data['pob_province'] = clean_province(clean_data['pob_province'])
        if clean_data.get('current_province'):
            clean_data['current_province'] = clean_province(clean_data['current_province'])

        return clean_data

    except Exception as e:
        print(f"Gemini Vision API Parsing Error: {e}")
        # Try fallback model if 2.5-flash hit an issue
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=key)
            content_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[content_part, GEMINI_CONTRACT_OFFICER_PROMPT],
                config=types.GenerateContentConfig(temperature=0.1, response_mime_type="application/json")
            )
            resp_text = response.text.strip()
            if resp_text.startswith("```json"): resp_text = resp_text[7:]
            if resp_text.startswith("```"): resp_text = resp_text[3:]
            if resp_text.endswith("```"): resp_text = resp_text[:-3]
            return json.loads(resp_text.strip())
        except Exception as e2:
            print(f"Gemini fallback model also failed: {e2}")
            return None


# ==============================================================================
# 📄 DIGITAL PDF FALLBACK PARSER (PyMuPDF / fitz & PyPDF)
# ==============================================================================

def parse_digital_pdf_contract_officer(pdf_bytes: bytes, original_filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses a Digital PDF (PDF with text stream) using PyMuPDF and regex patterns
    when Gemini API key is unavailable or offline.
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
        'contract_year': 2026,
        'contract_status': 'ACTIVE',
    }

    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text_lines = []

        for page in doc:
            text = page.get_text("text")
            for line in text.split("\n"):
                cleaned = clean_khmer_text(line)
                if cleaned:
                    full_text_lines.append(cleaned)
        doc.close()

        full_document_text = "\n".join(full_text_lines)

        for line in full_text_lines:
            line_lower = line.lower()
            # 1. Name & Gender & Nationality
            if 'គោត្តនាម' in line or 'នាមខ្លួន' in line or '1.' in line or '១.' in line or 'name:' in line_lower:
                m_full = re.search(r'(?:គោត្តនាម\s*(?:និង\s*)?នាមខ្លួន|[1១]\s*[\-\.\:៖]?\s*(?:គោត្តនាម|name).*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ភេទ|\s*gender|\s*សញ្ជាតិ|$)', line, re.IGNORECASE)
                if m_full:
                    raw_name = clean_noise(m_full.group(1)).strip()
                    parts = raw_name.split()
                    if len(parts) >= 2:
                        data['khmer_last_name'] = parts[0]
                        data['khmer_first_name'] = " ".join(parts[1:])
                    elif len(parts) == 1:
                        data['khmer_first_name'] = parts[0]

                m_g = re.search(r'(?:ភេទ|gender)\s*[:៖\.\-]?\s*(\S+)', line, re.IGNORECASE)
                if m_g:
                    if 'ស្រី' in m_g.group(1) or 'female' in m_g.group(1).lower(): data['gender'] = 'FEMALE'
                    else: data['gender'] = 'MALE'

                m_nat = re.search(r'(?:សញ្ជាតិ|nationality)\s*[:៖\.\-]?\s*([^\s,]+)', line, re.IGNORECASE)
                if m_nat: data['nationality'] = clean_noise(m_nat.group(1)) or 'ខ្មែរ'

            # 2. Latin Name
            if 'អក្សរពុម្ពឡាតាំង' in line or 'អក្សរឡាតាំង' in line or '២-អក្សរ' in line or '2.' in line or '២.' in line or 'latin' in line_lower:
                m_lat = re.search(r'(?:អក្សរពុម្ពឡាតាំង|អក្សរឡាតាំង|latin\s*name|[2២]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([A-Za-z\s]+)', line, re.IGNORECASE)
                if m_lat: data['latin_name'] = clean_noise(m_lat.group(1)).strip().upper()

            # 3. DOB
            if 'ថ្ងៃខែឆ្នាំកំណើត' in line or '៣-ថ្ងៃ' in line or '3.' in line or '៣.' in line or 'dob' in line_lower or 'birth' in line_lower:
                m_dob = re.search(r'(?:ថ្ងៃខែឆ្នាំកំណើត|dob|date\s*of\s*birth|[3៣]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ជនជាតិ|\s*សញ្ជាតិ|\s*ទីកន្លែង|$)', line, re.IGNORECASE)
                if m_dob: data['dob'] = to_arabic_digits(clean_noise(m_dob.group(1)).strip())

            # 4. POB
            if 'ទីកន្លែងកំណើត' in line or '៤-ទី' in line or '4.' in line or '៤.' in line or 'pob' in line_lower:
                m_pob = re.search(r'(?:ទីកន្លែងកំណើត|place\s*of\s*birth|[4៤]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line, re.IGNORECASE)
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

            # 5. General Education
            if 'កម្រិតវប្បធម៌ទូទៅ' in line or 'កម្រិតវប្បធម៌' in line or '៥-កម្រិត' in line or '5.' in line or '៥.' in line or 'education' in line_lower:
                m_edu = re.search(r'(?:កម្រិតវប្បធម៌ទូទៅ|កម្រិតវប្បធម៌|education|[5៥]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line, re.IGNORECASE)
                if m_edu: data['general_education'] = clean_noise(m_edu.group(1)).strip()

            # 6. Training & Specialization
            if 'កម្រិតបណ្តុះបណ្តាល' in line or 'ជំនាញ/ឯកទេស' in line or '៦-កម្រិត' in line or '6.' in line or '៦.' in line or 'skill' in line_lower:
                m_train = re.search(r'(?:កម្រិតបណ្តុះបណ្តាល|[6៦]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*?)(?=\s*ជំនាញ|\s*ឯកទេស|$)', line, re.IGNORECASE)
                if m_train: data['training_level'] = clean_noise(m_train.group(1)).strip()
                m_sk = re.search(r'(?:ជំនាញ/ឯកទេស|ជំនាញ|ឯកទេស|skill)\s*[:៖\.\-]?\s*(.*)', line, re.IGNORECASE)
                if m_sk: data['skill_specialization'] = clean_noise(m_sk.group(1)).strip()

            # 7. ID Card / Passport
            if 'អត្តសញ្ញាណប័ណ្ណ' in line or 'លិខិតឆ្លងដែន' in line or '៧-លេខ' in line or '7.' in line or '៧.' in line or 'id:' in line_lower:
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

            # 8. Working Unit
            if 'អង្គភាព/ការិយាល័យបំពេញការងារ' in line or 'អង្គភាព/ការិយាល័យ' in line or '៨-អង្គភាព' in line or '8.' in line or '៨.' in line or 'unit' in line_lower:
                m_unit = re.search(r'(?:អង្គភាព/ការិយាល័យបំពេញការងារ|អង្គភាព/ការិយាល័យ|working\s*unit|[8៨]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line, re.IGNORECASE)
                if m_unit: data['working_unit'] = clean_noise(m_unit.group(1)).strip()

            # 9. Current Address
            if 'អាសយដ្ឋានបច្ចុប្បន្ន' in line or '៩-អាសយដ្ឋាន' in line or '9.' in line or '៩.' in line or 'address' in line_lower:
                m_addr = re.search(r'(?:អាសយដ្ឋានបច្ចុប្បន្ន|current\s*address|[9៩]\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*(.*)', line, re.IGNORECASE)
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

            # 10. Phone
            if 'លេខទូរស័ព្ទ' in line or 'ទូរស័ព្ទ' in line or '១០-លេខ' in line or '10.' in line or '១០.' in line or 'phone' in line_lower or 'tel' in line_lower:
                m_ph = re.search(r'(?:លេខទូរស័ព្ទ|phone|tel|[10១០]+\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([0-9០-៩\s\-\/\+]+)', line, re.IGNORECASE)
                if m_ph: data['phone'] = to_arabic_digits(clean_noise(m_ph.group(1))).replace(' ', '').replace('-', '')

            # 11. Email
            if 'អ៊ីម៉ែល' in line or 'email' in line_lower or '១១-អ៊ីម៉ែល' in line or '11.' in line or '១១.' in line:
                m_em = re.search(r'(?:អ៊ីម៉ែល.*?|email|[11១១]+\s*[\-\.\:៖]?\s*.*?)\s*[:៖\.\-]?\s*([A-Za-z0-9\.\_\-]+@[A-Za-z0-9\.\_\-]+)', line, re.IGNORECASE)
                if m_em: data['email'] = clean_noise(m_em.group(1)).strip()

        # Fallback to full document text search
        if not data['khmer_last_name'] and not data['khmer_first_name']:
            m_fallback = re.search(r'(?:ឈ្មោះ|គោត្តនាម.*?នាមខ្លួន|name)\s*[:\.\-]?\s*([\u1780-\u17FFA-Za-z\s]+)', full_document_text, re.IGNORECASE)
            if m_fallback:
                parts = clean_noise(m_fallback.group(1)).split()
                if len(parts) >= 2:
                    data['khmer_last_name'] = parts[0]
                    data['khmer_first_name'] = " ".join(parts[1:])
                elif len(parts) == 1:
                    data['khmer_first_name'] = parts[0]

        # Fallback to filename
        if original_filename and (not data['khmer_last_name'] or not data['khmer_first_name']):
            base_name = os.path.splitext(os.path.basename(original_filename))[0]
            clean_fn = re.sub(r'[0-9_\-\.\(\)\s]+', ' ', base_name).strip()
            kh_words = re.findall(r'[\u1780-\u17F9]+', clean_fn)
            if len(kh_words) >= 2:
                data['khmer_last_name'] = kh_words[0]
                data['khmer_first_name'] = ' '.join(kh_words[1:])
            elif len(kh_words) == 1:
                data['khmer_first_name'] = kh_words[0]

    except Exception as e:
        print(f"Error parsing digital PDF: {e}")

    return data


# ==============================================================================
# 🚀 UNIVERSAL SCAN & PARSE PIPELINE (PDF, Images, DOCX)
# ==============================================================================

def parse_contract_officer_document(
    file_bytes: bytes,
    filename: str,
    custom_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point for scanning and parsing Contract Officer CVs from PDF, Image, or Word.
    Returns parsed fields, preview images as base64, extracted 4x6 photo as base64, and detection metadata.
    """
    fn_lower = filename.lower()
    ext = os.path.splitext(fn_lower)[1]

    extracted_data = {}
    photo_bytes: Optional[bytes] = None
    preview_images: List[str] = []
    source_used = 'UNKNOWN'
    has_api_key = bool(custom_api_key or get_gemini_api_key())

    # ==========================================
    # 1. CASE: WORD DOCUMENT (.docx)
    # ==========================================
    if ext == '.docx':
        try:
            file_io = io.BytesIO(file_bytes)
            file_io.name = filename
            docx_data = parse_docx_contract_officer(file_io, original_filename=filename)
            photo_bytes = docx_data.pop('photo_bytes', None)
            docx_data.pop('photo_filename', None)
            extracted_data = docx_data
            source_used = 'DOCX_PARSER'
        except Exception as e:
            return {'success': False, 'error': f"កំហុសក្នុងការអានឯកសារ Word: {str(e)}"}

    # ==========================================
    # 2. CASE: PDF DOCUMENT (.pdf)
    # ==========================================
    elif ext == '.pdf':
        # Render pages for preview and OCR
        page_images = pdf_to_page_images(file_bytes, max_pages=3)
        for _, prev_bytes in page_images:
            b64_prev = f"data:image/jpeg;base64,{base64.b64encode(prev_bytes).decode('utf-8')}"
            preview_images.append(b64_prev)

        # Extract embedded 4x6 photo from PDF stream if present
        photo_bytes = extract_embedded_images_from_pdf(file_bytes)

        # Attempt Gemini Vision AI first (Highest accuracy for handwriting and complex layout)
        if has_api_key:
            ai_data = parse_with_gemini_vision(
                file_bytes=file_bytes,
                mime_type="application/pdf",
                original_filename=filename,
                api_key=custom_api_key
            )
            if ai_data and (ai_data.get('khmer_last_name') or ai_data.get('khmer_first_name') or ai_data.get('id_number')):
                extracted_data = ai_data
                source_used = 'AI_GEMINI_VISION'

        # Fallback to Digital PDF text extraction if AI Vision was skipped or returned empty
        if not extracted_data:
            extracted_data = parse_digital_pdf_contract_officer(file_bytes, original_filename=filename)
            source_used = 'PDF_DIGITAL_TEXT'

        # If photo not found in PDF stream, try face detection on page 1 image
        if not photo_bytes and page_images:
            photo_bytes = extract_officer_photo_from_image(page_images[0][0])

    # ==========================================
    # 3. CASE: IMAGE FILE (.jpg, .png, .webp, .bmp, etc.)
    # ==========================================
    elif ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.heic']:
        enhanced_ocr_bytes, preview_bytes = enhance_image_for_ocr(file_bytes)
        b64_prev = f"data:image/jpeg;base64,{base64.b64encode(preview_bytes).decode('utf-8')}"
        preview_images.append(b64_prev)

        # Try to extract 4x6 officer portrait
        photo_bytes = extract_officer_photo_from_image(file_bytes)

        # Determine MIME type
        mime = 'image/jpeg'
        if ext == '.png': mime = 'image/png'
        elif ext == '.webp': mime = 'image/webp'

        if has_api_key:
            ai_data = parse_with_gemini_vision(
                file_bytes=enhanced_ocr_bytes,
                mime_type=mime,
                original_filename=filename,
                api_key=custom_api_key
            )
            if ai_data:
                extracted_data = ai_data
                source_used = 'AI_GEMINI_VISION'

        if not extracted_data:
            # Basic fallback structure if offline image
            extracted_data = {
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
                'contract_year': 2026,
            }
            # Try to infer name from filename
            base_name = os.path.splitext(os.path.basename(filename))[0]
            clean_fn = re.sub(r'[0-9_\-\.\(\)\s]+', ' ', base_name).strip()
            kh_words = re.findall(r'[\u1780-\u17F9]+', clean_fn)
            if len(kh_words) >= 2:
                extracted_data['khmer_last_name'] = kh_words[0]
                extracted_data['khmer_first_name'] = ' '.join(kh_words[1:])
            elif len(kh_words) == 1:
                extracted_data['khmer_first_name'] = kh_words[0]
            source_used = 'IMAGE_ENHANCED_FALLBACK'

    else:
        return {'success': False, 'error': 'ប្រភេទឯកសារមិនត្រឹមត្រូវ! ប្រព័ន្ធគាំទ្រតែ PDF, រូបភាព (JPG, PNG) និង Word (.docx) ប៉ុណ្ណោះ។'}

    # Prepare photo base64
    photo_base64 = None
    if photo_bytes:
        photo_base64 = f"data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode('utf-8')}"

    return {
        'success': True,
        'data': extracted_data,
        'photo_bytes': photo_bytes,
        'photo_base64': photo_base64,
        'preview_images': preview_images,
        'source': source_used,
        'has_api_key': has_api_key,
        'filename': filename,
    }
