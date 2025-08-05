# app.py - Flask backend for SOAP Note Voice Recorder

from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import tempfile
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import subprocess
from medical_spell_check import MedicalSpellChecker
import psycopg2
from psycopg2.extras import RealDictCursor

# Set temporary directory to system default
temp_dir = tempfile.gettempdir()
print(f"Temporary files will be stored in: {temp_dir}")

app = Flask(__name__)
CORS(app)

# Initialize models
print("Loading models...")

# Load environment variables and configure OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("⚠️  Warning: OPENAI_API_KEY not set in environment variables!")
    print("Please set it in your .env file or as an environment variable.")

# Use OpenAI Python SDK 1.x for chat completions
client = OpenAI()

# Initialize medical spell checker
medical_spell_checker = MedicalSpellChecker()

# Updated English SOAP prompt
SOAP_SYSTEM_PROMPT = """You are a medical documentation assistant specialized in creating SOAP notes from doctor-patient conversations.

Output ONLY a valid JSON object without any explanation or external text. If you add anything outside the JSON object, the response will be rejected. The response must be a JSON object only with the following structure:

{
  "soap_note": {
    "patient_id": "auto-generated",
    "visit_date": "current-date-time",
    "provider_name": "Dr. [Name from conversation or 'Unknown']",
    "patient_name": "[Patient's full name from conversation]",
    "patient_age": "[Patient's age from conversation]",
    "subjective": {
      "chief_complaint": "...",
      "history_of_present_illness": "...",
      "past_medical_history": "...",
      "family_history": "...",
      "social_history": "...",
      "medications": [
        {
          "name": "Medication name",
          "dosage": "Dosage information",
          "frequency": "How often taken",
          "route": "oral/inhalation/etc",
          "duration": "How long taking"
        }
      ],
      "allergies": ["List of allergies"]
    },
    "objective": {
      "vital_signs": {
        "temperature": "Temperature if mentioned",
        "blood_pressure": "BP if mentioned",
        "heart_rate": "HR if mentioned",
        "respiratory_rate": "RR if mentioned",
        "oxygen_saturation": "O2 sat if mentioned"
      },
      "physical_exam": "Physical examination findings"
    },
    "assessment": {
      "diagnosis": "Primary diagnosis",
      "risk_factors": ["List of risk factors"]
    },
    "plan": {
      "medications_prescribed": [
        {
          "name": "Medication name",
          "dosage": "Dosage",
          "frequency": "How often",
          "duration": "How long",
          "route": "oral/injection/etc"
        }
      ],
      "procedures_or_tests": ["List of tests/procedures"],
      "patient_education": "Education provided to patient",
      "follow_up_instructions": "Follow-up plan"
    }
  }
}

CRITICAL INSTRUCTIONS - CAPTURE EVERYTHING MENTIONED:

1. PATIENT IDENTIFICATION: Extract and include:
   - Patient's full name (first and last name) - MUST be included in patient_name field
   - IMPORTANT: Do NOT prefix patient name with "Dr." unless they are explicitly identified as a doctor who is the patient
   - Age (exact number mentioned) - MUST be included in patient_age field
   - If patient introduces themselves (e.g., "Hi, I'm Sarah"), that's the patient name
   - If doctor addresses patient by name (e.g., "Hello Sarah"), that's the patient name
   - Location/address/city mentioned
   - Any other demographic information
   - If patient name is mentioned as "Patient: [Name]" or "The patient [Name]", extract only the name part
   - If no patient name is explicitly mentioned, you can infer it from context (e.g., the person speaking who is not the doctor)

2. PROVIDER IDENTIFICATION: Extract and include:
   - Doctor's name (Dr. [Name] or د. [Name])
   - Department/specialty mentioned
   - Any other provider information

3. CHIEF COMPLAINT: Include:
   - Primary symptom(s) with exact description
   - Duration mentioned (hours, days, weeks)
   - Location of symptoms (if specified)

4. HISTORY OF PRESENT ILLNESS: MUST include ALL mentioned:
   - Exact timing (when symptoms started)
   - Detailed description of symptoms
   - Associated symptoms (fever, sweating, nausea, vomiting, etc.)
   - Aggravating factors (movement, pressure, etc.)
   - Relieving factors (if mentioned)
   - Progression of symptoms
   - Impact on daily activities
   - Any other symptoms mentioned in conversation
   - IMPORTANT: This should be a detailed narrative paragraph, not just bullet points

5. PAST MEDICAL HISTORY: Include ALL mentioned:
   - Chronic diseases
   - Previous surgeries (with dates if mentioned)
   - Current medications (even if "none" or "no medications" - MUST document this)
   - Previous hospitalizations
   - Any other medical history

6. FAMILY HISTORY: Include ALL mentioned:
   - Family members with medical conditions
   - Specific conditions mentioned
   - Ages of family members (if mentioned)
   - Any genetic conditions

7. SOCIAL HISTORY: Include ALL mentioned:
   - Occupation/job
   - Smoking/alcohol use
   - Living situation
   - Lifestyle factors
   - Any other social information

8. MEDICATIONS: Include ALL mentioned:
   - Current medications (name, dosage, frequency, route)
   - If "no medications" mentioned, document that explicitly
   - Duration of medication use
   - Any medication changes

9. ALLERGIES: Include ALL mentioned:
   - Drug allergies
   - Food allergies
   - Environmental allergies
   - If "no allergies" mentioned, document that explicitly

10. VITAL SIGNS: Include ALL mentioned:
    - Temperature (if mentioned)
    - Blood pressure (if mentioned)
    - Heart rate (if mentioned)
    - Respiratory rate (if mentioned)
    - Oxygen saturation (if mentioned)
    - Any other vital signs mentioned

11. PHYSICAL EXAMINATION: Include ALL mentioned:
    - Any examination performed
    - Findings mentioned
    - Areas examined
    - Any abnormal findings

12. DIAGNOSIS: Use the most likely diagnosis based on:
    - Symptoms described
    - Clinical findings
    - Medical reasoning

13. RISK FACTORS: Include ALL mentioned:
    - Medical conditions
    - Family history factors
    - Lifestyle factors
    - Age-related factors
    - Any other risk factors

14. MEDICATIONS PRESCRIBED: Include ALL mentioned:
    - New medications ordered
    - Dosage, frequency, route
    - Duration of treatment
    - Any medication changes

15. PROCEDURES/TESTS: Include ALL mentioned:
    - Laboratory tests
    - Imaging studies
    - Procedures ordered
    - Any investigations mentioned

16. PATIENT EDUCATION: Include ALL mentioned:
    - Instructions given
    - Warnings provided
    - Lifestyle advice
    - Any education provided
    - Diagnosis-specific education (e.g., for heart attack: signs to watch for, lifestyle changes)
    - Medication instructions and side effects
    - When to seek immediate medical attention
    - Prevention strategies

17. FOLLOW-UP: Include ALL mentioned:
    - Follow-up timing
    - Return instructions
    - Monitoring requirements
    - Any follow-up plans
    - Diagnosis-specific follow-up (e.g., "Cardiology follow-up" for cardiac issues, "Neurology follow-up" for neurological issues)
    - Emergency return criteria
    - Specialist referrals if needed

IMPORTANT: Do not omit any information mentioned in the conversation. If something is mentioned, it must be included in the appropriate section. Use exact quotes and details from the conversation rather than generic phrases.

REMINDER FOR PATIENT NAME: 
- Extract the actual patient name, not the doctor's name
- If you see "Patient: [Name]" extract only the name part
- Do NOT prefix patient names with "Dr." unless the patient themselves is explicitly identified as a doctor
- If a name appears after "Patient:" or "The patient", that is the patient's name
- If the transcript is very short (e.g., just a greeting), and no names are mentioned:
  - For provider_name: Keep as "Dr. Unknown" or "Dr. Not mentioned"
  - For patient_name: Keep as "Unknown" (do not use greetings like "Hello" as names)
  - For patient_age: Keep as "Unknown" if not mentioned
- Common greetings like "Hello", "Hi", "Good morning" are NOT names

EXAMPLES:
- If transcript is "Hello Doctor", patient_name should be "Unknown", NOT "Hello" or "Doctor"
- If transcript is "Dr. Smith: Hello Sarah, how are you?", then provider_name is "Dr. Smith" and patient_name is "Sarah"
- If transcript is "Patient: John Doe, 45 years old", then patient_name is "John Doe" and patient_age is "45"

Do not write anything outside the JSON object."""

