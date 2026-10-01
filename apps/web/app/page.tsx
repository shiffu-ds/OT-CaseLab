'use client';

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { ArrowDownToLine, ArrowLeft, ArrowRight, BookOpen, Check, CheckCircle2, ChevronRight, ClipboardList, Clock3, Eye, FileText, GraduationCap, HeartHandshake, Home, Image as ImageIcon, Layers3, LoaderCircle, LockKeyhole, LogOut, Menu, MessageCircle, Plus, Search, Send, Settings2, ShieldCheck, Sparkles, Target, Trash2, X } from 'lucide-react';
import { api, ApiError, json, printable } from '@/lib/api';
import { languageName, translate, type Label } from '@/lib/i18n';
import { emptyDraft, type Attempt, type Case, type Draft, type Evidence, type Feedback, type Job, type Language, type Progress, type Session, type User } from '@/lib/types';

type View = 'dashboard' | 'library' | 'history' | 'settings' | 'educator' | 'admin' | 'attempt';
type Step = 'interview' | 'observe' | 'plan' | 'feedback';
const icons = { dashboard: Home, library: Layers3, history: ClipboardList, settings: Settings2, educator: GraduationCap, admin: ShieldCheck };
const formatDate = (value: string) => new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'Asia/Karachi' }).format(new Date(value));
const humanize = (text: string) => String(text || '').replace(/[_-]/g, ' ');
const localize = (value: Case['introduction'], language: Language) => typeof value === 'string' ? value : value?.[language] || value?.en || '';
const isReviewed = (status: string) => ['reviewed', 'approved', 'published', 'educator_confirmed', 'educator_amended'].includes(status);

