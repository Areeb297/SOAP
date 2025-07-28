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

# Set temporary directory to a folder on D: drive
temp_dir = "D:/soap_temp_files"
os.makedirs(temp_dir, exist_ok=True)
tempfile.tempdir = temp_dir
print(f"Temporary files will be stored in: {tempfile.tempdir}")

app = Flask(__name__)
CORS(app)

# Initialize models
print("Loading models...")

# Note: We now use OpenAI gpt-4o-transcribe for both English and Arabic
# as it provides better medical transcription quality
# Keeping whisper as fallback for offline/development scenarios
# Remove Whisper model initialization and fallback logic

# Munsit API configuration
MUNSIT_API_KEY = "sk-ctxt-01f0b2224dbc4645b4ff24fd1d5f16fb"
MUNSIT_API_URL = "https://api.cntxt.tools/audio/transcribe"

# Load environment variables and configure OpenAI
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("⚠️  Warning: OPENAI_API_KEY not set in environment variables!")
    print("Please set it in your .env file or as an environment variable.")

# System prompt for SOAP note generation
SOAP_SYSTEM_PROMPT = """You are a medical documentation assistant specialized in creating SOAP notes from doctor-patient conversations.

Output ONLY a valid JSON object without any explanation or external text. If you add anything outside the JSON object, the response will be rejected. The response must be a JSON object only with the following structure:

{
  "subjective": {
    "chief_complaint": "...",
    "history_of_present_illness": "...",
    "past_medical_history": "...",
    "family_history": "...",
    "social_history": "...",
    "medications": "...",
    "allergies": "..."
  },
  "objective": {
    "vital_signs": "...",
    "physical_examination_findings": "..."
  },
  "assessment": {
    "diagnosis": "...",
    "risk_factors": "...",
    "differential_diagnosis": "..."
  },
  "plan": {
    "medications_prescribed": "...",
    "procedures_interventions": "...",
    "patient_education_counseling": "...",
    "follow_up_instructions": "..."
  }
}

Professional medical documentation instructions:

SUBJECTIVE:
- Chief Complaint: Write the main complaint clearly with duration (example: "Severe fatigue for 2 days")
- History of Present Illness: Should be detailed and include:
  • Duration and progression of symptoms with precision
  • Severity and description of symptoms
  • Associated and denied symptoms clearly (example: "No headache, no fever, no loss of appetite")
  • Triggering or alleviating factors if present
  • Impact on daily activities, sleep, and work - CRITICAL: If symptoms affect sleep, work, or physical function, include that specifically (e.g., "woke up due to pain", "unable to walk normally", "missed work due to symptoms")
- Past Medical History: If patient says "I'm healthy" or denies illness, write "No known chronic illnesses per patient report". If surgeries mentioned, include them clearly labeled (e.g., "Appendectomy 10 years ago"). If not discussed, use "Not discussed during encounter"
- Family History: If patient mentions family illness, document it. If not mentioned, use "Not discussed during encounter"
- Social History: If patient mentions exercise, diet, smoking, alcohol, or occupation, include that information. If not addressed, use "Not addressed during encounter"
- Medications: If not mentioned, use "No current medications"
- Allergies: If not mentioned, use "No known allergies"

OBJECTIVE:
- Vital Signs: Use "Vital signs not available currently" if not mentioned, or record what was mentioned
- Physical Examination Findings: Use "Pending clinical examination" if no specific examination mentioned, or document any examination that was mentioned

ASSESSMENT:
- Diagnosis: Use professional medical format like "Working diagnosis: Suspected..." or "Most likely diagnosis:" based on mentioned symptoms
- Differential Diagnosis: List possible differential diagnoses based on symptoms, such as:
  • Different causes for the mentioned symptoms
  • Similar medical conditions
  • Related nutritional or psychological issues
- Risk Factors: CRITICAL - If patient has family history, smoking, poor diet, hypertension, obesity, diabetes, or other comorbidities mentioned, always list them here. If patient mentions lifestyle factors, include them. Example: "Hypertension; family history of coronary artery disease; sedentary lifestyle". If truly not discussed, use "Not discussed during encounter"

PLAN:
- Medications Prescribed: If no medications mentioned, use "No medications prescribed currently"
- Procedures/Interventions: CRITICAL FOR PATIENT SAFETY - List required tests with correct medical names. For emergency/high-risk presentations:
  • Chest pain: Include "Serial ECG every 3-6 hours, serial troponins every 3 hours, continuous cardiac monitoring"
  • Abdominal pain: Include appropriate imaging like "Ultrasound abdomen" or "CT abdomen/pelvis if indicated"
  • Suspected infections: Include "Blood cultures, urinalysis with microscopy"
  • Dynamic conditions (DKA, electrolyte imbalance): Include "Serial glucose monitoring every hour" or "Repeat electrolytes in 2-4 hours"
  • For stable conditions: Standard testing like "CBC, comprehensive metabolic panel, inflammatory markers"
- Patient Education/Counseling: Should include comprehensive education such as:
  • Appropriate dietary advice for the condition
  • Warning signs that require immediate medical attention
  • Lifestyle instructions
  • When to seek immediate medical care
- Follow-up Instructions: CRITICAL - For emergency or high-risk presentations (chest pain, acute abdominal pain, neurological deficits), include urgent monitoring such as "Keep patient under observation in emergency department", "Serial monitoring in hospital setting", or "Immediate admission for further evaluation". For stable conditions: "Contact patient when test results are available" or routine follow-up.

Use precise and professional medical terminology. Make documentation comprehensive and detailed as expected in professional medical environments.

Do not write anything outside the JSON object."""

