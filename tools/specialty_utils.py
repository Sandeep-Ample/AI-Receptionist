from typing import Optional

def detect_specialty_from_symptoms(symptoms: str) -> Optional[str]:
    """
    Detect doctor specialty based on patient symptoms.

    Rules:
    - If symptoms are empty or not spoken → return None
    - If symptoms do not match → return None
    - NEVER default automatically to General Physician
    """

    if not symptoms or not symptoms.strip():
        return None

    s = symptoms.lower()

    # ---------------- Radiology ----------------
    if any(word in s for word in [
        "xray", "x-ray", "scan", "ct", "ct scan",
        "mri", "ultrasound", "usg", "sonography",
        "doppler", "imaging"
    ]):
        return "Radiology"

    # ---------------- Psychiatry ----------------
    if any(word in s for word in [
        "stress", "anxiety", "depression", "mental",
        "panic", "sleep problem", "insomnia",
        "mood swings", "behavior", "anger", "sadness"
    ]):
        return "Psychiatry"

    # ---------------- Cardiology ----------------
    if any(word in s for word in [
        "heart", "heart pain", "chest pain",
        "bp", "blood pressure",
        "palpitation", "heartbeat",
        "breathlessness", "shortness of breath",
        "cholesterol"
    ]):
        return "Cardiology"

    # ---------------- Orthopedic ----------------
    if any(word in s for word in [
        "bone", "joint", "joint pain",
        "back pain", "neck pain",
        "knee pain", "shoulder pain",
        "fracture", "injury", "arthritis"
    ]):
        return "Orthopedic"

    # ---------------- Urology ----------------
    if any(word in s for word in [
        "urine", "urinary", "uti",
        "burning urine", "painful urination",
        "kidney", "kidney stone",
        "bladder", "prostate"
    ]):
        return "Urology"

    # ---------------- Neurology ----------------
    if any(word in s for word in [
        "headache", "migraine", "seizure",
        "fits", "stroke", "numbness",
        "dizziness", "memory loss"
    ]):
        return "Neurology"

    # ---------------- Dermatology ----------------
    if any(word in s for word in [
        "skin", "rash", "itching",
        "acne", "eczema", "psoriasis",
        "fungal", "hair fall"
    ]):
        return "Dermatology"

    # ---------------- ENT ----------------
    if any(word in s for word in [
        "ear pain", "hearing problem",
        "throat pain", "sore throat",
        "tonsils", "sinus", "nose block"
    ]):
        return "ENT"

    # ---------------- Gastroenterology ----------------
    if any(word in s for word in [
        "stomach pain", "abdominal pain",
        "gas", "acidity", "indigestion",
        "vomiting", "diarrhea",
        "constipation", "liver"
    ]):
        return "Gastroenterology"

    # ---------------- Pulmonology ----------------
    if any(word in s for word in [
        "cough", "breathing problem",
        "shortness of breath",
        "asthma", "lungs", "wheezing", "tb"
    ]):
        return "Pulmonology"

    # ---------------- Gynecology ----------------
    if any(word in s for word in [
        "pregnancy", "period problem",
        "menstrual", "pcod",
        "uterus", "ovary",
        "white discharge"
    ]):
        return "Gynecology"

    # ---------------- Pediatrics ----------------
    if any(word in s for word in [
        "child", "baby", "infant",
        "newborn", "vaccination"
    ]):
        return "Pediatrics"

    # ---------------- Ophthalmology ----------------
    if any(word in s for word in [
        "eye pain", "eye infection",
        "blurred vision", "vision problem",
        "red eye", "watering eyes"
    ]):
        return "Ophthalmology"

    # ---------------- General Physician ----------------
    # ONLY when explicitly mentioned
    if any(word in s for word in [
        "fever", "high fever", "viral",
        "cold", "flu", "body pain",
        "weakness", "fatigue", "tiredness",
        "infection", "allergy",
        "diabetes", "sugar", "thyroid",
        "dengue", "malaria", "typhoid",
        "general checkup", "routine checkup"
    ]):
        return "General Physician"

    # ❌ DO NOT DEFAULT
    return None
