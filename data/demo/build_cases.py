"""Generate only original, fictional educational drafts. No clinical validation implied."""

import json
from pathlib import Path

ROOT = Path(__file__).parent


def tr(en, ur, roman):
    return {"en": en, "ur": ur, "roman": roman}


def fact(case_id, topic, words, texts):
    return {
        "id": f"{case_id}-{topic}",
        "topic": topic,
        "keywords": tr(*words),
        "text": tr(*texts),
        "disclosure": "on_question",
    }


KW = {
    "priority": (
        ["priority", "important", "want", "goal", "matter"],
        ["ترجیح", "اہم", "چاہ", "مقصد"],
        ["tarjeeh", "ahm", "chahti", "chahta", "maqsad"],
    ),
    "activity": (
        ["activity", "dress", "daily", "routine", "task", "work"],
        ["سرگرمی", "کپڑے", "روز", "معمول", "کام"],
        ["sargarmi", "kapray", "roz", "mamool", "kaam"],
    ),
    "support": (
        ["help", "family", "support", "live", "household"],
        ["مدد", "خاندان", "ساتھ", "رہتی", "رہتے"],
        ["madad", "khandan", "sath", "rehti", "rehta"],
    ),
    "environment": (
        ["room", "home", "chair", "environment", "desk", "space", "stairs", "access"],
        ["کمرہ", "گھر", "کرسی", "ماحول", "میز", "جگہ", "سیڑھی"],
        ["kamra", "ghar", "kursi", "mahol", "mez", "jagah", "seerhi"],
    ),
    "resources": (
        ["equipment", "money", "cost", "resources", "budget", "available"],
        ["سامان", "پیسے", "خرچ", "وسائل", "بجٹ", "دستیاب"],
        ["saman", "paisay", "kharch", "wasail", "budget", "dastiyab"],
    ),
    "uncertainty": (
        ["pain", "strength", "measurement", "diagnosis", "restriction", "medical", "test"],
        ["درد", "طاقت", "پیمائش", "تشخیص", "پابندی", "طبی", "ٹیسٹ"],
        ["dard", "taqat", "pemaish", "tashkhees", "pabandi", "tibbi", "test"],
    ),
}

RUBRIC_WORDS = {
    "interviewing": tr(
        ["important", "priority", "routine", "support", "prefer", "ask"],
        ["اہم", "ترجیح", "معمول", "مدد", "پسند", "پوچھ"],
        ["ahm", "tarjeeh", "mamool", "madad", "pasand", "pooch"],
    ),
    "goals": tr(
        ["goal", "priority", "dress", "work", "tea", "travel", "independent", "minutes"],
        ["مقصد", "ترجیح", "کپڑے", "کام", "چائے", "سفر", "خود", "منٹ"],
        ["maqsad", "tarjeeh", "kapray", "kaam", "chai", "safar", "khud", "minute"],
    ),
    "environment": tr(
        ["chair", "desk", "space", "shelf", "cable", "door", "image", "observe", "measure"],
        ["کرسی", "میز", "جگہ", "شیلف", "تار", "دروازہ", "تصویر", "دیکھ", "پیمائش"],
        ["kursi", "mez", "jagah", "shelf", "taar", "darwaza", "tasveer", "dekh", "pemaish"],
    ),
    "rationale": tr(
        ["because", "priority", "evidence", "uncertain", "review", "check", "ask"],
        ["کیونکہ", "ترجیح", "شواہد", "غیر یقینی", "جائزہ", "جانچ", "پوچھ"],
        ["kyun", "tarjeeh", "shawahid", "ghair yaqini", "jaiza", "check", "pooch"],
    ),
}

