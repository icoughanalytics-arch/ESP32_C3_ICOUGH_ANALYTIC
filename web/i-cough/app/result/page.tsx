"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import Link from "next/link";

/* ──────────────────────────────────────────────
   Decision Logic from project.md
   ────────────────────────────────────────────── */
type RiskLevel = "red" | "yellow" | "green";

interface RiskResult {
  level: RiskLevel;
  title: string;
  description: string;
  advice: string;
}

function computeRisk(
  aiClass: string,
  aiScore: number,
  checkedItems: string[],
  hasCritical: boolean
): RiskResult {
  // Rule 1: Any disease + critical symptom (chest indrawing / stridor / danger signs)
  if (hasCritical) {
    return {
      level: "red",
      title: "อันตรายขั้นวิกฤต",
      description: "เด็กมีสัญญาณภาวะทางเดินหายใจล้มเหลวเฉียบพลัน",
      advice:
        "โปรดนำส่งห้องฉุกเฉินโรงพยาบาลที่ใกล้ที่สุดทันที",
    };
  }

  // Rule 2: Disease class >= 75% confidence
  const isDiseaseClass = ["pneumonia", "bronchitis", "croup"].includes(aiClass);
  if (isDiseaseClass && aiScore >= 0.75) {
    return {
      level: "red",
      title: "อันตรายขั้นวิกฤต",
      description: `AI ตรวจพบ ${getDiseaseName(aiClass)} ด้วยความมั่นใจ ${(aiScore * 100).toFixed(0)}%`,
      advice:
        "โปรดนำส่งห้องฉุกเฉินโรงพยาบาลที่ใกล้ที่สุดทันที",
    };
  }

  // Rule 3: Rapid breathing only
  if (checkedItems.includes("rapid-breathing")) {
    return {
      level: "yellow",
      title: "เฝ้าระวัง",
      description: "เด็กมีอาการหายใจเร็วผิดปกติ",
      advice:
        "แนะนำให้พาเด็กไปพบแพทย์เพื่อตรวจประเมินซ้ำภายใน 48 ชั่วโมง",
    };
  }

  // Rule 4: Disease class 50-74%
  if (isDiseaseClass && aiScore >= 0.5) {
    return {
      level: "yellow",
      title: "เฝ้าระวัง",
      description: `AI ตรวจพบ ${getDiseaseName(aiClass)} ด้วยความมั่นใจ ${(aiScore * 100).toFixed(0)}%`,
      advice:
        "แนะนำให้พบแพทย์ที่คลินิกหรือโรงพยาบาลชุมชนเพื่อรับการรักษา",
    };
  }

  // Rule 5: Healthy >= 80%
  if (aiClass === "healthy" && aiScore >= 0.8) {
    return {
      level: "green",
      title: "ความเสี่ยงต่ำ",
      description: "เด็กมีความเสี่ยงต่ำ ปลอดภัยจากภาวะปอดบวม",
      advice:
        "ให้ดูแลตามอาการที่บ้าน ดื่มน้ำอุ่นเพื่อละลายเสมหะ และมาพบแพทย์หากเด็กไข้ขึ้นหรือไอถี่ขึ้น",
    };
  }

  // Default: Edge case / ambiguous
  if (checkedItems.length === 0 && (!aiClass || aiClass === "unknown")) {
    return {
      level: "yellow",
      title: "ไม่มีข้อมูล AI",
      description: "ยังไม่มีผลวิเคราะห์จาก AI",
      advice:
        "กรุณาตรวจสอบอาการร่วมอีกครั้ง หรือรอผลวิเคราะห์เสียงไอจากระบบ",
    };
  }

  return {
    level: "yellow",
    title: "เฝ้าระวัง",
    description: "ผลก้ำกึ่ง ระบบแนะนำให้ตรวจสอบเพิ่มเติม",
    advice:
      "แนะนำให้ทำ Checklist ตรวจสอบอาการอีกครั้ง หรือพาเด็กพบแพทย์เพื่อความปลอดภัย",
  };
}

