"use client";

import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import Link from "next/link";

type RiskLevel = "low" | "moderate" | "high";
type DiseaseKey = "pneumonia" | "croup" | "bronchitis" | "normal";

type CoughRecord = {
  id: string;
  device_id: string | null;
  spectrum_path: string | null;
  audio_path: string | null;
  pneumonia_score: number | null;
  croup_score: number | null;
  bronchitis_score: number | null;
  normal_score: number | null;
  risk_level: RiskLevel | null;
  created_at: string;
  is_poc: boolean | null;
};

type SummaryRecord = {
  id: string;
  device_id: string;
  cough_ids: string[];
  start_at: string;
  end_at: string;
  checklist: {
    fastBreathing: boolean;
    chestRetraction: boolean;
    stridor: boolean;
    dangerSign: boolean;
    source_type: string;
    source_title: string;
  };
  summary_result: {
    event_count: number;
    risk_counts: { high: number; moderate: number; low: number };
    average_scores: { pneumonia: number; croup: number; bronchitis: number; normal: number };
    top_disease: string | null;
    top_score: number | null;
  };
  risk_level: RiskLevel;
  created_at: string;
};

const DEFAULT_DEVICE_ID = "22222222-2222-2222-2222-222222222222";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "",
);

const diseaseLabels: Record<DiseaseKey, string> = {
  pneumonia: "ปอดบวม (Pneumonia)",
  croup: "ครูป (Croup)",
  bronchitis: "หลอดลมอักเสบ (Bronchitis)",
  normal: "ปกติ (Healthy)",
};

