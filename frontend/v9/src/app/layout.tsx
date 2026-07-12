import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { AgentChatWidget } from '../v9/components/agent/AgentChatWidget';

export const metadata: Metadata = {
  title: 'MEMS26 V9 Dashboard',
  description: 'MES Futures Trading Dashboard — V9 Architecture',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <Providers>{children}</Providers>
        {/* חלון-שיחה עם הסוכן — זמין מכל דף בדשבורד (מייקל 07-12) */}
        <AgentChatWidget />
      </body>
    </html>
  );
}
