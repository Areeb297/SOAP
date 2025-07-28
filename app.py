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
"""

# Updated Arabic SOAP prompt
ARABIC_SOAP_PROMPT = """
أنت طبيب متخصص في التوثيق الطبي وإنشاء ملاحظات SOAP احترافية من محادثات الطبيب والمريض. أجب فقط باللغة العربية واستخدم المصطلحات الطبية المناسبة.

أخرج فقط كائن JSON صالح بدون أي شرح أو نص خارجي. إذا أضفت أي شيء خارج كائن JSON سيتم رفض الإجابة. يجب أن يكون الرد كائن JSON فقط بالهيكل التالي:

{
  "soap_note": {
    "patient_id": "يتم إنشاؤه تلقائياً",
    "visit_date": "تاريخ ووقت الزيارة",
    "provider_name": "د. [الاسم من المحادثة أو 'غير محدد']",
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
"""

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
    """Generate metadata for SOAP note: patient_id, visit_date, provider_name"""
    from datetime import datetime
    import uuid
    # Generate current date in ISO format
    current_date = datetime.now().isoformat() + "Z"
    # Generate a simple patient ID
    patient_id = str(uuid.uuid4())[:8]
    # Extract provider name from transcript (basic extraction)
    provider_name = "Dr. Unknown" if language == "en" else "د. غير محدد"
    if language == "en":
        import re
        dr_match = re.search(r'Dr\.\s+([A-Z][a-z]+)', transcript)
        if dr_match:
            provider_name = f"Dr. {dr_match.group(1)}"
    elif language == "ar":
        import re
        dr_match = re.search(r'د\.\s*([^\s،]+)', transcript)
        if dr_match:
            provider_name = f"د. {dr_match.group(1)}"
    return {
        "patient_id": patient_id,
        "visit_date": current_date,
        "provider_name": provider_name
    }

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