function formatThaiTime(value: string | Date) {
  return new Intl.DateTimeFormat("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(new Date(value));
}

function formatShortTime(value: string | Date) {
  return new Intl.DateTimeFormat("th-TH", {
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(new Date(value));
}

export default function ResultHistoryPage() {
  const [history, setHistory] = useState<SummaryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHistory() {
      setLoading(true);
      setError(null);

      const { data, error: queryError } = await supabase
        .from("summary_record")
        .select("*")
        .eq("device_id", DEFAULT_DEVICE_ID)
        .order("created_at", { ascending: false });

      if (queryError) {
        setError(queryError.message);
      } else {
        setHistory((data ?? []) as SummaryRecord[]);
      }
      setLoading(false);
    }

    loadHistory();
  }, []);

  return (
    <main className="min-h-screen bg-gradient-medical">
      {/* Sticky Header */}
      <div
        className="sticky top-0 z-40 bg-white/90 backdrop-blur-xl border-b border-slate-100 shadow-sm"
      >
        <div className="max-w-lg mx-auto px-5 py-4 flex items-center justify-between">
          <h1 className="text-lg font-extrabold text-slate-900">
            📊 ประวัติการประเมินเสียงไอ
          </h1>
          <Link
            href="/assess"
            className="text-xs font-bold text-sky-600 bg-sky-50 hover:bg-sky-100/80 px-3 py-2 rounded-lg transition"
          >
            ประเมินเพิ่ม
          </Link>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-5 py-6 space-y-6">

        {/* ── Section 1: ตารางสรุปการแสดงผล (Reference Table ให้หมอดู) ── */}
        <div className="glass-card-static p-4 border border-slate-200 bg-white shadow-md overflow-hidden rounded-2xl">
          <h2 className="text-sm font-extrabold text-slate-900 mb-3 flex items-center gap-1.5 border-b pb-2">
            <span>📋 ตารางอ้างอิงเกณฑ์ประเมินสัญญาณไฟ 3 สี (WHO)</span>
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-[10px]">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100 text-slate-600 font-bold">
                  <th className="p-2 border-r border-slate-100">ด่าน 1: ผล AI</th>
                  <th className="p-2 border-r border-slate-100">ด่าน 2: Checklist</th>
                  <th className="p-2 text-center">สัญญาณไฟบนหน้าจอ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700 font-semibold leading-relaxed">
                <tr>
                  <td className="p-2 border-r border-slate-100">โรคใดก็ได้ (ไม่สนใจคะแนน)</td>
                  <td className="p-2 border-r border-slate-100 text-red-600">ติ๊กถูก ซี่โครงบุ๋ม / Stridor / อันตรายรุนแรง (≥1 ข้อ)</td>
                  <td className="p-2 text-center bg-red-50/50">
                    <span className="inline-flex items-center gap-1 text-red-700 font-extrabold justify-center w-full">
                      <span className="h-3 w-3 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)] animate-pulse" />
                      แดง (สูง/วิกฤต)
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="p-2 border-r border-slate-100 text-red-600 font-bold">กลุ่มโรค (≥ 75%)</td>
                  <td className="p-2 border-r border-slate-100">ไม่ติ๊ก หรือ ติ๊กหายใจเร็ว</td>
                  <td className="p-2 text-center bg-red-50/50">
                    <span className="inline-flex items-center gap-1 text-red-700 font-extrabold justify-center w-full">
                      <span className="h-3 w-3 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]" />
                      แดง (สูง/วิกฤต)
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="p-2 border-r border-slate-100 text-amber-600">กลุ่มโรค (50% - 74%)</td>
                  <td className="p-2 border-r border-slate-100">ไม่ได้ติ๊กถูกในข้อใดเลย</td>
                  <td className="p-2 text-center bg-amber-50/50">
                    <span className="inline-flex items-center gap-1 text-amber-700 font-extrabold justify-center w-full">
                      <span className="h-3 w-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                      เหลือง (ปานกลาง)
                    </span>
                  </td>
                </tr>
                <tr className="bg-yellow-50/40">
                  <td className="p-2 border-r border-slate-100 text-amber-700 font-bold">ทุกโรคคะแนนเท่ากันก้ำกึ่ง</td>
                  <td className="p-2 border-r border-slate-100">ไม่ได้ติ๊กถูกในข้อใดเลย</td>
                  <td className="p-2 text-center bg-amber-50/50">
                    <span className="inline-flex items-center gap-1 text-amber-700 font-extrabold justify-center w-full">
                      <span className="h-3 w-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                      เหลือง (ปานกลาง)
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="p-2 border-r border-slate-100">โรคใดก็ได้</td>
                  <td className="p-2 border-r border-slate-100 text-amber-600">ติ๊กถูก หายใจเร็ว (ข้อเดียว)</td>
                  <td className="p-2 text-center bg-amber-50/50">
                    <span className="inline-flex items-center gap-1 text-amber-700 font-extrabold justify-center w-full">
                      <span className="h-3 w-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                      เหลือง (ปานกลาง)
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="p-2 border-r border-slate-100 text-emerald-600">Healthy (≥ 80%)</td>
                  <td className="p-2 border-r border-slate-100">ไม่ได้ติ๊กเลยสักข้อ (ปกติทั้งหมด)</td>
                  <td className="p-2 text-center bg-emerald-50/50">
                    <span className="inline-flex items-center gap-1 text-emerald-700 font-extrabold justify-center w-full">
                      <span className="h-3 w-3 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
                      เขียว (ความเสี่ยงต่ำ)
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Section 2: รายการการ์ดประวัติประเมิน ── */}
        <div className="space-y-6">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider pl-1">
            บันทึกประวัติความเสี่ยงทั้งหมด (ประมวลผลข้อมูลส่งหมอ)
          </div>

          {loading && (
            <div className="glass-card-static p-6 text-center text-sm text-slate-500 animate-pulse">
              กำลังดึงประวัติการประเมินจากฐานข้อมูล...
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              เกิดข้อผิดพลาด: {error}
            </div>
          )}

          {!loading && !error && history.length === 0 && (
            <div className="glass-card-static p-8 text-center text-slate-500 space-y-4">
              <p className="text-sm">ยังไม่มีบันทึกประวัติการประเมินอาการร่วม</p>
              <Link
                href="/assess"
                className="inline-block rounded-xl bg-sky-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-sky-700 transition"
              >
                ประเมินด่าน Checklist ครั้งแรก
              </Link>
            </div>
          )}

          {!loading && !error && history.length > 0 && (
            <div className="space-y-6">
              {history.map((record) => (
                <HistoryCard key={record.id} record={record} />
              ))}
            </div>
          )}
        </div>

        {/* Footer Navigation Buttons */}
        <div className="mt-8 space-y-3">
          <Link href="/assess" className="btn-outline w-full text-sm font-extrabold py-3">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1.5"
            >
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            ประเมินอาการและจดอาการร่วมเพิ่ม
          </Link>
          <Link href="/" className="btn-outline w-full text-sm font-extrabold py-3">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1.5"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            กลับหน้าแรกสุด
          </Link>
        </div>
      </div>
    </main>
  );
}

