export type Language = 'en' | 'ur' | 'roman';
export type User = { id: string; email: string; name: string; role: string; language: Language; cohort_id: string; research_consent?: boolean };
export type Session = { user: User; csrf_token: string; mode: string };
export type Case = {
  id: string; version: number; title: string; summary: string; domain: string;
  difficulty: string; focus: string | string[]; review_status: string; estimated_minutes: number;
  patient: { name: string; age: number; occupation: string };
  asset: { id: string; url: string; alt: string; origin: string };
  introduction?: string | Partial<Record<Language, string>>; objectives?: string[];
};
export type Message = { id: string; role: string; text: string; ordinal: number; provenance?: Record<string, unknown> | string };
export type Draft = { profile: string; observations: string; goals: string; rationale: string; evidence_ids: string[] };
export type Recommendation = { case_id: string; title: string; domain: string; reason: string; mode: string };
export type Evidence = { id: string; title: string; text: string; url: string; origin: string };
export type FeedbackItem = {
  dimension: string; label: string; score: number; max_score: number;
  student_evidence: { field: string; start: number; end: number; text: string; message_id?: string }[];
  rubric_anchor: unknown; case_fact: unknown; visual_observation: unknown;
  reference_passage: { id: string; text: string; title: string; url: string } | null;
  explanation: string; uncertainty: string; review_status: string;
};
export type Review = { id: string; educator_name: string; comment: string; scores: Record<string, number>; created_at: string };
export type Feedback = { id: string; mode: string; review_status: string; items: FeedbackItem[]; total: number; max_total: number; trace: unknown[]; recommendation: Recommendation | null; reviews: Review[]; created_at: string };
export type Attempt = { id: string; case_id: string; case_version: number; state: string; language: Language; created_at: string; case: Case; messages: Message[]; draft: Draft; feedback: Feedback | null; jobs: Job[]; recommendation?: Recommendation };
export type Job = { id: string; status: string; output?: unknown; result?: unknown; error?: unknown; mode?: string };
export type Progress = { completed: number; active: number; domain_scores: Record<string, number | { score: number; max_score?: number; count?: number }>; history: unknown[]; recommendation: Recommendation | null };
export const emptyDraft = (): Draft => ({ profile: '', observations: '', goals: '', rationale: '', evidence_ids: [] });