# Updated Arabic SOAP prompt
ARABIC_SOAP_PROMPT = """
أنت طبيب متخصص في التوثيق الطبي وإنشاء ملاحظات SOAP احترافية من محادثات الطبيب والمريض. أجب فقط باللغة العربية واستخدم المصطلحات الطبية المناسبة.

أخرج فقط كائن JSON صالح بدون أي شرح أو نص خارجي. إذا أضفت أي شيء خارج كائن JSON سيتم رفض الإجابة. يجب أن يكون الرد كائن JSON فقط بالهيكل التالي:

{
  "soap_note": {
    "patient_id": "يتم إنشاؤه تلقائياً",
    "visit_date": "تاريخ الزيارة",
    "provider_name": "د. [الاسم من المحادثة أو 'غير محدد']",
    "patient_name": "[الاسم الكامل للمريض من المحادثة]",
    "patient_age": "[عمر المريض من المحادثة]",
    "subjective": {
      "chief_complaint": "...",
      "history_of_present_illness": "...",
      "past_medical_history": "...",
      "family_history": "...",
      "social_history": "...",
      "medications": [
        {
          "name": "اسم الدواء",
          "dosage": "معلومات الجرعة",
          "frequency": "عدد مرات الاستخدام",
          "route": "طريقة الاستخدام",
          "duration": "مدة الاستخدام"
        }
      ],
      "allergies": ["قائمة الحساسية"]
    },
    "objective": {
      "vital_signs": {
        "temperature": "درجة الحرارة إذا ذُكرت",
        "blood_pressure": "ضغط الدم إذا ذُكر",
        "heart_rate": "معدل النبض إذا ذُكر",
        "respiratory_rate": "معدل التنفس إذا ذُكر",
        "oxygen_saturation": "معدل الأكسجين إذا ذُكر"
      },
      "physical_exam": "نتائج الفحص البدني"
    },
    "assessment": {
      "diagnosis": "التشخيص الأساسي",
      "risk_factors": ["قائمة عوامل الخطر"]
    },
    "plan": {
      "medications_prescribed": [
        {
          "name": "اسم الدواء",
          "dosage": "الجرعة",
          "frequency": "عدد المرات",
          "duration": "المدة",
          "route": "طريقة الاستخدام"
        }
      ],
      "procedures_or_tests": ["قائمة الفحوصات والإجراءات"],
      "patient_education": "التعليمات المقدمة للمريض",
      "follow_up_instructions": "خطة المتابعة"
    }
  }
}

تعليمات مهمة جداً - استخرج كل شيء مذكور:

1. تحديد هوية المريض: استخرج وضمّن:
   - الاسم الكامل للمريض (الاسم الأول والأخير) - يجب تضمينه في حقل patient_name
   - مهم: لا تضع "د." أو "دكتور" قبل اسم المريض إلا إذا كان المريض نفسه طبيباً
   - العمر (الرقم المحدد المذكور) - يجب تضمينه في حقل patient_age
   - إذا عرّف المريض عن نفسه (مثل: "مرحبا، أنا سارة")، فهذا اسم المريض
   - إذا خاطب الطبيب المريض بالاسم (مثل: "مرحبا سارة")، فهذا اسم المريض
   - الموقع/العنوان/المدينة المذكورة
   - أي معلومات ديموغرافية أخرى
   - إذا ذُكر اسم المريض كـ "المريض: [الاسم]" أو "المريض [الاسم]"، استخرج الاسم فقط
   - إذا لم يُذكر اسم المريض صراحة، يمكنك استنتاجه من السياق (مثل: الشخص الذي يتحدث وليس الطبيب)

2. تحديد هوية الطبيب: استخرج وضمّن:
   - اسم الطبيب (د. [الاسم])
   - القسم/التخصص المذكور
   - أي معلومات أخرى عن الطبيب

3. الشكوى الرئيسية: ضمّن:
   - الأعراض الأساسية مع الوصف الدقيق
   - المدة المذكورة (ساعات، أيام، أسابيع)
   - موقع الأعراض (إذا تم تحديده)

4. تاريخ المرض الحالي: يجب أن يشمل كل شيء مذكور:
   - التوقيت الدقيق (متى بدأت الأعراض)
   - وصف مفصل للأعراض
   - الأعراض المصاحبة (الحرارة، التعرق، الغثيان، القيء، إلخ)
   - العوامل المحفزة (الحركة، الضغط، إلخ)
   - العوامل المخففة (إذا ذُكرت)
   - تطور الأعراض
   - التأثير على الأنشطة اليومية
   - أي أعراض أخرى مذكورة في المحادثة

5. التاريخ الطبي السابق: ضمّن كل شيء مذكور:
   - الأمراض المزمنة
   - العمليات السابقة (مع التواريخ إذا ذُكرت)
   - الأدوية الحالية (حتى لو "لا أدوية" أو "لا يتناول أدوية")
   - الاستشفاءات السابقة
   - أي تاريخ طبي آخر

6. التاريخ العائلي: ضمّن كل شيء مذكور:
   - أفراد العائلة المصابين بأمراض
   - الأمراض المحددة المذكورة
   - أعمار أفراد العائلة (إذا ذُكرت)
   - أي أمراض وراثية

7. التاريخ الاجتماعي: ضمّن كل شيء مذكور:
   - المهنة/الوظيفة
   - التدخين/استهلاك الكحول
   - الوضع المعيشي
   - عوامل نمط الحياة
   - أي معلومات اجتماعية أخرى

8. الأدوية: ضمّن كل شيء مذكور:
   - الأدوية الحالية (الاسم، الجرعة، التكرار، الطريقة)
   - إذا ذُكر "لا أدوية"، وثق ذلك صراحةً
   - مدة استخدام الدواء
   - أي تغييرات في الأدوية

9. الحساسية: ضمّن كل شيء مذكور:
   - حساسية الأدوية
   - حساسية الطعام
   - حساسية البيئة
   - إذا ذُكر "لا حساسية"، وثق ذلك صراحةً

10. العلامات الحيوية: ضمّن كل شيء مذكور:
    - درجة الحرارة (إذا ذُكرت)
    - ضغط الدم (إذا ذُكر)
    - معدل النبض (إذا ذُكر)
    - معدل التنفس (إذا ذُكر)
    - نسبة الأكسجين (إذا ذُكرت)
    - أي علامات حيوية أخرى مذكورة

11. الفحص البدني: ضمّن كل شيء مذكور:
    - أي فحص تم إجراؤه
    - النتائج المذكورة
    - المناطق المفحوصة
    - أي نتائج غير طبيعية

12. التشخيص: استخدم التشخيص الأكثر احتمالاً بناءً على:
    - الأعراض الموصوفة
    - النتائج السريرية
    - المنطق الطبي

13. عوامل الخطر: ضمّن كل شيء مذكور:
    - الحالات الطبية
    - عوامل التاريخ العائلي
    - عوامل نمط الحياة
    - العوامل المرتبطة بالعمر
    - أي عوامل خطر أخرى

14. الأدوية الموصوفة: ضمّن كل شيء مذكور:
    - الأدوية الجديدة المطلوبة
    - الجرعة، التكرار، الطريقة
    - مدة العلاج
    - أي تغييرات في الأدوية

15. الإجراءات/الفحوصات: ضمّن كل شيء مذكور:
    - فحوصات المختبر
    - دراسات التصوير
    - الإجراءات المطلوبة
    - أي تحقيقات مذكورة

16. تعليمات المريض: ضمّن كل شيء مذكور:
    - التعليمات المقدمة
    - التحذيرات المقدمة
    - النصائح المتعلقة بنمط الحياة
    - أي تعليمات مقدمة
    - التعليمات الخاصة بالتشخيص (مثل: علامات النوبة القلبية، تغييرات نمط الحياة)
    - تعليمات الأدوية والآثار الجانبية
    - متى يجب طلب الرعاية الطبية العاجلة
    - استراتيجيات الوقاية

17. المتابعة: ضمّن كل شيء مذكور:
    - توقيت المتابعة
    - تعليمات العودة
    - متطلبات المراقبة
    - أي خطط متابعة
    - المتابعة الخاصة بالتشخيص (مثل: "متابعة مع طبيب القلب" للمشاكل القلبية، "متابعة مع طبيب الأعصاب" للمشاكل العصبية)
    - معايير العودة الطارئة
    - الإحالات للمتخصصين إذا لزم الأمر

مهم جداً: لا تحذف أي معلومات مذكورة في المحادثة. إذا ذُكر شيء ما، يجب تضمينه في القسم المناسب. استخدم الاقتباسات الدقيقة والتفاصيل من المحادثة بدلاً من العبارات العامة.

تذكير بخصوص اسم المريض:
- استخرج اسم المريض الفعلي، وليس اسم الطبيب
- إذا رأيت "المريض: [الاسم]" استخرج الاسم فقط
- لا تضع "د." قبل اسم المريض إلا إذا كان المريض نفسه طبيباً
- إذا ظهر اسم بعد "المريض:" أو "المريض"، فهذا هو اسم المريض
- إذا كانت المحادثة قصيرة جداً (مثل: مجرد تحية)، ولم تُذكر أسماء:
  - لـ provider_name: احتفظ بـ "د. غير محدد"
  - لـ patient_name: احتفظ بـ "غير محدد" (لا تستخدم التحيات مثل "مرحبا" كأسماء)
  - لـ patient_age: احتفظ بـ "غير محدد" إذا لم يُذكر
- التحيات الشائعة مثل "مرحبا"، "أهلاً"، "صباح الخير" ليست أسماء

أمثلة:
- إذا كانت المحادثة "مرحبا دكتور"، يجب أن يكون patient_name "غير محدد"، وليس "مرحبا" أو "دكتور"
- إذا كانت المحادثة "د. أحمد: مرحبا سارة، كيف حالك؟"، فإن provider_name هو "د. أحمد" وpatient_name هو "سارة"
- إذا كانت المحادثة "المريض: محمد علي، 45 سنة"، فإن patient_name هو "محمد علي" وpatient_age هو "45"

لا تكتب أي شيء خارج كائن JSON."""

