import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'MEMS26 AI Trader',
  description: 'Real-time decision support for MEMS26 futures',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he">
      <body>{children}</body>
    </html>
  );
}
