"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import { Suspense } from "react";

/* ── Checklist Items based on project.md Decision Logic ── */
const checklistItems = [
  {
    id: "rapid-breathing",
    label: "หายใจเร็วผิดปกติ",
    description: "เด็กหายใจเร็วกว่าปกติ (นับอัตราการหายใจต่อนาที)",
    severity: "moderate",
    icon: "💨",
    detail:
      "เด็กอายุ < 2 เดือน: > 60 ครั้ง/นาที | 2-12 เดือน: > 50 ครั้ง/นาที | 1-5 ปี: > 40 ครั้ง/นาที",
  },
  {
    id: "chest-indrawing",
    label: "ซี่โครงบุ๋ม (Chest Indrawing)",
    description:
      "ผิวหนังบริเวณซี่โครงหรือใต้กระดูกสันอกจะบุ๋มเข้าไปขณะหายใจเข้า",
    severity: "critical",
    icon: "🫁",
    detail: "สัญญาณบ่งบอกว่าเด็กต้องออกแรงหายใจมากกว่าปกติ",
  },
  {
    id: "stridor",
    label: "เสียงหายใจเข้าผิดปกติ (Stridor)",
    description:
      "ได้ยินเสียงวี้ด ฮืด หรือเสียงสูง ๆ ขณะหายใจเข้า แม้เด็กนั่งเฉย ๆ",
    severity: "critical",
    icon: "🔊",
    detail:
      "Stridor ที่ได้ยินตอนเด็กอยู่เฉย ๆ บ่งบอกถึงการอุดกั้นทางเดินหายใจส่วนบน",
  },
  {
    id: "danger-signs",
    label: "สัญญาณอันตรายรุนแรง",
    description: "ดื่มนมไม่ได้ / ไม่ดูดนม / อาเจียน / ชัก / ซึมไม่รู้สึกตัว",
    severity: "critical",
    icon: "⚠️",
    detail:
      "สัญญาณเหล่านี้บ่งบอกว่าเด็กมีภาวะวิกฤตที่ต้องนำส่งโรงพยาบาลทันที",
  },
];

function AssessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Get AI result from URL parameters (sent from Line notification)
  const aiClass = searchParams.get("ai_class") || "";
  const aiScore = parseFloat(searchParams.get("score") || "0");

  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  const handleToggle = (id: string) => {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const checkedCount = Object.values(checked).filter(Boolean).length;
  const hasCritical = checklistItems
    .filter((item) => item.severity === "critical")
    .some((item) => checked[item.id]);

  const handleSubmit = () => {
    // Build query params for result page
    const params = new URLSearchParams();
    params.set("ai_class", aiClass || "unknown");
    params.set("score", aiScore.toString());

    // Pass checked items
    const checkedItems = Object.entries(checked)
      .filter(([, v]) => v)
      .map(([k]) => k);
    params.set("checked", checkedItems.join(","));
    params.set("has_critical", hasCritical.toString());

    router.push(`/result?${params.toString()}`);
  };

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
        <div className="max-w-lg mx-auto px-5 py-3 flex items-center justify-between">
          <h1
            className="text-lg font-bold"
            style={{ color: "var(--foreground)" }}
          >
            ประเมินอาการร่วม
          </h1>
          <div
            className="text-sm font-semibold px-3 py-1 rounded-full"
            style={{
              background: checkedCount > 0 ? "var(--primary-100)" : "#f1f5f9",
              color:
                checkedCount > 0 ? "var(--primary-700)" : "var(--muted-light)",
            }}
          >
            {checkedCount}/{checklistItems.length}
          </div>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-5 py-6">
        {/* ── AI Result Badge (if available) ── */}
        {aiClass && (
          <div
            className="glass-card-static p-4 mb-6 animate-fade-in-up"
            style={{ background: "rgba(239, 246, 255, 0.8)" }}
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 flex-shrink-0">
                <DotLottieReact src="/Lung infection.json" loop autoplay />
              </div>
              <div>
                <div
                  className="text-xs font-medium mb-0.5"
                  style={{ color: "var(--muted)" }}
                >
                  ผล AI วิเคราะห์เสียงไอ
                </div>
                <div
                  className="text-sm font-bold"
                  style={{ color: "var(--primary-700)" }}
                >
                  {aiClass === "pneumonia" && "ปอดบวม (Pneumonia)"}
                  {aiClass === "bronchitis" && "หลอดลมอักเสบ (Bronchitis)"}
                  {aiClass === "croup" && "ครูป (Croup)"}
                  {aiClass === "healthy" && "ปกติ (Healthy)"}
                  {!["pneumonia", "bronchitis", "croup", "healthy"].includes(
                    aiClass
                  ) && aiClass}
                </div>
                {aiScore > 0 && (
                  <div className="mt-1">
                    <div
                      className="h-1.5 rounded-full overflow-hidden"
                      style={{ background: "var(--primary-100)" }}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${aiScore * 100}%`,
                          background:
                            "linear-gradient(90deg, var(--primary-400), var(--primary-600))",
                        }}
                      />
                    </div>
                    <div
                      className="text-xs mt-0.5"
                      style={{ color: "var(--muted-light)" }}
                    >
                      ความมั่นใจ {(aiScore * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Instruction ── */}
        <div
          className="rounded-xl p-4 mb-6 animate-fade-in-up animate-delay-1"
          style={{
            background: "var(--primary-50)",
            border: "1px solid var(--primary-100)",
          }}
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 flex-shrink-0">
              <DotLottieReact src="/doctor describe.json" loop autoplay />
            </div>
            <div>
              <p
                className="text-sm font-semibold mb-1"
                style={{ color: "var(--primary-800)" }}
              >
                สังเกตอาการลูกน้อยของท่าน
              </p>
              <p
                className="text-xs leading-relaxed"
                style={{ color: "var(--muted)" }}
              >
                กรุณาตรวจสอบอาการของเด็กแล้วเลือกข้อที่ตรงกับอาการปัจจุบัน
                ข้อมูลนี้จะช่วยให้ระบบประเมินระดับความเสี่ยงได้แม่นยำขึ้น
              </p>
            </div>
          </div>
        </div>

        {/* ── Checklist ── */}
        <div className="space-y-3 mb-8">
          {checklistItems.map((item, i) => (
            <div
              key={item.id}
              className="animate-fade-in-up"
              style={{ animationDelay: `${0.15 + i * 0.1}s` }}
            >
              <div
                className="glass-card-static overflow-hidden transition-all duration-300"
                style={{
                  border: checked[item.id]
                    ? item.severity === "critical"
                      ? "2px solid var(--danger)"
                      : "2px solid var(--warning)"
                    : "1px solid rgba(255,255,255,0.6)",
                  background: checked[item.id]
                    ? item.severity === "critical"
                      ? "rgba(254,242,242,0.9)"
                      : "rgba(255,251,235,0.9)"
                    : "rgba(255,255,255,0.85)",
                }}
              >
                {/* Main checkbox area */}
                <label className="flex items-start gap-3 p-4 cursor-pointer">
                  <input
                    type="checkbox"
                    className="checkbox-medical mt-0.5"
                    checked={!!checked[item.id]}
                    onChange={() => handleToggle(item.id)}
                    id={`check-${item.id}`}
                    style={
                      checked[item.id]
                        ? {
                            background:
                              item.severity === "critical"
                                ? "var(--danger)"
                                : "var(--warning)",
                            borderColor:
                              item.severity === "critical"
                                ? "var(--danger)"
                                : "var(--warning)",
                          }
                        : {}
                    }
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-lg">{item.icon}</span>
                      <span
                        className="text-sm font-bold"
                        style={{ color: "var(--foreground)" }}
                      >
                        {item.label}
                      </span>
                      {item.severity === "critical" && (
                        <span
                          className="text-xs px-1.5 py-0.5 rounded-full font-semibold"
                          style={{
                            background: "#fef2f2",
                            color: "var(--danger)",
                            border: "1px solid #fecaca",
                          }}
                        >
                          วิกฤต
                        </span>
                      )}
                    </div>
                    <p
                      className="text-xs"
                      style={{ color: "var(--muted)", lineHeight: 1.6 }}
                    >
                      {item.description}
                    </p>
                  </div>
                </label>

                {/* Expandable detail */}
                <button
                  onClick={() =>
                    setExpandedItem(
                      expandedItem === item.id ? null : item.id
                    )
                  }
                  className="w-full px-4 pb-3 pt-0 flex items-center gap-1 text-xs font-medium transition-colors"
                  style={{ color: "var(--primary-500)" }}
                >
                  <span>
                    {expandedItem === item.id ? "ซ่อนรายละเอียด" : "ดูเพิ่มเติม"}
                  </span>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="transition-transform duration-200"
                    style={{
                      transform:
                        expandedItem === item.id
                          ? "rotate(180deg)"
                          : "rotate(0)",
                    }}
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>

                {expandedItem === item.id && (
                  <div
                    className="px-4 pb-4 animate-fade-in"
                    style={{
                      borderTop: "1px solid var(--card-border)",
                      paddingTop: "0.75rem",
                    }}
                  >
                    <p
                      className="text-xs leading-relaxed"
                      style={{ color: "var(--muted)" }}
                    >
                      ℹ️ {item.detail}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* ── Warning Banner ── */}
        {hasCritical && (
          <div
            className="risk-card risk-card-red mb-6 animate-fade-in-up flex items-center gap-3"
          >
            <span className="text-2xl">🚨</span>
            <div>
              <div
                className="text-sm font-bold"
                style={{ color: "#991b1b" }}
              >
                ตรวจพบอาการวิกฤต
              </div>
              <p className="text-xs mt-0.5" style={{ color: "#b91c1c" }}>
                หากเด็กมีอาการเหล่านี้ ควรนำส่งโรงพยาบาลทันที
              </p>
            </div>
          </div>
        )}

        {/* ── Submit Button ── */}
        <div className="text-center">
          <button
            onClick={handleSubmit}
            className="btn-primary w-full text-base"
            id="btn-submit-assessment"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            ดูผลสรุป
          </button>
          <p
            className="text-xs mt-3"
            style={{ color: "var(--muted-light)" }}
          >
            ระบบจะประเมินผลรวมจาก AI + อาการร่วมที่ท่านเลือก
          </p>
        </div>
      </div>
    </div>
  );
}

export default function AssessPage() {
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
      <AssessContent />
    </Suspense>
  );
}