def extract_json_from_response(response_text):
    """Extract JSON from response text that may contain extra text"""
    try:
        # First try to parse as-is
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Try to find JSON within the text using regex
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        lines = response_text.strip().split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        for line in lines:
            if '{' in line and not in_json:
                in_json = True
                brace_count = line.count('{') - line.count('}')
                json_lines.append(line)
            elif in_json:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0:
                    break
        if json_lines:
            try:
                return json.loads('\n'.join(json_lines))
            except json.JSONDecodeError:
                pass
        return None

def transcribe_with_openai(audio_path, language="auto"):
    """
    Transcribe audio using OpenAI gpt-4o-transcribe model
    This is the best model for medical transcription in both English and Arabic
    """
    try:
        print(f"Starting transcription with OpenAI gpt-4o-transcribe for file: {audio_path}, language: {language}")
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                response_format="text",
                language=language if language != "auto" else None
            )
        print(f"Transcription result: {transcription}")
        return transcription
    except Exception as e:
        print(f"Error in OpenAI gpt-4o-transcribe transcription: {str(e)}")
        import traceback
        print(f"Full error traceback: {traceback.format_exc()}")
        return None

def transcribe_arabic_audio(audio_path):
    """Transcribe Arabic audio using OpenAI gpt-4o-transcribe model (legacy function name)"""
    return transcribe_with_openai(audio_path, "ar")

