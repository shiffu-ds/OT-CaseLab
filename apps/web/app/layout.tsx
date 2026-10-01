import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'OTCaseLab · Practice with purpose',
  description: 'Bilingual occupational therapy reasoning practice: fictional cases, patient interviews, environment observations and traceable formative feedback.',
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