function getDiseaseName(cls: string): string {
  const map: Record<string, string> = {
    pneumonia: "ปอดบวม (Pneumonia)",
    bronchitis: "หลอดลมอักเสบ (Bronchitis)",
    croup: "ครูป (Croup)",
    healthy: "ปกติ (Healthy)",
  };
  return map[cls] || cls;
}

const symptomLabels: Record<string, string> = {
  "rapid-breathing": "หายใจเร็วผิดปกติ",
  "chest-indrawing": "ซี่โครงบุ๋ม",
  stridor: "เสียงหายใจเข้าผิดปกติ (Stridor)",
  "danger-signs": "สัญญาณอันตรายรุนแรง",
};

/* ── Signal Light Component ── */
function SignalLight({ level }: { level: RiskLevel }) {
  const config = {
    red: {
      className: "signal-red",
      animation: "/Lung infection.json",
      pulse: true,
    },
    yellow: {
      className: "signal-yellow",
      animation: "/Describe a disease.json",
      pulse: true,
    },
    green: {
      className: "signal-green",
      animation: "/doctor run.json",
      pulse: false,
    },
  }[level];

  return (
    <div className="flex flex-col items-center gap-4 mb-6 animate-fade-in-up">
      {/* Signal circle */}
      <div
        className={`w-28 h-28 rounded-full ${config.className} flex items-center justify-center`}
        style={{
          animation: config.pulse ? "pulse-gentle 2s ease-in-out infinite" : "none",
        }}
      >
        <div className="w-20 h-20">
          <DotLottieReact src={config.animation} loop autoplay />
        </div>
      </div>
    </div>
  );
}

