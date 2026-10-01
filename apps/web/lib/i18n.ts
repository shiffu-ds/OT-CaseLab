import type { Language } from './types';
const english = {
  dashboard: 'Practice studio', library: 'Case library', history: 'My learning', settings: 'Account & privacy',
  admin: 'Administration', educator: 'Educator workspace', signout: 'Sign out', welcome: 'Welcome back',
  start: 'Start this case', resume: 'Continue practice', back: 'Back to cases',
  interview: 'Interview', observe: 'Observe', plan: 'Build your plan', feedback: 'Feedback',
  save: 'Save draft', submit: 'Submit for feedback', send: 'Send message',
  profile: 'Occupational profile', observations: 'Environment observations', goals: 'Patient-prioritized goals', rationale: 'Intervention rationale',
  language: 'Practice language', loading: 'Loading your workspace…', name: 'Full name', email: 'Email address', password: 'Password',
  login: 'Sign in', register: 'Create student account', progress: 'Practice overview', cases: 'Explore cases',
  completed: 'Completed attempts', active: 'In progress', available: 'Available cases',
  pending: 'Pending educator review', reviewed: 'Educator reviewed', scripted: 'Scripted patient · baseline feedback',
  evidence: 'Evidence library', download: 'Download report', assistant: 'Request image assistance',
};
const urdu: typeof english = {
  dashboard: 'مشق کی جگہ', library: 'کیس لائبریری', history: 'میری پیش رفت', settings: 'اکاؤنٹ اور رازداری',
  admin: 'انتظامیہ', educator: 'استاد کا ورک اسپیس', signout: 'سائن آؤٹ', welcome: 'خوش آمدید',
  start: 'یہ کیس شروع کریں', resume: 'مشق جاری رکھیں', back: 'کیسز پر واپس جائیں',
  interview: 'انٹرویو', observe: 'مشاہدہ', plan: 'اپنا منصوبہ بنائیں', feedback: 'فیڈبیک',
  save: 'مسودہ محفوظ کریں', submit: 'فیڈبیک کے لیے جمع کریں', send: 'پیغام بھیجیں',
  profile: 'روزمرہ سرگرمیوں کا پروفائل', observations: 'ماحول کا مشاہدہ', goals: 'مریض کی ترجیحات پر مبنی اہداف', rationale: 'مداخلت کی وجہ',
  language: 'مشق کی زبان', loading: 'آپ کا ورک اسپیس کھل رہا ہے…', name: 'پورا نام', email: 'ای میل', password: 'پاس ورڈ',
  login: 'سائن ان', register: 'طالب علم کا اکاؤنٹ بنائیں', progress: 'مشق کی پیش رفت', cases: 'کیسز دیکھیں',
  completed: 'مکمل مشقیں', active: 'جاری مشقیں', available: 'دستیاب کیسز',
  pending: 'استاد کا جائزہ باقی ہے', reviewed: 'استاد نے جائزہ لیا', scripted: 'اسکرپٹڈ مریض · بنیادی فیڈبیک',
  evidence: 'حوالہ جات', download: 'رپورٹ ڈاؤن لوڈ کریں', assistant: 'تصویر کے تجزیے میں مدد لیں',
};
const roman: typeof english = {
  dashboard: 'Mashq ki jagah', library: 'Case library', history: 'Meri progress', settings: 'Account aur raazdari',
  admin: 'Intizaami workspace', educator: 'Ustad ka workspace', signout: 'Sign out', welcome: 'Khush aamdeed',
  start: 'Yeh case shuru karein', resume: 'Mashq jaari rakhein', back: 'Cases par wapas',
  interview: 'Interview', observe: 'Mushahida', plan: 'Apna plan banayein', feedback: 'Feedback',
  save: 'Draft save karein', submit: 'Feedback ke liye jama karein', send: 'Paigham bhejein',
  profile: 'Rozmarra sargarmiyon ka profile', observations: 'Mahol ka mushahida', goals: 'Patient ki tarjeehat par goals', rationale: 'Intervention ki wajah',
  language: 'Mashq ki zubaan', loading: 'Aap ka workspace khul raha hai…', name: 'Poora naam', email: 'Email address', password: 'Password',
  login: 'Sign in', register: 'Student account banayein', progress: 'Mashq ki progress', cases: 'Cases dekhein',
  completed: 'Mukammal attempts', active: 'Jaari mashq', available: 'Dastiyab cases',
  pending: 'Ustad ka review baqi hai', reviewed: 'Ustad ne review kiya', scripted: 'Scripted patient · baseline feedback',
  evidence: 'Hawala jaat', download: 'Report download karein', assistant: 'Tasveer ke tajziye mein madad lein',
};
export const translations = { en: english, ur: urdu, roman: roman };
export type Label = keyof typeof english;
export const translate = (language: Language, key: Label) => translations[language]?.[key] || english[key];
export const languageName = (language: Language) => ({ en: 'English', ur: 'اردو', roman: 'Roman Urdu' })[language];
