"use client";

import { useEffect, useMemo, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import ChecklistModal, { ChecklistState, ChecklistTarget } from "./ChecklistModal";

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
  noti_time: string | null;
  risk_level: RiskLevel | null;
  created_at: string;
  is_poc: boolean | null;
};


const DEFAULT_DEVICE_ID = "22222222-2222-2222-2222-222222222222";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "",
);

const diseaseLabels: Record<DiseaseKey, string> = {
  pneumonia: "Pneumonia",
  croup: "Croup",
  bronchitis: "Bronchitis",
  normal: "Normal",
};

function getNightStart(now = new Date()) {
  const start = new Date(now);
  start.setHours(19, 0, 0, 0);
  if (now.getHours() < 19) start.setDate(start.getDate() - 1);
  return start;
}

function formatThaiTime(value: string | Date) {
  return new Intl.DateTimeFormat("th-TH", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Bangkok",
  }).format(new Date(value));
}

function riskWeight(risk: RiskLevel | null) {
  if (risk === "high") return 3;
  if (risk === "moderate") return 2;
  if (risk === "low") return 1;
  return 0;
}

function riskClass(risk: RiskLevel | null) {
  if (risk === "high") return "bg-red-50 text-red-700 border-red-200";
  if (risk === "moderate") return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-emerald-50 text-emerald-700 border-emerald-200";
}

function getTopDisease(record: CoughRecord) {
  const scores: Array<[DiseaseKey, number]> = [
    ["pneumonia", record.pneumonia_score ?? 0],
    ["croup", record.croup_score ?? 0],
    ["bronchitis", record.bronchitis_score ?? 0],
    ["normal", record.normal_score ?? 0],
  ];
  return scores.sort((a, b) => b[1] - a[1])[0];
}

function getSummary(records: CoughRecord[]) {
  const count = records.length || 1;
  const avg: Record<DiseaseKey, number> = {
    pneumonia: records.reduce((sum, r) => sum + (r.pneumonia_score ?? 0), 0) / count,
    croup: records.reduce((sum, r) => sum + (r.croup_score ?? 0), 0) / count,
    bronchitis: records.reduce((sum, r) => sum + (r.bronchitis_score ?? 0), 0) / count,
    normal: records.reduce((sum, r) => sum + (r.normal_score ?? 0), 0) / count,
  };
  const top = (Object.entries(avg) as Array<[DiseaseKey, number]>).sort(
    (a, b) => b[1] - a[1],
  )[0];
  const riskCounts = {
    high: records.filter((r) => r.risk_level === "high").length,
    moderate: records.filter((r) => r.risk_level === "moderate").length,
    low: records.filter((r) => r.risk_level === "low").length,
  };
  const worstRisk =
    records
      .map((r) => r.risk_level)
      .sort((a, b) => riskWeight(b) - riskWeight(a))[0] ?? null;

  return { avg, top, riskCounts, worstRisk };
}