function LanguageSelect({ value, onChange, disabled = false }: { value: Language; onChange: (value: Language) => void; disabled?: boolean }) {
  return <label className="language-control"><span className="sr-only">Practice language</span><select aria-label="Practice language" value={value} disabled={disabled} onChange={e => onChange(e.target.value as Language)} dir="ltr"><option value="en">English</option><option value="ur">اردو</option><option value="roman">Roman Urdu</option></select></label>;
}
function Logo({ light = false }: { light?: boolean }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`}><span className="brand-mark"><HeartHandshake size={23} strokeWidth={1.7} /></span><span>OTCase<span className="brand-tail">Lab</span><small>LEARNING THROUGH PRACTICE</small></span></div>;
}
function Status({ value, language }: { value: string; language: Language }) {
  const reviewed = isReviewed(value);
  return <span className={`status ${reviewed ? 'status-good' : ''}`}><span />{translate(language, reviewed ? 'reviewed' : 'pending')}</span>;
}
function Button({ children, variant = 'primary', className = '', busy = false, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; busy?: boolean }) {
  return <button className={`button button-${variant} ${className}`} {...props} disabled={props.disabled || busy}>{busy && <LoaderCircle size={16} className="spin" />}{children}</button>;
}
function Empty({ icon = <BookOpen size={28} />, title, children }: { icon?: ReactNode; title: string; children: ReactNode }) {
  return <div className="empty-state"><span>{icon}</span><h3>{title}</h3><p>{children}</p></div>;
}

export default function Studio() {
  const [session, setSession] = useState<Session | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [language, setLanguage] = useState<Language>('en');
  const [view, setView] = useState<View>('dashboard');
  const [cases, setCases] = useState<Case[]>([]);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState<{ text: string; error: boolean } | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [step, setStep] = useState<Step>('interview');
  const t = (key: Label) => translate(language, key);
  const csrf = session?.csrf_token;
  const showError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401) { setSession(null); setAttempts([]); setCases([]); setProgress(null); setAttempt(null); setView('dashboard'); }
    setNotice({ text: error instanceof Error ? error.message : 'Something went wrong. Please try again.', error: true });
  };
  const success = (text: string) => setNotice({ text, error: false });

  useEffect(() => {
    api<Session>('/auth/me').then(data => { setSession(data); setLanguage(data.user.language); }).catch(error => { if (!(error instanceof ApiError && error.status === 401)) showError(error); }).finally(() => setAuthReady(true));
  }, []);
  useEffect(() => { document.documentElement.lang = language === 'ur' ? 'ur' : 'en'; document.documentElement.dir = language === 'ur' ? 'rtl' : 'ltr'; }, [language]);
  useEffect(() => { if (session) void refresh(); }, [session?.user.id]); // A session change reloads scoped server data.
  async function refresh() {
    setLoading(true);
    try {
      const results = await Promise.all([api<{ items: Case[] }>('/cases'), api<{ items: Attempt[] }>('/attempts'), api<Progress>('/progress')]);
      setCases(results[0].items); setAttempts(results[1].items); setProgress(results[2]);
    } catch (error) { showError(error); }
    finally { setLoading(false); }
  }
  async function changeLanguage(value: Language) {
    if (!session) { setLanguage(value); return; }
    setBusy('language');
    try { const updated = await api<Session>('/auth/me', json('PATCH', { language: value }), csrf); setSession(updated); setLanguage(updated.user.language); }
    catch (error) { showError(error); }
    finally { setBusy(''); }
  }
  async function startCase(caseId: string) {
    setBusy(caseId);
    try { const data = await api<Attempt>('/attempts', json('POST', { case_id: caseId, language }), csrf); setAttempt(data); setStep('interview'); setView('attempt'); await refresh(); }
    catch (error) { showError(error); }
    finally { setBusy(''); }
  }
  async function openAttempt(id: string) {
    setBusy(id);
    try { const data = await api<Attempt>(`/attempts/${id}`); setAttempt(data); setStep(data.feedback ? 'feedback' : 'interview'); setView('attempt'); }
    catch (error) { showError(error); }
    finally { setBusy(''); }
  }
  function navigate(next: View) { setView(next); setMobileOpen(false); setNotice(null); }
  async function signout() {
    setBusy('logout');
    try { await api('/auth/logout', json('POST'), csrf); setSession(null); setAttempts([]); setCases([]); setProgress(null); setAttempt(null); setView('dashboard'); }
    catch (error) { showError(error); }
    finally { setBusy(''); }
  }
  if (!authReady) return <div className="initial-loading"><Logo /><LoaderCircle className="spin" size={24} /><p>{t('loading')}</p></div>;
  if (!session) return <Auth language={language} onLanguage={changeLanguage} onSession={data => { setSession(data); setLanguage(data.user.language); setNotice(null); }} notice={notice} />;
  const firstName = session.user.name.split(' ')[0];
  const activeAttempts = attempts.filter(item => !item.feedback);
  return <div className="app-shell" dir={language === 'ur' ? 'rtl' : 'ltr'}>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    {mobileOpen && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <Logo />
      <div className="sidebar-label">YOUR WORKSPACE</div>
      <nav aria-label="Main navigation">{(['dashboard', 'library', 'history', ...(session.user.role !== 'student' ? ['educator'] : []), ...(session.user.role === 'admin' ? ['admin'] : []), 'settings'] as Exclude<View, 'attempt'>[]).map(item => { const Icon = icons[item]; return <button key={item} className={`nav-item ${view === item ? 'active' : ''}`} aria-current={view === item ? 'page' : undefined} onClick={() => navigate(item)}><Icon size={19} /><span>{t(item)}</span>{item === 'library' && <span className="nav-count" dir="ltr">{cases.length}</span>}</button>; })}</nav>
      <div className="sidebar-note"><div className="note-icon"><ShieldCheck size={20} /></div><strong>A space to practice.</strong><p>Fictional people. Real reasoning. Learn at your own pace.</p><span>Educational simulation</span></div>
      <div className="sidebar-footer"><div className="avatar">{session.user.name.slice(0, 1).toUpperCase()}</div><div><strong dir="auto">{session.user.name}</strong><small>{humanize(session.user.role)}</small></div><button title={t('signout')} aria-label={t('signout')} disabled={busy === 'logout'} onClick={signout}><LogOut size={18} /></button></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="topbar-start"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={21} /></button><span className="breadcrumb">Your workspace <ChevronRight size={14} /> <strong>{view === 'attempt' ? attempt?.case.title : t(view)}</strong></span></div><div className="topbar-end"><span className="demo-pill"><span />{humanize(session.mode || 'scripted demo')}</span><LanguageSelect value={language} onChange={changeLanguage} disabled={busy === 'language'} /></div></header>
      <main id="main-content" className={`main-content ${view === 'attempt' ? 'workbench-page' : ''}`}>
        {notice && <div className={`notice ${notice.error ? 'notice-error' : ''}`} role={notice.error ? 'alert' : 'status'}><span>{notice.text}</span><button aria-label="Dismiss notification" onClick={() => setNotice(null)}><X size={16} /></button></div>}
        {loading && <div className="sync-note" role="status"><LoaderCircle className="spin" size={14} />Updating from your saved workspace…</div>}
        {view === 'dashboard' && <>
          <div className="page-heading"><div><span className="eyebrow">THE PRACTICE STUDIO</span><h1>{t('welcome')}, <span dir="auto">{firstName}</span><span className="heading-dot">.</span></h1><p>Every thoughtful question is a step toward better reasoning.</p></div><span className="date-label" dir="ltr">{formatDate(new Date().toISOString())}</span></div>
          <section className="hero-card"><div className="hero-copy"><span className="hero-kicker"><span /> LEARN BY DOING</span><h2>See the person.<br />Understand the occupation.</h2><p>Interview a fictional patient, explore their environment, and connect what matters to a meaningful plan.</p><Button onClick={() => cases[0] && startCase(cases[0].id)} busy={busy === cases[0]?.id} disabled={!cases.length}>{cases.length ? 'Begin a practice case' : 'No cases available yet'}<ArrowRight size={18} /></Button><div className="hero-foot"><Clock3 size={14} />Text-based · At your own pace <span>EN / اردو / Roman Urdu</span></div></div><div className="hero-visual" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="visual-core"><HeartHandshake size={48} strokeWidth={1.2} /></div><div className="floating-label floating-interview"><MessageCircle size={18} /><span>Listen with curiosity<small>Patient interview</small></span></div><div className="floating-label floating-observe"><Eye size={18} /><span>Notice the context<small>Environment observations</small></span></div><div className="floating-label floating-goals"><Target size={18} /><span>Make it meaningful<small>Patient-prioritized goals</small></span></div><div className="visual-caption">PERSON · ENVIRONMENT · OCCUPATION</div></div></section>
          <div className="stats-grid"><Stat value={progress?.completed ?? attempts.filter(a => a.feedback).length} label={t('completed')} icon={<CheckCircle2 size={20} />} note="Build your learning record" /><Stat value={progress?.active ?? activeAttempts.length} label={t('active')} icon={<Clock3 size={20} />} note="Your drafts are saved on the server" /><Stat value={cases.length} label={t('available')} icon={<Layers3 size={20} />} note="Fictional adult rehabilitation cases" /></div>
          {activeAttempts.length > 0 && <section className="resume-strip"><div className="resume-icon"><FileText size={23} /></div><div><span className="eyebrow">PICK UP WHERE YOU LEFT OFF</span><h3 dir="auto">{activeAttempts[0].case.title}</h3><p>Started {formatDate(activeAttempts[0].created_at)} · {activeAttempts[0].messages.filter(m => m.role === 'student').length} interview questions</p></div><Button variant="secondary" busy={busy === activeAttempts[0].id} onClick={() => openAttempt(activeAttempts[0].id)}>{t('resume')}<ArrowRight size={16} /></Button></section>}
          <div className="section-heading"><div><h2>A new perspective, one case at a time</h2><p>Practice connecting patient priorities with everyday participation.</p></div><button className="text-button" onClick={() => navigate('library')}>View all cases<ArrowRight size={16} /></button></div>
          <div className="case-grid">{cases.slice(0, 3).map((item, index) => <CaseCard key={item.id} item={item} index={index} language={language} onStart={() => startCase(item.id)} busy={busy === item.id} />)}</div>
          {!loading && !cases.length && <Empty title="Your case library is waiting">An educator can publish a case from their workspace. Refresh to check for new cases.</Empty>}
          <div className="learning-note"><BookOpen size={20} /><p><strong>Focus on your reasoning.</strong> Patient dialogue and formative feedback are labelled by operating mode. Unreviewed cases remain pending educator review; scores are practice feedback.</p></div>
        </>}
        {view === 'library' && <CaseLibrary cases={cases} language={language} busy={busy} onStart={startCase} />}
        {view === 'history' && <Learning attempts={attempts} progress={progress} language={language} busy={busy} onOpen={openAttempt} onStart={startCase} />}
        {view === 'attempt' && attempt && <Workbench key={attempt.id} attempt={attempt} setAttempt={setAttempt} step={step} setStep={setStep} language={language} mode={session.mode} csrf={session.csrf_token} onError={showError} onSuccess={success} onBack={() => navigate('library')} onSubmitted={refresh} />}
        {view === 'settings' && <Privacy session={session} language={language} onLanguage={changeLanguage} onError={showError} onSuccess={success} onDeleted={() => { setSession(null); setAttempt(null); setCases([]); setAttempts([]); setView('dashboard'); }} />}
        {view === 'educator' && session.user.role !== 'student' && <Educator csrf={session.csrf_token} language={language} onError={showError} onSuccess={success} onPublished={refresh} />}
        {view === 'admin' && session.user.role === 'admin' && <Admin session={session} language={language} onError={showError} onSuccess={success} />}
      </main><footer className="main-footer"><span>OTCaseLab · Practice with purpose</span><span>Educational simulation · Fictional case data</span></footer>
    </div>
  </div>;
}

function Auth({ language, onLanguage, onSession, notice }: { language: Language; onLanguage: (value: Language) => void; onSession: (value: Session) => void; notice: { text: string; error: boolean } | null }) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const t = (key: Label) => translate(language, key);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { const data = await api<Session>(register ? '/auth/register' : '/auth/login', json('POST', register ? { email, password, name, language } : { email, password })); onSession(data); }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in. Please try again.'); }
    finally { setBusy(false); }
  }
  return <div className="auth-page" dir={language === 'ur' ? 'rtl' : 'ltr'}><section className="auth-story"><Logo light /><div className="auth-story-body"><span className="hero-kicker"><span /> OCCUPATIONAL THERAPY · LEARNING STUDIO</span><h1>Practice with<br /><em>purpose.</em></h1><p>Thoughtful questions. Everyday environments.<br />Plans that start with the person.</p><div className="auth-illustration" aria-hidden="true"><div className="auth-circle"><HeartHandshake size={66} strokeWidth={1} /></div><div className="auth-sticker"><CheckCircle2 size={18} /><span>Your reasoning matters.</span></div><span className="auth-small-orbit" /></div><div className="auth-steps"><div><MessageCircle size={19} /><strong>01</strong><span>Listen</span></div><div><Eye size={19} /><strong>02</strong><span>Observe</span></div><div><Target size={19} /><strong>03</strong><span>Connect</span></div></div></div><p className="auth-story-footer">A bilingual practice space for OT students and educators.</p></section><section className="auth-form-side"><div className="auth-top"><span className="demo-pill"><span /> Educational prototype</span><LanguageSelect value={language} onChange={onLanguage} /></div><div className="auth-form-box"><span className="eyebrow">YOUR NEXT STEP STARTS HERE</span><h2>{register ? 'Make room for learning.' : 'Welcome to your studio.'}</h2><p>{register ? 'Create a student account to begin your first fictional case.' : 'Sign in to continue your occupational therapy practice.'}</p><form onSubmit={submit}>{register && <label>{t('name')}<input required minLength={2} maxLength={120} autoComplete="name" value={name} onChange={e => setName(e.target.value)} placeholder="Your name" dir="auto" /></label>}<label>{t('email')}<input required type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" dir="ltr" /></label><label>{t('password')}<input aria-label={t('password')} required type="password" minLength={register ? 12 : 1} maxLength={128} autoComplete={register ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} placeholder={register ? 'At least 12 characters' : 'Enter your password'} dir="ltr" />{register && <small>Use at least 12 characters. Your password is hashed on the server.</small>}</label>{(error || notice?.text) && <p className="form-error" role="alert">{error || notice?.text}</p>}<Button type="submit" busy={busy} className="full-width">{t(register ? 'register' : 'login')}<ArrowRight size={17} /></Button></form><p className="auth-switch">{register ? 'Already have an account?' : 'New to OTCaseLab?'} <button onClick={() => { setRegister(!register); setError(''); }}>{t(register ? 'login' : 'register')}</button></p><div className="auth-demo-note"><ShieldCheck size={20} /><div><strong>A clearly labelled learning prototype</strong><p>Five fictional scenarios. Scripted dialogue is available for the local demonstration; feedback identifies its provider or baseline mode. Educator credentials are issued locally by the project owner.</p></div></div></div><footer className="auth-legal"><LockKeyhole size={13} />Secure session cookies · Your work stays in your account</footer></section></div>;
}
function Stat({ value, label, icon, note }: { value: number; label: string; icon: ReactNode; note: string }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><div>{icon}</div></div><strong dir="ltr">{String(value).padStart(2, '0')}</strong><p>{note}</p></div>;
}
function CaseCard({ item, index, language, onStart, busy }: { item: Case; index: number; language: Language; onStart: () => void; busy: boolean }) {
  return <article className={`case-card case-tone-${index % 5}`}><div className="case-art"><div className="case-number" dir="ltr">CASE {String(index + 1).padStart(2, '0')}</div><div className="case-art-icon">{[<Home key="home" />, <HeartHandshake key="heart" />, <BookOpen key="book" />, <Target key="target" />, <Layers3 key="layers" />][index % 5]}</div><span>{humanize(item.domain)}</span></div><div className="case-content"><div className="case-meta"><span>{humanize(item.difficulty)}</span><span><Clock3 size={12} />{item.estimated_minutes} min</span></div><h3 dir="auto">{item.title}</h3><p dir="auto">{item.summary}</p><div className="case-patient"><span className="mini-avatar">{item.patient.name.slice(0, 1)}</span><span dir="auto">{item.patient.name}<small>{item.patient.age} years · {item.patient.occupation}</small></span></div><div className="case-card-footer"><Status value={item.review_status} language={language} /><button className="case-open" disabled={busy} aria-label={`${translate(language, 'start')}: ${item.title}`} onClick={onStart}>{busy ? <LoaderCircle size={19} className="spin" /> : <ArrowRight size={19} />}</button></div></div></article>;
}
function CaseLibrary({ cases, language, busy, onStart }: { cases: Case[]; language: Language; busy: string; onStart: (id: string) => void }) {
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('all');
  const domains = [...new Set(cases.map(item => item.domain))];
  const shown = cases.filter(item => (domain === 'all' || domain === item.domain) && `${item.title} ${item.summary} ${item.patient.name}`.toLowerCase().includes(query.toLowerCase()));
  return <><div className="page-heading"><div><span className="eyebrow">EXPLORE EVERYDAY PARTICIPATION</span><h1>{translate(language, 'library')}<span className="heading-dot">.</span></h1><p>Different people, different contexts. A shared focus on meaningful occupation.</p></div><span className="small-counter">{cases.length} fictional cases</span></div><div className="filter-bar"><label className="search-field"><Search size={18} /><input aria-label="Search cases" placeholder="Search a case, activity, or person" value={query} onChange={e => setQuery(e.target.value)} dir="auto" /></label><select aria-label="Filter by practice domain" value={domain} onChange={e => setDomain(e.target.value)}><option value="all">All practice domains</option>{domains.map(item => <option key={item} value={item}>{humanize(item)}</option>)}</select></div><div className="case-grid library-grid">{shown.map((item, index) => <CaseCard item={item} key={item.id} index={index} language={language} onStart={() => onStart(item.id)} busy={busy === item.id} />)}</div>{!shown.length && <Empty title="No matching cases">Try another search or practice domain. Published cases will appear here.</Empty>}<div className="learning-note"><ShieldCheck size={20} /><p>All scenarios are fictional. A <strong>pending educator review</strong> label means the case has not yet been approved as reviewed educational content.</p></div></>;
}
function Learning({ attempts, progress, language, busy, onOpen, onStart }: { attempts: Attempt[]; progress: Progress | null; language: Language; busy: string; onOpen: (id: string) => void; onStart: (id: string) => void }) {
  return <><div className="page-heading"><div><span className="eyebrow">SMALL STEPS, THOUGHTFUL PROGRESS</span><h1>{translate(language, 'history')}<span className="heading-dot">.</span></h1><p>Return to your drafts, revisit feedback, and choose your next practice.</p></div></div>{progress?.recommendation && <div className="recommendation-card"><span className="recommendation-icon"><Sparkles size={23} /></span><div><span className="eyebrow">SUGGESTED NEXT PRACTICE · {humanize(progress.recommendation.mode)}</span><h3 dir="auto">{progress.recommendation.title}</h3><p dir="auto">{progress.recommendation.reason}</p></div><Button variant="secondary" busy={busy === progress.recommendation.case_id} onClick={() => onStart(progress.recommendation!.case_id)}>Explore this case<ArrowRight size={16} /></Button></div>}{progress && Object.keys(progress.domain_scores || {}).length > 0 && <section className="panel"><div className="panel-heading"><h2>Feedback by reasoning dimension</h2><span className="muted">Provisional practice scores</span></div><div className="domain-grid">{Object.entries(progress.domain_scores).map(([domain, value]) => { const score = typeof value === 'number' ? value : value.score; const max = typeof value === 'number' ? 100 : value.max_score || 100; return <div className="domain-score" key={domain}><div><strong>{humanize(domain)}</strong><span dir="ltr">{Number(score).toFixed(1)} / {max}</span></div><div className="progress-bar"><span style={{ width: `${Math.max(0, Math.min(100, score / max * 100))}%` }} /></div></div>; })}</div></section>}<section className="panel history-panel"><div className="panel-heading"><h2>Practice history</h2><span>{attempts.length} attempts</span></div>{attempts.length ? attempts.map(item => <div className="history-row" key={item.id}><div className={`history-icon ${item.feedback ? 'done' : ''}`}>{item.feedback ? <CheckCircle2 size={21} /> : <FileText size={21} />}</div><div className="history-description"><strong dir="auto">{item.case.title}</strong><span>{formatDate(item.created_at)} · {languageName(item.language)} · version {item.case_version}</span></div><span className={`attempt-state ${item.feedback ? 'submitted' : ''}`}>{humanize(item.state)}</span>{item.feedback && <span className="history-score" dir="ltr">{item.feedback.total}/{item.feedback.max_total}<small>practice score</small></span>}<Button variant="ghost" busy={busy === item.id} onClick={() => onOpen(item.id)}>{item.feedback ? 'View report' : 'Continue'}<ArrowRight size={16} /></Button></div>) : <Empty title="Your learning record starts with one case">Your saved drafts and submitted feedback will appear here after you begin a practice case.</Empty>}</section></>;
}

function Workbench({ attempt, setAttempt, step, setStep, language, mode, csrf, onError, onSuccess, onBack, onSubmitted }: { attempt: Attempt; setAttempt: (value: Attempt) => void; step: Step; setStep: (value: Step) => void; language: Language; mode: string; csrf: string; onError: (error: unknown) => void; onSuccess: (value: string) => void; onBack: () => void; onSubmitted: () => Promise<void> }) {
  const [draft, setDraft] = useState<Draft>(attempt.draft || emptyDraft());
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState('');
  const [dirty, setDirty] = useState(false);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [query, setQuery] = useState('');
  const [job, setJob] = useState<Job | null>(attempt.jobs?.at(-1) || null);
  const [extraction, setExtraction] = useState<unknown>(null);
  const [messageMode, setMessageMode] = useState(mode);
  const [cancelled, setCancelled] = useState(false);
  const [cooldown, setCooldown] = useState(true);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const messageAbort = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const idempotency = useRef('');
  const t = (key: Label) => translate(language, key);
  const submitted = Boolean(attempt.feedback);
  useEffect(() => () => messageAbort.current?.abort(), []);
  useEffect(() => { setCooldown(true); const timer = setTimeout(() => setCooldown(false), 1100); return () => clearTimeout(timer); }, [attempt.messages.length]);
  useEffect(() => { if (!dirty) return; const protect = (event: BeforeUnloadEvent) => event.preventDefault(); window.addEventListener('beforeunload', protect); return () => window.removeEventListener('beforeunload', protect); }, [dirty]);
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [attempt.messages.length]);
  useEffect(() => { if (step === 'plan') void searchEvidence(); }, [step]);
  useEffect(() => {
    if (!job || ['completed', 'succeeded', 'failed', 'cancelled'].includes(job.status)) return;
    const controller = new AbortController();
    const timeout = setInterval(() => { api<Job>(`/jobs/${job.id}`, { signal: controller.signal }).then(setJob).catch(error => { if (error?.name !== 'AbortError') { clearInterval(timeout); onError(error); } }); }, 2000);
    return () => { clearInterval(timeout); controller.abort(); };
  }, [job?.id, job?.status]);
  function update(field: keyof Draft, value: string | string[]) { setDraft(old => ({ ...old, [field]: value })); setDirty(true); idempotency.current = ''; }
  async function save(announce = true) {
    setBusy('save');
    try { const data = await api<Attempt>(`/attempts/${attempt.id}/draft`, json('PATCH', draft), csrf); setAttempt(data); setDirty(false); if (announce) onSuccess('Your draft was saved.'); return data; }
    catch (error) { onError(error); throw error; }
    finally { setBusy(''); }
  }
  async function send(event: FormEvent) {
    event.preventDefault(); if (!message.trim()) return; setBusy('message'); setCancelled(false); messageAbort.current = new AbortController();
    try { const result = await api<{ student_message: Attempt['messages'][number]; patient_message: Attempt['messages'][number]; extraction: unknown; mode: string }>(`/attempts/${attempt.id}/messages`, { ...json('POST', { text: message.trim() }), signal: messageAbort.current.signal }, csrf); setMessageMode(result.mode); setAttempt({ ...attempt, messages: [...attempt.messages, result.student_message, result.patient_message] }); setExtraction(result.extraction); setMessage(''); }
    catch (error) { if (error instanceof Error && error.name === 'AbortError') setCancelled(true); else onError(error); }
    finally { setBusy(''); messageAbort.current = null; }
  }
  async function reloadTranscript() {
    setBusy('reload');
    try { const data = await api<Attempt>(`/attempts/${attempt.id}`); setAttempt(data); setCancelled(false); setMessage(''); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function upload() {
    if (!uploadFile) return;
    if (uploadFile.size > 5 * 1024 * 1024) { onError(new Error('Choose a JPEG or PNG smaller than 5 MB.')); return; }
    try { await save(false); setBusy('upload'); const form = new FormData(); form.append('file', uploadFile); const data = await api<Job>(`/attempts/${attempt.id}/uploads`, { method: 'POST', body: form }, csrf); setJob(data); onSuccess('Your educational image was uploaded for analysis.'); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function searchEvidence(event?: FormEvent) {
    event?.preventDefault(); setBusy('evidence');
    try { const data = await api<{ items: Evidence[] }>(`/evidence?case_id=${encodeURIComponent(attempt.case_id)}&q=${encodeURIComponent(query)}`); setEvidence(data.items); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function analyze() {
    try { await save(false); setBusy('analysis'); const data = await api<Job>(`/attempts/${attempt.id}/analysis`, json('POST', { asset_id: attempt.case.asset.id }), csrf); setJob(data); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy('submit');
    if (!idempotency.current) idempotency.current = crypto.randomUUID();
    try { const data = await api<Attempt>(`/attempts/${attempt.id}/submit`, { ...json('POST', draft), headers: { 'Idempotency-Key': idempotency.current } }, csrf); setAttempt(data); setDirty(false); setStep('feedback'); await onSubmitted(); onSuccess('Your plan is submitted. Formative feedback is ready for review.'); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  return <><button className="text-button back-button" onClick={onBack}><ArrowLeft size={15} />{t('back')}</button><div className="case-workbench-heading"><div><div className="case-heading-meta"><span className="eyebrow">{humanize(attempt.case.domain)} · {humanize(attempt.case.difficulty)}</span><Status value={attempt.case.review_status} language={language} /></div><h1 dir="auto">{attempt.case.title}</h1><p dir="auto">{attempt.case.summary}</p></div><div className="case-session-info"><Clock3 size={15} /><span>{attempt.case.estimated_minutes} min<br /><small>Case version {attempt.case_version}</small></span></div></div><div className="workbench-tabs" role="tablist" aria-label="Case practice stages">{(['interview', 'observe', 'plan', 'feedback'] as Step[]).map((item, index) => <button id={`tab-${item}`} aria-controls={`panel-${item}`} role="tab" aria-selected={step === item} key={item} disabled={item === 'feedback' && !submitted} className={step === item ? 'active' : ''} onClick={() => setStep(item)}><span>{submitted && item !== 'feedback' ? <Check size={13} /> : index + 1}</span>{t(item)}<small>{['Listen to the person', 'Look at the context', 'Connect your reasoning', 'Reflect and improve'][index]}</small></button>)}</div>
    <div id={`panel-${step}`} role="tabpanel" aria-labelledby={`tab-${step}`}>
    {step === 'interview' && <div className="interview-layout"><section className="interview-panel panel"><div className="interview-header"><div className="patient-avatar">{attempt.case.patient.name.slice(0, 1)}</div><div><h2 dir="auto">{attempt.case.patient.name}</h2><p>{attempt.case.patient.age} years · {attempt.case.patient.occupation}</p></div><span className="patient-mode">Simulated patient</span></div><div className="mode-banner"><ShieldCheck size={14} /><span>{humanize(messageMode)} patient dialogue · {languageName(attempt.language)} attempt</span></div><div className="chat-messages" aria-live="polite" aria-relevant="additions">{!attempt.messages.length && <div className="chat-welcome"><MessageCircle size={30} /><h3>Start with what matters.</h3><p>Introduce yourself and invite {attempt.case.patient.name.split(' ')[0]} to share their everyday activities, priorities, and context.</p><span>Your questions shape the occupational profile.</span></div>}{attempt.messages.map(item => <div className={`chat-message ${item.role === 'student' ? 'student-message' : 'patient-message'}`} key={item.id}><small>{item.role === 'student' ? 'You' : attempt.case.patient.name}<span>{item.role !== 'student' ? 'Simulated dialogue' : ''}</span></small><div dir="auto">{item.text}</div></div>)}{busy === 'message' && <div className="patient-thinking" role="status"><LoaderCircle size={15} className="spin" />The simulated patient is responding…<button type="button" onClick={() => messageAbort.current?.abort()}>Stop waiting</button></div>}{cancelled && <div className="cancelled-message" role="status"><p>Waiting stopped. The server may still finish this response. Reload the saved transcript before sending another question.</p><Button variant="secondary" busy={busy === 'reload'} onClick={reloadTranscript}>Reload transcript</Button></div>}<div ref={scrollRef} /></div>{submitted ? <div className="frozen-banner"><LockKeyhole size={16} />This submitted transcript is read-only.</div> : <form className="chat-composer" onSubmit={send}><label className="sr-only" htmlFor="patient-message">Your interview question</label><textarea id="patient-message" rows={2} maxLength={4000} placeholder="Ask about a meaningful everyday activity…" value={message} onChange={e => setMessage(e.target.value)} dir="auto" /><Button type="submit" busy={busy === 'message'} disabled={!!busy || !message.trim() || cancelled || cooldown} aria-label={t('send')}><Send size={18} /></Button><small>{cooldown ? 'Please wait a moment before your next question.' : 'Write in English, اردو, or Roman Urdu. Keep your question focused.'}</small></form>}</section><aside className="interview-aside"><section className="panel scenario-card"><span className="eyebrow">THE STARTING POINT</span><h3>Meet the person</h3><p dir="auto">{localize(attempt.case.introduction, language) || attempt.case.summary}</p><hr /><span className="eyebrow">YOUR LEARNING FOCUS</span>{(attempt.case.objectives || [printable(attempt.case.focus)]).map((objective, index) => <div className="objective" key={index}><span>{index + 1}</span><p dir="auto">{objective}</p></div>)}<p className="scenario-footnote">Ask before making assumptions. Unknown details may remain unknown in this fictional case.</p></section>{Boolean(extraction) && <section className="panel extraction-card"><span className="eyebrow">PROVISIONAL EXTRACTION</span><p>Review these dialogue cues and write your own profile.</p><pre dir="auto">{JSON.stringify(extraction, null, 2)}</pre></section>}<Button variant="secondary" onClick={() => setStep('observe')}>Continue to environment<ArrowRight size={16} /></Button></aside></div>}
    {step === 'observe' && <div className="observe-layout"><section className="panel environment-panel"><div className="panel-heading"><div><span className="eyebrow">PERSON + ENVIRONMENT</span><h2>Look closely. Describe what you see.</h2></div><ImageIcon size={22} /></div><img className="environment-image" src={attempt.case.asset.url} alt={attempt.case.asset.alt} /><div className="image-caption"><span dir="auto">{attempt.case.asset.alt}</span><span>Origin: {humanize(attempt.case.asset.origin)}</span></div><p className="image-limit">This educational image cannot establish exact dimensions, fall probability, or accessibility compliance. Separate visible details from assumptions.</p></section><section className="panel observation-editor"><span className="eyebrow">YOUR OBSERVATIONS FIRST</span><h2>{t('observations')}</h2><p>Describe visible objects, possible activity constraints, and the additional context you would ask about.</p><label className="sr-only" htmlFor="observations">{t('observations')}</label><textarea id="observations" rows={11} value={draft.observations} onChange={e => update('observations', e.target.value)} disabled={submitted} maxLength={12000} placeholder="I notice… This may affect… I would ask…" dir="auto" />{!submitted && <div className="editor-actions"><Button variant="secondary" busy={busy === 'save'} disabled={!!busy || !dirty} onClick={() => void save().catch(() => {})}>{t('save')}</Button><Button variant="ghost" busy={busy === 'analysis'} disabled={!!busy || !draft.observations.trim()} onClick={analyze}><Sparkles size={16} />{t('assistant')}</Button></div>}{!submitted && <div className="upload-box"><label htmlFor="educational-image">Optional staged educational image<input id="educational-image" type="file" accept="image/jpeg,image/png" onChange={e => setUploadFile(e.target.files?.[0] || null)} /></label><p>Choose an image you have rights to use, without real patient details or identifiable people. JPEG or PNG, up to 5 MB.</p><Button variant="secondary" busy={busy === 'upload'} disabled={!!busy || !uploadFile || !draft.observations.trim()} onClick={upload}><ImageIcon size={15} />Upload for analysis</Button></div>}<small className="field-help">Assistance becomes available after you record your observations. Analysis identifies its mode and remains provisional.</small>{job && <div className={`analysis-result ${job.status === 'failed' ? 'analysis-failed' : ''}`} role="status"><strong>Image assistance · {humanize(job.status)}</strong>{job.mode && <span>{humanize(job.mode)}</span>}{Boolean(job.error) && <p>{printable(job.error)}</p>}{Boolean(job.output || job.result) && <pre dir="auto">{JSON.stringify(job.output || job.result, null, 2)}</pre>}</div>}<Button onClick={() => setStep('plan')} variant="secondary" className="full-width">Continue to your plan<ArrowRight size={16} /></Button></section></div>}
    {step === 'plan' && <form onSubmit={submit} className="plan-layout"><section className="panel plan-editor"><div className="panel-heading"><div><span className="eyebrow">CONNECT WHAT YOU HAVE LEARNED</span><h2>Build a meaningful plan</h2></div><span className={`save-state ${dirty ? 'unsaved' : ''}`}>{submitted ? 'Submission frozen' : dirty ? 'Unsaved changes' : 'Saved draft'}</span></div><p className="plan-intro">Use the patient&apos;s own priorities and your environmental observations to explain your reasoning.</p>{(['profile', 'goals', 'rationale'] as const).map((field, index) => <label className="plan-field" key={field}><span className="plan-field-title"><span>{String(index + 1).padStart(2, '0')}</span>{t(field)}</span><small>{field === 'profile' ? 'Who is this person? What activities, routines, roles, and priorities matter to them?' : field === 'goals' ? 'State the meaningful activity, patient priority, timeframe, and observable outcome.' : 'Explain how the plan connects patient priorities, environmental context, and your selected evidence.'}</small><textarea required minLength={10} maxLength={12000} rows={field === 'profile' ? 5 : 4} value={draft[field]} onChange={e => update(field, e.target.value)} disabled={submitted} placeholder={field === 'profile' ? 'Describe the person and the occupations that matter…' : field === 'goals' ? 'A patient-prioritized functional goal…' : 'I propose this because…'} dir="auto" /></label>)}<label className="plan-field"><span className="plan-field-title"><span>04</span>{t('observations')}</span><small>Your environment notes are included with the submitted plan.</small><textarea required minLength={10} maxLength={12000} rows={3} value={draft.observations} onChange={e => update('observations', e.target.value)} disabled={submitted} dir="auto" /></label>{!submitted && <div className="submission-footer"><p><ShieldCheck size={17} />Submission freezes your plan and transcript for transparent formative feedback.</p><div><Button type="button" variant="secondary" busy={busy === 'save'} disabled={!!busy || !dirty} onClick={() => void save().catch(() => {})}>{t('save')}</Button><Button type="submit" busy={busy === 'submit'} disabled={!!busy || attempt.messages.every(m => m.role !== 'student')}>{t('submit')}<ArrowRight size={16} /></Button></div>{attempt.messages.every(m => m.role !== 'student') && <small>Interview the simulated patient before submitting your plan.</small>}</div>}</section><aside className="panel evidence-panel"><span className="eyebrow">SUPPORT YOUR REASONING</span><h2>{t('evidence')}</h2><p>Choose relevant passages. Check their scope and explain how they inform your plan.</p><div className="evidence-search"><input aria-label="Search evidence" placeholder="Search activities or reasoning…" value={query} onChange={e => setQuery(e.target.value)} dir="auto" /><button type="button" aria-label="Search evidence" disabled={busy === 'evidence'} onClick={() => void searchEvidence()}>{busy === 'evidence' ? <LoaderCircle className="spin" size={16} /> : <Search size={17} />}</button></div><div className="evidence-list">{evidence.map(item => <label className={`evidence-item ${draft.evidence_ids.includes(item.id) ? 'evidence-selected' : ''}`} key={item.id}><div><input type="checkbox" checked={draft.evidence_ids.includes(item.id)} disabled={submitted} onChange={e => update('evidence_ids', e.target.checked ? [...draft.evidence_ids, item.id] : draft.evidence_ids.filter(id => id !== item.id))} /><strong dir="auto">{item.title}</strong></div><p dir="auto">{item.text}</p><small>{humanize(item.origin)} · <bdi>{item.id}</bdi></small>{item.url && <a href={item.url} target="_blank" rel="noreferrer">Open source<ArrowRight size={12} /></a>}</label>)}{!evidence.length && <p className="muted">No matching reference passages. Try another search.</p>}</div><div className="evidence-note"><BookOpen size={18} /><p>These passages include provenance. An original teaching passage is labelled as such; it is not a validated clinical guideline.</p></div></aside></form>}
    {step === 'feedback' && attempt.feedback && <Report feedback={attempt.feedback} attemptId={attempt.id} language={language} />}
    </div>
  </>;
}

function Report({ feedback, attemptId, language }: { feedback: Feedback; attemptId: string; language: Language }) {
  return <div className="report"><section className="feedback-summary"><div><span className="eyebrow">A MOMENT TO REFLECT</span><h2>Your reasoning, made visible.</h2><p>Every feedback item links a criterion to your submitted words and the available context.</p><div className="report-mode"><Status value={feedback.review_status} language={language} /><span>{humanize(feedback.mode)} · provisional formative feedback</span></div></div><div className="total-score" dir="ltr"><strong>{feedback.total}<small>/{feedback.max_total}</small></strong><span>Rubric coverage score</span></div></section><div className="report-toolbar"><span><ShieldCheck size={16} />Original model output is preserved when educators amend feedback.</span><a className="button button-secondary" href={`/api/v1/attempts/${attemptId}/report`} download><ArrowDownToLine size={16} />{translate(language, 'download')}</a></div><div className="feedback-items">{feedback.items.map((item, index) => <article className="panel feedback-item" key={item.dimension}><div className="feedback-item-heading"><span className="feedback-index">{String(index + 1).padStart(2, '0')}</span><div><h3 dir="auto">{item.label}</h3><small>{humanize(item.review_status)}</small></div><span className="dimension-score" dir="ltr">{item.score}<small> / {item.max_score}</small></span></div><p className="feedback-explanation" dir="auto">{item.explanation}</p><div className="feedback-detail-grid"><div className="student-evidence"><span className="eyebrow">YOUR EXACT WORDS</span>{item.student_evidence.length ? item.student_evidence.map((span, position) => <div className="evidence-span" key={position}><blockquote dir="auto">“{span.text}”</blockquote><small>{humanize(span.field)} · <bdi>characters {span.start}–{span.end}</bdi>{span.message_id && <> · transcript <bdi>{span.message_id.slice(0, 8)}</bdi></>}</small></div>) : <p>No supporting student span was identified. Review the stated rule and uncertainty.</p>}</div><div className="feedback-grounding"><div><span className="eyebrow">RUBRIC ANCHOR</span><p dir="auto">{printable(item.rubric_anchor) || 'No anchor available.'}</p></div>{Boolean(item.case_fact) && <div><span className="eyebrow">CASE CONTEXT</span><p dir="auto">{printable(item.case_fact)}</p></div>}{Boolean(item.visual_observation) && <div><span className="eyebrow">ENVIRONMENT REFERENCE</span><p dir="auto">{printable(item.visual_observation)}</p></div>}</div></div>{item.reference_passage && <div className="reference-passage"><BookOpen size={18} /><div><strong dir="auto">{item.reference_passage.title}</strong><p dir="auto">{item.reference_passage.text}</p><small>Passage <bdi>{item.reference_passage.id}</bdi></small>{item.reference_passage.url && <a href={item.reference_passage.url} target="_blank" rel="noreferrer">View reference</a>}</div></div>}{item.uncertainty && <p className="uncertainty"><Eye size={15} /><span dir="auto"><strong>Uncertainty: </strong>{item.uncertainty}</span></p>}</article>)}</div>{feedback.reviews?.length > 0 && <section className="panel educator-amendments"><span className="eyebrow">HUMAN REVIEW</span><h2>Educator feedback</h2>{feedback.reviews.map(review => <div className="educator-review" key={review.id}><strong dir="auto">{review.educator_name}</strong><small>{formatDate(review.created_at)}</small><p dir="auto">{review.comment}</p><div className="review-scores">{Object.entries(review.scores).map(([dimension, score]) => <span key={dimension}>{humanize(dimension)} <bdi>{score}</bdi></span>)}</div></div>)}</section>}{feedback.recommendation && <section className="recommendation-card"><span className="recommendation-icon"><Target size={23} /></span><div><span className="eyebrow">NEXT PRACTICE · {humanize(feedback.recommendation.mode)}</span><h3 dir="auto">{feedback.recommendation.title}</h3><p dir="auto">{feedback.recommendation.reason}</p></div></section>}<details className="panel trace-details"><summary>View the bounded feedback workflow trace</summary><pre dir="ltr">{JSON.stringify(feedback.trace, null, 2)}</pre></details></div>;
}

function Privacy({ session, language, onLanguage, onError, onSuccess, onDeleted }: { session: Session; language: Language; onLanguage: (value: Language) => void; onError: (error: unknown) => void; onSuccess: (text: string) => void; onDeleted: () => void }) {
  const [consent, setConsent] = useState<boolean | null>(session.user.research_consent ?? null);
  const [busy, setBusy] = useState('');
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmation, setConfirmation] = useState('');
  async function changeConsent(granted: boolean) {
    setBusy('consent');
    try { await api('/privacy/consent', json('POST', { granted }), session.csrf_token); setConsent(granted); onSuccess(granted ? 'Your optional research consent was recorded.' : 'Your research consent was withdrawn.'); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function deleteAccount() {
    setBusy('delete');
    try { await api('/privacy/me', json('DELETE'), session.csrf_token); onDeleted(); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  return <><div className="page-heading"><div><span className="eyebrow">YOUR ACCOUNT, YOUR CHOICES</span><h1>{translate(language, 'settings')}<span className="heading-dot">.</span></h1><p>Manage your practice language and personal data.</p></div></div><div className="settings-layout"><section className="panel settings-panel"><h2>Profile</h2><div className="account-field"><span>Name</span><strong dir="auto">{session.user.name}</strong></div><div className="account-field"><span>Email</span><strong dir="ltr">{session.user.email}</strong></div><div className="account-field"><span>Role</span><strong>{humanize(session.user.role)}</strong></div><div className="account-field"><span>{translate(language, 'language')}</span><LanguageSelect value={language} onChange={onLanguage} /></div><p className="field-help">Your selected language is saved to your account. An attempt keeps its original practice language.</p></section><section className="panel settings-panel"><ShieldCheck size={25} className="teal-text" /><h2>Optional research participation</h2><p>Practice is available without research participation. Granting consent records your choice for eligible de-identified research use; it does not establish study approval or permission for unrelated exports.</p><div className="consent-status">{consent === null ? 'Consent status has not been loaded for this session.' : consent ? 'Your current choice: consent granted.' : 'Your current choice: consent not granted.'}</div><div className="editor-actions"><Button variant="secondary" busy={busy === 'consent'} disabled={!!busy || consent === true} onClick={() => changeConsent(true)}>Grant consent</Button><Button variant="ghost" disabled={!!busy || consent === false} onClick={() => changeConsent(false)}>Withdraw consent</Button></div></section><section className="panel settings-panel delete-panel"><Trash2 size={25} /><h2>Delete your account and learning data</h2><p>This removes your eligible personal data and attempts and ends your current session. Download any reports you want to retain first.</p>{!deleteOpen ? <Button variant="danger" onClick={() => setDeleteOpen(true)}>Review account deletion</Button> : <div className="delete-confirm"><label>Type DELETE to confirm<input value={confirmation} onChange={e => setConfirmation(e.target.value)} autoComplete="off" dir="ltr" /></label><div className="editor-actions"><Button variant="danger" busy={busy === 'delete'} disabled={confirmation !== 'DELETE'} onClick={deleteAccount}>Delete my account</Button><Button variant="ghost" onClick={() => { setDeleteOpen(false); setConfirmation(''); }}>Cancel</Button></div></div>}</section></div></>;
}

function Educator({ csrf, language, onError, onSuccess, onPublished }: { csrf: string; language: Language; onError: (error: unknown) => void; onSuccess: (text: string) => void; onPublished: () => Promise<void> }) {
  const [cases, setCases] = useState<Record<string, unknown>[]>([]);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [tab, setTab] = useState<'reviews' | 'cases'>('reviews');
  const [selected, setSelected] = useState<Attempt | null>(null);
  const [comment, setComment] = useState('');
  const [scores, setScores] = useState<Record<string, number>>({});
  const [editingId, setEditingId] = useState('');
  const [source, setSource] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [busy, setBusy] = useState('load');
  useEffect(() => { void load(); }, []);
  async function load() {
    setBusy('load');
    try { const data = await Promise.all([api<{ items: Record<string, unknown>[] }>('/educator/cases'), api<{ items: Attempt[] }>('/educator/attempts')]); setCases(data[0].items); setAttempts(data[1].items); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  function chooseAttempt(item: Attempt) { setSelected(item); setComment(''); setScores(Object.fromEntries((item.feedback?.items || []).map(dimension => [dimension.dimension, dimension.score]))); }
  async function review(event: FormEvent) {
    event.preventDefault(); if (!selected) return; setBusy('review');
    try { const feedback = await api<Feedback>(`/educator/attempts/${selected.id}/review`, json('POST', { comment, scores }), csrf); setSelected({ ...selected, feedback }); onSuccess('Your attributed educator review was saved; the original feedback is preserved.'); setComment(''); await load(); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function saveCase(event: FormEvent) {
    event.preventDefault(); setBusy('save-case');
    try { const content = JSON.parse(source); await api(editingId ? `/educator/cases/${encodeURIComponent(editingId)}/versions` : '/educator/cases', json('POST', { case: content }), csrf); onSuccess(editingId ? 'A new immutable draft version was created.' : 'The case draft was created.'); setSource(''); setEditingId(''); await load(); }
    catch (error) { onError(error instanceof SyntaxError ? new Error('The case JSON is invalid. Correct the syntax before saving.') : error); }
    finally { setBusy(''); }
  }
  async function publish(caseId: string) {
    if (!reviewNote.trim()) { onError(new Error('Add a review note describing your case, rubric, and asset checks before publishing.')); return; }
    setBusy(caseId);
    try { await api(`/educator/cases/${encodeURIComponent(caseId)}/publish`, json('POST', { review_note: reviewNote }), csrf); onSuccess('The reviewed case version was published.'); await load(); await onPublished(); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  const caseId = (item: Record<string, unknown>) => String(item.id || item.case_id || '');
  return <><div className="page-heading"><div><span className="eyebrow">TEACHING WITH TRANSPARENT FEEDBACK</span><h1>{translate(language, 'educator')}<span className="heading-dot">.</span></h1><p>Review your authorized cohort&apos;s reasoning and version educational content.</p></div><span className="educator-access"><GraduationCap size={17} />Cohort-scoped access</span></div><div className="segmented-tabs"><button className={tab === 'reviews' ? 'active' : ''} onClick={() => setTab('reviews')}>Learner reviews <span>{attempts.length}</span></button><button className={tab === 'cases' ? 'active' : ''} onClick={() => setTab('cases')}>Case authoring <span>{cases.length}</span></button></div>{busy === 'load' && <p className="sync-note"><LoaderCircle className="spin" size={15} />Loading cohort workspace…</p>}{tab === 'reviews' && <div className="educator-layout"><section className="panel cohort-attempts"><div className="panel-heading"><h2>Cohort attempts</h2></div>{attempts.length ? attempts.map(item => <button className={`cohort-attempt ${selected?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => chooseAttempt(item)}><strong dir="auto">{item.case.title}</strong><span><bdi>{item.id.slice(0, 8)}</bdi> · {formatDate(item.created_at)}</span><small>{item.feedback ? `${item.feedback.total}/${item.feedback.max_total} · ${humanize(item.feedback.review_status)}` : humanize(item.state)}</small></button>) : <Empty title="No cohort attempts yet">Learner attempts from your authorized cohort will appear here.</Empty>}</section><div className="educator-review-main">{selected ? <><section className="panel review-form-panel"><h2>Educator review</h2>{selected.feedback ? <form onSubmit={review}><div className="educator-score-inputs">{selected.feedback.items.map(item => <label key={item.dimension}>{item.label}<input type="number" required min={0} max={item.max_score} step={1} value={scores[item.dimension] ?? item.score} onChange={e => setScores(old => ({ ...old, [item.dimension]: Number(e.target.value) }))} dir="ltr" /><small>Maximum {item.max_score}</small></label>)}</div><label>Your review and correction rationale<textarea rows={4} required minLength={10} maxLength={6000} value={comment} onChange={e => setComment(e.target.value)} placeholder="Explain your judgement and any corrections to the provisional feedback…" dir="auto" /></label><Button busy={busy === 'review'} type="submit">Save attributed review<Check size={16} /></Button></form> : <p>This learner has not submitted a plan. Feedback review is available after submission.</p>}</section><details className="panel submitted-work"><summary>Inspect learner transcript and submitted plan</summary><div className="submitted-transcript">{selected.messages.map(message => <p key={message.id}><strong>{message.role}: </strong><span dir="auto">{message.text}</span></p>)}</div>{Object.entries(selected.draft || {}).filter(([field]) => field !== 'evidence_ids').map(([field, text]) => <div key={field}><strong>{humanize(field)}</strong><p dir="auto">{String(text)}</p></div>)}</details>{selected.feedback && <Report feedback={selected.feedback} attemptId={selected.id} language={language} />}</> : <Empty icon={<GraduationCap size={30} />} title="Bring your judgement to the feedback">Select a cohort attempt to inspect the submitted work and add an attributed review.</Empty>}</div></div>}{tab === 'cases' && <><div className="learning-note"><ShieldCheck size={20} /><p>Case authoring includes restricted facts and original rubrics. Only educators can access this source. New and revised content begins as a draft.</p></div><div className="authoring-layout"><section className="panel case-source-list"><div className="panel-heading"><h2>Case versions</h2><Button variant="ghost" onClick={() => { setEditingId(''); setSource(cases[0] ? JSON.stringify({ ...cases[0], id: 'new-case-id', title: 'New fictional teaching case', review_status: 'draft' }, null, 2) : '{}'); }}><Plus size={15} />New</Button></div><label className="publish-note-label">Educator publication review note<textarea rows={3} value={reviewNote} onChange={e => setReviewNote(e.target.value)} placeholder="Document your review of facts, learning objectives, rubric, references, and asset rights…" dir="auto" /></label>{cases.map((item, index) => <article className="source-case" key={`${caseId(item)}-${index}`}><h3 dir="auto">{String(item.title || caseId(item))}</h3><span>Version {String(item.version || 1)} · {humanize(String(item.review_status || 'draft'))}</span><div className="editor-actions"><Button variant="ghost" onClick={() => { setEditingId(caseId(item)); setSource(JSON.stringify(item, null, 2)); }}>Create revision</Button><Button variant="secondary" busy={busy === caseId(item)} disabled={!!busy || isReviewed(String(item.review_status))} onClick={() => publish(caseId(item))}>Review & publish</Button></div></article>)}</section><form className="panel source-editor" onSubmit={saveCase}><div className="panel-heading"><h2>{editingId ? 'New case version' : 'New case draft'}</h2><span className="muted">Schema-validated JSON</span></div><p>Use an existing version as a structural template. Retain all required fields and review licences before publishing.</p><label className="sr-only" htmlFor="case-json">Restricted case source JSON</label><textarea id="case-json" rows={25} value={source} onChange={e => setSource(e.target.value)} placeholder="Select Create revision or New to prepare a case source…" spellCheck={false} dir="ltr" required /><Button type="submit" busy={busy === 'save-case'} disabled={!source.trim() || !!busy}>Save draft version<Check size={16} /></Button></form></div></>}</>;
}

