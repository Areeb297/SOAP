import os
import pytest

from medical_spell_check.soap_section_extractor import extract_english_soap_sections, is_soap_complete
from medical_spell_check.langextract_adapter import LangExtractAdapter


def langextract_available() -> bool:
    try:
        adapter = LangExtractAdapter()
        return adapter.is_available()
    except Exception:
        return False


skip_if_no_langextract = pytest.mark.skipif(
    not langextract_available(),
    reason="LangExtract not installed/available; skipping SOAP extraction tests."
)


@skip_if_no_langextract
def test_stroke_case_sections_complete_and_structured():
    transcript = (
        "Good morning, I'm Dr. Michael from the neurology department. Can I get your name and age?\n\n"
        "I'm Patricia Johnson, 67 years old, from Boston.\n\n"
        "What brings you in today, Patricia?\n\n"
        "I woke up this morning and noticed my left arm and leg feel weak and numb.\n\n"
        "When did you first notice this?\n\n"
        "Around 7 AM when I tried to get out of bed. I couldn't lift my left arm properly.\n\n"
        "Any other symptoms?\n\n"
        "I have a severe headache that started about an hour ago, and I'm having trouble speaking clearly.\n\n"
        "Can you describe the headache?\n\n"
        "It's the worst headache I've ever had, like a thunderclap, and it's mostly on the right side of my head.\n\n"
        "Any vision problems?\n\n"
        "Yes, my vision is blurry, especially in my left eye.\n\n"
        "Any dizziness or balance problems?\n\n"
        "Yes, I feel dizzy and unsteady when I try to walk.\n\n"
        "Any nausea or vomiting?\n\n"
        "I feel nauseous but haven't vomited.\n\n"
        "Any confusion or memory problems?\n\n"
        "I'm having trouble finding the right words and I feel confused.\n\n"
        "Have you had similar symptoms before?\n\n"
        "No, never anything like this.\n\n"
        "Any medical conditions?\n\n"
        "I have high blood pressure, atrial fibrillation, and I take blood thinners.\n\n"
        "What medications do you take?\n\n"
        "Warfarin 5mg daily, Lisinopril 10mg daily, and Metoprolol 25mg twice daily.\n\n"
        "Any allergies?\n\n"
        "I'm allergic to penicillin.\n\n"
        "Any previous surgeries?\n\n"
        "I had a hip replacement 3 years ago.\n\n"
        "Family history of stroke?\n\n"
        "Yes, my father had a stroke at age 70.\n\n"
        "Do you smoke or drink alcohol?\n\n"
        "I quit smoking 10 years ago, and I have 1 glass of wine with dinner.\n\n"
        "What's your occupation?\n\n"
        "I'm retired, but I volunteer at the library twice a week.\n\n"
        "Let me check your vital signs. Your blood pressure is 180/110, heart rate 95, temperature 98.8°F, respiratory rate 18.\n\n"
        "I'll perform a neurological exam. I can see left-sided weakness, slurred speech, and left facial droop.\n\n"
        "I'll order a CT scan of your head, MRI, and blood work including coagulation studies.\n\n"
        "Based on your symptoms and exam, I suspect you're having an acute ischemic stroke affecting the right side of your brain.\n\n"
        "I'll start you on aspirin and arrange for immediate thrombolytic therapy if the CT scan confirms it's safe.\n\n"
        "You'll need to stay in the hospital for monitoring and rehabilitation. We'll also need to adjust your blood thinners.\n\n"
        "It's crucial to call 911 immediately if you experience any worsening symptoms. We'll arrange for stroke rehabilitation."
    )

    sections = extract_english_soap_sections(transcript)
    assert isinstance(sections, dict)
    assert is_soap_complete(sections)

    subj = sections.get("subjective", {})
    assert isinstance(subj, dict)
    assert subj.get("chief_complaint", "")
    assert "left" in subj.get("history_of_present_illness", "").lower()

    obj = sections.get("objective", {})
    assert isinstance(obj, dict)
    vitals = obj.get("vital_signs", {})
    assert isinstance(vitals, dict)
    assert "180/110" in vitals.get("blood_pressure", "")

    assess = sections.get("assessment", {})
    assert isinstance(assess, dict)
    assert "stroke" in assess.get("diagnosis", "").lower()

    plan = sections.get("plan", {})
    assert isinstance(plan, dict)
    assert any("ct" in t.lower() for t in plan.get("procedures_or_tests", []))


