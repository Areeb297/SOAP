import copy
from typing import Any, Dict, List, Optional

# Local adapter that wraps the langextract library and already includes the user's few-shots
from .langextract_adapter import LangExtractAdapter


SoapSections = Dict[str, Any]


def _ensure_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_medication_item(item: Dict[str, Any]) -> Dict[str, str]:
    # Enforce the medication schema fields
    return {
        "name": _ensure_string(item.get("name", "")),
        "dosage": _ensure_string(item.get("dosage", "")),
        "frequency": _ensure_string(item.get("frequency", "")),
        "route": _ensure_string(item.get("route", "")),
        "duration": _ensure_string(item.get("duration", "")),
    }


def _normalize_vitals(vitals: Optional[Dict[str, Any]]) -> Dict[str, str]:
    vitals = vitals or {}
    return {
        "temperature": _ensure_string(vitals.get("temperature", "")),
        "blood_pressure": _ensure_string(vitals.get("blood_pressure", "")),
        "heart_rate": _ensure_string(vitals.get("heart_rate", "")),
        "respiratory_rate": _ensure_string(vitals.get("respiratory_rate", "")),
        "oxygen_saturation": _ensure_string(vitals.get("oxygen_saturation", "")),
    }


def normalize_soap_sections(sections: SoapSections) -> SoapSections:
    """
    Normalize while PRESERVING all content:
    - Enforce canonical keys and schemas for known fields
    - Map common aliases (e.g., HPI -> history_of_present_illness)
    - Keep unknown keys as-is so nothing mentioned is lost
    - Ensure medications arrays are normalized objects
    - Ensure vital_signs contains all standard keys
    """
    sections = copy.deepcopy(sections or {})
    subj_in = sections.get("subjective", {}) or {}
    obj_in = sections.get("objective", {}) or {}
    assess_in = sections.get("assessment", {}) or {}
    plan_in = sections.get("plan", {}) or {}

    # Alias maps (lowercased, stripped, underscores/spaces normalized)
    def keynorm(k: str) -> str:
        return (k or "").strip().lower().replace("-", " ").replace("_", " ")

    subj_alias = {
        "cc": "chief_complaint",
        "chief complaint": "chief_complaint",
        "chiefcomplaint": "chief_complaint",
        "hpi": "history_of_present_illness",
        "history of present illness": "history_of_present_illness",
        "pmh": "past_medical_history",
        "past medical history": "past_medical_history",
        "fh": "family_history",
        "family history": "family_history",
        "sh": "social_history",
        "social history": "social_history",
        "meds": "medications",
        "medications": "medications",
        "allergy": "allergies",
        "allergies": "allergies",
    }
    obj_alias = {
        "vitals": "vital_signs",
        "vital signs": "vital_signs",
        "pe": "physical_exam",
        "exam": "physical_exam",
        "physical exam": "physical_exam",
    }
    assess_alias = {
        "dx": "diagnosis",
        "impression": "diagnosis",
        "assessment/diagnosis": "diagnosis",
        "risks": "risk_factors",
        "risk factors": "risk_factors",
    }
    plan_alias = {
        "rx": "medications_prescribed",
        "medications": "medications_prescribed",
        "orders": "procedures_or_tests",
        "tests": "procedures_or_tests",
        "labs": "procedures_or_tests",
        "imaging": "procedures_or_tests",
        "education": "patient_education",
        "patient education": "patient_education",
        "follow up": "follow_up_instructions",
        "follow-up": "follow_up_instructions",
        "followup": "follow_up_instructions",
        "instructions": "follow_up_instructions",
    }

    # Known canonical keys we always include (subjective)
    subj_out: Dict[str, Any] = {
        "chief_complaint": "",
        "history_of_present_illness": "",
        "past_medical_history": "",
        "family_history": "",
        "social_history": "",
        "medications": [],
        "allergies": [],
    }
    # Merge subjective with alias mapping + preserve unknowns
    if isinstance(subj_in, dict):
        for k, v in subj_in.items():
            kn = keynorm(k)
            canonical = subj_alias.get(kn)
            if canonical:
                if canonical == "medications":
                    meds = v or []
                    if isinstance(meds, dict):
                        meds = [meds]
                    if isinstance(meds, list):
                        subj_out["medications"].extend(
                            [_normalize_medication_item(m) for m in meds if isinstance(m, dict)]
                        )
                    else:
                        subj_out[k] = v
                elif canonical == "allergies":
                    allergies = v or []
                    if isinstance(allergies, str) and allergies.strip():
                        allergies = [allergies]
                    if not isinstance(allergies, list):
                        allergies = []
                    subj_out["allergies"].extend([_ensure_string(a) for a in allergies])
                else:
                    subj_out[canonical] = _ensure_string(v)
            else:
                # Unknown subjective key – keep it
                subj_out[k] = v

    # Objective defaults
    obj_out: Dict[str, Any] = {
        "vital_signs": _normalize_vitals(None),
        "physical_exam": "",
    }
    # Merge objective with alias mapping + preserve unknowns
    vitals_seen = False
    if isinstance(obj_in, dict):
        for k, v in obj_in.items():
            kn = keynorm(k)
            canonical = obj_alias.get(kn)
            if canonical == "vital_signs":
                obj_out["vital_signs"] = _normalize_vitals(v if isinstance(v, dict) else {})
                vitals_seen = True
            elif canonical == "physical_exam":
                obj_out["physical_exam"] = _ensure_string(v)
            else:
                # Preserve unknowns, but try to capture common vitals patterns even if mislabeled
                if not vitals_seen and isinstance(v, dict) and any(
                    any(alias in keynorm(subk) for alias in ["temp", "temperature", "bp", "blood pressure", "hr", "heart rate", "rr", "respiratory rate", "spo2", "oxygen", "o2"])
                    for subk in v.keys()
                ):
                    obj_out["vital_signs"] = _normalize_vitals(v)
                    vitals_seen = True
                else:
                    obj_out[k] = v

    # Assessment defaults
    assess_out: Dict[str, Any] = {
        "diagnosis": "",
        "risk_factors": [],
    }
    if isinstance(assess_in, dict):
        for k, v in assess_in.items():
            kn = keynorm(k)
            canonical = assess_alias.get(kn)
            if canonical == "diagnosis":
                assess_out["diagnosis"] = _ensure_string(v)
            elif canonical == "risk_factors":
                rf = v or []
                if isinstance(rf, str) and rf.strip():
                    rf = [rf]
                if not isinstance(rf, list):
                    rf = []
                assess_out["risk_factors"].extend([_ensure_string(r) for r in rf])
            else:
                assess_out[k] = v

    # Plan defaults
    plan_out: Dict[str, Any] = {
        "medications_prescribed": [],
        "procedures_or_tests": [],
        "patient_education": _ensure_string(plan_in.get("patient_education", "")) if isinstance(plan_in, dict) else "",
        "follow_up_instructions": _ensure_string(plan_in.get("follow_up_instructions", "")) if isinstance(plan_in, dict) else "",
    }
    if isinstance(plan_in, dict):
        for k, v in plan_in.items():
            kn = keynorm(k)
            canonical = plan_alias.get(kn)
            if canonical == "medications_prescribed":
                meds_rx = v or []
                if isinstance(meds_rx, dict):
                    meds_rx = [meds_rx]
                if isinstance(meds_rx, list):
                    plan_out["medications_prescribed"].extend(
                        [_normalize_medication_item(m) for m in meds_rx if isinstance(m, dict)]
                    )
                else:
                    plan_out[k] = v
            elif canonical == "procedures_or_tests":
                tests = v or []
                if isinstance(tests, str) and tests.strip():
                    tests = [tests]
                if not isinstance(tests, list):
                    tests = []
                plan_out["procedures_or_tests"].extend([_ensure_string(t) for t in tests])
            elif canonical == "patient_education":
                plan_out["patient_education"] = _ensure_string(v)
            elif canonical == "follow_up_instructions":
                plan_out["follow_up_instructions"] = _ensure_string(v)
            else:
                # Unknown plan key – keep it
                plan_out[k] = v

    return {
        "subjective": subj_out,
        "objective": obj_out,
        "assessment": assess_out,
        "plan": plan_out,
    }


