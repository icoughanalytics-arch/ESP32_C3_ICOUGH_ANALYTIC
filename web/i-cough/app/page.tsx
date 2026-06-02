"use client";

import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import Image from "next/image";
import Link from "next/link";

/* ── Disease Knowledge Cards Data ── */
const diseases = [
  {
    title: "ปอดบวม (Pneumonia)",
    img: "/pneumonia.png",
    desc: "การติดเชื้อในปอดที่ทำให้ถุงลมอักเสบและมีของเหลวสะสม พบบ่อยในเด็กเล็ก อาจเป็นอันตรายถึงชีวิตหากไม่ได้รับการรักษา",
    symptoms: ["ไอมีเสมหะ", "หายใจเร็ว", "ไข้สูง", "หอบเหนื่อย"],
    color: "#ef4444",
    bgColor: "#fef2f2",
    borderColor: "#fecaca",
  },
  {
    title: "หลอดลมอักเสบ (Bronchitis)",
    img: "/bronchitis.png",
    desc: "การอักเสบของหลอดลม ทำให้หลอดลมบวมและมีเสมหะมาก มักเกิดจากไวรัส พบบ่อยในเด็กที่อยู่ในสภาพแวดล้อมที่มีมลภาวะ",
    symptoms: ["ไอแห้ง→มีเสมหะ", "แน่นหน้าอก", "หายใจมีเสียง", "อ่อนเพลีย"],
    color: "#f59e0b",
    bgColor: "#fffbeb",
    borderColor: "#fde68a",
  },
  {
    title: "โรคครูป (Croup)",
    img: "/croup.png",
    desc: "การติดเชื้อทางเดินหายใจส่วนบนที่ทำให้กล่องเสียงและหลอดลมบวม มักพบในเด็กอายุ 6 เดือน - 3 ปี มีเสียงไอเหมือนสุนัขเห่า",
    symptoms: [
      "ไอเสียงก้อง (Barking)",
      "เสียงแหบ",
      "Stridor",
      "อาการหนักตอนกลางคืน",
    ],
    color: "#8b5cf6",
    bgColor: "#f5f3ff",
    borderColor: "#ddd6fe",
  },
];

/* ── How It Works Steps ── */
const steps = [
  {
    num: "01",
    title: "ESP32 ดักฟังเสียงไอ",
    desc: "ไมโครโฟน INMP441 บนบอร์ด ESP32-C3 คอยฟังเสียงตลอดเวลา เมื่อตรวจจับเสียงไอจะอัดคลิปส่งขึ้น Server",
    animation: "/chip.json",
  },
  {
    num: "02",
    title: "AI วิเคราะห์เสียง",
    desc: "Server ประมวลผลเสียงไอด้วย CNN + Mel-Spectrogram จำแนกออกเป็น 4 กลุ่ม: ปกติ, ปอดบวม, หลอดลมอักเสบ, ครูป",
    animation: "/ai.json",
  },
  {
    num: "03",
    title: "แจ้งเตือน & ประเมินผล",
    desc: "ส่งผลวิเคราะห์ผ่าน Line Notification ให้ผู้ปกครอง ทำ Checklist ประเมินอาการร่วม สรุปเป็นระดับเสี่ยง เขียว/เหลือง/แดง",
    animation: "/line.json",
  },
];