SPECS = [
    {
        "id": "stroke-home",
        "title": "Ayesha: choosing a dressing routine",
        "summary": "A fictional adult after stroke wants to choose a workable morning dressing routine in a shared home.",
        "focus": "goals",
        "difficulty": "Foundation",
        "patient": {"name": "Ayesha", "age": 58, "occupation": "School librarian"},
        "asset": "room-home",
        "intro": tr(
            "I am Ayesha. Since my stroke, my morning routine takes more effort. Please ask about what I would like to do at home.",
            "میں عائشہ ہوں۔ فالج کے بعد صبح کے معمول میں زیادہ محنت لگتی ہے۔ براہ کرم پوچھیں کہ میں گھر میں کیا کرنا چاہتی ہوں۔",
            "Main Ayesha hoon. Falij ke baad subah ke mamool mein zyada mehnat lagti hai. Barah karam poochein ke main ghar mein kya karna chahti hoon.",
        ),
        "facts": [
            (
                "priority",
                (
                    "I want to choose my own clothes and put on a comfortable shirt before breakfast. That matters more to me than doing every household task alone.",
                    "میں ناشتے سے پہلے اپنے کپڑے چننا اور آرام دہ قمیض پہننا چاہتی ہوں۔ یہ میرے لیے گھر کا ہر کام اکیلے کرنے سے زیادہ اہم ہے۔",
                    "Main nashtay se pehle apne kapray chunna aur aaram deh qameez pehnna chahti hoon. Yeh mere liye ghar ka har kaam akelay karne se zyada ahm hai.",
                ),
            ),
            (
                "activity",
                (
                    "Buttons and arranging a sleeve are difficult. I usually dress while sitting on a chair. I have not tried a different sequence with an educator.",
                    "بٹن بند کرنا اور آستین درست کرنا مشکل ہے۔ میں عموماً کرسی پر بیٹھ کر کپڑے پہنتی ہوں۔ میں نے کسی معلم کے ساتھ مختلف ترتیب نہیں آزمائی۔",
                    "Button band karna aur aasteen durust karna mushkil hai. Main aam tor par kursi par baith kar kapray pehnti hoon. Main ne kisi moallim ke sath mukhtalif tarteeb nahin azmai.",
                ),
            ),
            (
                "support",
                (
                    "I share the flat with my sister. She can help in the morning, but I would like her to ask before taking over a task.",
                    "میں اپنی بہن کے ساتھ فلیٹ میں رہتی ہوں۔ وہ صبح مدد کر سکتی ہے، لیکن میں چاہتی ہوں کہ کام خود کرنے سے پہلے وہ مجھ سے پوچھے۔",
                    "Main apni behen ke sath flat mein rehti hoon. Woh subah madad kar sakti hai, lekin main chahti hoon ke kaam khud karne se pehle woh mujh se poochay.",
                ),
            ),
            (
                "environment",
                (
                    "My clothes are on a shelf near the chair. The room illustration is only a schematic; its real clearances and furniture heights have not been measured.",
                    "میرے کپڑے کرسی کے قریب شیلف پر ہیں۔ کمرے کی تصویر صرف خاکہ ہے؛ اصل راستے کی چوڑائی اور فرنیچر کی اونچائی نہیں ناپی گئی۔",
                    "Mere kapray kursi ke qareeb shelf par hain. Kamray ki tasveer sirf khaka hai; asal rastay ki chorai aur furniture ki oonchai nahin napi gai.",
                ),
            ),
            (
                "resources",
                (
                    "We already have the chair and shelf. I prefer trying a small change to the routine before buying equipment. My spending limit has not been decided.",
                    "ہمارے پاس کرسی اور شیلف پہلے سے ہیں۔ میں سامان خریدنے سے پہلے معمول میں چھوٹی تبدیلی آزمانا پسند کرتی ہوں۔ خرچ کی حد ابھی طے نہیں ہوئی۔",
                    "Hamare paas kursi aur shelf pehle se hain. Main saman khareedne se pehle mamool mein chhoti tabdeeli azmana pasand karti hoon. Kharch ki had abhi tay nahin hui.",
                ),
            ),
            (
                "uncertainty",
                (
                    "This case does not provide test scores, exact strength or medical restrictions. Please record those as unknown and ask a supervising educator what assessment information would be needed.",
                    "اس کیس میں ٹیسٹ کے اسکور، درست طاقت یا طبی پابندیاں نہیں دی گئیں۔ انہیں نامعلوم لکھیں اور نگران معلم سے پوچھیں کہ جانچ کی کون سی معلومات درکار ہوں گی۔",
                    "Is case mein test ke score, durust taqat ya tibbi pabandiyan nahin di gain. Inhein namaloom likhein aur nigran moallim se poochein ke jaanch ki kaun si maloomat darkar hongi.",
                ),
            ),
        ],
    },
    {
        "id": "stroke-community",
        "title": "Bilal: planning a journey with his child",
        "summary": "A fictional adult after stroke describes a valued community routine and asks the learner to identify missing information.",
        "focus": "interviewing",
        "difficulty": "Intermediate",
        "patient": {"name": "Bilal", "age": 46, "occupation": "Accountant"},
        "asset": "room-home",
        "intro": tr(
            "I am Bilal. After my stroke, I am rebuilding my usual routines. I would like to discuss a journey that matters to my family.",
            "میں بلال ہوں۔ فالج کے بعد میں اپنے معمولات دوبارہ بنا رہا ہوں۔ میں ایک ایسے سفر پر بات کرنا چاہتا ہوں جو میرے خاندان کے لیے اہم ہے۔",
            "Main Bilal hoon. Falij ke baad main apne mamoolat dobara bana raha hoon. Main aik aisay safar par baat karna chahta hoon jo mere khandan ke liye ahm hai.",
        ),
        "facts": [
            (
                "priority",
                (
                    "I want to take my child to the nearby library on Saturday. I value spending time together more than returning to a full workday immediately.",
                    "میں ہفتے کے دن اپنے بچے کو قریب کی لائبریری لے جانا چاہتا ہوں۔ فوراً پورے دن کام پر واپس جانے سے زیادہ میرے لیے ساتھ وقت گزارنا اہم ہے۔",
                    "Main haftay ke din apne bachay ko qareeb ki library le jana chahta hoon. Foran pooray din kaam par wapas jane se zyada mere liye sath waqt guzarna ahm hai.",
                ),
            ),
            (
                "activity",
                (
                    "The journey involves leaving our flat, reaching the street and using a bus or arranging a ride. I have not described the complete route yet.",
                    "سفر میں فلیٹ سے نکلنا، سڑک تک پہنچنا اور بس لینا یا سواری کا انتظام کرنا شامل ہے۔ میں نے ابھی پورا راستہ نہیں بتایا۔",
                    "Safar mein flat se nikalna, sarak tak pohanchna aur bus lena ya sawari ka intizam karna shamil hai. Main ne abhi poora rasta nahin bataya.",
                ),
            ),
            (
                "support",
                (
                    "My partner can come with us if we plan ahead. My child is not expected to provide physical assistance.",
                    "پہلے منصوبہ بنانے پر میری شریک حیات ہمارے ساتھ آ سکتی ہے۔ میرے بچے سے جسمانی مدد کی توقع نہیں ہے۔",
                    "Pehle mansooba banane par meri shareek e hayat hamare sath aa sakti hai. Mere bachay se jismani madad ki tawaqqo nahin hai.",
                ),
            ),
            (
                "environment",
                (
                    "Our flat has a shared entrance. The provided room image does not show the street, bus stop or library, so those conditions remain unknown.",
                    "ہمارے فلیٹ کا داخلی راستہ مشترک ہے۔ دی گئی کمرے کی تصویر میں سڑک، بس اسٹاپ یا لائبریری نہیں ہے، اس لیے وہاں کی حالت نامعلوم ہے۔",
                    "Hamare flat ka dakhli rasta mushtarik hai. Di gai kamray ki tasveer mein sarak, bus stop ya library nahin hai, is liye wahan ki halat namaloom hai.",
                ),
            ),
            (
                "resources",
                (
                    "We can consider a bus or a paid ride. Cost and availability need to be discussed with me; please do not assume either option is feasible.",
                    "ہم بس یا کرائے کی سواری پر غور کر سکتے ہیں۔ خرچ اور دستیابی پر مجھ سے بات کرنا ضروری ہے؛ کسی بھی طریقے کو خود بخود قابل عمل نہ سمجھیں۔",
                    "Hum bus ya kiraye ki sawari par ghour kar saktay hain. Kharch aur dastiyabi par mujh se baat karna zaroori hai; kisi bhi tareeqay ko khud ba khud qabil e amal na samjhein.",
                ),
            ),
            (
                "uncertainty",
                (
                    "This scenario has no measured walking endurance or transport assessment. Those facts cannot be inferred from the room picture or my diagnosis.",
                    "اس منظرنامے میں پیدل چلنے کی برداشت یا سفر کی جانچ کی پیمائش نہیں ہے۔ یہ باتیں کمرے کی تصویر یا میری تشخیص سے اخذ نہیں کی جا سکتیں۔",
                    "Is manzarnamay mein paidal chalne ki bardasht ya safar ki jaanch ki pemaish nahin hai. Yeh batein kamray ki tasveer ya meri tashkhees se akhaz nahin ki ja sakteen.",
                ),
            ),
        ],
    },
    {
        "id": "hand-work",
        "title": "Farah: returning to repair tasks",
        "summary": "A fictional technician recovering from a hand injury discusses her priorities and staged workstation.",
        "focus": "environment",
        "difficulty": "Intermediate",
        "patient": {"name": "Farah", "age": 34, "occupation": "Electronics repair technician"},
        "asset": "room-work",
        "intro": tr(
            "I am Farah. I am recovering from a hand injury and want to discuss a gradual return to some repair tasks.",
            "میں فرح ہوں۔ ہاتھ کی چوٹ سے صحت یاب ہو رہی ہوں اور مرمت کے کچھ کاموں میں بتدریج واپسی پر بات کرنا چاہتی ہوں۔",
            "Main Farah hoon. Haath ki chot se sehatyab ho rahi hoon aur murammat ke kuch kaamon mein batadreej wapsi par baat karna chahti hoon.",
        ),
        "facts": [
            (
                "priority",
                (
                    "I want to sort parts and complete the written repair log before trying precision tools again. I want to remain involved in my business.",
                    "میں باریک اوزار دوبارہ استعمال کرنے سے پہلے پرزے ترتیب دینا اور مرمت کا تحریری ریکارڈ مکمل کرنا چاہتی ہوں۔ میں اپنے کاروبار میں شامل رہنا چاہتی ہوں۔",
                    "Main bareek auzar dobara istemal karne se pehle purzay tarteeb dena aur murammat ka tehreeri record mukammal karna chahti hoon. Main apne karobar mein shamil rehna chahti hoon.",
                ),
            ),
            (
                "activity",
                (
                    "My usual tasks include sorting small parts, typing notes and handling tools. My left hand was injured. No permitted load or movement limit is supplied in this case.",
                    "میرے کام میں چھوٹے پرزے ترتیب دینا، نوٹ ٹائپ کرنا اور اوزار سنبھالنا شامل ہیں۔ میرے بائیں ہاتھ کو چوٹ لگی تھی۔ اس کیس میں وزن یا حرکت کی اجازت کی حد نہیں دی گئی۔",
                    "Mere kaam mein chhotay purzay tarteeb dena, note type karna aur auzar sambhalna shamil hain. Mere baein haath ko chot lagi thi. Is case mein wazan ya harkat ki ijazat ki had nahin di gai.",
                ),
            ),
            (
                "support",
                (
                    "A colleague can handle precision repairs temporarily. I prefer agreeing on roles together instead of being removed from all tasks.",
                    "ایک ساتھی عارضی طور پر باریک مرمت کا کام کر سکتا ہے۔ میں تمام کاموں سے الگ ہونے کے بجائے مل کر ذمہ داریاں طے کرنا پسند کرتی ہوں۔",
                    "Aik sathi aarzi tor par bareek murammat ka kaam kar sakta hai. Main tamam kaamon se alag hone ke bajaye mil kar zimmedariyan tay karna pasand karti hoon.",
                ),
            ),
            (
                "environment",
                (
                    "Parts are on the shelf and the desk has a computer and tools. The drawing shows a cable on the floor but cannot establish actual trip risk or reachable distances.",
                    "پرزے شیلف پر ہیں اور میز پر کمپیوٹر اور اوزار ہیں۔ خاکے میں فرش پر تار دکھائی گئی ہے لیکن اس سے ٹھوکر کا اصل خطرہ یا پہنچنے کا فاصلہ ثابت نہیں ہوتا۔",
                    "Purzay shelf par hain aur mez par computer aur auzar hain. Khakay mein farsh par taar dikhai gai hai lekin is se thokar ka asal khatra ya pohanchne ka fasla sabit nahin hota.",
                ),
            ),
            (
                "resources",
                (
                    "We can rearrange the existing desk with permission. I have not agreed to purchase a device or disclose a budget yet.",
                    "اجازت سے موجودہ میز کی ترتیب بدل سکتے ہیں۔ میں نے ابھی کوئی آلہ خریدنے یا بجٹ بتانے پر اتفاق نہیں کیا۔",
                    "Ijazat se mojooda mez ki tarteeb badal saktay hain. Main ne abhi koi aala khareedne ya budget batane par ittefaq nahin kiya.",
                ),
            ),
            (
                "uncertainty",
                (
                    "Medical clearance, sensation, healing stage and task tolerance are unknown here. A learner should identify the missing information, not prescribe exercises or loads.",
                    "یہاں طبی اجازت، حس، زخم بھرنے کا مرحلہ اور کام کی برداشت نامعلوم ہیں۔ طالب علم کو گمشدہ معلومات پہچاننی چاہییں، ورزش یا وزن تجویز نہیں کرنا چاہیے۔",
                    "Yahan tibbi ijazat, hiss, zakhm bharne ka marhala aur kaam ki bardasht namaloom hain. Talib e ilm ko gumshuda maloomat pehchanni chahiye, warzish ya wazan tajweez nahin karna chahiye.",
                ),
            ),
        ],
    },
    {
        "id": "desk-return",
        "title": "Nadeem: shaping a manageable workday",
        "summary": "A fictional office administrator after shoulder surgery discusses work participation and an adaptable desk routine.",
        "focus": "rationale",
        "difficulty": "Intermediate",
        "patient": {"name": "Nadeem", "age": 51, "occupation": "Office administrator"},
        "asset": "room-work",
        "intro": tr(
            "I am Nadeem. After shoulder surgery, I would like to discuss which parts of my office routine matter most to me.",
            "میں ندیم ہوں۔ کندھے کی سرجری کے بعد میں بات کرنا چاہتا ہوں کہ دفتری معمول کے کون سے حصے میرے لیے سب سے اہم ہیں۔",
            "Main Nadeem hoon. Kandhay ki surgery ke baad main baat karna chahta hoon ke daftari mamool ke kaun se hissay mere liye sab se ahm hain.",
        ),
        "facts": [
            (
                "priority",
                (
                    "I want to answer important emails and coordinate colleagues for a manageable period. A full day at my usual speed is not my first priority.",
                    "میں قابل برداشت وقت کے لیے اہم ای میل کا جواب دینا اور ساتھیوں کے کام میں رابطہ کرنا چاہتا ہوں۔ معمول کی رفتار سے پورا دن کام کرنا میری پہلی ترجیح نہیں۔",
                    "Main qabil e bardasht waqt ke liye ahm email ka jawab dena aur sathiyon ke kaam mein rabta karna chahta hoon. Mamool ki raftaar se poora din kaam karna meri pehli tarjeeh nahin.",
                ),
            ),
            (
                "activity",
                (
                    "My routine includes typing, phone calls and reaching for files. I prefer alternating tasks, but we have not agreed a schedule or measured tolerance.",
                    "میرے معمول میں ٹائپ کرنا، فون کرنا اور فائلیں اٹھانا شامل ہے۔ میں کام بدل بدل کر کرنا پسند کرتا ہوں لیکن ابھی شیڈول طے یا برداشت ناپی نہیں گئی۔",
                    "Mere mamool mein type karna, phone karna aur files uthana shamil hai. Main kaam badal badal kar karna pasand karta hoon lekin abhi schedule tay ya bardasht napi nahin gai.",
                ),
            ),
            (
                "support",
                (
                    "My manager is open to discussing temporary duties. A colleague can retrieve files if we agree that arrangement.",
                    "میرا مینیجر عارضی ذمہ داریوں پر بات کرنے کے لیے تیار ہے۔ اتفاق ہونے پر ایک ساتھی فائلیں لا سکتا ہے۔",
                    "Mera manager aarzi zimmedariyon par baat karne ke liye tayyar hai. Ittefaq hone par aik sathi files la sakta hai.",
                ),
            ),
            (
                "environment",
                (
                    "The provided desk picture shows a chair, monitor, shelf and cable. It does not show measurements, chair adjustments or my working posture.",
                    "دی گئی میز کی تصویر میں کرسی، مانیٹر، شیلف اور تار ہیں۔ اس میں پیمائش، کرسی کی تبدیلیاں یا کام کرتے وقت میری حالت نہیں دکھائی گئی۔",
                    "Di gai mez ki tasveer mein kursi, monitor, shelf aur taar hain. Is mein pemaish, kursi ki tabdeeliyan ya kaam karte waqt meri halat nahin dikhai gai.",
                ),
            ),
            (
                "resources",
                (
                    "The employer can discuss rearranging current equipment. Please ask which changes are permitted and whether I would be comfortable with them.",
                    "آجر موجودہ سامان کی ترتیب بدلنے پر بات کر سکتا ہے۔ پوچھیں کہ کون سی تبدیلیوں کی اجازت ہے اور کیا میں ان سے مطمئن ہوں گا۔",
                    "Aajir mojooda saman ki tarteeb badalne par baat kar sakta hai. Poochein ke kaun si tabdeeliyon ki ijazat hai aur kya main in se mutmain hoon ga.",
                ),
            ),
            (
                "uncertainty",
                (
                    "Surgical restrictions and clinical assessment findings are not supplied. Neither an image nor a language model should invent clearance for a task.",
                    "سرجری کی پابندیاں اور طبی جانچ کے نتائج نہیں دیے گئے۔ تصویر یا زبان کا ماڈل کسی کام کی اجازت خود سے نہیں بنا سکتا۔",
                    "Surgery ki pabandiyan aur tibbi jaanch ke nataij nahin diye gaye. Tasveer ya zaban ka model kisi kaam ki ijazat khud se nahin bana sakta.",
                ),
            ),
        ],
    },
    {
        "id": "home-energy",
        "title": "Sana: making space for a valued home routine",
        "summary": "A fictional retired lecturer recovering after a leg fracture prioritizes tea with a friend and home participation.",
        "focus": "goals",
        "difficulty": "Foundation",
        "patient": {"name": "Sana", "age": 63, "occupation": "Retired lecturer"},
        "asset": "room-home",
        "intro": tr(
            "I am Sana. During recovery after a leg fracture, I want to discuss a home routine that gives me enjoyment and connection.",
            "میں ثنا ہوں۔ ٹانگ کے فریکچر سے صحت یابی کے دوران میں گھر کے ایک معمول پر بات کرنا چاہتی ہوں جو مجھے خوشی اور میل جول دیتا ہے۔",
            "Main Sana hoon. Taang ke fracture se sehatyabi ke dauran main ghar ke aik mamool par baat karna chahti hoon jo mujhe khushi aur mel jol deta hai.",
        ),
        "facts": [
            (
                "priority",
                (
                    "I want to prepare tea with a friend and sit together near my plants. I prefer chair seating and would like help only with parts we agree on.",
                    "میں ایک دوست کے ساتھ چائے تیار کرنا اور اپنے پودوں کے قریب ساتھ بیٹھنا چاہتی ہوں۔ میں کرسی پر بیٹھنا پسند کرتی ہوں اور صرف طے شدہ حصوں میں مدد چاہتی ہوں۔",
                    "Main aik dost ke sath chai tayyar karna aur apne podon ke qareeb sath baithna chahti hoon. Main kursi par baithna pasand karti hoon aur sirf tay shuda hisson mein madad chahti hoon.",
                ),
            ),
            (
                "activity",
                (
                    "Preparing tea involves several steps and carrying items. The case gives no permission to carry hot liquids or bear weight, so those decisions need supervising clinical information.",
                    "چائے بنانے میں کئی مراحل اور چیزیں اٹھانا شامل ہے۔ کیس میں گرم مشروب اٹھانے یا ٹانگ پر وزن ڈالنے کی اجازت نہیں دی گئی، اس لیے ان فیصلوں کے لیے نگران طبی معلومات درکار ہیں۔",
                    "Chai banane mein kai marahil aur cheezein uthana shamil hai. Case mein garam mashroob uthane ya taang par wazan dalne ki ijazat nahin di gai, is liye in faislon ke liye nigran tibbi maloomat darkar hain.",
                ),
            ),
            (
                "support",
                (
                    "I live alone and my friend visits by arrangement. My relatives live elsewhere. Please ask whom I want involved rather than assuming family help is available.",
                    "میں اکیلی رہتی ہوں اور طے کرنے پر میری دوست آتی ہے۔ میرے رشتہ دار دوسری جگہ رہتے ہیں۔ خاندان کی مدد فرض کرنے کے بجائے پوچھیں کہ میں کس کو شامل کرنا چاہتی ہوں۔",
                    "Main akeli rehti hoon aur tay karne par meri dost aati hai. Mere rishtedar doosri jagah rehtay hain. Khandan ki madad farz karne ke bajaye poochein ke main kis ko shamil karna chahti hoon.",
                ),
            ),
            (
                "environment",
                (
                    "The schematic shows a sitting room, not my kitchen. You can describe visible furniture, but the preparation area and route between rooms remain unknown.",
                    "خاکہ بیٹھنے کا کمرہ دکھاتا ہے، میرا باورچی خانہ نہیں۔ آپ دکھائی دینے والا فرنیچر بیان کر سکتے ہیں لیکن تیاری کی جگہ اور کمروں کے درمیان راستہ نامعلوم ہیں۔",
                    "Khaka baithne ka kamra dikhata hai, mera bawarchi khana nahin. Aap dikhai dene wala furniture bayan kar saktay hain lekin tayyari ki jagah aur kamron ke darmiyan rasta namaloom hain.",
                ),
            ),
            (
                "resources",
                (
                    "I have a chair and table. I would like to discuss changes using what I own. Equipment costs and purchasing preferences need to be asked.",
                    "میرے پاس کرسی اور میز ہیں۔ میں اپنے سامان کے ساتھ تبدیلیوں پر بات کرنا چاہتی ہوں۔ آلات کے خرچ اور خریداری کی پسند کے بارے میں پوچھنا ضروری ہے۔",
                    "Mere paas kursi aur mez hain. Main apne saman ke sath tabdeeliyon par baat karna chahti hoon. Aalat ke kharch aur khareedari ki pasand ke bare mein poochna zaroori hai.",
                ),
            ),
            (
                "uncertainty",
                (
                    "Weight-bearing restrictions, pain severity and walking capacity are unknown in this draft. Please state what further information is needed before choosing a plan.",
                    "اس مسودے میں ٹانگ پر وزن ڈالنے کی پابندیاں، درد کی شدت اور چلنے کی صلاحیت نامعلوم ہیں۔ منصوبہ چننے سے پہلے بتائیں کہ مزید کون سی معلومات درکار ہیں۔",
                    "Is musawwaday mein taang par wazan dalne ki pabandiyan, dard ki shiddat aur chalne ki salahiyat namaloom hain. Mansooba chunne se pehle batayein ke mazeed kaun si maloomat darkar hain.",
                ),
            ),
        ],
    },
]