def is_soap_complete(sections: SoapSections) -> bool:
    """
    Heuristic completeness check:
    - Must have 'subjective' with either HPI or chief complaint non-empty
    - And at least one of: objective.physical_exam, assessment.diagnosis, plan.medications_prescribed/procedures_or_tests non-empty
    """
    if not sections or not isinstance(sections, dict):
        return False

    subj = sections.get("subjective") or {}
    hpi = _ensure_string(subj.get("history_of_present_illness", "")).strip()
    cc = _ensure_string(subj.get("chief_complaint", "")).strip()
    if not hpi and not cc:
        return False

    obj = sections.get("objective") or {}
    pe = _ensure_string(obj.get("physical_exam", "")).strip()

    assess = sections.get("assessment") or {}
    dx = _ensure_string(assess.get("diagnosis", "")).strip()

    plan = sections.get("plan") or {}
    meds_rx = plan.get("medications_prescribed", []) or []
    tests = plan.get("procedures_or_tests", []) or []

    return bool(pe or dx or (isinstance(meds_rx, list) and len(meds_rx) > 0) or (isinstance(tests, list) and len(tests) > 0))


def extract_english_soap_sections(transcript: str) -> SoapSections:
    """
    Use LangExtract via the adapter to extract English SOAP sections with few-shots.
    Returns normalized sections dict (subjective/objective/assessment/plan).
    If LangExtract is unavailable or fails, returns empty sections.
    """
    try:
        adapter = LangExtractAdapter()
        if not adapter.is_available():
            return {"subjective": {}, "objective": {}, "assessment": {}, "plan": {}}

        raw = adapter.extract_soap(transcript=transcript, language="en")
        # Adapter returns dict with keys already; normalize for schema conformity
        normalized = normalize_soap_sections(raw or {})
        return normalized
    except Exception as e:
        print(f"soap_section_extractor.extract_english_soap_sections error: {e}")
        return {"subjective": {}, "objective": {}, "assessment": {}, "plan": {}}
