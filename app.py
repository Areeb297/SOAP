# app.py - Flask backend for SOAP Note Voice Recorder

from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper
import openai
import os
import tempfile
import json
from datetime import datetime
from dotenv import load_dotenv
import requests
from pydub import AudioSegment
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

# Initialize Whisper model for English
model_size = os.getenv("WHISPER_MODEL", "base")
print(f"Loading Whisper model ({model_size}) for English...")
whisper_model = whisper.load_model(model_size)

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

Create a structured SOAP note with the following sections:

SUBJECTIVE:
- Chief Complaint (CC): The main reason for the visit
- History of Present Illness (HPI): Detailed description of the current problem
- Past Medical History (PMH): Relevant past medical conditions
- Family History: Relevant family medical history
- Social History: Lifestyle factors (smoking, alcohol, occupation, etc.)
- Medications: Current medications the patient is taking
- Allergies: Known allergies

OBJECTIVE:
- Vital Signs: Temperature, blood pressure, heart rate, respiratory rate, etc.
- Physical Examination Findings: Observable clinical findings

ASSESSMENT:
- Diagnosis: Doctor's clinical impression and diagnoses
- Risk Factors: Identified risk factors

PLAN:
- Medications Prescribed: New medications with dosage
- Procedures/Interventions: Lab tests, imaging, or procedures ordered
- Patient Education/Counseling: Instructions given to patient
- Follow-up Instructions: When to return, referrals, etc.

Format the output as a JSON object with these four main sections. Only include subsections that have relevant information from the conversation. If information for a subsection is not mentioned, omit that subsection."""

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
- Family History: إذا لم تُذكر استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"
- History of Present Illness: يجب أن يكون مفصلاً ويشمل:
  • مدة الأعراض وتطورها بدقة
  • شدة الأعراض ووصفها
  • الأعراض المصاحبة والمنفية بوضوح (مثال: "لا صداع، لا حرارة، لا فقدان شهية")
  • العوامل المحفزة أو المخففة إن وُجدت
  • التأثير على الأنشطة اليومية والنوم والعمل
- Medications: إذا لم تُذكر استخدم "لا يتناول أدوية حالياً"
- Past Medical History: إذا لم تُذكر استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"
- Social History: إذا لم تُذكر استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"

OBJECTIVE (القسم الموضوعي):
- Physical Examination Findings: استخدم "بانتظار الفحص السريري" إذا لم يُذكر فحص محدد، أو وثق أي فحص تم ذكره
- Vital Signs: استخدم "العلامات الحيوية غير متوفرة حالياً" إذا لم تُذكر، أو سجل ما ذُكر من قياسات

ASSESSMENT (قسم التقييم):
- Diagnosis: استخدم صيغة طبية احترافية مثل "التشخيص المبدئي: اشتباه في..." أو "التشخيص الأكثر احتمالاً:" بناءً على الأعراض المذكورة
- Differential Diagnosis: اذكر التشخيصات التفريقية المحتملة بناءً على الأعراض، مثل:
  • أسباب مختلفة للأعراض المذكورة
  • حالات طبية مشابهة
  • مشاكل غذائية أو نفسية ذات علاقة
- Risk Factors: إذا لم تُذكر استخدم "لم يتم التطرق لهذه النقاط أثناء اللقاء"

PLAN (قسم الخطة):
- Follow Up Instructions: حدد خطة المتابعة بوضوح (مثال: "الاتصال بالمريض فور توفر نتائج الفحوصات")
- Investigations: اذكر الفحوصات المطلوبة بأسمائها الطبية الصحيحة (مثال: "CBC، Ferritin، Iron profile، Vitamin B12، Folate")
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

def transcribe_arabic_audio(audio_path):
    """Transcribe Arabic audio using OpenAI gpt-4o-transcribe model"""
    try:
        print(f"Starting Arabic transcription with OpenAI gpt-4o-transcribe for file: {audio_path}")
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                response_format="text"
            )
        print(f"Transcription result: {transcription}")
        return transcription
    except Exception as e:
        print(f"Error in OpenAI gpt-4o-transcribe transcription: {str(e)}")
        import traceback
        print(f"Full error traceback: {traceback.format_exc()}")
        return None

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
                # Use Whisper for English
                result = whisper_model.transcribe(tmp_filename, language="en")
                transcript = result["text"]
            
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