ASSETS = {
    "room-home": {
        "id": "room-home",
        "url": "/api/v1/assets/room-home",
        "alt": "Original schematic of a room with a chair, clothing shelf, table and door; dimensions are illustrative.",
        "origin": "original schematic",
        "license": "CC0-1.0",
        "coordinate_system": "normalized_xywh",
        "annotations": [
            {
                "id": "home-chair",
                "label": "chair",
                "x": 0.16,
                "y": 0.40,
                "width": 0.22,
                "height": 0.38,
                "observation": "A chair is shown near the table. Seat height and stability are not measured.",
                "review_status": "pending_review",
            },
            {
                "id": "home-shelf",
                "label": "shelf",
                "x": 0.64,
                "y": 0.18,
                "width": 0.23,
                "height": 0.35,
                "observation": "A shelf with folded items is shown. Reach distance cannot be established from this schematic.",
                "review_status": "pending_review",
            },
            {
                "id": "home-table",
                "label": "table",
                "x": 0.43,
                "y": 0.56,
                "width": 0.21,
                "height": 0.21,
                "observation": "A table is shown in the room; clearances need actual measurement.",
                "review_status": "pending_review",
            },
        ],
    },
    "room-work": {
        "id": "room-work",
        "url": "/api/v1/assets/room-work",
        "alt": "Original schematic workstation with a desk, computer, chair, parts shelf and floor cable; no person or measured dimensions.",
        "origin": "original schematic",
        "license": "CC0-1.0",
        "coordinate_system": "normalized_xywh",
        "annotations": [
            {
                "id": "work-desk",
                "label": "desk",
                "x": 0.22,
                "y": 0.35,
                "width": 0.48,
                "height": 0.39,
                "observation": "A desk with a computer and small tools is shown. Work posture is not visible.",
                "review_status": "pending_review",
            },
            {
                "id": "work-chair",
                "label": "chair",
                "x": 0.38,
                "y": 0.57,
                "width": 0.18,
                "height": 0.32,
                "observation": "A chair is shown; adjustment and suitability are unknown.",
                "review_status": "pending_review",
            },
            {
                "id": "work-cable",
                "label": "cable",
                "x": 0.70,
                "y": 0.69,
                "width": 0.16,
                "height": 0.16,
                "observation": "A cable is drawn on the floor. Its location invites further questions but does not establish actual trip risk.",
                "review_status": "pending_review",
            },
        ],
    },
}