@skip_if_no_langextract
def test_dka_case_sections_complete_and_structured():
    transcript = (
        "Hello, I'm Dr. Sarah from the emergency department. Can I get your name and age?\n\n"
        "I'm Robert Wilson, 58 years old, from Seattle.\n\n"
        "What brings you to the ER today, Robert?\n\n"
        "I've been feeling very weak and dizzy for the past few days, and today I couldn't even get out of bed.\n\n"
        "When did these symptoms start?\n\n"
        "About 3 days ago, but they've been getting worse each day.\n\n"
        "Any other symptoms?\n\n"
        "I'm very thirsty all the time, urinating a lot, and I've lost about 10 pounds in the last month.\n\n"
        "Have you been eating normally?\n\n"
        "No, I've had no appetite lately, and when I do eat, I feel nauseous.\n\n"
        "Any vomiting?\n\n"
        "Yes, I vomited twice yesterday and once this morning.\n\n"
        "Any abdominal pain?\n\n"
        "Yes, I have some cramping in my stomach.\n\n"
        "Any fever?\n\n"
        "I feel warm, but I haven't checked my temperature.\n\n"
        "Any shortness of breath?\n\n"
        "Yes, especially when I try to walk around.\n\n"
        "Have you had similar symptoms before?\n\n"
        "No, this is completely new to me.\n\n"
        "Any medical conditions?\n\n"
        "I have diabetes type 2, but I haven't been taking my medication regularly.\n\n"
        "What medications do you take?\n\n"
        "Metformin 1000mg twice daily, but I haven't taken it for about a week.\n\n"
        "Any allergies?\n\n"
        "No known allergies.\n\n"
        "Any previous surgeries?\n\n"
        "I had a hernia repair 5 years ago.\n\n"
        "Family history of diabetes?\n\n"
        "Yes, my mother and father both had diabetes.\n\n"
        "Do you smoke or drink alcohol?\n\n"
        "I drink 2-3 beers on weekends, no smoking.\n\n"
        "What's your occupation?\n\n"
        "I'm a truck driver, so I'm sitting most of the day.\n\n"
        "Let me check your vital signs. Your blood pressure is 145/95, heart rate 110, temperature 99.2°F, respiratory rate 24, and oxygen saturation 94%.\n\n"
        "I can see you're dehydrated and your blood sugar is very high at 450 mg/dL.\n\n"
        "I'll order a complete metabolic panel, blood gas analysis, and urinalysis. We'll also need to check your ketone levels.\n\n"
        "Based on your symptoms and lab results, you have diabetic ketoacidosis, which is a serious complication of diabetes.\n\n"
        "I'll start you on IV fluids, insulin, and electrolyte replacement. We'll need to monitor your blood sugar closely.\n\n"
        "You'll need to stay in the hospital for at least 24-48 hours until your blood sugar stabilizes and your ketones clear.\n\n"
        "It's crucial to take your diabetes medication regularly and monitor your blood sugar daily. We'll arrange for diabetes education."
    )

    sections = extract_english_soap_sections(transcript)
    assert isinstance(sections, dict)
    assert is_soap_complete(sections)

    subj = sections.get("subjective", {})
    assert "weak and dizzy" in subj.get("history_of_present_illness", "").lower() or subj.get("history_of_present_illness", "")

    obj = sections.get("objective", {})
    vitals = obj.get("vital_signs", {})
    assert "99.2" in vitals.get("temperature", "") or "99.2°f" in vitals.get("temperature", "").lower()
    assert "145/95" in vitals.get("blood_pressure", "")

    assess = sections.get("assessment", {})
    assert "ketoacidosis" in assess.get("diagnosis", "").lower()

    plan = sections.get("plan", {})
    tests = [t.lower() for t in plan.get("procedures_or_tests", [])]
    assert any("urinalysis" in t or "cmp" in t or "blood gas" in t for t in tests)