function computeFinalRisk(records: CoughRecord[], checklist: ChecklistState): RiskLevel {
  const summary = getSummary(records);
  const avgP = summary.avg.pneumonia;
  const avgC = summary.avg.croup;
  const avgB = summary.avg.bronchitis;
  const avgN = summary.avg.normal;

  // 1. ไฟสีแดง: ความเสี่ยงสูง / วิกฤต (High Risk)
  // - เงื่อนไขข้ามสาย (Override Logic): ติ๊ก ซี่โครงบุ๋ม หรือ Stridor หรือ สัญญาณอันตรายรุนแรง
  if (checklist.chestRetraction || checklist.stridor || checklist.dangerSign) {
    return "high";
  }
  // - เงื่อนไข AI: วิเคราะห์ได้กลุ่มโรค (ปอดบวม หรือ ครูป หรือ หลอดลมอักเสบ) เฉลี่ยตั้งแต่ 75% ขึ้นไป
  if (avgP >= 0.75 || avgC >= 0.75 || avgB >= 0.75) {
    return "high";
  }

  // 2. ไฟสีเหลือง: เฝ้าระวัง / ความเสี่ยงปานกลาง (Moderate Risk)
  // - เงื่อนไข Checklist: ติ๊ก "หายใจเร็วเกินเกณฑ์อายุ" เพียงข้อเดียว (โดยไม่มีอาการรุนแรงอื่นในกลุ่มไฟแดง)
  if (checklist.fastBreathing) {
    return "moderate";
  }
  // - เงื่อนไข AI: วิเคราะห์ได้กลุ่มโรค (ปอดบวม หรือ ครูป หรือ หลอดลมอักเสบ) เฉลี่ยอยู่ระหว่าง 50% - 74%
  if (
    (avgP >= 0.50 && avgP < 0.75) ||
    (avgC >= 0.50 && avgC < 0.75) ||
    (avgB >= 0.50 && avgB < 0.75)
  ) {
    return "moderate";
  }
  // - เงื่อนไขกรณีสับสน (Edge Case): คะแนน AI กลุ่มโรค ออกมาก้ำกึ่งใกล้เคียงกันมาก (เช่น 30% เท่ากันเป๊ะ หรือต่างกันไม่เกิน 2%)
  const hasDiseaseScores = avgP > 0 || avgC > 0 || avgB > 0;
  const isConfused =
    hasDiseaseScores &&
    Math.abs(avgP - avgB) < 0.02 &&
    Math.abs(avgB - avgC) < 0.02 &&
    Math.abs(avgP - avgC) < 0.02;
  if (isConfused) {
    return "moderate";
  }

  // 3. ไฟสีเขียว: ความเสี่ยงต่ำ (Low Risk)
  // - เงื่อนไขร่วมกัน: AI วิเคราะห์กลุ่มปกติ (Healthy) ตั้งแต่ 80% ขึ้นไป และไม่ได้ติ๊กช่องใดๆ เลย
  const noChecklist =
    !checklist.fastBreathing &&
    !checklist.chestRetraction &&
    !checklist.stridor &&
    !checklist.dangerSign;
  if (avgN >= 0.80 && noChecklist) {
    return "low";
  }

  // เผื่อกรณีอื่นๆ ที่ไม่เข้าเงื่อนไขเด่นชัดข้างต้น ให้ค่าเริ่มต้นเป็นความเสี่ยงต่ำเพื่อความปลอดภัย
  return "low";
}