cases = []
for s in SPECS:
    cid = s["id"]
    evidence_id = f"{cid}-draft-reasoning"
    anchors = {
        "interviewing": "0: no relevant learner evidence; 1: identifies an activity; 2: elicits a stated priority and context; 3: checks priorities, support/preferences and missing information without assuming them.",
        "goals": "0: no functional goal; 1: names an activity; 2: links a goal to the patient's stated priority; 3: states an observable agreed activity, context and review criterion while marking missing feasibility information.",
        "environment": "0: no image observation; 1: describes a visible object; 2: connects an observation to a relevant task; 3: distinguishes observation, interpretation and missing measurements and asks for contextual confirmation.",
        "rationale": "0: no learner rationale; 1: gives a generic explanation; 2: connects the patient's priority to a proposed approach; 3: links priority and contextual evidence, records uncertainty, and proposes educator review rather than inventing clinical clearance.",
    }
    labels = {
        "interviewing": "Occupational interviewing",
        "goals": "Patient-prioritized functional goals",
        "environment": "Environmental reasoning",
        "rationale": "Reasoned educational plan",
    }
    fields = {
        "interviewing": "profile",
        "goals": "goals",
        "environment": "observations",
        "rationale": "rationale",
    }
    cases.append(
        {
            "id": cid,
            "version": 1,
            "title": s["title"],
            "summary": s["summary"],
            "introduction": s["intro"],
            "domain": "adult-physical-rehabilitation",
            "difficulty": s["difficulty"],
            "focus": s["focus"],
            "review_status": "pending_review",
            "estimated_minutes": 25,
            "patient": s["patient"],
            "facts": [fact(cid, topic, KW[topic], texts) for topic, texts in s["facts"]],
            "unknown_response": tr(
                "That information is not supplied in this fictional case. Please record it as unknown and say what you would ask or assess next.",
                "یہ معلومات اس فرضی کیس میں نہیں دی گئیں۔ اسے نامعلوم لکھیں اور بتائیں کہ آپ آگے کیا پوچھیں گے یا جانچیں گے۔",
                "Yeh maloomat is farzi case mein nahin di gain. Isay namaloom likhein aur batayein ke aap agay kya poochein ge ya jaanchein ge.",
            ),
            "objectives": [
                "Elicit the person's priorities and preferences without assumptions.",
                "Link a functional goal to patient-reported priorities and contextual observations.",
                "Distinguish visible observations from unmeasured interpretations.",
                "Record missing information and justify a provisional educational plan.",
            ],
            "rubric": [
                {
                    "dimension": d,
                    "label": labels[d],
                    "field": fields[d],
                    "anchor": anchors[d],
                    "max_score": 3,
                    "keywords": RUBRIC_WORDS[d],
                    "fact_ids": [f"{cid}-priority", f"{cid}-environment", f"{cid}-uncertainty"],
                    "reference_ids": [evidence_id],
                }
                for d in anchors
            ],
            "asset": ASSETS[s["asset"]],
            "evidence": [
                {
                    "id": evidence_id,
                    "title": "Draft educational reasoning note: confirm priorities and context",
                    "text": "For this fictional exercise, describe the person's stated priority, distinguish visible observations from interpretations, and record missing information before proposing a provisional goal. An educator must review this original draft before it is treated as approved educational reference content.",
                    "url": None,
                    "origin": "original educational draft",
                    "approved": False,
                }
            ],
            "eligible_demo": True,
            "review_note": None,
        }
    )
(ROOT / "cases.json").write_text(
    json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print(f"Wrote {len(cases)} fictional pending-review cases; no approved reference passages.")