def transcribe_english_audio(audio_path):
    """Transcribe English audio using OpenAI gpt-4o-transcribe model for better medical accuracy"""
    return transcribe_with_openai(audio_path, "en")

def generate_soap_note_metadata(transcript, language):
    """Generate metadata for SOAP note: patient_id, visit_date, provider_name, patient_name, patient_age"""
    from datetime import datetime
    import uuid
    import re
    
    # Generate current date in ISO format (date only, no time)
    current_date = datetime.now().strftime("%Y-%m-%d")
    # Generate a simple patient ID
    patient_id = str(uuid.uuid4())[:8]
    
    print(f"\n=== Extracting metadata from transcript (language: {language}) ===")
    print(f"Transcript preview: {transcript[:200]}...")
    
    # Extract provider name from transcript (improved extraction)
    provider_name = "Dr. Unknown" if language == "en" else "د. غير محدد"
    if language == "en":
        # Improved English provider name extraction
        dr_match = re.search(r'Dr\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', transcript)
        if dr_match:
            provider_name = f"Dr. {dr_match.group(1)}"
        else:
            provider_name = "Dr. Not mentioned"
    elif language == "ar":
        # Improved Arabic provider name extraction - look for "دكتور" or "د." followed by name
        # More specific pattern to avoid false matches
        dr_patterns = [
            r'دكتور\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)',
            r'د\.\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)',
            r'الطبيب\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)'
        ]
        provider_found = False
        for pattern in dr_patterns:
            dr_match = re.search(pattern, transcript)
            if dr_match:
                extracted_name = dr_match.group(1)
                # Validate that it's actually a name (not random text)
                if len(extracted_name) > 2 and not any(word in extracted_name.lower() for word in ['في', 'من', 'إلى', 'على', 'مع', 'بدا', 'كان', 'هذا', 'ذلك', 'التي', 'الذي']):
                    provider_name = f"د. {extracted_name}"
                    provider_found = True
                    break
        if not provider_found:
            provider_name = "د. غير محدد"
    
    # Extract patient name and age
    patient_name = "Unknown" if language == "en" else "غير محدد"
    patient_age = "Unknown" if language == "en" else "غير محدد"
    
    if language == "en":
        # Extract English patient name - improved patterns
        # Look for formal titles and names in doctor-patient dialogue first
        patient_patterns = [
            # Pattern for "Mr./Mrs./Ms./Dr. [Name]" in dialogue
            r"(?:Mr\.?|Mrs\.?|Ms\.?|Miss)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            # Pattern for "Patient: [Name], [age]" or "Patient: [Name]" (but exclude greetings)
            r"patient\s*:\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:\s*,|\s+\d+|$)",
            # Pattern for "The patient [Name]"
            r"(?:the\s+)?patient\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:\s*,|\s+is|\s+\d+|$)",
            # Pattern for "patient is [Name]"
            r"patient\s+is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*?)(?:\s*,|\s+\d+|$)",
            # Pattern for "[Name] is a XX-year-old"
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+is\s+(?:a\s+)?\d+\s*(?:-)?\s*year",
            r"I'm\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"My name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"I am\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"name is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            r"This is\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)"
        ]
        for pattern in patient_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                extracted_name = match.group(1).strip()
                # Remove common titles if they appear at the start
                extracted_name = re.sub(r'^(Dr\.?|Mr\.?|Mrs\.?|Ms\.?)\s+', '', extracted_name)
                # Validate it's a reasonable name (not common words or greetings)
                invalid_names = ['the', 'and', 'with', 'this', 'that', 'here', 'there', 'dr', 'doctor', 
                               'good', 'morning', 'afternoon', 'evening', 'hello', 'hi', 'hey', 'thank', 'you',
                               'please', 'yes', 'no', 'okay', 'alright', 'sure', 'well', 'now', 'today']
                if len(extracted_name) > 2 and extracted_name.lower() not in invalid_names:
                    patient_name = extracted_name
                    print(f"Matched patient name '{patient_name}' with pattern: {pattern}")
                    break
        
        # Extract English patient age - improved patterns
        age_patterns = [
            r"(\d+)\s*(?:-)?\s*year\s*(?:-)?\s*old",
            r"age\s*(?:is)?\s*[:\s]*(\d+)",
            r"aged\s+(\d+)",
            r"he's\s+(\d+)",
            r"she's\s+(\d+)",
            r"patient is\s+(\d+)"
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, transcript, re.IGNORECASE)
            if age_match:
                patient_age = age_match.group(1)
                break
    
    elif language == "ar":
        # Extract Arabic patient name - improved patterns
        name_patterns = [
            # Pattern for "المريض: [الاسم]"
            r"المريض\s*:\s*([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*?)(?:\s*،|\s*\d+|$)",
            # Pattern for "المريض [الاسم]"
            r"المريض\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*?)(?:\s*،|\s*\d+|$)",
            # Pattern for "المريضة [الاسم]"
            r"المريضة\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*?)(?:\s*،|\s*\d+|$)",
            r"اسمي\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"أنا\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"اسم المريض\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"هذا\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"هذه\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, transcript)
            if match:
                extracted_name = match.group(1).strip()
                # Remove common prefixes
                extracted_name = re.sub(r'^(د\.|دكتور|الدكتور)\s+', '', extracted_name)
                # Validate that it's actually a name (not random text)
                if len(extracted_name) > 1 and not any(word in extracted_name for word in ['في', 'من', 'إلى', 'على', 'مع', 'هو', 'هي']):
                    patient_name = extracted_name
                    print(f"Matched patient name '{patient_name}' with pattern: {pattern}")
                    break
        
        # Extract Arabic patient age - improved patterns
        age_patterns = [
            r"عمري\s+(\d+)\s+سنة",
            r"عمره\s+(\d+)\s+سنة",
            r"عمرها\s+(\d+)\s+سنة",
            r"العمر\s*[:]*\s*(\d+)",
            r"(\d+)\s+سنة"
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, transcript)
            if age_match:
                patient_age = age_match.group(1)
                break
    
    print(f"\nExtracted metadata:")
    print(f"  Provider: {provider_name}")
    print(f"  Patient: {patient_name}")
    print(f"  Age: {patient_age}")
    
    return {
        "patient_id": patient_id,
        "visit_date": current_date,
        "provider_name": provider_name,
        "patient_name": patient_name,
        "patient_age": patient_age
    }

def convert_to_wav(input_path):
    import tempfile
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    output_path = output_file.name
    output_file.close()
    try:
        subprocess.run(['ffmpeg', '-y', '-i', input_path, output_path], check=True)
        return output_path
    except Exception as e:
        print(f"ffmpeg conversion failed: {e}")
        return input_path

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file using appropriate model based on language"""
    try:
        print("\n=== Starting new transcription request ===")
        if 'audio' not in request.files:
            print("No audio file in request")
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio']
        language = request.form.get('language', 'en')
        print(f"Received audio file: {audio_file.filename}, language: {language}")

        # Save audio file temporarily
        file_extension = '.wav'
        if audio_file.filename and '.' in audio_file.filename:
            file_extension = '.' + audio_file.filename.rsplit('.', 1)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            audio_file.save(tmp_file.name)
            tmp_filename = tmp_file.name
            print(f"Saved audio file temporarily as: {tmp_filename}")

        # Convert to WAV
        wav_filename = convert_to_wav(tmp_filename)
        print(f"Converted audio file to WAV: {wav_filename}")

        try:
            if language == 'ar':
                # Use OpenAI gpt-4o-transcribe for Arabic
                transcript = transcribe_arabic_audio(wav_filename)
                if transcript is None:
                    return jsonify({'error': 'Arabic transcription failed'}), 500
            else:
                # Use OpenAI gpt-4o-transcribe for English (best for medical transcription)
                transcript = transcribe_english_audio(wav_filename)
                if transcript is None:
                    return jsonify({'error': 'English transcription failed'}), 500

            print(f"Transcription successful: {len(transcript)} characters")
            print(f"Transcript content: {transcript}")

            # Save transcript
            with open('SOAP.txt', 'w', encoding='utf-8') as f:
                f.write(f"Transcript generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")
                f.write(transcript)

            return jsonify({
                'transcript': transcript,
                'message': 'Transcript saved to SOAP.txt'
            })

        except Exception as e:
            print(f"Transcription error: {str(e)}")
            return jsonify({'error': f'Transcription failed: {str(e)}'}), 500
        finally:
            # Clean up temporary files
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)
                print(f"Cleaned up temporary audio file: {tmp_filename}")
            if os.path.exists(wav_filename):
                os.unlink(wav_filename)
                print(f"Cleaned up temporary WAV file: {wav_filename}")

    except Exception as e:
        print(f"Error in transcription: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-soap', methods=['POST'])
def generate_soap():
    """Generate SOAP note from transcript using OpenAI"""
    try:
        data = request.json
        transcript = data.get('transcript', '')
        language = data.get('language', 'en')

        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400

        if not client.api_key:
            return jsonify({'error': 'OpenAI API key not configured'}), 500

        print("Generating SOAP note...")
        print(f"Transcript length: {len(transcript)} characters")
        print(f"Transcript content: {transcript}")
        print(f"Language: {language}")

        try:
            if language == 'ar':
                print("Calling OpenAI with model gpt-4o for Arabic SOAP note...")
                print(f"Prompt sent to OpenAI:\n{ARABIC_SOAP_PROMPT}")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": ARABIC_SOAP_PROMPT},
                        {"role": "user", "content": f"قم بإنشاء ملاحظة SOAP من هذه المحادثة بين الطبيب والمريض:\n\n{transcript}"}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
            else:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SOAP_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Create a SOAP note from this doctor-patient conversation:\n\n{transcript}"}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )

            soap_content = response.choices[0].message.content
            print(f"OpenAI response length: {len(soap_content)} characters")
            print(f"OpenAI raw response: {soap_content}")

        except Exception as openai_error:
            print(f"OpenAI API error: {str(openai_error)}")
            return jsonify({'error': f'OpenAI API error: {str(openai_error)}'}), 500

        try:
            # First try to extract JSON from the response
            soap_note = extract_json_from_response(soap_content)
            if soap_note is None:
                print(f"Could not extract JSON from response: {soap_content}")
                return jsonify({
                    'soapNote': {'raw_response': soap_content},
                    'message': 'SOAP note could not be parsed as JSON. See raw response.',
                    'error': 'json_parse_failed'
                })
            # Add metadata to the SOAP note
            metadata = generate_soap_note_metadata(transcript, language)
            if 'soap_note' in soap_note:
                # Only update metadata fields if they were not properly extracted by AI
                if soap_note['soap_note'].get('provider_name', '').lower() in ['unknown', 'غير محدد', 'not mentioned', 'dr. unknown']:
                    soap_note['soap_note']['provider_name'] = metadata['provider_name']
                if soap_note['soap_note'].get('patient_name', '').lower() in ['unknown', 'غير محدد', 'dr', 'د', 'مرحبا', 'hello']:
                    soap_note['soap_note']['patient_name'] = metadata['patient_name']
                if soap_note['soap_note'].get('patient_age', '').lower() in ['unknown', 'غير محدد']:
                    soap_note['soap_note']['patient_age'] = metadata['patient_age']
                # Always update these
                soap_note['soap_note']['patient_id'] = metadata['patient_id']
                soap_note['soap_note']['visit_date'] = metadata['visit_date']
            else:
                # If the response doesn't have the new structure, wrap it
                soap_note = {
                    'soap_note': {
                        **metadata,
                        **soap_note
                    }
                }
            print("Successfully parsed JSON from OpenAI response")

            # === POST-PROCESSING: Remove unmentioned fields/sections ===
            def is_unmentioned(val):
                if not isinstance(val, str):
                    return False
                val_lower = val.strip().lower()
                # English phrases
                unmentioned_phrases = [
                    'not mentioned', 'not discussed', 'not addressed',
                    'no known', 'no current', 'pending clinical examination',
                    'vital signs not available', 'no medications prescribed currently',
                    'no known allergies', 'no current medications', 'not available currently',
                    'not specified', 'not available', 'none', 'n/a', 'na'
                ]
                # Arabic phrases
                unmentioned_phrases += [
                    'لم يذكر', 'لم يتم التطرق', 'لا يتناول أدوية حالياً',
                    'لا يوجد تاريخ مرضي مزمن', 'بانتظار الفحص السريري',
                    'العلامات الحيوية غير متوفرة حالياً', 'لم يتم وصف أدوية حالياً',
                    'لم يتم التطرق لهذه النقاط أثناء اللقاء', 'غير متوفرة حالياً',
                    'غير محدد', 'غير متوفر', 'لا يوجد', 'غير متاح', 'غير معروف',
                    'غير مذكور', 'غير محدد في المحادثة', 'لم يتم ذكره',
                    'غير متوفر حالياً', 'غير محدد في المحادثة', 'غير متوفر في المحادثة'
                ]
                return any(phrase in val_lower for phrase in unmentioned_phrases)

            def clean_section(section):
                if not isinstance(section, dict):
                    return section
                cleaned = {k: v for k, v in section.items() if v and not is_unmentioned(v)}
                return cleaned if cleaned else None

            # Clean each main section
            soap_note = soap_note.get('soap_note', soap_note)
            for main_section in ["subjective", "objective", "assessment", "plan"]:
                if main_section in soap_note:
                    cleaned = clean_section(soap_note[main_section])
                    if cleaned:
                        soap_note[main_section] = cleaned
                    else:
                        # For objective section, always keep it even if empty
                        if main_section == "objective":
                            soap_note[main_section] = {}
                        else:
                            del soap_note[main_section]
                else:
                    # Always ensure objective section exists
                    if main_section == "objective":
                        soap_note[main_section] = {}
            # === END POST-PROCESSING ===

            # Wrap the response in the expected structure if needed
            if 'soap_note' not in soap_note:
                metadata = generate_soap_note_metadata(transcript, language)
                soap_note = {
                    'soap_note': {
                        **metadata,
                        **soap_note
                    }
                }
        except Exception as json_error:
            print(f"JSON processing error: {json_error}")
            print(f"Raw OpenAI response: {soap_content}")
            return jsonify({
                'soapNote': {'raw_response': soap_content},
                'message': 'SOAP note could not be parsed as JSON. See raw response.',
                'error': 'json_parse_failed'
            })

        with open('SOAP_note.json', 'w', encoding='utf-8') as f:
            json.dump(soap_note, f, indent=2, ensure_ascii=False)

        with open('SOAP.txt', 'a', encoding='utf-8') as f:
            f.write("\n\n" + "="*50 + "\n")
            f.write("SOAP NOTE\n")
            f.write("="*50 + "\n")
            f.write(json.dumps(soap_note, indent=2, ensure_ascii=False))

        print("SOAP note generated and saved successfully")

        return jsonify({
            'soapNote': soap_note,
            'message': 'SOAP note generated and saved'
        })

    except Exception as e:
        print(f"Error generating SOAP note: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    """Home endpoint with API information"""
    return jsonify({
        'message': 'SOAP Note Voice Recorder Backend',
        'status': 'running',
        'endpoints': {
            'transcribe': '/transcribe',
            'generate-soap': '/generate-soap',
            'health': '/health'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/suggest', methods=['GET'])
def get_medical_suggestions():
    """Get medical suggestions from Supabase database"""
    try:
        word = request.args.get('word', '').strip()
        
        if not word:
            return jsonify({'error': 'No word provided'}), 400
        
        if len(word) < 2:
            return jsonify({'error': 'Word must be at least 2 characters'}), 400
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return jsonify({'error': 'Database not configured'}), 500
        
        # Connect to Supabase database
        try:
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Execute the SQL query with proper parameterization
            query = """
                SELECT T."TypeName", C."CodeDisplayValue" 
                FROM "Sys_TypeLookups" T
                INNER JOIN "Sys_Codes" C ON T."TypeID" = C."TypeID"
                WHERE C."CodeDisplayValue" ILIKE %s
                LIMIT 30
            """
            
            # Use parameterized query to prevent SQL injection
            search_pattern = f'%{word}%'
            cursor.execute(query, (search_pattern,))
            
            results = cursor.fetchall()
            print(f"Database query returned {len(results)} raw results for word '{word}'")
            
            # Format results and remove duplicates
            formatted_results = []
            seen_values = set()
            
            for row in results:
                display_value = row['CodeDisplayValue']
                type_name = row['TypeName']
                print(f"Raw result: {display_value} | Type: {type_name}")
                
                # Case-insensitive deduplication
                display_value_lower = display_value.lower()
                if display_value_lower not in seen_values:
                    seen_values.add(display_value_lower)
                    formatted_results.append({
                        'typeName': type_name,
                        'value': display_value
                    })
            
            print(f"Formatted results after deduplication: {len(formatted_results)} items")
            print(f"Final response: {formatted_results}")
            
            # Close database connection
            cursor.close()
            conn.close()
            
            response_data = {
                'word': word,
                'results': formatted_results,
                'uniqueCount': len(formatted_results),
                'source': 'supabase'
            }
            print(f"Sending response: {response_data}")
            
            return jsonify(response_data)
            
        except psycopg2.Error as db_error:
            print(f"Database error: {str(db_error)}")
            return jsonify({'error': 'Database query failed'}), 500
        
    except Exception as e:
        print(f"Error in get_medical_suggestions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check-medical-terms', methods=['POST'])
def check_medical_terms():
    """Check medical terms in text for spelling errors"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Ensure text is a string to fix .trim() error
        if not isinstance(text, str):
            text = str(text) if text else ""
        
        # Check medical terms
        check_result = medical_spell_checker.check_text(text)
        
        # Handle new format with unique counts
        if isinstance(check_result, dict):
            results = check_result.get('results', [])
            unique_terms = check_result.get('unique_terms', [])
            unique_count = check_result.get('unique_count', 0)
            total_occurrences = check_result.get('total_occurrences', 0)
        else:
            # Fallback for old format
            results = check_result
            unique_terms = list(set([r['term'].lower() for r in results]))
            unique_count = len(unique_terms)
            total_occurrences = len(results)
        
        # Format results for frontend
        formatted_results = []
        for result in results:
            formatted_results.append({
                'term': result['term'],
                'start': result['start_pos'],
                'end': result['end_pos'],
                'isCorrect': result['is_correct'],
                'suggestions': result['suggestions'],
                'confidence': result['confidence'],
                'category': result.get('category', 'medical')
            })
        
        return jsonify({
            'results': formatted_results,
            'unique_terms': unique_terms,
            'unique_count': unique_count,
            'total_occurrences': total_occurrences,
            'text': text
        })
        
    except Exception as e:
        print(f"Error checking medical terms: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/add-medicine', methods=['POST'])
def add_medicine():
    """Add a medicine term to the dynamic list"""
    try:
        data = request.json
        term = data.get('term', '')
        
        if not term:
            return jsonify({'error': 'No term provided'}), 400
        
        # Add to dynamic list
        medical_spell_checker.add_medicine_to_dynamic_list(term)
        
        return jsonify({
            'message': f'Added "{term}" to dynamic medicine list',
            'success': True
        })
        
    except Exception as e:
        print(f"Error adding medicine: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dynamic-list-stats', methods=['GET'])
def get_dynamic_list_stats():
    """Get statistics about the dynamic medicine list"""
    try:
        stats = medical_spell_checker.get_dynamic_list_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting dynamic list stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/medical-nlp-status', methods=['GET'])
def get_medical_nlp_status():
    """Get medical NLP status and configuration"""
    try:
        status = medical_spell_checker.get_medical_nlp_status()
        return jsonify(status)
    except Exception as e:
        print(f"Error getting medical NLP status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/validate-medical-term', methods=['POST'])
def validate_medical_term():
    """Validate a single medical term"""
    try:
        data = request.json
        term = data.get('term', '')
        context = data.get('context', '')
        position = data.get('position', 0)
        
        if not term:
            return jsonify({'error': 'No term provided'}), 400
        
        # Check the term
        result = medical_spell_checker.check_spelling(term)
        
        # Get contextual suggestions if available
        if context and not result['is_correct']:
            contextual_suggestions = medical_spell_checker.get_contextual_suggestions(
                term, context, position
            )
            if contextual_suggestions:
                result['suggestions'] = contextual_suggestions
        
        return jsonify({
            'term': term,
            'isCorrect': result['is_correct'],
            'suggestions': result['suggestions'],
            'confidence': result['confidence']
        })
        
    except Exception as e:
        print(f"Error validating medical term: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting SOAP Note Backend Server...")
    if not openai.api_key:
        print("⚠️  OPENAI_API_KEY not set! The SOAP generation will not work.")

    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    app.run(debug=debug, port=port, host='0.0.0.0')