export default function ReportPage() {
  const [records, setRecords] = useState<CoughRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [modalTarget, setModalTarget] = useState<ChecklistTarget | null>(null);
  const [rangeMode, setRangeMode] = useState<"night" | "all">("night");
  const [checklist, setChecklist] = useState<ChecklistState>({
    fastBreathing: false,
    chestRetraction: false,
    stridor: false,
    dangerSign: false,
  });

  const now = useMemo(() => new Date(), []);
  const startAt = useMemo(() => getNightStart(now), [now]);

  useEffect(() => {
    async function loadRecords() {
      setLoading(true);
      setError(null);

      let query = supabase
        .from("cough_record")
        .select("*")
        .eq("device_id", DEFAULT_DEVICE_ID)
        .order("created_at", { ascending: true });

      if (rangeMode === "night") {
        query = query.gte("created_at", startAt.toISOString()).lte("created_at", now.toISOString());
      }

      const { data, error: queryError } = await query;

      if (queryError) setError(queryError.message);
      else setRecords((data ?? []) as CoughRecord[]);
      setLoading(false);
    }

    loadRecords();
  }, [now, rangeMode, startAt]);

  const pocRecords = records.filter((record) => record.is_poc);
  const normalRecords = records.filter((record) => !record.is_poc);
  const importantRecords = normalRecords
    .filter((record) => record.risk_level === "high" || record.noti_time)
    .sort((a, b) => {
      const riskDiff = riskWeight(b.risk_level) - riskWeight(a.risk_level);
      if (riskDiff !== 0) return riskDiff;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  function openChecklist(target: ChecklistTarget) {
    setChecklist({
      fastBreathing: false,
      chestRetraction: false,
      stridor: false,
      dangerSign: false,
    });
    setSaveStatus(null);
    setModalTarget(target);
  }

  async function saveSummary() {
    if (!modalTarget) return;

    const targetSummary = getSummary(modalTarget.records);
    const finalRisk = computeFinalRisk(modalTarget.records, checklist);
    setSaveStatus("กำลังบันทึก...");

    const { error: insertError } = await supabase.from("summary_record").insert({
      device_id: DEFAULT_DEVICE_ID,
      cough_ids: modalTarget.records.map((record) => record.id),
      start_at: modalTarget.records[0]?.created_at ?? startAt.toISOString(),
      end_at: modalTarget.records.at(-1)?.created_at ?? now.toISOString(),
      checklist: {
        ...checklist,
        source_type: modalTarget.sourceType,
        source_title: modalTarget.title,
      },
      summary_result: {
        event_count: modalTarget.records.length,
        risk_counts: targetSummary.riskCounts,
        average_scores: targetSummary.avg,
        top_disease: targetSummary.top?.[0] ?? null,
        top_score: targetSummary.top?.[1] ?? null,
      },
      risk_level: finalRisk,
    });

    setSaveStatus(insertError ? `บันทึกไม่สำเร็จ: ${insertError.message}` : "บันทึก summary_record แล้ว");
  }

  return (
    <main className="min-h-screen bg-gradient-medical">
      <div className="mx-auto max-w-2xl px-4 py-5">
        <header className="mb-5">
          <div className="text-xs font-bold uppercase tracking-wide text-sky-700">iCough Report</div>
          <h1 className="mt-1 text-2xl font-extrabold text-slate-900">สรุปเสียงไอ</h1>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {rangeMode === "night"
              ? `ช่วงข้อมูล ${formatThaiTime(startAt)} ถึง ${formatThaiTime(now)}`
              : "แสดงข้อมูลทั้งหมดของอุปกรณ์นี้"}
          </p>
          <div className="mt-4 grid grid-cols-2 gap-2 rounded-xl bg-white/70 p-1">
            <button
              type="button"
              onClick={() => setRangeMode("night")}
              className={`rounded-lg px-3 py-2 text-sm font-bold transition ${
                rangeMode === "night" ? "bg-sky-600 text-white shadow-sm" : "text-slate-600"
              }`}
            >
              คืนนี้
            </button>
            <button
              type="button"
              onClick={() => setRangeMode("all")}
              className={`rounded-lg px-3 py-2 text-sm font-bold transition ${
                rangeMode === "all" ? "bg-sky-600 text-white shadow-sm" : "text-slate-600"
              }`}
            >
              ดึงทั้งหมด
            </button>
          </div>
        </header>

        {loading && <div className="glass-card-static p-5 text-sm text-slate-600">กำลังดึงข้อมูล...</div>}
        {error && <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        {!loading && !error && (
          <div className="space-y-5">
            <ReportSection
              title="POC/Test Event"
              description="เสียงที่เกิดจากการกดทดสอบ แยกไว้ไม่ปนกับเหตุการณ์ใช้งานจริง"
              records={pocRecords}
              emptyText="ยังไม่มี PoC/Test event"
              onChecklistAverage={() =>
                openChecklist({
                  title: "POC/Test Event average",
                  records: pocRecords,
                  sourceType: "section_average",
                })
              }
              onChecklistRecord={(record) =>
                openChecklist({
                  title: `PoC event ${formatThaiTime(record.created_at)}`,
                  records: [record],
                  sourceType: "single_event",
                })
              }
            />

            <ReportSection
              title="เหตุการณ์สำคัญ"
              description="event ที่เป็น high risk หรือมีการแจ้งเตือน"
              records={importantRecords}
              emptyText="ยังไม่มี event สำคัญ"
              onChecklistAverage={() =>
                openChecklist({
                  title: "เหตุการณ์สำคัญ average",
                  records: importantRecords,
                  sourceType: "section_average",
                })
              }
              onChecklistRecord={(record) =>
                openChecklist({
                  title: `เหตุการณ์สำคัญ ${formatThaiTime(record.created_at)}`,
                  records: [record],
                  sourceType: "single_event",
                })
              }
            />

            <ReportSection
              title="Timeline ทั้งหมด"
              description="event ใช้งานจริงทั้งหมดในช่วงเวลาที่เลือก"
              records={normalRecords}
              emptyText="ยังไม่มี event ในช่วงเวลานี้"
              onChecklistAverage={() =>
                openChecklist({
                  title: "Timeline ทั้งหมด average",
                  records: normalRecords,
                  sourceType: "section_average",
                })
              }
              onChecklistRecord={(record) =>
                openChecklist({
                  title: `Timeline event ${formatThaiTime(record.created_at)}`,
                  records: [record],
                  sourceType: "single_event",
                })
              }
            />
          </div>
        )}
      </div>

      {modalTarget && (
        <ChecklistModal
          target={modalTarget}
          checklist={checklist}
          saveStatus={saveStatus}
          onChange={setChecklist}
          onClose={() => setModalTarget(null)}
          onSave={saveSummary}
        />
      )}
    </main>
  );
}

function ReportSection({
  title,
  description,
  records,
  emptyText,
  onChecklistAverage,
  onChecklistRecord,
}: {
  title: string;
  description: string;
  records: CoughRecord[];
  emptyText: string;
  onChecklistAverage: () => void;
  onChecklistRecord: (record: CoughRecord) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const summary = getSummary(records);
  const displayedRecords = showAll ? records : records.slice(0, 3);

  return (
    <section className="space-y-3">
      <div className="glass-card-static p-4">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">{title}</h2>
            <p className="mt-0.5 text-xs leading-5 text-slate-500">{description}</p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-bold ${riskClass(summary.worstRisk)}`}>
            {summary.worstRisk ?? "none"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Events" value={`${records.length}`} />
          <Metric label="High" value={`${summary.riskCounts.high}`} />
          <Metric label="Moderate" value={`${summary.riskCounts.moderate}`} />
          <Metric label="Top avg" value={summary.top ? `${diseaseLabels[summary.top[0]]} ${(summary.top[1] * 100).toFixed(0)}%` : "-"} />
        </div>

        <button
          type="button"
          disabled={records.length === 0}
          onClick={onChecklistAverage}
          className="mt-4 w-full rounded-lg bg-sky-600 px-4 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Checklist average
        </button>
      </div>

      <div className="space-y-3">
        {displayedRecords.length > 0 ? (
          displayedRecords.map((record) => (
            <EventCard key={record.id} record={record} onChecklist={() => onChecklistRecord(record)} />
          ))
        ) : (
          <div className="glass-card-static p-4 text-sm text-slate-600">{emptyText}</div>
        )}

        {records.length > 3 && (
          <button
            type="button"
            onClick={() => setShowAll(!showAll)}
            className="w-full flex items-center justify-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50/70 hover:bg-sky-100/80 px-4 py-3 text-xs font-extrabold text-sky-700 shadow-sm transition active:scale-95"
          >
            <span>{showAll ? "แสดงน้อยลง (Show less)" : `แสดงทั้งหมด (Show all ${records.length} รายการ)`}</span>
            <svg
              className={`h-3 w-3 transform transition-transform duration-200 ${showAll ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={3}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>
    </section>
  );
}

function EventCard({ record, onChecklist }: { record: CoughRecord; onChecklist: () => void }) {
  const [topDisease, topScore] = getTopDisease(record);

  return (
    <details className="glass-card-static overflow-hidden">
      <summary className="cursor-pointer list-none p-4 [&::-webkit-details-marker]:hidden">
        <div className="flex items-start gap-3">
          {record.spectrum_path && (
            <img
              src={record.spectrum_path}
              alt="Mel spectrogram"
              className="h-20 w-24 flex-shrink-0 rounded-lg border border-slate-200 object-cover"
            />
          )}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${riskClass(record.risk_level)}`}>
                {record.risk_level ?? "unknown"}
              </span>
              {record.noti_time && (
                <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-xs font-bold text-sky-700">
                  notified
                </span>
              )}
              {record.is_poc && (
                <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-xs font-bold text-violet-700">
                  PoC
                </span>
              )}
            </div>
            <div className="mt-2 text-sm font-bold text-slate-800">
              {diseaseLabels[topDisease]} {(topScore * 100).toFixed(0)}%
            </div>
            <div className="mt-0.5 text-xs text-slate-500">{formatThaiTime(record.created_at)}</div>
          </div>
        </div>
      </summary>

      <div className="border-t border-slate-100 p-4">
        {record.audio_path && <audio className="mb-3 w-full" controls src={record.audio_path} />}
        <div className="mb-3 grid grid-cols-2 gap-2 text-xs">
          <Score label="Pneumonia" value={record.pneumonia_score} />
          <Score label="Croup" value={record.croup_score} />
          <Score label="Bronchitis" value={record.bronchitis_score} />
          <Score label="Normal" value={record.normal_score} />
        </div>
        <button
          type="button"
          onClick={onChecklist}
          className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-indigo-700"
        >
          ทำ Checklist การ์ดนี้
        </button>
      </div>
    </details>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 break-words text-lg font-extrabold text-slate-900">{value}</div>
    </div>
  );
}

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg bg-white p-2">
      <div className="text-slate-500">{label}</div>
      <div className="font-bold text-slate-800">{((value ?? 0) * 100).toFixed(0)}%</div>
    </div>
  );
}

