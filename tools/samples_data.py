"""Content for the 18 specimen documents used by the demo workspace.

All people, companies, policies and amounts are fictitious. Each sample pairs
rendered ground truth with an OCR-style error map so the review experience has
something meaningful to review.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from formlib import (CONTENT_W, FONT, MARGIN, PAGE_H, PAGE_W, FieldSpec, Form,
                     SectionSpec)

# --------------------------------------------------------------------------- terms
TERMS = {
    "male": {"en": "Male", "hi": "पुरुष", "mr": "पुरुष", "ta": "ஆண்", "bn": "পুরুষ", "ar": "ذكر"},
    "female": {"en": "Female", "hi": "महिला", "mr": "स्त्री", "ta": "பெண்", "bn": "মহিলা", "ar": "أنثى"},
    "married": {"en": "Married", "hi": "विवाहित", "mr": "विवाहित", "ta": "திருமணமானவர்", "bn": "বিবাহিত", "ar": "متزوج"},
    "single": {"en": "Single", "hi": "अविवाहित", "mr": "अविवाहित", "ta": "திருமணமாகாதவர்", "bn": "অবিবাহিত", "ar": "أعزب"},
    "savings": {"en": "Savings", "hi": "बचत", "mr": "बचत", "ta": "சேமிப்பு", "bn": "সঞ্চয়", "ar": "ادخار"},
    "current": {"en": "Current", "hi": "चालू", "mr": "चालू", "ta": "நடப்பு", "bn": "চলতি", "ar": "جاري"},
    "salary": {"en": "Salary", "hi": "वेतन", "mr": "पगार", "ta": "சம்பளம்", "bn": "বেতন", "ar": "راتب"},
    "salaried": {"en": "Salaried", "hi": "नौकरीपेशा", "mr": "नोकरदार", "ta": "சம்பளதாரர்", "bn": "চাকরিজীবী", "ar": "موظف"},
    "self_employed": {"en": "Self-employed", "hi": "स्व-रोज़गार", "mr": "स्वयंरोजगार", "ta": "சுயதொழில்", "bn": "স্বনির্ভর", "ar": "عمل حر"},
    "business": {"en": "Business owner", "hi": "व्यवसायी", "mr": "व्यावसायिक", "ta": "வணிகர்", "bn": "ব্যবসায়ী", "ar": "صاحب عمل"},
    "professional": {"en": "Professional", "hi": "पेशेवर", "mr": "व्यावसायिक", "ta": "தொழில் வல்லுநர்", "bn": "পেশাদার", "ar": "مهني"},
    "spouse": {"en": "Spouse", "hi": "पति/पत्नी", "mr": "जोडीदार", "ta": "துணைவர்", "bn": "স্বামী/স্ত্রী", "ar": "الزوج/الزوجة"},
    "mother": {"en": "Mother", "hi": "माता", "mr": "आई", "ta": "தாய்", "bn": "মা", "ar": "الأم"},
    "father": {"en": "Father", "hi": "पिता", "mr": "वडील", "ta": "தந்தை", "bn": "বাবা", "ar": "الأب"},
    "daughter": {"en": "Daughter", "hi": "पुत्री", "mr": "मुलगी", "ta": "மகள்", "bn": "কন্যা", "ar": "الابنة"},
    "son": {"en": "Son", "hi": "पुत्र", "mr": "मुलगा", "ta": "மகன்", "bn": "পুত্র", "ar": "الابن"},
    "aadhaar": {"en": "Aadhaar", "hi": "आधार", "mr": "आधार", "ta": "ஆதார்", "bn": "আধার", "ar": "أدهار"},
    "pan": {"en": "PAN", "hi": "पैन", "mr": "पॅन", "ta": "பான்", "bn": "প্যান", "ar": "PAN"},
    "voter": {"en": "Voter ID", "hi": "मतदाता पहचान पत्र", "mr": "मतदार ओळखपत्र", "ta": "வாக்காளர் அடையாளம்", "bn": "ভোটার আইডি", "ar": "بطاقة ناخب"},
    "standard": {"en": "Standard", "hi": "सामान्य", "mr": "सामान्य", "ta": "வழக்கமானது", "bn": "সাধারণ", "ar": "عادي"},
    "express": {"en": "Express", "hi": "त्वरित", "mr": "त्वरित", "ta": "விரைவு", "bn": "দ্রুত", "ar": "سريع"},
    "address_update": {"en": "Address update", "hi": "पता अद्यतन", "mr": "पत्ता अद्ययावत", "ta": "முகவரி புதுப்பிப்பு", "bn": "ঠিকানা হালনাগাদ", "ar": "تحديث العنوان"},
    "duplicate_statement": {"en": "Duplicate statement", "hi": "डुप्लिकेट स्टेटमेंट", "mr": "डुप्लिकेट स्टेटमेंट", "ta": "நகல் அறிக்கை", "bn": "নকল বিবরণী", "ar": "كشف حساب مكرر"},
    "card_replacement": {"en": "Card replacement", "hi": "कार्ड बदलना", "mr": "कार्ड बदलणे", "ta": "அட்டை மாற்றம்", "bn": "কার্ড প্রতিস্থাপন", "ar": "استبدال البطاقة"},
    "home_renovation": {"en": "Home renovation", "hi": "घर नवीनीकरण", "mr": "घर नूतनीकरण", "ta": "வீடு புதுப்பித்தல்", "bn": "বাড়ি সংস্কার", "ar": "تجديد المنزل"},
    "education": {"en": "Education", "hi": "शिक्षा", "mr": "शिक्षण", "ta": "கல்வி", "bn": "শিক্ষা", "ar": "تعليم"},
    "business_expansion": {"en": "Business expansion", "hi": "व्यवसाय विस्तार", "mr": "व्यवसाय विस्तार", "ta": "வணிக விரிவாக்கம்", "bn": "ব্যবসা সম্প্রসারণ", "ar": "توسيع الأعمال"},
    "vehicle": {"en": "Vehicle purchase", "hi": "वाहन खरीद", "mr": "वाहन खरेदी", "ta": "வாகனம் வாங்குதல்", "bn": "যানবাহন ক্রয়", "ar": "شراء مركبة"},
    "residential": {"en": "Residential property", "hi": "आवासीय संपत्ति", "mr": "निवासी मालमत्ता", "ta": "குடியிருப்பு சொத்து", "bn": "আবাসিক সম্পত্তি", "ar": "عقار سكني"},
    "fixed_deposit": {"en": "Fixed deposit", "hi": "सावधि जमा", "mr": "मुदत ठेव", "ta": "நிலையான வைப்பு", "bn": "স্থায়ী আমানত", "ar": "وديعة ثابتة"},
    "none": {"en": "None", "hi": "कोई नहीं", "mr": "काही नाही", "ta": "இல்லை", "bn": "কোনোটি নয়", "ar": "لا يوجد"},
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def t(term: str, lang: str) -> str:
    return TERMS.get(term, {}).get(lang) or TERMS.get(term, {}).get("en", term)


def inr(n: int | float, decimals: bool = False) -> str:
    """Indian digit grouping with a Rupee prefix."""
    if decimals:
        s = f"{n:,.2f}"
    else:
        s = f"{int(round(n)):,}"
    # Convert 1,234,567 to 12,34,567.
    parts = s.split(".")
    whole = parts[0].replace(",", "")
    if len(whole) > 3:
        last3 = whole[-3:]
        rest = whole[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        whole = ",".join(groups) + "," + last3
    out = "₹ " + whole
    if len(parts) > 1:
        out += "." + parts[1]
    return out


# --------------------------------------------------------------------------- people
@dataclass
class Person:
    names: dict[str, str]
    city: str
    area: int
    house: str
    pin: str
    gender: str
    dob: str
    pan: str
    aadhaar: str
    mobile: str
    email: str
    income: int
    father: dict[str, str]
    mother: dict[str, str]


PEOPLE: list[Person] = [
    Person({"en": "Ramesh Iyer", "hi": "रमेश अय्यर", "mr": "रमेश अय्यर", "ta": "ரமேஷ் ஐயர்", "bn": "রমেশ আইয়ার", "ar": "راميش أيير"},
           "mumbai", 0, "12", "400058", "male", "14/06/1987", "AKJPI4821R", "4821", "9820112233", "ramesh.iyer@example.in", 960000,
           {"en": "Suresh Iyer", "hi": "सुरेश अय्यर", "mr": "सुरेश अय्यर", "ta": "சுரேஷ் ஐயர்", "bn": "সুরেশ আইয়ার", "ar": "سوريش أيير"},
           {"en": "Latha Iyer", "hi": "लता अय्यर", "mr": "लता अय्यर", "ta": "லதா ஐயர்", "bn": "লতা আইয়ার", "ar": "لاتا أيير"}),
    Person({"en": "Sunita Deshmukh", "hi": "सुनीता देशमुख", "mr": "सुनीता देशमुख", "ta": "சுனிதா தேஷ்முக்", "bn": "সুনীতা দেশমুখ", "ar": "سونيتا ديشموك"},
           "pune", 1, "48", "411038", "female", "03/11/1992", "BQPDS7392L", "7392", "9822456781", "sunita.d@example.in", 720000,
           {"en": "Anil Deshmukh", "hi": "अनिल देशमुख", "mr": "अनिल देशमुख", "ta": "அனில் தேஷ்முக்", "bn": "অনিল দেশমুখ", "ar": "أنيل ديشموك"},
           {"en": "Vaishali Deshmukh", "hi": "वैशाली देशमुख", "mr": "वैशाली देशमुख", "ta": "வைஷாலி தேஷ்முக்", "bn": "বৈশালী দেশমুখ", "ar": "فايشالي ديشموك"}),
    Person({"en": "Imran Qureshi", "hi": "इमरान कुरैशी", "mr": "इमरान कुरैशी", "ta": "இம்ரான் குரேஷி", "bn": "ইমরান কুরেশি", "ar": "عمران قريشي"},
           "hyderabad", 2, "7-2-118", "500028", "male", "21/02/1985", "CDLPQ5518M", "5518", "9949123456", "imran.q@example.in", 1440000,
           {"en": "Rashid Qureshi", "hi": "रशीद कुरैशी", "mr": "रशीद कुरैशी", "ta": "ரஷீத் குரேஷி", "bn": "রশিদ কুরেশি", "ar": "رشيد قريشي"},
           {"en": "Naseem Qureshi", "hi": "नसीम कुरैशी", "mr": "नसीम कुरैशी", "ta": "நசீம் குரேஷி", "bn": "নসীম কুরেশি", "ar": "نسيم قريشي"}),
    Person({"en": "Lakshmi Narayanan", "hi": "लक्ष्मी नारायणन", "mr": "लक्ष्मी नारायणन", "ta": "லக்ஷ்மி நாராயணன்", "bn": "লক্ষ্মী নারায়ণন", "ar": "لاكشمي نارايانان"},
           "chennai", 3, "18", "600041", "female", "30/08/1979", "DEFPN8840K", "8840", "9841022334", "lakshmi.n@example.in", 1800000,
           {"en": "R. Narayanan", "hi": "आर. नारायणन", "mr": "आर. नारायणन", "ta": "ஆர். நாராயணன்", "bn": "আর. নারায়ণন", "ar": "ر. نارايانان"},
           {"en": "Saraswathi Narayanan", "hi": "सरस्वती नारायणन", "mr": "सरस्वती नारायणन", "ta": "சரஸ்வதி நாராயணன்", "bn": "সরস্বতী নারায়ণন", "ar": "ساراسواتي نارايانان"}),
    Person({"en": "Ananya Bose", "hi": "अनन्या बोस", "mr": "अनन्या बोस", "ta": "அனன்யா போஸ்", "bn": "অনন্যা বসু", "ar": "أنانيا بوس"},
           "kolkata", 4, "23B", "700019", "female", "19/01/1996", "EFGPB1901N", "1901", "9830776655", "ananya.bose@example.in", 660000,
           {"en": "Subir Bose", "hi": "सुबीर बोस", "mr": "सुबीर बोस", "ta": "சுபீர் போஸ்", "bn": "সুবীর বসু", "ar": "سوبير بوس"},
           {"en": "Mitali Bose", "hi": "मिताली बोस", "mr": "मिताली बोस", "ta": "மிதாலி போஸ்", "bn": "মিতালি বসু", "ar": "ميتالي بوس"}),
    Person({"en": "Vikram Singh", "hi": "विक्रम सिंह", "mr": "विक्रम सिंह", "ta": "விக்ரம் சிங்", "bn": "বিক্রম সিং", "ar": "فيكرام سينغ"},
           "delhi", 5, "C-42", "110024", "male", "07/04/1983", "FGHPS2277P", "2277", "9811445566", "vikram.singh@example.in", 2400000,
           {"en": "Harjeet Singh", "hi": "हरजीत सिंह", "mr": "हरजीत सिंह", "ta": "ஹர்ஜீத் சிங்", "bn": "হরজিৎ সিং", "ar": "هارجيت سينغ"},
           {"en": "Gurmeet Kaur", "hi": "गुरमीत कौर", "mr": "गुरमीत कौर", "ta": "குர்மீத் கவுர்", "bn": "গুরমীত কৌর", "ar": "غورميت كور"}),
    Person({"en": "Fatima Al-Zahra", "hi": "फातिमा अल-ज़हरा", "mr": "फातिमा अल-झहरा", "ta": "ஃபாத்திமா அல்-ஜஹ்ரா", "bn": "ফাতিমা আল-জাহরা", "ar": "فاطمة الزهراء"},
           "mumbai", 2, "B-14", "400053", "female", "12/09/1990", "HIJPA6634Q", "6634", "9820678899", "fatima.az@example.in", 1080000,
           {"en": "Yusuf Al-Zahra", "hi": "यूसुफ अल-ज़हरा", "mr": "युसूफ अल-झहरा", "ta": "யூசுப் அல்-ஜஹ்ரா", "bn": "ইউসুফ আল-জাহরা", "ar": "يوسف الزهراء"},
           {"en": "Maryam Al-Zahra", "hi": "मरियम अल-ज़हरा", "mr": "मरियम अल-झहरा", "ta": "மரியம் அல்-ஜஹ்ரா", "bn": "মরিয়ম আল-জাহরা", "ar": "مريم الزهراء"}),
    Person({"en": "Karthik Subramanian", "hi": "कार्तिक सुब्रमण्यम", "mr": "कार्तिक सुब्रमण्यम", "ta": "கார்த்திக் சுப்ரமணியன்", "bn": "কার্তিক সুব্রামণ্যম", "ar": "كارثيك سوبرامانيان"},
           "bengaluru", 1, "44", "560095", "male", "05/12/1988", "IJKPS9081R", "9081", "9880443322", "karthik.s@example.in", 1560000,
           {"en": "S. Subramanian", "hi": "एस. सुब्रमण्यम", "mr": "एस. सुब्रमण्यम", "ta": "எஸ். சுப்ரமணியன்", "bn": "এস. সুব্রামণ্যম", "ar": "س. سوبرامانيان"},
           {"en": "Radha Subramanian", "hi": "राधा सुब्रमण्यम", "mr": "राधा सुब्रमण्यम", "ta": "ராதா சுப்ரமணியன்", "bn": "রাধা সুব্রামণ্যম", "ar": "رادها سوبرامانيان"}),
    Person({"en": "Meera Krishnan", "hi": "मीरा कृष्णन", "mr": "मीरा कृष्णन", "ta": "மீரா கிருஷ்ணன்", "bn": "মীরা কৃষ্ণন", "ar": "ميرا كريشنان"},
           "chennai", 0, "9", "600020", "female", "25/03/1975", "JKLPN3320T", "3320", "9840998877", "meera.k@example.in", 2100000,
           {"en": "P. Krishnan", "hi": "पी. कृष्णन", "mr": "पी. कृष्णन", "ta": "பி. கிருஷ்ணன்", "bn": "পি. কৃষ্ণন", "ar": "ب. كريشنان"},
           {"en": "Kamala Krishnan", "hi": "कमला कृष्णन", "mr": "कमला कृष्णन", "ta": "கமலா கிருஷ்ணன்", "bn": "কমলা কৃষ্ণন", "ar": "كامالا كريشنان"}),
    Person({"en": "Rahul Banerjee", "hi": "राहुल बनर्जी", "mr": "राहुल बनर्जी", "ta": "ராகுல் பானர்ஜி", "bn": "রাহুল ব্যানার্জী", "ar": "راهول بانيرجي"},
           "kolkata", 2, "5A", "700091", "male", "16/07/1994", "KLMNB7742V", "7742", "9831223344", "rahul.b@example.in", 840000,
           {"en": "Amit Banerjee", "hi": "अमित बनर्जी", "mr": "अमित बनर्जी", "ta": "அமித் பானர்ஜி", "bn": "অমিত ব্যানার্জী", "ar": "أميت بانيرجي"},
           {"en": "Rina Banerjee", "hi": "रीना बनर्जी", "mr": "रीना बनर्जी", "ta": "ரீனா பானர்ஜி", "bn": "রীনা ব্যানার্জী", "ar": "رينا بانيرجي"}),
    Person({"en": "Ayesha Siddiqui", "hi": "आयशा सिद्दीकी", "mr": "आयशा सिद्दीकी", "ta": "ஆயிஷா சித்திகி", "bn": "আয়েশা সিদ্দিকী", "ar": "عائشة صديقي"},
           "hyderabad", 1, "8-3-214", "500034", "female", "09/05/1991", "LMNPQ4416W", "4416", "9948776655", "ayesha.s@example.in", 900000,
           {"en": "Nadeem Siddiqui", "hi": "नदीम सिद्दीकी", "mr": "नदीम सिद्दीकी", "ta": "நதீம் சித்திகி", "bn": "নদীম সিদ্দিকী", "ar": "نديم صديقي"},
           {"en": "Shabana Siddiqui", "hi": "शबाना सिद्दीकी", "mr": "शबाना सिद्दीकी", "ta": "ஷபானா சித்திகி", "bn": "শাবানা সিদ্দিকী", "ar": "شبانة صديقي"}),
    Person({"en": "Joseph Mathew", "hi": "जोसेफ मैथ्यू", "mr": "जोसेफ मॅथ्यू", "ta": "ஜோசப் மேத்யூ", "bn": "জোসেফ ম্যাথিউ", "ar": "جوزيف ماثيو"},
           "bengaluru", 4, "31", "560034", "male", "28/10/1980", "MNOPM1188X", "1188", "9880113344", "joseph.m@example.in", 2700000,
           {"en": "Thomas Mathew", "hi": "थॉमस मैथ्यू", "mr": "थॉमस मॅथ्यू", "ta": "தாமஸ் மேத்யூ", "bn": "টমাস ম্যাথিউ", "ar": "توماس ماثيو"},
           {"en": "Elsy Mathew", "hi": "एल्सी मैथ्यू", "mr": "एल्सी मॅथ्यू", "ta": "எல்சி மேத்யூ", "bn": "এলসি ম্যাথিউ", "ar": "إلسي ماثيو"}),
    Person({"en": "Priya Nair", "hi": "प्रिया नायर", "mr": "प्रिया नायर", "ta": "பிரியா நாயர்", "bn": "প্রিয়া নায়ার", "ar": "بريا ناير"},
           "mumbai", 5, "16", "400076", "female", "14/02/1993", "NOPPN5561Y", "5561", "9821990011", "priya.nair@example.in", 780000,
           {"en": "Gopal Nair", "hi": "गोपाल नायर", "mr": "गोपाल नायर", "ta": "கோபால் நாயர்", "bn": "গোপাল নায়ার", "ar": "غوبال ناير"},
           {"en": "Sreeja Nair", "hi": "श्रीजा नायर", "mr": "श्रीजा नायर", "ta": "ஸ்ரீஜா நாயர்", "bn": "শ্রীজা নায়ার", "ar": "سريجا ناير"}),
    Person({"en": "Arvind Rao", "hi": "अरविंद राव", "mr": "अरविंद राव", "ta": "அரவிந்த் ராவ்", "bn": "অরবিন্দ রাও", "ar": "أرفيند راو"},
           "bengaluru", 0, "72", "560043", "male", "02/06/1986", "OPQPR2299Z", "2299", "9880667788", "arvind.rao@example.in", 1320000,
           {"en": "K. Rao", "hi": "के. राव", "mr": "के. राव", "ta": "கே. ராவ்", "bn": "কে. রাও", "ar": "ك. راو"},
           {"en": "Sudha Rao", "hi": "सुधा राव", "mr": "सुधा राव", "ta": "சுதா ராவ்", "bn": "সুধা রাও", "ar": "سودها راو"}),
    Person({"en": "Nandini Gupta", "hi": "नंदिनी गुप्ता", "mr": "नंदिनी गुप्ता", "ta": "நந்தினி குப்தா", "bn": "নন্দিনী গুপ্তা", "ar": "نانديني غوبتا"},
           "delhi", 2, "D-9", "110016", "female", "22/11/1998", "PQRPG8834A", "8834", "9810778899", "nandini.g@example.in", 480000,
           {"en": "Rajesh Gupta", "hi": "राजेश गुप्ता", "mr": "राजेश गुप्ता", "ta": "ராஜேஷ் குப்தா", "bn": "রাজেশ গুপ্তা", "ar": "راجيش غوبتا"},
           {"en": "Anita Gupta", "hi": "अनीता गुप्ता", "mr": "अनीता गुप्ता", "ta": "அனிதா குப்தா", "bn": "অনিতা গুপ্তা", "ar": "أنيتا غوبتا"}),
    Person({"en": "Salim Khan", "hi": "सलीम खान", "mr": "सलीम खान", "ta": "சலீம் கான்", "bn": "সলিম খান", "ar": "سليم خان"},
           "hyderabad", 3, "11-4-77", "500001", "male", "11/01/1978", "QRSPK4410B", "4410", "9948001122", "salim.khan@example.in", 3000000,
           {"en": "Karim Khan", "hi": "करीम खान", "mr": "करीम खान", "ta": "கரீம் கான்", "bn": "করিম খান", "ar": "كريم خان"},
           {"en": "Razia Khan", "hi": "रज़िया खान", "mr": "रझिया खान", "ta": "ரஜியா கான்", "bn": "রাজিয়া খান", "ar": "رازيا خان"}),
    Person({"en": "Kavya Menon", "hi": "काव्या मेनन", "mr": "काव्या मेनन", "ta": "காவ்யா மேனன்", "bn": "কাব্যা মেনন", "ar": "كافيا مينون"},
           "chennai", 2, "27", "600096", "female", "08/08/1995", "RSTPM7753C", "7753", "9840556677", "kavya.menon@example.in", 1020000,
           {"en": "S. Menon", "hi": "एस. मेनन", "mr": "एस. मेनन", "ta": "எஸ். மேனன்", "bn": "এস. মেনন", "ar": "س. مينون"},
           {"en": "Bindu Menon", "hi": "बिंदु मेनन", "mr": "बिंदू मेनन", "ta": "பிந்து மேனன்", "bn": "বিন্দু মেনন", "ar": "بيندو مينون"}),
    Person({"en": "Rohit Sharma", "hi": "रोहित शर्मा", "mr": "रोहित शर्मा", "ta": "ரோஹித் சர்மா", "bn": "রোহিত শর্মা", "ar": "روهيت شارما"},
           "delhi", 0, "88", "110017", "male", "17/03/1989", "STUPS6612D", "6612", "9811002233", "rohit.sharma@example.in", 1200000,
           {"en": "Mohan Sharma", "hi": "मोहन शर्मा", "mr": "मोहन शर्मा", "ta": "மோகன் சர்மா", "bn": "মোহন শর্মা", "ar": "موهان شارما"},
           {"en": "Kiran Sharma", "hi": "किरण शर्मा", "mr": "किरण शर्मा", "ta": "கிரண் சர்மா", "bn": "কিরণ শর্মা", "ar": "كيرن شارما"}),
]

CITIES = {
    "mumbai": {"en": "Mumbai", "hi": "मुंबई", "mr": "मुंबई", "ta": "மும்பை", "bn": "মুম্বাই", "ar": "مومباي"},
    "pune": {"en": "Pune", "hi": "पुणे", "mr": "पुणे", "ta": "புனே", "bn": "পুনে", "ar": "بونه"},
    "hyderabad": {"en": "Hyderabad", "hi": "हैदराबाद", "mr": "हैदराबाद", "ta": "ஹைதராபாத்", "bn": "হায়দরাবাদ", "ar": "حيدر آباد"},
    "chennai": {"en": "Chennai", "hi": "चेन्नई", "mr": "चेन्नई", "ta": "சென்னை", "bn": "চেন্নাই", "ar": "تشيناي"},
    "kolkata": {"en": "Kolkata", "hi": "कोलकाता", "mr": "कोलकाता", "ta": "கொல்கத்தா", "bn": "কলকাতা", "ar": "كولكاتا"},
    "delhi": {"en": "New Delhi", "hi": "नई दिल्ली", "mr": "नवी दिल्ली", "ta": "புது டெல்லி", "bn": "নয়াদিল্লি", "ar": "نيودلهي"},
    "bengaluru": {"en": "Bengaluru", "hi": "बेंगलुरु", "mr": "बेंगळुरू", "ta": "பெங்களூரு", "bn": "বেঙ্গালুরু", "ar": "بنغالورو"},
}

AREAS = {
    "en": ["Sundar Nagar, Andheri West", "Shivaji Housing Society, Kothrud", "Banjara Hills, Road No. 12",
           "Besant Nagar, 2nd Main Road", "Salt Lake, Sector II", "Greater Kailash II", "Indiranagar, 12th Main",
           "Powai, Hiranandani Gardens"],
    "hi": ["सुंदर नगर, अंधेरी पश्चिम", "शिवाजी हाउसिंग सोसाइटी, कोथरूड", "बंजारा हिल्स, रोड नंबर 12",
           "बेसेंट नगर, दूसरी मेन रोड", "सॉल्ट लेक, सेक्टर II", "ग्रेटर कैलाश II", "इंदिरानगर, 12वीं मेन",
           "पोवाई, हीरानंदानी गार्डन्स"],
    "mr": ["सुंदर नगर, अंधेरी पश्चिम", "शिवाजी हाउसिंग सोसायटी, कोथरूड", "बंजारा हिल्स, रोड क्रमांक 12",
           "बेसेंट नगर, दुसरी मेन रोड", "सॉल्ट लेक, सेक्टर II", "ग्रेटर कैलाश II", "इंदिरानगर, 12वी मेन",
           "पोवाई, हीरानंदानी गार्डन्स"],
    "ta": ["சுந்தர் நகர், அந்தேரி மேற்கு", "சிவாஜி ஹவுசிங் சொசைட்டி, கோத்ரூட்", "பஞ்சாரா ஹில்ஸ், சாலை 12",
           "பெசன்ட் நகர், 2வது மெயின் ரோடு", "சால்ட் லேக், செக்டர் II", "கிரேட்டர் கைலாஷ் II", "இந்திரநகர், 12வது மெயின்",
           "பவாய், ஹிரானந்தானி கார்டன்ஸ்"],
    "bn": ["সুন্দর নগর, আন্দেরি পশ্চিম", "শিবাজি হাউজিং সোসাইটি, কোথরুড", "বাঞ্জারা হিলস, রোড ১২",
           "বেসান্ট নগর, ২য় মেইন রোড", "সল্ট লেক, সেক্টর II", "গ্রেটার কৈলাশ II", "ইন্দিরানগর, ১২তম মেইন",
           "পোওয়াই, হিরানন্দানি গার্ডেনস"],
    "ar": ["شارع النور، حي الأندلس", "شارع السلام، حي الكوثر", "طريق رقم 12، بانجارا هيلز",
           "بيسانت نجر، الطريق الرئيسي الثاني", "سولت ليك، القطاع الثاني", "غريتر كايلاش الثاني", "إنديرانجر، الطريق الرئيسي 12",
           "بوواي، حدائق هيرانانداني"],
}

STATES = {"mumbai": "Maharashtra", "pune": "Maharashtra", "hyderabad": "Telangana",
          "chennai": "Tamil Nadu", "kolkata": "West Bengal", "delhi": "Delhi",
          "bengaluru": "Karnataka"}


def name(p: Person, lang: str) -> str:
    return p.names.get(lang) or p.names["en"]


def address(p: Person, lang: str) -> str:
    area = AREAS.get(lang, AREAS["en"])[p.area]
    if lang == "ar":
        return f"{p.house} {area}، {CITIES[p.city]['ar']} {p.pin}"
    if lang == "bn":
        return f"{p.house}, {area}, {CITIES[p.city]['bn']} {p.pin}"
    return f"{p.house}, {area}, {CITIES[p.city][lang]} {p.pin}"


# --------------------------------------------------------------------------- sample metadata
@dataclass
class Sample:
    id: str
    kind: str
    person_idx: int
    lang: str
    quality: str
    status: str
    priority: str = "normal"
    submitted_minutes: int = 30
    assignee: str | None = None
    reviewer: str | None = None
    reviewed_after: int | None = None
    amount: float | None = None
    low: dict[str, tuple[float, str | None]] = field(default_factory=dict)
    note: str = ""
    reject_reason: str = ""
    escalation_reason: str = ""
    rescan_reason: str = ""
    bill_to: str = ""
    sequence: int = 0

    @property
    def person(self) -> Person:
        return PEOPLE[self.person_idx]

    @property
    def rtl(self) -> bool:
        return self.lang == "ar"


SAMPLES: list[Sample] = [
    Sample("bank_01", "bank", 0, "hi", "fair", "queued", "high", 38,
           low={"full_name": (0.58, "name"), "dob": (0.63, "date"),
                "mobile": (0.44, "phone"), "account_type": (0.72, None)},
           note="Branch walk-in application with a folded first page."),
    Sample("claim_01", "claim", 5, "en", "poor", "queued", "urgent", 96,
           low={"claim_amount": (0.56, "amount"), "diagnosis": (0.61, None),
                "discharge_date": (0.68, None)},
           note="Discharge date precedes admission date."),
    Sample("service_01", "service", 7, "ta", "good", "auto_approved", "normal", 12),
    Sample("loan_01", "loan", 4, "bn", "good", "approved", "normal", 210,
           assignee="maya", reviewer="maya", reviewed_after=26, amount=850000),
    Sample("invoice_01", "invoice", 13, "en", "good", "auto_approved", "normal", 25,
           bill_to="Meridian Retail Ltd.", amount=128450),
    Sample("kyc_01", "kyc", 6, "ar", "fair", "queued", "normal", 65,
           low={"full_name": (0.62, "name"), "id_number": (0.57, "digit"),
                "pan": (0.69, "ifsc")},
           note="Arabic address block; bilingual KYC update."),
    Sample("bank_02", "bank", 1, "mr", "good", "approved", "normal", 1440,
           assignee="arjun", reviewer="arjun", reviewed_after=18),
    Sample("claim_02", "claim", 8, "hi", "fair", "escalated", "urgent", 255,
           assignee="arjun", amount=485000,
           low={"diagnosis": (0.64, None), "claim_amount": (0.69, None)},
           escalation_reason="High-value claim above ₹4,00,000; senior adjudication required.",
           note="Requested cashless enhancement during admission."),
    Sample("loan_02", "loan", 2, "ta", "poor", "needs_rescan", "high", 310,
           assignee="maya", amount=1250000,
           low={"applicant_name": (0.51, "name"), "pan": (0.46, "ifsc"),
                "monthly_income": (0.58, "digit"), "property_address": (0.42, "name")},
           rescan_reason="Scan quality below threshold: page cropped and text smudged. Requested a fresh copy from the branch.",
           note="Customer submitted a phone photo of a photocopy."),
    Sample("service_02", "service", 12, "en", "good", "queued", "normal", 22,
           note="Duplicate statement request through the mobile app."),
    Sample("invoice_02", "invoice", 4, "ar", "fair", "queued", "high", 150,
           bill_to="Northstar Logistics", amount=294500,
           low={"vendor_name": (0.67, "name"), "total": (0.61, "total_mismatch"),
                "invoice_no": (0.73, None)},
           note="Arabic invoice with a totals mismatch."),
    Sample("bank_03", "bank", 13, "bn", "good", "auto_approved", "normal", 35),
    Sample("claim_03", "claim", 10, "en", "good", "rejected", "normal", 2880,
           assignee="maya", reviewer="maya", reviewed_after=14,
           reject_reason="Duplicate submission: original claim SH-2025-118220 was settled on 22 Oct 2026."),
    Sample("loan_03", "loan", 9, "hi", "fair", "in_review", "high", 88,
           assignee="arjun", amount=2200000,
           low={"property_address": (0.56, None), "credit_score": (0.71, None)},
           note="Applicant is self-employed; income proof attached separately."),
    Sample("invoice_03", "invoice", 16, "ta", "good", "approved", "normal", 1320,
           assignee="maya", reviewer="maya", reviewed_after=21,
           bill_to="Kaveri Foods", amount=76400),
    Sample("kyc_02", "kyc", 10, "ar", "poor", "queued", "urgent", 1320,
           low={"id_number": (0.41, "blank"), "address": (0.49, "name"),
                "mobile": (0.60, "phone")},
           note="SLA breached. ID number unreadable in the scan."),
    Sample("service_03", "service", 15, "bn", "good", "queued", "normal", 55,
           low={"contact_pref": (0.77, None)},
           note="Bengali service request; customer prefers a call back."),
    Sample("claim_04", "claim", 14, "ta", "fair", "in_review", "normal", 70,
           assignee="maya", amount=72000,
           low={"claim_amount": (0.67, None), "diagnosis": (0.74, None)},
           note="Day-care procedure; discharge summary attached."),
]

for i, s in enumerate(SAMPLES):
    s.sequence = 1042 + i


# --------------------------------------------------------------------------- builders
LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil",
              "bn": "Bengali", "ar": "Arabic"}
SCRIPT_NAMES = {"en": "Latin", "hi": "Devanagari", "mr": "Devanagari",
                "ta": "Tamil", "bn": "Bengali", "ar": "Arabic"}
# (brand, tagline, initials, accent, dark) — matches Form(...) parameter order.
BRAND = {
    "bank": ("Bharat Meridian Bank", "Retail banking · भरोसे का नया अध्याय", "BM", "#C9A227", "#0F3B36"),
    "claim": ("Suraksha Health Assurance", "Claims that keep their promise", "SH", "#D99A63", "#6E1F2A"),
    "service": ("BharatConnect Service Centres", "Every request, resolved", "BC", "#E0894F", "#153B5B"),
    "loan": ("Bharat Meridian Bank", "Retail lending · आपके सपनों का साथ", "BM", "#B99A63", "#2B3B2D"),
    "invoice": ("Sundaram Textiles Pvt. Ltd.", "Handloom & home textiles · Coimbatore", "ST", "#D2A72E", "#24262A"),
    "kyc": ("Bharat Meridian Bank", "Know your customer · केवाईसी", "BM", "#C77655", "#302A5A"),
}
TITLES = {
    "bank": ("Account Opening Application", "खाता खोलने का आवेदन", "BM/SAV/14"),
    "claim": ("Health Claim Intimation", "स्वास्थ्य दावा सूचना", "SH/CLM/07"),
    "service": ("Service Request Form", "सेवा अनुरोध फॉर्म", "BC/SR/22"),
    "loan": ("Retail Loan Application", "खुदरा ऋण आवेदन", "BM/LN/09"),
    "invoice": ("Tax Invoice", "कर बीजक", "ST/INV/03"),
    "kyc": ("KYC Update Form", "केवाईसी अद्यतन फॉर्म", "BM/KYC/11"),
}
TITLE_BY_LANG = {
    "bank": {"en": "Account Opening Application", "hi": "खाता खोलने का आवेदन",
             "mr": "खाते उघडण्याचा अर्ज", "ta": "கணக்கு தொடங்கும் விண்ணப்பம்",
             "bn": "অ্যাকাউন্ট খোলার আবেদন", "ar": "طلب فتح حساب"},
    "claim": {"en": "Health Claim Intimation", "hi": "स्वास्थ्य दावा सूचना",
              "mr": "आरोग्य दावा सूचना", "ta": "சுகாதார காப்பீட்டு கோரிக்கை",
              "bn": "স্বাস্থ্য দাবি বিবরণী", "ar": "إخطار بمطالبة تأمين صحي"},
    "service": {"en": "Service Request Form", "hi": "सेवा अनुरोध फॉर्म",
                "mr": "सेवा विनंती अर्ज", "ta": "சேவை கோரிக்கை படிவம்",
                "bn": "পরিষেবা অনুরোধ ফর্ম", "ar": "نموذج طلب خدمة"},
    "loan": {"en": "Retail Loan Application", "hi": "खुदरा ऋण आवेदन",
             "mr": "किरकोळ कर्ज अर्ज", "ta": "சில்லறை கடன் விண்ணப்பம்",
             "bn": "খুচরা ঋণ আবেদন", "ar": "طلب قرض تجزئة"},
    "invoice": {"en": "Tax Invoice", "hi": "कर बीजक", "mr": "कर बीजक",
                "ta": "வரி விலைப்பட்டியல்", "bn": "কর চালান", "ar": "فاتورة ضريبية"},
    "kyc": {"en": "KYC Update Form", "hi": "केवाईसी अद्यतन फॉर्म",
            "mr": "केव्हायसी अद्ययावत फॉर्म", "ta": "கேஒய்சி புதுப்பிப்பு படிவம்",
            "bn": "কেওয়াইসি হালনাগাদ ফর্ম", "ar": "نموذج تحديث بيانات العميل"},
}


def f(key, label, value, sub="", **kw) -> FieldSpec:
    return FieldSpec(key=key, label=label, value=value, label_sub=sub, **kw)


def sec(title, fields, subtitle="", columns=2, row_h=82, width=CONTENT_W) -> SectionSpec:
    return SectionSpec(title=title, fields=fields, subtitle=subtitle,
                       columns=columns, row_h=row_h, width=width)


def _num_field(key, label, value, sub="", **kw):
    return f(key, label, value, sub, font_size=26, **kw)


def build_bank(s: Sample) -> tuple[Form, list[SectionSpec]]:
    p = s.person
    lang = s.lang
    form = Form(*BRAND["bank"], rtl=s.rtl)
    form.header(f"BM/SAV/{s.sequence}", "07 NOV 2026", "BM")
    form.title(TITLE_BY_LANG["bank"][lang], "Account Opening Application" if lang != "en" else "Retail banking · savings & current accounts",
               f"AK-26-{s.sequence}", "07 Nov 2026", subtitle_font=FONT)
    form.watermark()
    form.paper_artifacts()
    sections = [
        sec("Applicant identity", [
            f("full_name", "Full name", name(p, lang), "पूरा नाम" if lang == "hi" else ""),
            f("dob", "Date of birth", p.dob, "जन्म तिथि" if lang == "hi" else "", type="date"),
            f("gender", "Gender", t(p.gender, lang), "लिंग" if lang == "hi" else "", type="choice", options=["Male", "Female"]),
            f("marital_status", "Marital status", t("married" if s.person_idx % 2 else "single", lang), "वैवाहिक स्थिति" if lang == "hi" else "", type="choice"),
            f("father_name", "Father's name", p.father.get(lang, p.father["en"])),
            f("mother_name", "Mother's name", p.mother.get(lang, p.mother["en"]), required=False),
        ], "आवेदक की पहचान" if lang == "hi" else "", width=880),
        sec("Contact & address", [
            f("mobile", "Mobile number", p.mobile, "मोबाइल नंबर" if lang == "hi" else "", type="phone"),
            f("email", "Email address", p.email, "ईमेल" if lang == "hi" else "", type="email", required=False),
            f("address", "Residential address", address(p, lang), "निवास पता" if lang == "hi" else "", full=True, font_size=22),
            f("city", "City", CITIES[p.city][lang], "शहर" if lang == "hi" else ""),
            f("state", "State", STATES[p.city], "राज्य" if lang == "hi" else ""),
            f("pincode", "PIN code", p.pin, "पिन कोड" if lang == "hi" else "", type="pincode"),
        ], "संपर्क और पता" if lang == "hi" else ""),
        sec("Account preferences", [
            f("account_type", "Account type", t("savings", lang), "खाता प्रकार" if lang == "hi" else "", type="choice", options=["Savings", "Current", "Salary"]),
            f("occupation", "Occupation", t("salaried" if s.person_idx % 3 else "business", lang), "व्यवसाय" if lang == "hi" else ""),
            _num_field("annual_income", "Annual income", inr(p.income), "वार्षिक आय" if lang == "hi" else "", type="amount"),
            f("branch", "Home branch", f"Meridian — {CITIES[p.city]['en']}", "शाखा" if lang == "hi" else ""),
            f("aadhaar_last4", "Aadhaar (last 4)", p.aadhaar, "आधार अंतिम 4" if lang == "hi" else "", type="number"),
            f("pan", "PAN", p.pan, "पैन" if lang == "hi" else "", type="pan"),
        ], "खाता संबंधी जानकारी" if lang == "hi" else ""),
        sec("Nominee & declaration", [
            f("nominee_name", "Nominee name", name(PEOPLE[(s.person_idx + 1) % len(PEOPLE)], lang), "नामांकित व्यक्ति" if lang == "hi" else ""),
            f("nominee_relation", "Relationship", t("spouse", lang), "संबंध" if lang == "hi" else ""),
            f("declaration", "Declaration accepted", "Accepted", "घोषणा स्वीकृत" if lang == "hi" else "", type="consent"),
        ], "नामांकन और घोषणा" if lang == "hi" else ""),
    ]
    form.photo_box(1000, 335, 168, 218)
    form.stamp(1000, 1490, "BRANCH RECEIVED", "RETAIL BANKING")
    return form, sections


def build_claim(s: Sample) -> tuple[Form, list[SectionSpec]]:
    p = s.person
    lang = s.lang
    form = Form(*BRAND["claim"], rtl=s.rtl)
    form.header(f"SH/CLM/{s.sequence}", "07 NOV 2026", "SH")
    form.title(TITLE_BY_LANG["claim"][lang], "Health indemnity · cashless reimbursement",
               f"AK-26-{s.sequence}", "07 Nov 2026")
    form.watermark()
    form.paper_artifacts()
    claim_amount = 185000 if s.id == "claim_01" else 485000 if s.id == "claim_02" else 72000
    sum_insured = 1000000 if claim_amount > 400000 else 500000
    admission = "02/11/2026" if s.id != "claim_04" else "05/11/2026"
    discharge = "06/11/2026" if s.id != "claim_04" else "05/11/2026"
    if s.id == "claim_01":
        admission, discharge = "06/11/2026", "03/11/2026"  # deliberate validation failure
    hospitals = ["Lotus Multispeciality Hospital", "Sanjeevani Hospital", "Meridian Health City",
                 "Arogya Nidhi Hospital", "Sunrise Medical Centre"]
    diagnoses = ["Acute gastroenteritis with dehydration", "Viral fever with thrombocytopenia",
                 "Acute appendicitis", "Fracture of right femur", "Dengue fever",
                 "Cardiac arrhythmia — paroxysmal"]
    hospital = hospitals[s.person_idx % len(hospitals)]
    diagnosis = diagnoses[s.person_idx % len(diagnoses)]
    sections = [
        sec("Policy & insured", [
            f("policy_no", "Policy number", f"SH-2026-00{4821 + s.person_idx}", "पॉलिसी संख्या" if lang == "hi" else "", type="id"),
            f("insured_name", "Insured name", name(p, lang), "बीमित व्यक्ति" if lang == "hi" else ""),
            f("dob", "Date of birth", p.dob, "जन्म तिथि" if lang == "hi" else "", type="date"),
            f("patient_id", "Patient ID", f"P-{77210 + s.person_idx}", "रोगी आईडी" if lang == "hi" else "", type="id"),
        ], "पॉलिसी और बीमित व्यक्ति" if lang == "hi" else ""),
        sec("Hospitalisation", [
            f("hospital_name", "Hospital", hospital, "अस्पताल" if lang == "hi" else ""),
            f("hospital_city", "City", CITIES[p.city][lang], "शहर" if lang == "hi" else ""),
            f("admission_date", "Admission date", admission, "भर्ती तिथि" if lang == "hi" else "", type="date"),
            f("discharge_date", "Discharge date", discharge, "छुट्टी तिथि" if lang == "hi" else "", type="date"),
            f("diagnosis", "Primary diagnosis", diagnosis, "निदान" if lang == "hi" else "", full=True),
            f("treating_doctor", "Treating doctor", f"Dr. {['A. Menon', 'S. Kulkarni', 'R. Iyer', 'P. Rao', 'N. Shah'][s.person_idx % 5]}", "चिकित्सक" if lang == "hi" else ""),
            f("pre_auth_no", "Pre-authorisation no.", f"PA-{99120 + s.person_idx}", "पूर्व प्राधिकरण" if lang == "hi" else "", required=False),
        ], "अस्पताल में भर्ती" if lang == "hi" else ""),
        sec("Claim summary", [
            _num_field("claim_amount", "Amount claimed", inr(claim_amount), "दावा राशि" if lang == "hi" else "", type="amount"),
            _num_field("sum_insured", "Sum insured", inr(sum_insured), "बीमा राशि" if lang == "hi" else "", type="amount"),
        ], "दावा सारांश" if lang == "hi" else "", row_h=78),
        sec("Settlement details", [
            f("bank_account", "Bank account number", f"50100{2345678 + s.person_idx}", "बैंक खाता" if lang == "hi" else "", type="account"),
            f("ifsc", "IFSC", "BMER0001234", "आईएफएससी" if lang == "hi" else "", type="ifsc"),
            f("contact", "Contact number", p.mobile, "संपर्क" if lang == "hi" else "", type="phone"),
        ], "भुगतान विवरण" if lang == "hi" else ""),
    ]
    return form, sections


def build_service(s: Sample) -> tuple[Form, list[SectionSpec]]:
    p = s.person
    lang = s.lang
    form = Form(*BRAND["service"], rtl=s.rtl)
    form.header(f"BC/SR/{s.sequence}", "07 NOV 2026", "BC")
    form.title(TITLE_BY_LANG["service"][lang], "Customer service · branch & digital channels",
               f"AK-26-{s.sequence}", "07 Nov 2026")
    form.watermark()
    form.paper_artifacts()
    request = ["address_update", "duplicate_statement", "card_replacement"][s.person_idx % 3]
    details = {
        "address_update": "Please update my registered address to the new residential address shown in the attached proof. All future correspondence should go to this address.",
        "duplicate_statement": "Requesting a duplicate account statement for the period 01 Apr 2026 to 31 Oct 2026 for a home loan application.",
        "card_replacement": "Debit card was damaged and is not readable at POS terminals. Requesting a replacement card at the home branch.",
    }[request]
    sections = [
        sec("Customer", [
            f("customer_name", "Customer name", name(p, lang), "ग्राहक का नाम" if lang == "hi" else ""),
            f("account_no", "Account number", f"50100{2345678 + s.person_idx}", "खाता संख्या" if lang == "hi" else "", type="account"),
            f("mobile", "Registered mobile", p.mobile, "पंजीकृत मोबाइल" if lang == "hi" else "", type="phone"),
            f("alt_contact", "Alternate contact", f"022-{40000000 + s.person_idx * 137}", "वैकल्पिक संपर्क" if lang == "hi" else "", required=False),
        ], "ग्राहक" if lang == "hi" else ""),
        sec("Request details", [
            f("request_type", "Request type", t(request, lang), "अनुरोध प्रकार" if lang == "hi" else "", type="choice"),
            f("priority", "Priority", t("express" if s.priority == "high" else "standard", lang), "प्राथमिकता" if lang == "hi" else "", type="choice"),
            f("service_details", "Request description", details, "अनुरोध विवरण" if lang == "hi" else "", full=True, font_size=19),
            f("branch", "Service branch", f"BharatConnect — {CITIES[p.city]['en']}", "शाखा" if lang == "hi" else ""),
            f("preferred_date", "Preferred date", "12/11/2026", "पसंदीदा तिथि" if lang == "hi" else "", type="date"),
        ], "अनुरोध विवरण" if lang == "hi" else "", row_h=78),
        sec("Consent", [
            f("contact_pref", "Contact preference", "Call back on registered mobile", "संपर्क वरीयता" if lang == "hi" else ""),
            f("consent", "Consent to process", "Agreed", "सहमति" if lang == "hi" else "", type="consent"),
        ], "सहमति" if lang == "hi" else "", row_h=76),
    ]
    return form, sections


def build_loan(s: Sample) -> tuple[Form, list[SectionSpec]]:
    p = s.person
    lang = s.lang
    form = Form(*BRAND["loan"], rtl=s.rtl)
    form.header(f"BM/LN/{s.sequence}", "07 NOV 2026", "BM")
    form.title(TITLE_BY_LANG["loan"][lang], "Retail lending · secured & unsecured",
               f"AK-26-{s.sequence}", "07 Nov 2026")
    form.watermark()
    form.paper_artifacts()
    amount = 850000 if s.id == "loan_01" else 1250000 if s.id == "loan_02" else 2200000
    sections = [
        sec("Applicant", [
            f("applicant_name", "Applicant name", name(p, lang), "आवेदक का नाम" if lang == "hi" else ""),
            f("co_applicant", "Co-applicant", name(PEOPLE[(s.person_idx + 2) % len(PEOPLE)], lang), "सह-आवेदक" if lang == "hi" else "", required=False),
            f("dob", "Date of birth", p.dob, "जन्म तिथि" if lang == "hi" else "", type="date"),
            f("pan", "PAN", p.pan, "पैन" if lang == "hi" else "", type="pan"),
            f("marital_status", "Marital status", t("married" if s.person_idx % 2 else "single", lang), "वैवाहिक स्थिति" if lang == "hi" else "", type="choice"),
        ], "आवेदक" if lang == "hi" else "", width=880),
        sec("Employment & income", [
            f("employment_type", "Employment type", t("self_employed" if s.person_idx % 3 == 2 else "salaried", lang), "रोज़गार प्रकार" if lang == "hi" else ""),
            f("employer", "Employer / business", ["Infosys BPM", "Tata Motors", "Self — Qureshi Traders", "Apollo Tyres", "Self — Deshmukh Design"][s.person_idx % 5], "नियोक्ता" if lang == "hi" else "", required=False),
            _num_field("monthly_income", "Monthly income", inr(max(60000, p.income // 12)), "मासिक आय" if lang == "hi" else "", type="amount"),
            _num_field("existing_emi", "Existing EMI", inr(12500 if s.person_idx % 2 else 0), "मौजूदा ईएमआई" if lang == "hi" else "", type="amount", required=False),
            f("credit_score", "Credit score", str(720 + (s.person_idx * 7) % 90), "क्रेडिट स्कोर" if lang == "hi" else "", type="number"),
        ], "रोज़गार और आय" if lang == "hi" else "", row_h=78),
        sec("Loan request", [
            _num_field("loan_amount", "Loan amount", inr(amount), "ऋण राशि" if lang == "hi" else "", type="amount"),
            f("tenure_months", "Tenure (months)", str([60, 84, 120, 48][s.person_idx % 4]), "अवधि" if lang == "hi" else "", type="number"),
            f("purpose", "Purpose", t(["home_renovation", "education", "business_expansion", "vehicle"][s.person_idx % 4], lang), "उद्देश्य" if lang == "hi" else ""),
            f("collateral", "Collateral", t("residential" if s.person_idx % 2 else "fixed_deposit", lang), "संपार्श्विक" if lang == "hi" else ""),
        ], "ऋण अनुरोध" if lang == "hi" else "", row_h=78),
        sec("Property & branch", [
            f("property_address", "Property / collateral address", address(p, lang), "संपत्ति का पता" if lang == "hi" else "", full=True, font_size=21),
            f("branch", "Processing branch", f"Meridian — {CITIES[p.city]['en']}", "शाखा" if lang == "hi" else ""),
            f("contact", "Contact number", p.mobile, "संपर्क" if lang == "hi" else "", type="phone"),
        ], "संपत्ति और शाखा" if lang == "hi" else "", row_h=76),
    ]
    form.photo_box(1000, 335, 168, 218)
    form.summary_box(1000, 1350, 168, 96, "Credit score", str(720 + (s.person_idx * 7) % 90), "CIBIL · 300–900")
    form.stamp(1000, 1500, "BRANCH RECEIVED", "RETAIL LENDING")
    return form, sections


def _invoice_items(s: Sample):
    catalog = [
        ("Cotton bed linen set — king", "6302", 24, 3250),
        ("Handloom cushion covers (pair)", "6304", 40, 780),
        ("Terry towels 600 GSM", "6302", 60, 640),
        ("Organic cotton fabric (metre)", "5208", 120, 410),
        ("Table runner set of 6", "6304", 18, 1150),
    ]
    start = s.person_idx % 3
    items = [catalog[(start + i) % len(catalog)] for i in range(3)]
    return items


def build_invoice(s: Sample) -> tuple[Form, list[SectionSpec]]:
    p = s.person
    lang = s.lang
    form = Form(*BRAND["invoice"], rtl=s.rtl)
    form.header(f"ST/INV/{s.sequence}", "07 NOV 2026", "ST")
    form.title(TITLE_BY_LANG["invoice"][lang], "Sundaram Textiles Pvt. Ltd. · GSTIN 33AAACS1234F1Z5",
               f"AK-26-{s.sequence}", "07 Nov 2026")
    form.watermark()
    form.paper_artifacts()
    items = _invoice_items(s)
    subtotal = sum(qty * rate for _, _, qty, rate in items)
    cgst = round(subtotal * 0.09, 2)
    sgst = round(subtotal * 0.09, 2)
    total = round(subtotal + cgst + sgst, 2)
    details = sec("Invoice details", [
        f("vendor_name", "Supplier", "Sundaram Textiles Pvt. Ltd.", "आपूर्तिकर्ता" if lang == "hi" else ""),
        f("vendor_gstin", "Supplier GSTIN", "33AAACS1234F1Z5", "जीएसटीआईएन" if lang == "hi" else "", type="gstin"),
        f("invoice_no", "Invoice number", f"ST/2026/00{4100 + s.sequence % 100}", "चालान संख्या" if lang == "hi" else "", type="id"),
        f("invoice_date", "Invoice date", "04/11/2026", "चालान तिथि" if lang == "hi" else "", type="date"),
        f("bill_to", "Billed to", s.bill_to or "Meridian Retail Ltd.", "ग्राहक" if lang == "hi" else "", full=True),
        f("po_number", "Purchase order", f"PO-{7781 + s.person_idx}", "खरीद आदेश" if lang == "hi" else "", required=False),
        f("due_date", "Payment due", "18/11/2026", "भुगतान तिथि" if lang == "hi" else "", type="date"),
    ], "चालान विवरण" if lang == "hi" else "", row_h=78)
    y = form.section(300, details)
    form.section_title = "Line items"
    y = form.start_section(max(704, y + 10), "Line items", "वस्तु विवरण" if lang == "hi" else "")
    rows = []
    for i, (desc, hsn, qty, rate) in enumerate(items):
        rows.append({
            "cells": [desc, hsn, str(qty), inr(rate), inr(qty * rate)],
            "keys": [f"item{i+1}_desc", f"item{i+1}_hsn", f"item{i+1}_qty", f"item{i+1}_rate", f"item{i+1}_amount"],
        })
    table_y = form.table(MARGIN, y, CONTENT_W,
                         [("Description", 0.44, "left"), ("HSN", 0.10, "left"),
                          ("Qty", 0.08, "right"), ("Rate", 0.17, "right"),
                          ("Amount", 0.21, "right")],
                         rows, row_h=42)
    form.section_title = "Totals"
    totals = [
        ("subtotal", "Subtotal", inr(subtotal, True), "Before GST", MARGIN, table_y + 22, 520, 92),
        ("cgst", "CGST 9%", inr(cgst, True), "", MARGIN + 538, table_y + 22, 300, 92),
        ("sgst", "SGST 9%", inr(sgst, True), "", MARGIN + 856, table_y + 22, 240, 92),
        ("total", "Total payable", inr(total, True),
         "Amount in words: Rupees " + _words(int(total)) + " only",
         MARGIN, table_y + 126, 760, 78),
    ]
    for key, label, value, sub, x, y0, w, h in totals:
        form.summary_box(x, y0, w, h, label, value, sub,
                         fill="#EFE9D8" if key == "total" else "#F4F1E8",
                         value_id=key, value_size=20 if key == "total" else 22)
        form.fields.append({
            "key": key, "label": label, "label_sub": "", "type": "amount",
            "required": True, "options": [], "section": "Totals", "dir": "ltr",
            "confidence": 0.96, "error": None, "truth": value,
            "rect": [x + 16, y0 + 32, w - 32, 34],
        })
    payment = sec("Payment details", [
        f("bank_account", "Bank account", "5010023456789", "बैंक खाता" if lang == "hi" else "", type="account"),
        f("ifsc", "IFSC", "BMER0001234", "आईएफएससी" if lang == "hi" else "", type="ifsc"),
        f("payment_terms", "Payment terms", "NEFT / RTGS within 14 days", "भुगतान शर्तें" if lang == "hi" else "", full=True, required=False),
    ], "भुगतान विवरण" if lang == "hi" else "", row_h=68)
    form.section(table_y + 250, payment)
    return form, []


def _words(n: int) -> str:
    ones = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    if n < 20:
        return ones[n]
    if n < 100:
        return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
    if n < 1000:
        return ones[n // 100] + " Hundred" + (" " + _words(n % 100) if n % 100 else "")
    if n < 100000:
        return _words(n // 1000) + " Thousand" + (" " + _words(n % 1000) if n % 1000 else "")
    if n < 10000000:
        return _words(n // 100000) + " Lakh" + (" " + _words(n % 100000) if n % 100000 else "")
    return _words(n // 10000000) + " Crore" + (" " + _words(n % 10000000) if n % 10000000 else "")


def build_kyc(s: Sample) -> tuple[Form, list[SectionSpec]]:
    p = s.person
    lang = s.lang
    form = Form(*BRAND["kyc"], rtl=s.rtl)
    form.header(f"BM/KYC/{s.sequence}", "07 NOV 2026", "BM")
    form.title(TITLE_BY_LANG["kyc"][lang], "Periodic KYC · re-verification",
               f"AK-26-{s.sequence}", "07 Nov 2026")
    form.watermark()
    form.paper_artifacts()
    id_type = t(["aadhaar", "pan", "voter"][s.person_idx % 3], lang)
    sections = [
        sec("Identity", [
            f("full_name", "Full name", name(p, lang), "पूरा नाम" if lang == "hi" else ""),
            f("dob", "Date of birth", p.dob, "जन्म तिथि" if lang == "hi" else "", type="date"),
            f("id_type", "ID document", id_type, "पहचान पत्र" if lang == "hi" else ""),
            f("id_number", "ID number", f"{p.aadhaar} {6734 + s.person_idx} {9000 + s.sequence % 900}", "पहचान संख्या" if lang == "hi" else "", type="id"),
            f("pan", "PAN", p.pan, "पैन" if lang == "hi" else "", type="pan"),
        ], "पहचान" if lang == "hi" else "", width=880),
        sec("Address & contact", [
            f("address", "Residential address", address(p, lang), "निवास पता" if lang == "hi" else "", full=True, font_size=21),
            f("city", "City", CITIES[p.city][lang], "शहर" if lang == "hi" else ""),
            f("pincode", "PIN code", p.pin, "पिन कोड" if lang == "hi" else "", type="pincode"),
            f("mobile", "Mobile number", p.mobile, "मोबाइल" if lang == "hi" else "", type="phone"),
            f("email", "Email address", p.email, "ईमेल" if lang == "hi" else "", type="email", required=False),
        ], "पता और संपर्क" if lang == "hi" else ""),
        sec("Profile", [
            f("occupation", "Occupation", t("salaried" if s.person_idx % 2 else "self_employed", lang), "व्यवसाय" if lang == "hi" else ""),
            _num_field("annual_income", "Annual income", inr(p.income), "वार्षिक आय" if lang == "hi" else "", type="amount"),
            f("update_reason", "Reason for update", "Address and contact details changed", "अद्यतन का कारण" if lang == "hi" else "", full=True),
        ], "प्रोफ़ाइल" if lang == "hi" else "", row_h=78),
        sec("Verification", [
            f("verified_by", "Verified by", "Branch operations", "सत्यापनकर्ता" if lang == "hi" else ""),
            f("declaration", "Customer declaration", "Confirmed", "ग्राहक घोषणा" if lang == "hi" else "", type="consent"),
        ], "सत्यापन" if lang == "hi" else "", row_h=76),
    ]
    if s.rtl:
        for section in sections:
            section.width = 880
        form.id_card(72, 335, 168, 96, id_type, p.aadhaar, name(p, lang))
        form.photo_box(72, 442, 168, 166)
        form.stamp(72, 1500, "KYC VERIFIED", "BRANCH OPERATIONS")
    else:
        form.id_card(1000, 335, 168, 96, id_type, p.aadhaar, name(p, lang))
        form.photo_box(1000, 442, 168, 166)
        form.stamp(1000, 1500, "KYC VERIFIED", "BRANCH OPERATIONS")
    return form, sections


BUILDERS = {"bank": build_bank, "claim": build_claim, "service": build_service,
            "loan": build_loan, "invoice": build_invoice, "kyc": build_kyc}


# --------------------------------------------------------------------------- OCR simulation
def _mutate(value: str, kind: str | None) -> str:
    if not kind or not value:
        return value
    if kind == "blank":
        return ""
    if kind == "name":
        return value[:-1] if len(value) > 3 else value
    if kind == "date":
        for ch in ("0", "1"):
            if ch in value:
                return value.replace(ch, "O" if ch == "0" else "l", 1)
        return value[:-1]
    if kind == "phone":
        return value.replace("0", "O", 1) if "0" in value else value[:-1] + "8"
    if kind == "amount":
        return value.replace("0", "O", 2)
    if kind == "digit":
        for ch in ("0", "1", "5"):
            if ch in value:
                return value.replace(ch, {"0": "O", "1": "l", "5": "S"}[ch], 1)
        return value[:-1] + "8"
    if kind == "ifsc":
        return value.replace("0", "O", 1)
    if kind == "total_mismatch":
        # Move ₹ 10,000 into the total so cross-field validation fails.
        try:
            amount = float(value.replace("₹", "").replace(",", "").strip())
        except ValueError:
            return value
        return inr(amount + 10000, True)
    return value


def confidence_for(s: Sample, key: str, base_values=None) -> float:
    if key in s.low:
        return s.low[key][0]
    rnd = random.Random(f"conf:{s.id}:{key}")
    if s.quality == "good":
        return round(rnd.uniform(0.945, 0.994), 3)
    if s.quality == "fair":
        return round(rnd.uniform(0.83, 0.965), 3)
    return round(rnd.uniform(0.61, 0.855), 3)


def build_sample(s: Sample):
    form, sections = BUILDERS[s.kind](s)
    form.y = 300
    y = 300
    for section in sections:
        y = form.section(y, section)
    # Some templates place custom content and sections manually.
    if s.kind == "invoice":
        # The invoice template already rendered sections and custom content;
        # the builder returns a section list that is not flow-rendered twice.
        pass
    form.footer(f"AK-26-{s.sequence}")
    fields = []
    for fld in form.fields:
        truth = fld.get("truth", "")
        kind = s.low.get(fld["key"], (None, None))[1]
        ocr = _mutate(truth, kind)
        conf = confidence_for(s, fld["key"])
        if kind and kind != "blank" and ocr == truth:
            conf = min(conf, 0.69)
        fields.append({
            "key": fld["key"],
            "label": fld["label"],
            "label_sub": fld.get("label_sub", ""),
            "section": fld.get("section", ""),
            "type": fld.get("type", "text"),
            "required": bool(fld.get("required", True)),
            "options": fld.get("options", []),
            "value": ocr,
            "truth": truth,
            "confidence": round(conf, 3),
            "dir": "rtl" if s.rtl and any(ord(c) > 127 for c in ocr) else "ltr",
            "corrected": False,
        })
    # Preserve metadata ordering by section appearance.
    pages = [{"no": 1, "file": f"{s.id}.jpg", "width": PAGE_W, "height": PAGE_H}]
    meta = {
        "id": s.id,
        "kind": s.kind,
        "ref": f"AK-26-{s.sequence}",
        "title": TITLE_BY_LANG[s.kind][s.lang],
        "customer_name": name(s.person, s.lang),
        "language": s.lang,
        "language_name": LANG_NAMES[s.lang],
        "script": SCRIPT_NAMES[s.lang],
        "quality": s.quality,
        "status": s.status,
        "priority": s.priority,
        "submitted_minutes": s.submitted_minutes,
        "assignee": s.assignee,
        "reviewer": s.reviewer,
        "reviewed_after": s.reviewed_after,
        "amount": s.amount,
        "note": s.note,
        "reject_reason": s.reject_reason,
        "escalation_reason": s.escalation_reason,
        "rescan_reason": s.rescan_reason,
        "sequence": s.sequence,
        "pages": pages,
        "field_ocr": fields,
    }
    return form, meta
