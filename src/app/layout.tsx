import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/Navigation";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LeadScout – Lokale Unternehmens-Leadgenerierung",
  description: "Finde und bewerte lokale Unternehmen als Verkaufschancen",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className={inter.className}>
        <div className="min-h-screen bg-slate-50">
          <Navigation />
          <main className="container mx-auto px-4 py-8 max-w-7xl">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
