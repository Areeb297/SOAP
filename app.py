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
   - Age (exact number mentioned) - MUST be included in patient_age field
   - Location/address/city mentioned
   - Any other demographic information

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
   - العمر (الرقم المحدد المذكور) - يجب تضمينه في حقل patient_age
   - الموقع/العنوان/المدينة المذكورة
   - أي معلومات ديموغرافية أخرى

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
        # Extract English patient name (look for "I'm [Name]" or "My name is [Name]")
        name_patterns = [
            r"I'm\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"My name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"I am\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                patient_name = match.group(1)
                break
        
        # Extract English patient age (look for "I'm [age] years old" or similar)
        age_match = re.search(r"(\d+)\s+years?\s+old", transcript, re.IGNORECASE)
        if age_match:
            patient_age = age_match.group(1)
    
    elif language == "ar":
        # Extract Arabic patient name (look for "اسمي [Name]" or "أنا [Name]")
        name_patterns = [
            r"اسمي\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"أنا\s+([^\s،؟!\.]+(?:\s+[^\s،؟!\.]+)*)",
            r"اسمي\s+([^\s،؟!\.]+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, transcript)
            if match:
                patient_name = match.group(1)
                break
        
        # Extract Arabic patient age (look for "عمري [age] سنة" or similar)
        age_match = re.search(r"عمري\s+(\d+)\s+سنة", transcript)
        if age_match:
            patient_age = age_match.group(1)
    
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
                soap_note['soap_note'].update(metadata)
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
                        del soap_note[main_section]
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

if __name__ == '__main__':
    print("Starting SOAP Note Backend Server...")
    if not openai.api_key:
        print("⚠️  OPENAI_API_KEY not set! The SOAP generation will not work.")

    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    app.run(debug=debug, port=port, host='0.0.0.0')