import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import BottomNav from "./components/BottomNav";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#2563eb",
};

export const metadata: Metadata = {
  title: "iCough Analytic — ระบบวิเคราะห์เสียงไอสำหรับเด็ก",
  description:
    "ระบบคัดกรองโรคทางเดินหายใจในเด็กอายุ 0-5 ปี ด้วย AI วิเคราะห์เสียงไอ จำแนก ปอดบวม หลอดลมอักเสบ ครูป พร้อม Checklist ประเมินอาการร่วม",
  keywords: [
    "iCough",
    "เสียงไอเด็ก",
    "ปอดบวม",
    "AI วิเคราะห์เสียง",
    "คัดกรองโรค",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="th" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[var(--background)] text-[var(--foreground)]">
        <main className="flex-1 safe-bottom">{children}</main>
        <BottomNav />
      </body>
    </html>
  );
}