# Arabic SOAP prompt
ARABIC_SOAP_PROMPT = """
أنت طبيب متخصص في التوثيق الطبي وإنشاء ملاحظات SOAP احترافية من محادثات الطبيب والمريض. أجب فقط باللغة العربية واستخدم المصطلحات الطبية المناسبة. 

أخرج فقط كائن JSON صالح بدون أي شرح أو نص خارجي. إذا أضفت أي شيء خارج كائن JSON سيتم رفض الإجابة. يجب أن يكون الرد كائن JSON فقط بالهيكل التالي:

{
  "subjective": {
    "allergies": "...",
    "chief_complaint": "...",
    "family_history": "...",
    "history_of_present_illness": "...",
    "medications": "...",
    "past_medical_history": "...",
    "social_history": "..."
  },
  "objective": {
    "physical_examination_findings": "...",
    "vital_signs": "..."
  },
  "assessment": {
    "diagnosis": "...",
    "differential_diagnosis": "...",
    "risk_factors": "..."
  },
  "plan": {
    "follow_up_instructions": "...",
    "investigations": "...",
    "medications_prescribed": "...",
    "patient_education_counseling": "..."
  }
}

تعليمات احترافية للتوثيق الطبي:

SUBJECTIVE (القسم الذاتي):
- Allergies: إذا لم تُذكر استخدم "لم يذكر وجود حساسية"
- Chief Complaint: اكتب الشكوى الرئيسية بوضوح مع المدة (مثال: "تعب شديد منذ يومين")
- Family History: إذا ذكر المريض تاريخ عائلي، وثقه. إذا لم تُذكر استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"
- History of Present Illness: يجب أن يكون مفصلاً ويشمل:
  • مدة الأعراض وتطورها بدقة
  • شدة الأعراض ووصفها
  • الأعراض المصاحبة والمنفية بوضوح (مثال: "لا صداع، لا حرارة، لا فقدان شهية")
  • العوامل المحفزة أو المخففة إن وُجدت
  • التأثير على الأنشطة اليومية والنوم والعمل - مهم جداً: إذا أثرت الأعراض على النوم أو العمل أو الحركة، اذكر ذلك بوضوح (مثال: "استيقظ من النوم بسبب الألم"، "لا يستطيع المشي بشكل طبيعي"، "تغيب عن العمل بسبب الأعراض")
- Medications: إذا لم تُذكر استخدم "لا يتناول أدوية حالياً"
- Past Medical History: إذا قال المريض "أنا بصحة جيدة" أو نفى وجود أمراض، اكتب "لا يوجد تاريخ مرضي مزمن حسب إفادة المريض". إذا ذُكرت عمليات جراحية، ضعها مع التوضيح (مثال: "استئصال الزائدة منذ 10 سنوات"). إذا لم تُذكر استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"
- Social History: إذا ذكر المريض الرياضة أو النظام الغذائي أو التدخين أو الكحول أو المهنة، ضع هذه المعلومات. إذا لم تُناقش استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"

OBJECTIVE (القسم الموضوعي):
- Physical Examination Findings: استخدم "بانتظار الفحص السريري" إذا لم يُذكر فحص محدد، أو وثق أي فحص تم ذكره
- Vital Signs: استخدم "العلامات الحيوية غير متوفرة حالياً" إذا لم تُذكر، أو سجل ما ذُكر من قياسات

ASSESSMENT (قسم التقييم):
- Diagnosis: استخدم صيغة طبية احترافية مثل "التشخيص المبدئي: اشتباه في..." أو "التشخيص الأكثر احتمالاً:" بناءً على الأعراض المذكورة
- Differential Diagnosis: اذكر التشخيصات التفريقية المحتملة بناءً على الأعراض، مثل:
  • أسباب مختلفة للأعراض المذكورة
  • حالات طبية مشابهة
  • مشاكل غذائية أو نفسية ذات علاقة
- Risk Factors: مهم جداً - إذا ذكر المريض تاريخ عائلي أو تدخين أو نظام غذائي سيء أو ارتفاع ضغط الدم أو سمنة أو سكري أو أمراض مصاحبة، اذكرها هنا دائماً. إذا ذكر عوامل نمط الحياة، ضعها. مثال: "ارتفاع ضغط الدم؛ تاريخ عائلي لأمراض القلب؛ نمط حياة خامل". إذا لم تُناقش حقاً استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"

PLAN (قسم الخطة):
- Follow Up Instructions: مهم جداً لسلامة المريض - للحالات الطارئة أو عالية الخطورة (ألم صدر، ألم بطن حاد، أعراض عصبية)، اذكر المراقبة العاجلة مثل "إبقاء المريض تحت المراقبة في قسم الطوارئ"، "مراقبة متسلسلة في المستشفى"، أو "دخول فوري للتقييم الإضافي". للحالات المستقرة: "الاتصال بالمريض عند توفر النتائج" أو متابعة روتينية
- Investigations: مهم جداً لسلامة المريض - اذكر الفحوصات المطلوبة بأسمائها الطبية الصحيحة. للحالات الطارئة/عالية الخطورة:
  • ألم الصدر: "تخطيط قلب متسلسل كل 3-6 ساعات، إنزيمات قلبية متسلسلة كل 3 ساعات، مراقبة قلبية مستمرة"
  • ألم البطن: تصوير مناسب مثل "سونار البطن" أو "CT البطن والحوض عند الحاجة"
  • التهابات مشتبهة: "مزارع الدم، تحليل البول مع الفحص المجهري"
  • حالات متغيرة (DKA، خلل أملاح): "مراقبة السكر كل ساعة" أو "إعادة فحص الأملاح في 2-4 ساعات"
  • للحالات المستقرة: فحوصات معيارية مثل "CBC، لوحة أيضية شاملة، مؤشرات التهاب"
- Medications Prescribed: إذا لم تُذكر أدوية استخدم "لم يتم وصف أدوية حالياً"
- Patient Education Counseling: يجب أن يشمل تثقيف شامل مثل:
  • النصائح الغذائية المناسبة للحالة
  • علامات التحذير التي تستدعي مراجعة فورية
  • تعليمات نمط الحياة
  • متى يجب مراجعة الطبيب فوراً

استخدم مصطلحات طبية دقيقة ومهنية. اجعل التوثيق شاملاً ومفصلاً كما يتوقع في البيئة الطبية الاحترافية.

لا تكتب أي شيء خارج كائن JSON.
"""

