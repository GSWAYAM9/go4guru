import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Plus_Jakarta_Sans } from "next/font/google";
import type { ReactNode } from "react";
import "katex/dist/katex.min.css";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/lib/auth-context";
import { LanguageProvider } from "@/lib/language-context";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["600", "700"],
  style: ["normal", "italic"],
});

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Go4Guru by GO4GURU Inc. — Online Tutoring & Global Learning Platform",
  description:
    "Online Tutoring (USA & India) and International Educational Tour Operators by GO4GURU Inc. Live whiteboard tutoring, Grades 6–12 STEM practice, CBSE, JEE, NEET & SAT prep.",
  openGraph: {
    title: "Go4Guru by GO4GURU Inc. — Online Tutoring & Global Learning Platform",
    description:
      "Live whiteboard online tutoring across USA & India, Grades 6–12 STEM mastery, exam prep, parent progress summaries, and international educational tours.",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${plusJakarta.variable} ${ibmPlexMono.variable}`}
    >
      <body className="min-h-screen font-sans antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-[#0B104A] focus:px-3 focus:py-2 focus:text-white"
        >
          Skip to main content
        </a>
        <AuthProvider>
          <LanguageProvider>
            <AppShell>{children}</AppShell>
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