function HistoryCard({ record }: { record: SummaryRecord }) {
  const finalRisk = record.risk_level;
  const [coughs, setCoughs] = useState<CoughRecord[]>([]);
  const [loadingCoughs, setLoadingCoughs] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // ดึงข้อมูลรูปภาพและไฟล์เสียงสำหรับไอแต่ละครั้งตาม cough_ids ของการ์ดนั้นๆ
  useEffect(() => {
    if (!showDetails || coughs.length > 0 || !record.cough_ids || record.cough_ids.length === 0) return;

    async function fetchCoughs() {
      setLoadingCoughs(true);
      const { data, error } = await supabase
        .from("cough_record")
        .select("*")
        .in("id", record.cough_ids)
        .order("created_at", { ascending: true });

      if (!error && data) {
        setCoughs(data as CoughRecord[]);
      }
      setLoadingCoughs(false);
    }

    fetchCoughs();
  }, [showDetails, record.cough_ids, coughs.length]);

  // รูปแบบสีการ์ด
  const cardStyles = {
    high: {
      border: "border-red-200",
      bg: "bg-white",
      lightColor: "bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.7)] animate-pulse",
      riskText: "ความเสี่ยงสูง / วิกฤต",
      riskTextColor: "text-red-700 bg-red-50 border-red-100",
      advice: "อันตรายขั้นวิกฤต! เด็กมีสัญญาณภาวะทางเดินหายใจล้มเหลวเฉียบพลัน โปรดนำเด็กส่งห้องฉุกเฉินของโรงพยาบาลที่ใกล้ที่สุดทันที"
    },
    moderate: {
      border: "border-amber-200",
      bg: "bg-white",
      lightColor: "bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.7)]",
      riskText: "เฝ้าระวัง / ปานกลาง",
      riskTextColor: "text-amber-700 bg-amber-50 border-amber-100",
      advice: "เฝ้าระวัง: เด็กมีภาวะหายใจเร็วเข้าเกณฑ์โรคปอดบวม แนะนำให้พาเด็กไปพบแพทย์ที่คลินิกหรือโรงพยาบาลชุมชนเพื่อรับยาปฏิชีวนะชนิดกิน และควรทำประเมินซ้ำภายใน 48 ชั่วโมง"
    },
    low: {
      border: "border-emerald-200",
      bg: "bg-white",
      lightColor: "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.7)]",
      riskText: "ความเสี่ยงต่ำ / ปลอดภัย",
      riskTextColor: "text-emerald-700 bg-emerald-50 border-emerald-100",
      advice: "เด็กมีความเสี่ยงต่ำ ปลอดภัยจากภาวะปอดบวม ให้ดูแลตามอาการที่บ้าน เช่น ดื่มน้ำอุ่นเพื่อละลายเสมหะ และทำประเมินซ้ำหากเด็กเริ่มไอถี่ขึ้น"
    }
  }[finalRisk] || {
    border: "border-slate-200",
    bg: "bg-white",
    lightColor: "bg-slate-400 shadow-[0_0_8px_rgba(148,163,184,0.5)]",
    riskText: "ไม่ทราบระดับความเสี่ยง",
    riskTextColor: "text-slate-700 bg-slate-50 border-slate-100",
    advice: "ยังไม่ได้รับการวินิจฉัยอย่างแน่ชัด"
  };

  const symptomsFound: string[] = [];
  if (record.checklist?.fastBreathing) symptomsFound.push("หายใจเร็วผิดปกติ");
  if (record.checklist?.chestRetraction) symptomsFound.push("ทรวงอกหรือซี่โครงบุ๋ม 🔴");
  if (record.checklist?.stridor) symptomsFound.push("เสียงหายใจเข้าแหลม (Stridor) 🔴");
  if (record.checklist?.dangerSign) symptomsFound.push("สัญญาณอันตรายรุนแรง 🔴");

  // พล็อตกราฟ SVG แสดงช่วงเวลาและความถี่การไอของกลุ่มนี้ (Timeline)
  const renderCoughTimeline = () => {
    if (record.cough_ids.length <= 1) return null;
    const minTime = new Date(record.start_at).getTime();
    const maxTime = new Date(record.end_at).getTime();
    const durationMs = maxTime - minTime || 1;

    // หาจุดพล็อตเปอร์เซ็นต์ตามค่า created_at ของข้อมูลไอแต่ละครั้ง
    // ใช้ record.cough_ids ในการพล็อตเส้นจำลอง หรือข้อมูลจริงของ coughs ถ้าโหลดแล้ว
    const plotTimes = coughs.length > 0
      ? coughs.map(c => new Date(c.created_at).getTime())
      : [minTime, ...record.cough_ids.slice(1, -1).map((_, idx) => minTime + (durationMs * (idx + 1)) / record.cough_ids.length), maxTime]; // จำลองจุดพล็อตก่อนดึงจริง

    return (
      <div className="rounded-xl border border-slate-150 bg-slate-50/40 p-3 space-y-2 mt-4">
        <div className="text-[11px] font-bold text-slate-800 flex justify-between">
          <span>📈 กราฟประเมินความถี่การไอตาม Timeline (ส่งหมอดู)</span>
          <span className="text-sky-700 font-bold">รวม {record.cough_ids.length} ครั้ง</span>
        </div>

        {/* SVG Timeline plotting */}
        <div className="relative pt-3 pb-5">
          <svg className="w-full h-8" overflow="visible">
            {/* เส้นแนวขวางหลักของแกนไทม์ไลน์ */}
            <line x1="5%" y1="50%" x2="95%" y2="50%" stroke="#cbd5e1" strokeWidth="2.5" strokeLinecap="round" />

            {/* เส้นเวลาแบ่งย่อย */}
            <line x1="5%" y1="35%" x2="5%" y2="65%" stroke="#94a3b8" strokeWidth="1.5" />
            <line x1="50%" y1="40%" x2="50%" y2="60%" stroke="#cbd5e1" strokeWidth="1" />
            <line x1="95%" y1="35%" x2="95%" y2="65%" stroke="#94a3b8" strokeWidth="1.5" />

            {/* จุดพล็อตเวลาการไอแต่ละครั้ง */}
            {plotTimes.map((time, idx) => {
              const diffMs = time - minTime;
              const pct = (diffMs / durationMs) * 90 + 5; // กราวด์ให้อยู่ระหว่าง 5% ถึง 95%
              return (
                <g key={idx} className="group">
                  <circle
                    cx={`${pct}%`}
                    cy="50%"
                    r="5.5"
                    fill="#0284c7"
                    className="cursor-pointer hover:r-7 transition-all shadow-[0_0_8px_rgba(2,132,199,0.7)]"
                  />
                  {/* ข้อมูล Tooltip เวลาอย่างย่อเหนือจุด */}
                  <text
                    x={`${pct}%`}
                    y="10"
                    textAnchor="middle"
                    fill="#475569"
                    fontSize="8px"
                    fontWeight="bold"
                  >
                    {formatShortTime(new Date(time))}
                  </text>
                </g>
              );
            })}
          </svg>
          {/* ข้อมูลเวลากำกับซ้าย-ขวา */}
          <div className="flex justify-between text-[9px] text-slate-500 font-bold px-1 mt-1">
            <span>{formatShortTime(record.start_at)}</span>
            <span className="text-slate-400">← แกนเวลาไอจริงความถี่ →</span>
            <span>{formatShortTime(record.end_at)}</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`rounded-2xl border ${cardStyles.border} ${cardStyles.bg} shadow-md overflow-hidden transition-all duration-300 hover:shadow-lg animate-fade-in-up`}>
      {/* Card Header with Signal Light */}
      <div className="border-b border-slate-100 px-4 py-3.5 bg-slate-50/50 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {record.checklist?.source_type === "section_average" ? "ประเมินเฉลี่ยเซ็กชัน" : "ประเมินรายเหตุการณ์ไอ"}
          </div>
          <h2 className="text-sm font-extrabold text-slate-800 truncate mt-0.5">
            {record.checklist?.source_title || "การประเมินเสียงไอ"}
          </h2>
        </div>

        {/* Signal Light Indicator (ไฟสัญญาณ) */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${cardStyles.riskTextColor}`}>
            {cardStyles.riskText}
          </span>
          <div className={`h-5 w-5 rounded-full ${cardStyles.lightColor}`} />
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Time info and Event count */}
        <div className="flex justify-between items-center text-xs text-slate-500">
          <span>เวลาประเมิน: {formatThaiTime(record.created_at)}</span>
          <span className="font-semibold text-slate-700 bg-slate-100 px-2.5 py-0.5 rounded-md">
            ไอ {record.summary_result?.event_count ?? 1} ครั้ง
          </span>
        </div>

        {/* AI Scores Summary */}
        <div className="rounded-xl bg-slate-50/70 border border-slate-100 p-3 space-y-2.5">
          <div className="text-xs font-bold text-slate-800 flex justify-between">
            <span>คะแนนเฉลี่ยผลตรวจ AI:</span>
            {record.summary_result?.top_disease && (
              <span className="text-sky-700 font-extrabold">
                {diseaseLabels[record.summary_result.top_disease as DiseaseKey] || record.summary_result.top_disease}: {((record.summary_result.top_score ?? 0) * 100).toFixed(0)}%
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <ScoreIndicator label="ปอดบวม" value={record.summary_result?.average_scores?.pneumonia} />
            <ScoreIndicator label="ครูป" value={record.summary_result?.average_scores?.croup} />
            <ScoreIndicator label="หลอดลมฯ" value={record.summary_result?.average_scores?.bronchitis} />
            <ScoreIndicator label="ปกติ" value={record.summary_result?.average_scores?.normal} />
          </div>
        </div>

        {/* Checklist Symptoms found */}
        <div className="space-y-1.5">
          <div className="text-xs font-bold text-slate-800">อาการประเมินร่วมทางกายภาพ:</div>
          {symptomsFound.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {symptomsFound.map((symptom) => (
                <span
                  key={symptom}
                  className={`text-[10px] font-bold px-2 py-1 rounded-md border ${symptom.includes("🔴")
                      ? "bg-red-50 text-red-700 border-red-150 animate-pulse"
                      : "bg-amber-50 text-amber-700 border-amber-150"
                    }`}
                >
                  {symptom.replace(" 🔴", "")}
                </span>
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-emerald-600 bg-emerald-50/50 border border-emerald-100 rounded-lg px-2.5 py-1.5 font-semibold">
              🟢 แข็งแรงดี: ไม่พบอาการประเมินผิดปกติใดๆ ทางเช็กลิสต์
            </div>
          )}
        </div>

        {/* Medical Advice Box */}
        <div className="border-t border-slate-100 pt-3">
          <div className="text-[11px] text-slate-700 font-semibold bg-sky-50/40 rounded-xl px-3 py-2.5 border border-sky-100/50 leading-relaxed">
            💡 <strong className="font-extrabold text-slate-800">คำแนะนำ:</strong> {cardStyles.advice}
          </div>
        </div>

        {/* SVG Timeline rendering (กราฟพล็อตเวลา) */}
        {renderCoughTimeline()}

        {/* ── Toggleable Details (รูป และเสียง ที่เก็บซ่อนไว้ส่งหมอดู) ── */}
        <div className="border-t border-slate-100 pt-3">
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="w-full flex items-center justify-between rounded-xl border border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-slate-50 px-3 py-2.5 text-xs font-bold text-slate-700 transition active:scale-95 shadow-sm"
          >
            <span>📁 {showDetails ? "ซ่อนข้อมูลรูปและเสียงไอ (Hide details)" : "📂 แสดงข้อมูลรูปและเสียงไอ (Show details)"}</span>
            <svg
              className={`h-3 w-3 transform transition-transform duration-200 ${showDetails ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={3}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showDetails && (
            <div className="mt-3 space-y-3 animate-fade-in border-t border-slate-100 pt-3">
              {loadingCoughs ? (
                <div className="text-center py-4 text-xs text-slate-500 animate-pulse">
                  กำลังโหลดข้อมูลเสียงและสเปกตรัมจาก Supabase...
                </div>
              ) : coughs.length === 0 ? (
                <div className="text-center py-2 text-[11px] text-slate-400">
                  ไม่พบไฟล์เสียงเชื่อมโยงในระบบ
                </div>
              ) : (
                <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                  {coughs.map((cough, idx) => (
                    <div
                      key={cough.id}
                      className="rounded-xl border border-slate-100 bg-white p-3 space-y-2.5 shadow-inner"
                    >
                      <div className="flex justify-between items-center text-[10px] font-bold text-slate-500">
                        <span>ไอครั้งที่ {idx + 1} | ID: ...{cough.id.slice(-8)}</span>
                        <span className="text-sky-700 bg-sky-50 px-2 py-0.5 rounded">{formatShortTime(cough.created_at)}</span>
                      </div>

                      {cough.spectrum_path && (
                        <div className="relative">
                          <img
                            src={cough.spectrum_path}
                            alt="Mel spectrogram ของหมอ"
                            className="w-full h-16 object-cover rounded-lg border border-slate-200 shadow-sm"
                          />
                          <div className="absolute bottom-1 right-1 bg-black/60 text-[8px] text-white px-1.5 py-0.5 rounded font-semibold">
                            Spectrogram
                          </div>
                        </div>
                      )}

                      {cough.audio_path && (
                        <audio
                          src={cough.audio_path}
                          controls
                          className="w-full h-8 max-h-8 text-xs scale-98"
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

function ScoreIndicator({ label, value }: { label: string; value: number | undefined | null }) {
  const percent = ((value ?? 0) * 100).toFixed(0);
  return (
    <div className="flex justify-between items-center bg-white border border-slate-100 rounded-lg px-2 py-1.5 shadow-sm">
      <span className="text-slate-500 font-semibold">{label}</span>
      <span className="text-slate-800 font-extrabold">{percent}%</span>
    </div>
  );
}
