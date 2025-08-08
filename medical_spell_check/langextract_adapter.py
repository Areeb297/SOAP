import os
import textwrap
from typing import List

try:
    import langextract as lx  # type: ignore
except Exception as e:
    lx = None  # Will handle at runtime


from .medical_extractor import ExtractedEntity


class LangExtractAdapter:
    """
    Thin adapter around the LangExtract Python library.
    Returns grounded entities (text + character offsets) using a clinical-focused prompt.
    Also exposes a SOAP-specific extractor to feed structured sections.
    """

    def __init__(self, model_id: str | None = None, api_key: str | None = None):
        self.model_id = model_id or os.getenv("LANGEXTRACT_MODEL_ID", "gemini-2.5-pro")
        # LangExtract supports picking API key from env; still allow override
        self.api_key = api_key or os.getenv("LANGEXTRACT_API_KEY")

        # Default prompt tuned for medication/clinical extraction
        self.prompt = textwrap.dedent("""\
            Extract medication-related information including medication name, dosage, route, frequency, duration,
            and conditions in the exact order they appear in the text.

            Rules:
            - Use exact spans from the source text (no paraphrasing).
            - Do not overlap entities.
            - Prefer concise spans (e.g., "500 mg" not "the 500 mg dose").
        """)

        # High-quality examples to bootstrap extraction in clinical and Arabic texts
        self.examples = [
            self._example_medication(),
            self._example_stroke_neuro_english(),
            self._example_dka_english(),
            self._example_chest_pain_arabic(),
            self._example_pneumonia_arabic()
        ]

        # SOAP few-shots (English) provided by user to maximize section completeness
        self.soap_few_shots = [
            {
                "input": "Good morning, I'm Dr. Michael from the neurology department. Can I get your name and age?\n\nI'm Patricia Johnson, 67 years old, from Boston.\n\nWhat brings you in today, Patricia?\n\nI woke up this morning and noticed my left arm and leg feel weak and numb.\n\nWhen did you first notice this?\n\nAround 7 AM when I tried to get out of bed. I couldn't lift my left arm properly.\n\nAny other symptoms?\n\nI have a severe headache that started about an hour ago, and I'm having trouble speaking clearly.\n\nCan you describe the headache?\n\nIt's the worst headache I've ever had, like a thunderclap, and it's mostly on the right side of my head.\n\nAny vision problems?\n\nYes, my vision is blurry, especially in my left eye.\n\nAny dizziness or balance problems?\n\nYes, I feel dizzy and unsteady when I try to walk.\n\nAny nausea or vomiting?\n\nI feel nauseous but haven't vomited.\n\nAny confusion or memory problems?\n\nI'm having trouble finding the right words and I feel confused.\n\nHave you had similar symptoms before?\n\nNo, never anything like this.\n\nAny medical conditions?\n\nI have high blood pressure, atrial fibrillation, and I take blood thinners.\n\nWhat medications do you take?\n\nWarfarin 5mg daily, Lisinopril 10mg daily, and Metoprolol 25mg twice daily.\n\nAny allergies?\n\nI'm allergic to penicillin.\n\nAny previous surgeries?\n\nI had a hip replacement 3 years ago.\n\nFamily history of stroke?\n\nYes, my father had a stroke at age 70.\n\nDo you smoke or drink alcohol?\n\nI quit smoking 10 years ago, and I have 1 glass of wine with dinner.\n\nWhat's your occupation?\n\nI'm retired, but I volunteer at the library twice a week.\n\nLet me check your vital signs. Your blood pressure is 180/110, heart rate 95, temperature 98.8°F, respiratory rate 18.\n\nI'll perform a neurological exam. I can see left-sided weakness, slurred speech, and left facial droop.\n\nI'll order a CT scan of your head, MRI, and blood work including coagulation studies.\n\nBased on your symptoms and exam, I suspect you're having an acute ischemic stroke affecting the right side of your brain.\n\nI'll start you on aspirin and arrange for immediate thrombolytic therapy if the CT scan confirms it's safe.\n\nYou'll need to stay in the hospital for monitoring and rehabilitation. We'll also need to adjust your blood thinners.\n\nIt's crucial to call 911 immediately if you experience any worsening symptoms. We'll arrange for stroke rehabilitation.",
                "output": {
                    "subjective": {
                        "chief_complaint": "Weakness and numbness in left arm and leg.",
                        "history_of_present_illness": "Patient noticed weakness and numbness in the left arm and leg upon waking around 7 AM. Severe thunderclap headache on the right side, blurry vision in the left eye, slurred speech, dizziness, and confusion.",
                        "past_medical_history": "Hypertension, atrial fibrillation, previous hip replacement 3 years ago.",
                        "family_history": "Father had a stroke at age 70.",
                        "social_history": "Former smoker (quit 10 years ago), 1 glass of wine with dinner, retired, volunteers at library.",
                        "medications": [
                            {"name": "Warfarin", "dosage": "5mg", "frequency": "daily", "route": "oral", "duration": "current"},
                            {"name": "Lisinopril", "dosage": "10mg", "frequency": "daily", "route": "oral", "duration": "current"},
                            {"name": "Metoprolol", "dosage": "25mg", "frequency": "twice daily", "route": "oral", "duration": "current"}
                        ],
                        "allergies": ["Penicillin"]
                    },
                    "objective": {
                        "vital_signs": {"temperature": "98.8°F","blood_pressure": "180/110","heart_rate": "95","respiratory_rate": "18","oxygen_saturation": ""},
                        "physical_exam": "Left-sided weakness, slurred speech, left facial droop."
                    },
                    "assessment": {
                        "diagnosis": "Acute ischemic stroke affecting the right hemisphere.",
                        "risk_factors": ["Hypertension", "Atrial fibrillation", "Age", "Family history of stroke"]
                    },
                    "plan": {
                        "medications_prescribed": [{"name": "Aspirin","dosage": "","frequency": "","duration": "","route": "oral"}],
                        "procedures_or_tests": ["CT scan of the head","MRI","Blood work","Coagulation studies"],
                        "patient_education": "Call 911 for any worsening symptoms.",
                        "follow_up_instructions": "Immediate thrombolytic therapy pending imaging; inpatient monitoring, rehabilitation, adjust anticoagulation."
                    }
                }
            },
            {
                "input": "Hello, I'm Dr. Sarah from the emergency department. Can I get your name and age?\n\nI'm Robert Wilson, 58 years old, from Seattle.\n\nWhat brings you to the ER today, Robert?\n\nI've been feeling very weak and dizzy for the past few days, and today I couldn't even get out of bed.\n\nWhen did these symptoms start?\n\nAbout 3 days ago, but they've been getting worse each day.\n\nAny other symptoms?\n\nI'm very thirsty all the time, urinating a lot, and I've lost about 10 pounds in the last month.\n\nHave you been eating normally?\n\nNo, I've had no appetite lately, and when I do eat, I feel nauseous.\n\nAny vomiting?\n\nYes, I vomited twice yesterday and once this morning.\n\nAny abdominal pain?\n\nYes, I have some cramping in my stomach.\n\nAny fever?\n\nI feel warm, but I haven't checked my temperature.\n\nAny shortness of breath?\n\nYes, especially when I try to walk around.\n\nHave you had similar symptoms before?\n\nNo, this is completely new to me.\n\nAny medical conditions?\n\nI have diabetes type 2, but I haven't been taking my medication regularly.\n\nWhat medications do you take?\n\nMetformin 1000mg twice daily, but I haven't taken it for about a week.\n\nAny allergies?\n\nNo known allergies.\n\nAny previous surgeries?\n\nI had a hernia repair 5 years ago.\n\nFamily history of diabetes?\n\nYes, my mother and father both had diabetes.\n\nDo you smoke or drink alcohol?\n\nI drink 2-3 beers on weekends, no smoking.\n\nWhat's your occupation?\n\nI'm a truck driver, so I'm sitting most of the day.\n\nLet me check your vital signs. Your blood pressure is 145/95, heart rate 110, temperature 99.2°F, respiratory rate 24, and oxygen saturation 94%.\n\nI can see you're dehydrated and your blood sugar is very high at 450 mg/dL.\n\nI'll order a complete metabolic panel, blood gas analysis, and urinalysis. We'll also need to check your ketone levels.\n\nBased on your symptoms and lab results, you have diabetic ketoacidosis, which is a serious complication of diabetes.\n\nI'll start you on IV fluids, insulin, and electrolyte replacement. We'll need to monitor your blood sugar closely.\n\nYou'll need to stay in the hospital for at least 24-48 hours until your blood sugar stabilizes and your ketones clear.\n\nIt's crucial to take your diabetes medication regularly and monitor your blood sugar daily. We'll arrange for diabetes education.",
                "output": {
                    "subjective": {
                        "chief_complaint": "Weakness and dizziness for several days.",
                        "history_of_present_illness": "3 days of worsening weakness and dizziness with thirst, frequent urination, weight loss; nausea, vomiting, abdominal cramping, and shortness of breath.",
                        "past_medical_history": "Type 2 diabetes, hernia repair 5 years ago.",
                        "family_history": "Parents had diabetes.",
                        "social_history": "Truck driver, sedentary lifestyle, drinks 2–3 beers on weekends, no smoking.",
                        "medications": [{"name":"Metformin","dosage":"1000mg","frequency":"twice daily","route":"oral","duration":"not taken for 1 week"}],
                        "allergies": []
                    },
                    "objective": {
                        "vital_signs": {"temperature":"99.2°F","blood_pressure":"145/95","heart_rate":"110","respiratory_rate":"24","oxygen_saturation":"94%"},
                        "physical_exam": "Dehydration; blood glucose 450 mg/dL."
                    },
                    "assessment": {
                        "diagnosis": "Diabetic ketoacidosis (DKA)",
                        "risk_factors": ["Diabetes", "Non-compliance with medication", "Sedentary lifestyle"]
                    },
                    "plan": {
                        "medications_prescribed": [{"name":"Insulin","dosage":"","frequency":"continuous IV","duration":"as needed","route":"IV"}],
                        "procedures_or_tests": ["CMP","Blood gas","Urinalysis","Ketone levels"],
                        "patient_education": "Importance of adherence and monitoring.",
                        "follow_up_instructions": "Admit 24–48 hours; diabetes education post-discharge."
                    }
                }
            },
            {
                "input": "Hello, I'm Dr. Lisa from the psychiatric emergency department. Can I get your name and age?\n\nI'm James Anderson, 34 years old, from Portland.\n\nWhat brings you to the psychiatric emergency today, James?\n\nI've been having thoughts of harming myself for the past week, and I don't think I can keep myself safe anymore.\n\nWhen did these thoughts start?\n\nAbout a week ago, but they've been getting worse each day.\n\nCan you tell me more about these thoughts?\n\nI keep thinking about ending my life. I've been researching methods online and I have a plan.\n\nHave you made any attempts recently?\n\nNo, but I came very close last night. I had the means ready but I called a friend instead.\n\nWhat made you decide to come in today?\n\nI realized I need help. I can't control these thoughts anymore and I'm scared.\n\nAny other symptoms?\n\nI haven't been sleeping well for months, I have no energy, and I've lost interest in everything I used to enjoy.\n\nHow long have you been feeling this way?\n\nAbout 3 months, but it's been getting much worse in the last few weeks.\n\nAny changes in your appetite?\n\nI've lost about 15 pounds because I have no appetite.\n\nAny anxiety or panic attacks?\n\nYes, I have constant anxiety and I've had several panic attacks in the last month.\n\nAny hallucinations or delusions?\n\nNo, I know these thoughts are my own, but I can't stop them.\n\nHave you had similar problems before?\n\nYes, I was hospitalized for depression 2 years ago.\n\nAny medical conditions?\n\nI have hypothyroidism and I take medication for it.\n\nWhat medications do you take?\n\nLevothyroxine 50mcg daily, and I was taking Sertraline but I stopped it 2 weeks ago.\n\nAny allergies?\n\nNo known allergies.\n\nAny previous psychiatric hospitalizations?\n\nYes, one hospitalization 2 years ago for major depression.\n\nFamily history of mental illness?\n\nYes, my mother has bipolar disorder and my sister has depression.\n\nDo you use any substances?\n\nI drink 2-3 beers daily, and I smoke marijuana occasionally.\n\nWhat's your occupation?\n\nI'm a software engineer, but I've been on medical leave for the past month.\n\nLet me check your vital signs. Your blood pressure is 130/85, heart rate 88, temperature 98.6°F, respiratory rate 16.\n\nI'll perform a mental status exam. You appear depressed with poor eye contact, slowed speech, and hopeless affect.\n\nI'll order blood work to check your thyroid levels and drug screen. We'll also need a psychiatric evaluation.\n\nBased on your symptoms and risk assessment, you have severe major depression with suicidal ideation and plan.\n\nI'll start you on antidepressant medication and arrange for inpatient psychiatric hospitalization for safety.\n\nYou'll need to stay in the hospital for at least 72 hours for safety monitoring and medication adjustment.\n\nIt's important to remove any means of self-harm from your environment and have someone stay with you when you're discharged.",
                "output": {
                    "subjective": {
                        "chief_complaint": "Thoughts of self-harm and inability to remain safe.",
                        "history_of_present_illness": "Worsening suicidal thoughts over a week; 3 months of insomnia, anergia, anhedonia; 15 lb weight loss, panic attacks, persistent anxiety.",
                        "past_medical_history": "Hypothyroidism; prior hospitalization for depression 2 years ago.",
                        "family_history": "Mother bipolar disorder; sister depression.",
                        "social_history": "Software engineer on medical leave; daily alcohol; occasional marijuana.",
                        "medications": [
                            {"name":"Levothyroxine","dosage":"50mcg","frequency":"daily","route":"oral","duration":"current"},
                            {"name":"Sertraline","dosage":"","frequency":"","route":"oral","duration":"stopped 2 weeks ago"}
                        ],
                        "allergies": []
                    },
                    "objective": {
                        "vital_signs": {"temperature":"98.6°F","blood_pressure":"130/85","heart_rate":"88","respiratory_rate":"16","oxygen_saturation":""},
                        "physical_exam": "Mental status: depressed mood, poor eye contact, slowed speech, hopeless affect."
                    },
                    "assessment": {
                        "diagnosis": "Severe major depressive disorder with suicidal ideation and plan.",
                        "risk_factors": ["History of depression","Stopped antidepressants","Family history","Substance use"]
                    },
                    "plan": {
                        "medications_prescribed": [{"name":"Antidepressant (to be determined)","dosage":"","frequency":"","duration":"","route":"oral"}],
                        "procedures_or_tests": ["Thyroid panel","Drug screening","Psychiatric evaluation"],
                        "patient_education": "Safety, adherence, support systems.",
                        "follow_up_instructions": "Inpatient admission 72 hours for observation, adjustments, and safety planning."
                    }
                }
            }
        ]

    def _example_medication(self):
        # Mirrors the example shared in the documentation the user provided
        if lx is None:
            return None
        return lx.data.ExampleData(
            text="Patient was given 250 mg IV Cefazolin TID for one week.",
            extractions=[
                lx.data.Extraction(extraction_class="dosage", extraction_text="250 mg"),
                lx.data.Extraction(extraction_class="route", extraction_text="IV"),
                lx.data.Extraction(extraction_class="medication", extraction_text="Cefazolin"),
                lx.data.Extraction(extraction_class="frequency", extraction_text="TID"),
                lx.data.Extraction(extraction_class="duration", extraction_text="for one week"),
            ],
        )

    def _example_stroke_neuro_english(self):
        if lx is None:
            return None
        text = (
            "I woke up this morning and noticed my left arm and leg feel weak and numb. "
            "I have a severe headache like a thunderclap mostly on the right side. "
            "I have slurred speech and a left facial droop. "
            "BP is 180/110. I suspect acute ischemic stroke affecting the right side of the brain. "
            "Start aspirin and arrange thrombolytic therapy if CT confirms it's safe. "
            "Medications: Warfarin 5mg daily, Lisinopril 10mg daily, Metoprolol 25mg twice daily."
        )
        return lx.data.ExampleData(
            text=text,
            extractions=[
                lx.data.Extraction(extraction_class="symptom", extraction_text="left arm and leg feel weak and numb"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="severe headache"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="slurred speech"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="left facial droop"),
                lx.data.Extraction(extraction_class="vital", extraction_text="BP is 180/110"),
                lx.data.Extraction(extraction_class="diagnosis", extraction_text="acute ischemic stroke"),
                lx.data.Extraction(extraction_class="test", extraction_text="CT"),
                lx.data.Extraction(extraction_class="medication", extraction_text="aspirin"),
                lx.data.Extraction(extraction_class="medication", extraction_text="Warfarin"),
                lx.data.Extraction(extraction_class="dosage", extraction_text="5mg"),
                lx.data.Extraction(extraction_class="frequency", extraction_text="daily"),
                lx.data.Extraction(extraction_class="medication", extraction_text="Lisinopril"),
                lx.data.Extraction(extraction_class="dosage", extraction_text="10mg"),
                lx.data.Extraction(extraction_class="frequency", extraction_text="daily"),
                lx.data.Extraction(extraction_class="medication", extraction_text="Metoprolol"),
                lx.data.Extraction(extraction_class="dosage", extraction_text="25mg"),
                lx.data.Extraction(extraction_class="frequency", extraction_text="twice daily"),
            ],
        )

    def _example_dka_english(self):
        if lx is None:
            return None
        text = (
            "I feel very weak and dizzy and couldn't get out of bed. "
            "Very thirsty, urinating a lot, and lost 10 pounds. "
            "Vomited twice. Some abdominal cramping. "
            "Blood sugar is very high at 450 mg/dL. "
            "Diagnosis: diabetic ketoacidosis. Start IV fluids, insulin, and electrolyte replacement. "
            "Medication non-adherence: Metformin 1000mg twice daily not taken for a week."
        )
        return lx.data.ExampleData(
            text=text,
            extractions=[
                lx.data.Extraction(extraction_class="symptom", extraction_text="very weak and dizzy"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="Very thirsty"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="urinating a lot"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="lost 10 pounds"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="Vomited twice"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="abdominal cramping"),
                lx.data.Extraction(extraction_class="test", extraction_text="Blood sugar is very high at 450 mg/dL"),
                lx.data.Extraction(extraction_class="diagnosis", extraction_text="diabetic ketoacidosis"),
                lx.data.Extraction(extraction_class="treatment", extraction_text="IV fluids"),
                lx.data.Extraction(extraction_class="treatment", extraction_text="insulin"),
                lx.data.Extraction(extraction_class="treatment", extraction_text="electrolyte replacement"),
                lx.data.Extraction(extraction_class="medication", extraction_text="Metformin"),
                lx.data.Extraction(extraction_class="dosage", extraction_text="1000mg"),
                lx.data.Extraction(extraction_class="frequency", extraction_text="twice daily"),
            ],
        )

    def _example_chest_pain_arabic(self):
        if lx is None:
            return None
        text = (
            "أعاني من ألم شديد في الصدر منذ ساعة ونصف. ينتشر إلى الذراع الأيسر والفك وأسفل الظهر. "
            "أعرق كثيراً وأشعر بالغثيان والدوخة وضيق في التنفس. "
            "ضغط دمك 170/105 ومعدل النبض 120 ونسبة الأكسجين 89%. "
            "سأبدأ بإعطائك الأسبرين، النيتروغليسرين، والأكسجين، ومورفين لتخفيف الألم."
        )
        return lx.data.ExampleData(
            text=text,
            extractions=[
                lx.data.Extraction(extraction_class="symptom", extraction_text="ألم شديد في الصدر"),
                lx.data.Extraction(extraction_class="radiation", extraction_text="ينتشر إلى الذراع الأيسر والفك وأسفل الظهر"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="الغثيان"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="الدوخة"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="ضيق في التنفس"),
                lx.data.Extraction(extraction_class="vital", extraction_text="ضغط دمك 170/105"),
                lx.data.Extraction(extraction_class="vital", extraction_text="معدل النبض 120"),
                lx.data.Extraction(extraction_class="vital", extraction_text="نسبة الأكسجين 89%"),
                lx.data.Extraction(extraction_class="medication", extraction_text="الأسبرين"),
                lx.data.Extraction(extraction_class="medication", extraction_text="النيتروغليسرين"),
                lx.data.Extraction(extraction_class="treatment", extraction_text="الأكسجين"),
                lx.data.Extraction(extraction_class="medication", extraction_text="مورفين"),
            ],
        )

    def _example_pneumonia_arabic(self):
        if lx is None:
            return None
        text = (
            "أعاني من سعال شديد وحمى منذ 5 أيام وصعوبة شديدة في التنفس. "
            "سعال عميق مع بلغم أصفر كثيف وألم في الصدر عند السعال. "
            "درجة الحرارة 103.2°F ومعدل التنفس 32 ونسبة الأكسجين 88%. "
            "تشخيص: التهاب رئوي حاد. سأبدأ بالمضادات الحيوية وريدياً والأكسجين."
        )
        return lx.data.ExampleData(
            text=text,
            extractions=[
                lx.data.Extraction(extraction_class="symptom", extraction_text="سعال شديد"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="حمى"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="صعوبة شديدة في التنفس"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="بلغم أصفر كثيف"),
                lx.data.Extraction(extraction_class="symptom", extraction_text="ألم في الصدر عند السعال"),
                lx.data.Extraction(extraction_class="vital", extraction_text="درجة الحرارة 103.2°F"),
                lx.data.Extraction(extraction_class="vital", extraction_text="معدل التنفس 32"),
                lx.data.Extraction(extraction_class="vital", extraction_text="نسبة الأكسجين 88%"),
                lx.data.Extraction(extraction_class="diagnosis", extraction_text="التهاب رئوي حاد"),
                lx.data.Extraction(extraction_class="treatment", extraction_text="المضادات الحيوية وريدياً"),
                lx.data.Extraction(extraction_class="treatment", extraction_text="الأكسجين"),
            ],
        )

    def is_available(self) -> bool:
        return lx is not None
    
    # New: SOAP extraction for English using LangExtract
    def extract_soap(self, transcript: str, language: str = "en", few_shots=None):
        # Ensure default few-shots include user's scenarios
        if few_shots is None:
            few_shots = getattr(self, "soap_few_shots", None)
        """
        Return a dict with keys: subjective, objective, assessment, plan (nested dicts).
        We keep it flexible to match app.py SOAP_SYSTEM_PROMPT structure so we don't lose fields:
          subjective: chief_complaint, history_of_present_illness, past_medical_history,
                      family_history, social_history, medications[], allergies[]
          objective: vital_signs{temperature, blood_pressure, heart_rate, respiratory_rate, oxygen_saturation},
                     physical_exam
          assessment: diagnosis, risk_factors[]
          plan: medications_prescribed[], procedures_or_tests[], patient_education, follow_up_instructions
        """
        if lx is None or not transcript or not transcript.strip() or not language.lower().startswith("en"):
            return {"subjective": {}, "objective": {}, "assessment": {}, "plan": {}}
        
        soap_prompt = (
            "Extract a structured SOAP note from the conversation. "
            "Output JSON with keys subjective, objective, assessment, plan. "
            "Preserve all content mentioned using concise text. "
            "Fields to include exactly as named if present in the conversation:\n"
            "- subjective: chief_complaint, history_of_present_illness, past_medical_history, family_history, social_history, "
            "  medications (array of {name, dosage, frequency, route, duration}), allergies (array)\n"
            "- objective: vital_signs {temperature, blood_pressure, heart_rate, respiratory_rate, oxygen_saturation}, physical_exam\n"
            "- assessment: diagnosis, risk_factors (array)\n"
            "- plan: medications_prescribed (array of {name, dosage, frequency, duration, route}), "
            "  procedures_or_tests (array), patient_education, follow_up_instructions\n"
            "Rules:\n"
            "- Use exact phrasing from transcript where possible, but you may lightly summarize.\n"
            "- If a field is not mentioned, omit it (do not hallucinate).\n"
            "- Keep the output a single JSON object with only these top-level keys."
        )
        
        # Inline few-shot examples into the prompt to avoid relying on langextract ExampleData types
        prompt_full = soap_prompt
        try:
            if few_shots:
                parts = []
                for ex in few_shots[:3]:
                    if not isinstance(ex, dict):
                        continue
                    ex_in = ex.get("input", "")
                    ex_out = ex.get("output", {})
                    if not ex_in or not isinstance(ex_out, (dict, str)):
                        continue
                    import json as _json
                    if isinstance(ex_out, dict):
                        ex_out_str = _json.dumps(ex_out, ensure_ascii=False)
                    else:
                        ex_out_str = str(ex_out)
                    parts.append(f"Example:\nTranscript:\n{ex_in}\nJSON:\n{ex_out_str}")
                if parts:
                    prompt_full = soap_prompt + "\n\nFollow these examples exactly (structure and field names):\n" + "\n\n---\n\n".join(parts)
        except Exception:
            # If anything goes wrong with examples, proceed with base prompt
            prompt_full = soap_prompt
        
        try:
            # Build few-shot examples as ExampleData with a single "json" extraction containing the expected SOAP JSON.
            examples_lx = []
            try:
                import json as _json
                if few_shots and hasattr(lx, "data") and hasattr(lx.data, "ExampleData") and hasattr(lx.data, "Extraction"):
                    for ex in (few_shots or [])[:3]:
                        if not isinstance(ex, dict):
                            continue
                        ex_in = ex.get("input", "")
                        ex_out = ex.get("output", {})
                        if not ex_in or not isinstance(ex_out, (dict, str)):
                            continue
                        ex_out_str = _json.dumps(ex_out, ensure_ascii=False) if isinstance(ex_out, dict) else str(ex_out)
                        examples_lx.append(
                            lx.data.ExampleData(
                                text=ex_in,
                                extractions=[
                                    lx.data.Extraction(extraction_class="json", extraction_text=ex_out_str)
                                ],
                            )
                        )
            except Exception:
                # If example construction fails, proceed without examples (some versions allow this)
                examples_lx = []

            # Build kwargs compatibly across langextract versions (schemas may not exist)
            extract_kwargs = dict(
                text_or_documents=transcript,
                prompt_description=prompt_full,
                model_id=self.model_id,
                api_key=self.api_key,
            )
            # Attach examples if we have any (some versions require at least one ExampleData)
            if examples_lx:
                extract_kwargs["examples"] = examples_lx

            try:
                # Only attach response_schema if the installed version exposes schemas
                if hasattr(lx, "schemas") and hasattr(lx.schemas, "JsonSchemaObject"):
                    extract_kwargs["response_schema"] = lx.schemas.JsonSchemaObject(  # type: ignore
                        keys=[
                            lx.schemas.JsonSchemaKey("subjective", optional=True),
                            lx.schemas.JsonSchemaKey("objective", optional=True),
                            lx.schemas.JsonSchemaKey("assessment", optional=True),
                            lx.schemas.JsonSchemaKey("plan", optional=True),
                        ]
                    )
            except Exception:
                # If schema attachment fails, continue without it
                pass

            result = lx.extract(**extract_kwargs)
        except Exception as e:
            print(f"LangExtractAdapter.extract_soap error: {e}")
            return {"subjective": {}, "objective": {}, "assessment": {}, "plan": {}}
        
        # If some versions return a plain dict already
        try:
            if isinstance(result, dict):
                # If it already looks like our sections, return it
                if any(k in result for k in ("subjective", "objective", "assessment", "plan")):
                    return result
                # Or unwrap a nested 'content' if present
                possible_dict_content = result.get("content")
                if isinstance(possible_dict_content, dict):
                    return possible_dict_content
        except Exception:
            pass

        # Try multiple locations for JSON/string content depending on library version
        content = getattr(result, "content", None)
        if isinstance(content, dict):
            return content
        
        # Some versions may expose a plain string under 'content' or 'text' or 'output_text'
        possible_texts = [
            content,
            getattr(result, "text", None),
            getattr(result, "output_text", None),
            getattr(result, "raw_content", None),
        ]
        try:
            import json as _json
            for txt in possible_texts:
                if isinstance(txt, str) and txt.strip().startswith("{"):
                    return _json.loads(txt)
        except Exception:
            pass

        # Also try to parse from an 'extractions' list if returned (look for a json-like extraction_text)
        try:
            exts = getattr(result, "extractions", None)
            if exts:
                for ext in exts:
                    cls = str(getattr(ext, "extraction_class", "") or "").lower()
                    txt = getattr(ext, "extraction_text", None)
                    if isinstance(txt, str) and ("{" in txt and "}" in txt):
                        try:
                            import json as _json
                            parsed = _json.loads(txt)
                            if isinstance(parsed, dict) and any(k in parsed for k in ("subjective", "objective", "assessment", "plan")):
                                return parsed
                        except Exception:
                            continue
        except Exception:
            pass
        
        return {"subjective": {}, "objective": {}, "assessment": {}, "plan": {}}

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        if lx is None:
            # Library not installed in current environment
            return []

        # Filter None examples (in case import failed)
        examples = [e for e in self.examples if e is not None]

        try:
            result = lx.extract(
                text_or_documents=text,
                prompt_description=self.prompt,
                examples=examples,
                model_id=self.model_id,
                api_key=self.api_key,  # optional if env is set
            )
        except Exception as e:
            # Fail closed – do not impact existing flow
            print(f"LangExtractAdapter error: {e}")
            return []

        entities: List[ExtractedEntity] = []
        for ext in getattr(result, "extractions", []) or []:
            # ext has fields: extraction_class, extraction_text, attributes, char_interval
            start, end = None, None
            if getattr(ext, "char_interval", None):
                start = ext.char_interval.start_pos
                end = ext.char_interval.end_pos

            if start is None or end is None:
                # Must be grounded for our UI; skip if no offsets
                continue

            label = str(getattr(ext, "extraction_class", "") or "")
            text_span = str(getattr(ext, "extraction_text", "") or "")

            # Confidence may not be exposed; keep None
            entities.append(
                ExtractedEntity(
                    text=text_span,
                    start=int(start),
                    end=int(end),
                    label=label,
                    attributes=getattr(ext, "attributes", None) or None,
                    confidence=None,
                )
            )
        return entities