function ResultContent() {
  const searchParams = useSearchParams();

  const aiClass = searchParams.get("ai_class") || "";
  const aiScore = parseFloat(searchParams.get("score") || "0");
  const checkedParam = searchParams.get("checked") || "";
  const checkedItems = checkedParam ? checkedParam.split(",") : [];
  const hasCritical = searchParams.get("has_critical") === "true";

  const risk = computeRisk(aiClass, aiScore, checkedItems, hasCritical);

  const riskCardClass = {
    red: "risk-card risk-card-red",
    yellow: "risk-card risk-card-yellow",
    green: "risk-card risk-card-green",
  }[risk.level];

  const riskEmoji = { red: "🔴", yellow: "🟡", green: "🟢" }[risk.level];

  const riskTitleColor = {
    red: "#991b1b",
    yellow: "#92400e",
    green: "#166534",
  }[risk.level];

  const riskDescColor = {
    red: "#b91c1c",
    yellow: "#a16207",
    green: "#15803d",
  }[risk.level];

  return (
    <div className="bg-gradient-medical min-h-screen">
      {/* ── Header ── */}
      <div
        className="sticky top-0 z-40"
        style={{
          background: "rgba(255,255,255,0.9)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--card-border)",
        }}
      >
        <div className="max-w-lg mx-auto px-5 py-3">
          <h1
            className="text-lg font-bold text-center"
            style={{ color: "var(--foreground)" }}
          >
            ผลสรุปการประเมิน
          </h1>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-5 py-6">
        {/* ── Signal Light ── */}
        <SignalLight level={risk.level} />

        {/* ── Risk Card ── */}
        <div
          className={`${riskCardClass} mb-6 animate-fade-in-up animate-delay-2`}
        >
          <div className="text-center">
            <span className="text-3xl">{riskEmoji}</span>
            <h2
              className="text-xl font-extrabold mt-2"
              style={{ color: riskTitleColor }}
            >
              {risk.title}
            </h2>
            <p
              className="text-sm mt-2 font-medium"
              style={{ color: riskDescColor }}
            >
              {risk.description}
            </p>
          </div>
        </div>

        {/* ── Advice Card ── */}
        <div className="glass-card-static p-5 mb-6 animate-fade-in-up animate-delay-3">
          <div className="flex items-start gap-3">
            <div className="w-12 h-12 flex-shrink-0">
              <DotLottieReact src="/doctor describe.json" loop autoplay />
            </div>
            <div>
              <h3
                className="text-sm font-bold mb-1"
                style={{ color: "var(--foreground)" }}
              >
                คำแนะนำ
              </h3>
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--muted)" }}
              >
                {risk.advice}
              </p>
            </div>
          </div>
        </div>

        {/* ── AI Analysis Detail ── */}
        {aiClass && aiClass !== "unknown" && (
          <div className="glass-card-static p-5 mb-6 animate-fade-in-up animate-delay-4">
            <h3
              className="text-sm font-bold mb-3 flex items-center gap-2"
              style={{ color: "var(--foreground)" }}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--primary-600)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
              ผลวิเคราะห์จาก AI
            </h3>

            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span
                  className="text-sm"
                  style={{ color: "var(--muted)" }}
                >
                  คลาสโรค
                </span>
                <span
                  className="text-sm font-bold"
                  style={{ color: "var(--primary-700)" }}
                >
                  {getDiseaseName(aiClass)}
                </span>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <span
                    className="text-sm"
                    style={{ color: "var(--muted)" }}
                  >
                    ความมั่นใจ
                  </span>
                  <span
                    className="text-sm font-bold"
                    style={{ color: "var(--primary-700)" }}
                  >
                    {(aiScore * 100).toFixed(1)}%
                  </span>
                </div>
                <div
                  className="h-2.5 rounded-full overflow-hidden"
                  style={{ background: "var(--primary-100)" }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-1000 ease-out"
                    style={{
                      width: `${aiScore * 100}%`,
                      background:
                        aiScore >= 0.75
                          ? "linear-gradient(90deg, #ef4444, #dc2626)"
                          : aiScore >= 0.5
                            ? "linear-gradient(90deg, #f59e0b, #d97706)"
                            : "linear-gradient(90deg, var(--primary-400), var(--primary-600))",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Checked Symptoms ── */}
        {checkedItems.length > 0 && (
          <div className="glass-card-static p-5 mb-6 animate-fade-in-up animate-delay-5">
            <h3
              className="text-sm font-bold mb-3 flex items-center gap-2"
              style={{ color: "var(--foreground)" }}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--primary-600)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
              อาการร่วมที่พบ
            </h3>

            <div className="space-y-2">
              {checkedItems.map((item) => {
                const isCritical = [
                  "chest-indrawing",
                  "stridor",
                  "danger-signs",
                ].includes(item);
                return (
                  <div
                    key={item}
                    className="flex items-center gap-2 text-sm rounded-lg px-3 py-2"
                    style={{
                      background: isCritical ? "#fef2f2" : "#fffbeb",
                      border: `1px solid ${isCritical ? "#fecaca" : "#fde68a"}`,
                    }}
                  >
                    <span>{isCritical ? "🔴" : "🟡"}</span>
                    <span
                      className="font-medium"
                      style={{
                        color: isCritical ? "#991b1b" : "#92400e",
                      }}
                    >
                      {symptomLabels[item] || item}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Disclaimer ── */}
        <div
          className="rounded-xl p-4 mb-6 text-center"
          style={{
            background: "var(--primary-50)",
            border: "1px solid var(--primary-100)",
          }}
        >
          <p
            className="text-xs leading-relaxed"
            style={{ color: "var(--muted)" }}
          >
            ⚠️ ผลนี้เป็นการประเมินเบื้องต้นด้วย AI เท่านั้น
            ไม่ใช่การวินิจฉัยทางการแพทย์
            <br />
            โปรดปรึกษาแพทย์เพื่อการวินิจฉัยที่แม่นยำ
          </p>
        </div>

        {/* ── Action Buttons ── */}
        <div className="space-y-3">
          <Link href="/assess" className="btn-outline w-full text-base">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            ประเมินอาการอีกครั้ง
          </Link>
          <Link href="/" className="btn-outline w-full text-base">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            กลับหน้าแรก
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ResultPage() {
  return (
    <Suspense
      fallback={
        <div className="bg-gradient-medical min-h-screen flex items-center justify-center">
          <div className="w-20 h-20">
            <DotLottieReact src="/heart.json" loop autoplay />
          </div>
        </div>
      }
    >
      <ResultContent />
    </Suspense>
  );
}