export default function Home() {
  return (
    <div className="bg-gradient-medical min-h-screen">
      {/* ── Hero Section ── */}
      <section className="bg-gradient-hero relative overflow-hidden">
        <div className="relative z-10 max-w-lg mx-auto px-5 pt-10 pb-6 text-center">
          {/* Logo Animation */}
          <div
            className="w-36 h-36 mx-auto mb-4 animate-fade-in-up"
            style={{ animationDelay: "0.1s" }}
          >
            <DotLottieReact src="/heart-line.json" loop autoplay />
          </div>

          {/* Title */}
          <h1
            className="text-3xl font-extrabold tracking-tight mb-2 animate-fade-in-up"
            style={{ animationDelay: "0.2s" }}
          >
            <span className="text-gradient">iCough</span>{" "}
            <span style={{ color: "var(--foreground)" }}>Analytic</span>
          </h1>

          <p
            className="text-base font-medium animate-fade-in-up"
            style={{
              color: "var(--muted)",
              animationDelay: "0.3s",
              lineHeight: 1.7,
            }}
          >
            ระบบคัดกรองโรคทางเดินหายใจในเด็กอายุ 0-5 ปี
            <br />
            ด้วยเทคโนโลยี AI วิเคราะห์เสียงไอ
          </p>
        </div>

        {/* Wave Divider */}
        <svg
          viewBox="0 0 1440 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full"
          preserveAspectRatio="none"
          style={{ display: "block", marginBottom: "-1px" }}
        >
          <path
            d="M0,40 C360,80 720,0 1080,40 C1260,60 1380,50 1440,40 L1440,80 L0,80 Z"
            fill="#f8fafc"
          />
        </svg>
      </section>

      {/* ── Content Area ── */}
      <div className="max-w-lg mx-auto px-5 pb-8">
        {/* ── AI Coverage Section ── */}
        <section className="mb-8 animate-fade-in-up animate-delay-3">
          <div className="flex items-center gap-2 mb-4">
            <h2
              className="text-lg font-bold"
              style={{ color: "var(--foreground)" }}
            >
              AI ครอบคลุม 4 กลุ่มโรค
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              {
                label: "ปกติ (Healthy)",
                img: "/normal.png",
                bg: "#f0fdf4",
                border: "#bbf7d0",
              },
              {
                label: "ปอดบวม",
                img: "/pneumonia.png",
                bg: "#fef2f2",
                border: "#fecaca",
              },
              {
                label: "หลอดลมอักเสบ",
                img: "/bronchitis.png",
                bg: "#fffbeb",
                border: "#fde68a",
              },
              {
                label: "ครูป (Croup)",
                img: "/croup.png",
                bg: "#f5f3ff",
                border: "#ddd6fe",
              },
            ].map((item, i) => (
              <div
                key={i}
                className="rounded-xl p-3 text-center transition-all duration-200"
                style={{
                  background: item.bg,
                  border: `1px solid ${item.border}`,
                }}
              >
                <div className="w-12 h-12 mx-auto mb-1 flex items-center justify-center">
                  <Image
                    src={item.img}
                    alt={item.label}
                    width={48}
                    height={48}
                    className="object-contain"
                  />
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── How It Works ── */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <h2
              className="text-lg font-bold"
              style={{ color: "var(--foreground)" }}
            >
              ระบบทำงานอย่างไร
            </h2>
          </div>

          <div className="space-y-4">
            {steps.map((step, i) => (
              <div
                key={i}
                className="glass-card p-4 flex gap-4 items-start animate-fade-in-up"
                style={{ animationDelay: `${0.2 + i * 0.15}s` }}
              >
                {/* Lottie Animation */}
                <div
                  className="w-16 h-16 flex-shrink-0 rounded-xl overflow-hidden flex items-center justify-center"
                  style={{ background: "var(--primary-50)" }}
                >
                  <DotLottieReact src={step.animation} loop autoplay />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded-full"
                      style={{
                        background: "var(--primary-100)",
                        color: "var(--primary-700)",
                      }}
                    >
                      {step.num}
                    </span>
                    <h3
                      className="text-sm font-bold"
                      style={{ color: "var(--foreground)" }}
                    >
                      {step.title}
                    </h3>
                  </div>
                  <p
                    className="text-xs leading-relaxed"
                    style={{ color: "var(--muted)" }}
                  >
                    {step.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Disease Knowledge ── */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <h2
              className="text-lg font-bold"
              style={{ color: "var(--foreground)" }}
            >
              ความรู้เรื่องโรค
            </h2>
          </div>

          <div className="space-y-3">
            {diseases.map((disease, i) => (
              <details
                key={i}
                className="glass-card-static overflow-hidden group"
              >
                <summary className="p-4 cursor-pointer flex items-center gap-3 list-none [&::-webkit-details-marker]:hidden">
                  <Image
                    src={disease.img}
                    alt={disease.title}
                    width={40}
                    height={40}
                    className="object-contain flex-shrink-0"
                  />
                  <div className="flex-1">
                    <h3
                      className="text-sm font-bold"
                      style={{ color: "var(--foreground)" }}
                    >
                      {disease.title}
                    </h3>
                  </div>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--muted-light)"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="transition-transform duration-200 group-open:rotate-180"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </summary>

                <div
                  className="px-4 pb-4 border-t"
                  style={{ borderColor: disease.borderColor }}
                >
                  <p
                    className="text-xs mt-3 mb-3 leading-relaxed"
                    style={{ color: "var(--muted)" }}
                  >
                    {disease.desc}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {disease.symptoms.map((s, j) => (
                      <span
                        key={j}
                        className="text-xs px-2.5 py-1 rounded-full font-medium"
                        style={{
                          background: disease.bgColor,
                          color: disease.color,
                          border: `1px solid ${disease.borderColor}`,
                        }}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </details>
            ))}
          </div>
        </section>

        {/* ── Credits & Acknowledgment ── */}
        <section className="mb-4">
          <div
            className="glass-card-static p-5 text-center"
            style={{ background: "rgba(239, 246, 255, 0.7)" }}
          >
            <div className="w-30 h-30 mx-auto mb-3">
              <DotLottieReact src="/many-doctor.json" loop autoplay />
            </div>
            <h3
              className="text-sm font-bold mb-2"
              style={{ color: "var(--foreground)" }}
            >
              กิตติกรรมประกาศ
            </h3>
            <p
              className="text-xs leading-relaxed mb-3"
              style={{ color: "var(--muted)" }}
            >
              ขอขอบคุณ{" "}
              <strong style={{ color: "var(--primary-700)" }}>
                มหาวิทยาลัยเสฉวน (Sichuan University)
              </strong>{" "}
              สำหรับชุดข้อมูลตัวอย่างเสียงไอที่ใช้ในการพัฒนาและฝึกฝนโมเดล AI
              ซึ่งเป็นส่วนสำคัญในการวิจัยและพัฒนาระบบ iCough Analytic
            </p>
            <div
              className="flex items-center justify-center gap-2 text-xs"
              style={{ color: "var(--muted-light)" }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              <span>Research Collaboration</span>
            </div>
          </div>
        </section>

        {/* ── Disclaimer ── */}
        <section className="mb-2">
          <div
            className="rounded-xl p-4 text-center"
            style={{
              background: "var(--primary-50)",
              border: "1px solid var(--primary-100)",
            }}
          >
            <p
              className="text-xs leading-relaxed"
              style={{ color: "var(--muted)" }}
            >
              ⚠️ ระบบนี้เป็นเครื่องมือคัดกรองเบื้องต้นเท่านั้น
              ไม่ได้ใช้แทนการวินิจฉัยจากแพทย์
              <br />
              หากเด็กมีอาการผิดปกติ โปรดพาพบแพทย์ทันที
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