# Use OpenAI Python SDK 1.x for chat completions
client = OpenAI()

def extract_json_from_response(response_text):
    """Extract JSON from response text that may contain extra text"""
    try:
        # First try to parse as-is
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        # Try to find JSON within the text using regex
        import re
        # Look for content between outermost curly braces
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        # Try to find content that starts with { and ends with }
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

        try:
            if language == 'ar':
                # Use OpenAI gpt-4o-transcribe for Arabic
                transcript = transcribe_arabic_audio(tmp_filename)
                if transcript is None:
                    return jsonify({'error': 'Arabic transcription failed'}), 500
            else:
                # Use OpenAI gpt-4o-transcribe for English (best for medical transcription)
                transcript = transcribe_english_audio(tmp_filename)
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
            # Clean up temporary file
            if os.path.exists(tmp_filename):
                os.unlink(tmp_filename)
                print(f"Cleaned up temporary audio file: {tmp_filename}")

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
                # Show the raw response in the frontend if JSON parsing fails
                return jsonify({
                    'soapNote': {'raw_response': soap_content},
                    'message': 'SOAP note could not be parsed as JSON. See raw response.',
                    'error': 'json_parse_failed'
                })
            print("Successfully parsed JSON from OpenAI response")
        except Exception as json_error:
            print(f"JSON processing error: {json_error}")
            print(f"Raw OpenAI response: {soap_content}")
            # Show the raw response in the frontend if JSON parsing fails
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