function Admin({ session, language, onError, onSuccess }: { session: Session; language: Language; onError: (error: unknown) => void; onSuccess: (text: string) => void }) {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Record<string, string>>({});
  const [operations, setOperations] = useState<{ health: unknown; modes: Record<string, unknown>; limits: unknown; audit_events: { id: string; action: string; created_at: string }[]; configuration_note: string } | null>(null);
  const [busy, setBusy] = useState('load');
  useEffect(() => { void load(); }, []);
  async function load() {
    setBusy('load');
    try { const result = await Promise.all([api<{ items: User[] }>('/admin/users'), api<NonNullable<typeof operations>>('/admin/operations')]); setUsers(result[0].items); setRoles(Object.fromEntries(result[0].items.map(user => [user.id, user.role]))); setOperations(result[1]); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  async function updateRole(user: User) {
    setBusy(user.id);
    try { await api(`/admin/users/${encodeURIComponent(user.id)}/role`, json('POST', { role: roles[user.id] }), session.csrf_token); onSuccess('The member role was updated and their existing sessions were revoked.'); await load(); }
    catch (error) { onError(error); }
    finally { setBusy(''); }
  }
  return <><div className="page-heading"><div><span className="eyebrow">COHORT MEMBERSHIP AND SERVICE STATUS</span><h1>{translate(language, 'admin')}<span className="heading-dot">.</span></h1><p>Authorize educators within your cohort and inspect recorded operating modes.</p></div></div>{busy === 'load' && <p className="sync-note"><LoaderCircle size={15} className="spin" />Loading administration…</p>}<section className="panel admin-members"><div className="panel-heading"><h2>Cohort members</h2><span>{users.length} members</span></div><p className="field-help">Changing a member&apos;s role revokes their active sessions. The member signs in again to receive the new permissions.</p>{users.map(user => <div className="admin-member" key={user.id}><div><strong dir="auto">{user.name}</strong><small dir="ltr">{user.email}</small></div>{user.role === 'admin' ? <span className="status status-good">Administrator</span> : <><select aria-label={`Role for ${user.name}`} value={roles[user.id] || user.role} onChange={e => setRoles(old => ({ ...old, [user.id]: e.target.value }))}><option value="student">Student</option><option value="educator">Educator</option></select><Button variant="secondary" busy={busy === user.id} disabled={!!busy || roles[user.id] === user.role} onClick={() => updateRole(user)}>Update role</Button></>}</div>)}</section>{operations && <div className="admin-operations"><section className="panel"><span className="eyebrow">RECORDED SERVICE STATE</span><h2>Health and operating modes</h2><pre dir="ltr">{JSON.stringify(operations.health, null, 2)}</pre><div className="operating-modes">{Object.entries(operations.modes).map(([name, value]) => <div key={name}><strong>{humanize(name)}</strong><span dir="auto">{printable(value)}</span></div>)}</div><p>{operations.configuration_note}</p><details><summary>Configured resource limits</summary><pre dir="ltr">{JSON.stringify(operations.limits, null, 2)}</pre></details></section><section className="panel"><span className="eyebrow">ATTRIBUTED ACTIONS</span><h2>Recent audit events</h2>{operations.audit_events.length ? operations.audit_events.map(event => <div className="audit-event" key={event.id}><strong>{humanize(event.action)}</strong><span dir="ltr">{formatDate(event.created_at)}</span></div>) : <p>No recorded audit events.</p>}</section></div>}</>;
}
