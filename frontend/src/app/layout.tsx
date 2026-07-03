import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Phenotype Predictor Engine",
  description: "AI-Powered Genomic Trait Prediction",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased min-h-screen text-slate-200 selection:bg-neon-blue selection:text-space-900`} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
