import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SplunkGate — Runtime safety net for AI agents",
  description:
    "SplunkGate intercepts any AI agent before it acts — prompt injections blocked, PII and secrets kept in, unsafe tool calls stopped. Every verdict lands in Splunk.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