@skip_if_no_langextract
def test_psych_case_sections_complete_and_structured():
    transcript = (
        "Hello, I'm Dr. Lisa from the psychiatric emergency department. Can I get your name and age?\n\n"
        "I'm James Anderson, 34 years old, from Portland.\n\n"
        "What brings you to the psychiatric emergency today, James?\n\n"
        "I've been having thoughts of harming myself for the past week, and I don't think I can keep myself safe anymore.\n\n"
        "When did these thoughts start?\n\n"
        "About a week ago, but they've been getting worse each day.\n\n"
        "Can you tell me more about these thoughts?\n\n"
        "I keep thinking about ending my life. I've been researching methods online and I have a plan.\n\n"
        "Have you made any attempts recently?\n\n"
        "No, but I came very close last night. I had the means ready but I called a friend instead.\n\n"
        "What made you decide to come in today?\n\n"
        "I realized I need help. I can't control these thoughts anymore and I'm scared.\n\n"
        "Any other symptoms?\n\n"
        "I haven't been sleeping well for months, I have no energy, and I've lost interest in everything I used to enjoy.\n\n"
        "How long have you been feeling this way?\n\n"
        "About 3 months, but it's been getting much worse in the last few weeks.\n\n"
        "Any changes in your appetite?\n\n"
        "I've lost about 15 pounds because I have no appetite.\n\n"
        "Any anxiety or panic attacks?\n\n"
        "Yes, I have constant anxiety and I've had several panic attacks in the last month.\n\n"
        "Any hallucinations or delusions?\n\n"
        "No, I know these thoughts are my own, but I can't stop them.\n\n"
        "Have you had similar problems before?\n\n"
        "Yes, I was hospitalized for depression 2 years ago.\n\n"
        "Any medical conditions?\n\n"
        "I have hypothyroidism and I take medication for it.\n\n"
        "What medications do you take?\n\n"
        "Levothyroxine 50mcg daily, and I was taking Sertraline but I stopped it 2 weeks ago.\n\n"
        "Any allergies?\n\n"
        "No known allergies.\n\n"
        "Any previous psychiatric hospitalizations?\n\n"
        "Yes, one hospitalization 2 years ago for major depression.\n\n"
        "Family history of mental illness?\n\n"
        "Yes, my mother has bipolar disorder and my sister has depression.\n\n"
        "Do you use any substances?\n\n"
        "I drink 2-3 beers daily, and I smoke marijuana occasionally.\n\n"
        "What's your occupation?\n\n"
        "I'm a software engineer, but I've been on medical leave for the past month.\n\n"
        "Let me check your vital signs. Your blood pressure is 130/85, heart rate 88, temperature 98.6°F, respiratory rate 16.\n\n"
        "I'll perform a mental status exam. You appear depressed with poor eye contact, slowed speech, and hopeless affect.\n\n"
        "I'll order blood work to check your thyroid levels and drug screen. We'll also need a psychiatric evaluation.\n\n"
        "Based on your symptoms and risk assessment, you have severe major depression with suicidal ideation and plan.\n\n"
        "I'll start you on antidepressant medication and arrange for inpatient psychiatric hospitalization for safety.\n\n"
        "You'll need to stay in the hospital for at least 72 hours for safety monitoring and medication adjustment.\n\n"
        "It's important to remove any means of self-harm from your environment and have someone stay with you when you're discharged."
    )

    sections = extract_english_soap_sections(transcript)
    assert isinstance(sections, dict)
    assert is_soap_complete(sections)

    subj = sections.get("subjective", {})
    assert "suicid" in subj.get("chief_complaint", "").lower() or "harm" in subj.get("chief_complaint", "").lower()

    obj = sections.get("objective", {})
    pe = obj.get("physical_exam", "").lower()
    assert "depressed" in pe or "poor eye contact" in pe or "hopeless" in pe

    assess = sections.get("assessment", {})
    assert "depress" in assess.get("diagnosis", "").lower()

    plan = sections.get("plan", {})
    tests = [t.lower() for t in plan.get("procedures_or_tests", [])]
    assert any("thyroid" in t or "psychiatric evaluation" in t or "drug" in t for t in tests)
