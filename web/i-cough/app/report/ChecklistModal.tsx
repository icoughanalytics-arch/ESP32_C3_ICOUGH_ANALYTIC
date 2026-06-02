"use client";

import { useState } from "react";

export type RiskLevel = "low" | "moderate" | "high";
export type DiseaseKey = "pneumonia" | "croup" | "bronchitis" | "normal";

export type CoughRecord = {
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

export type ChecklistState = {
  fastBreathing: boolean;
  chestRetraction: boolean;
  stridor: boolean;
  dangerSign: boolean;
};

export type ChecklistTarget = {
  title: string;
  records: CoughRecord[];
  sourceType: "section_average" | "single_event";
};

interface ChecklistModalProps {
  target: ChecklistTarget;
  checklist: ChecklistState;
  saveStatus: string | null;
  onChange: (next: ChecklistState) => void;
  onClose: () => void;
  onSave: () => void;
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
  if (checklist.chestRetraction || checklist.stridor || checklist.dangerSign) return "high";
  if (records.some((r) => r.risk_level === "high")) return "high";
  if (checklist.fastBreathing || records.some((r) => r.risk_level === "moderate")) {
    return "moderate";
  }
  return "low";
}

function Score({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg bg-white p-2 border border-slate-100">
      <div className="text-slate-500 text-xs">{label}</div>
      <div className="font-bold text-slate-800 text-sm">{((value ?? 0) * 100).toFixed(0)}%</div>
    </div>
  );
}

export default function ChecklistModal({
  target,
  checklist,
  saveStatus,
  onChange,
  onClose,
  onSave,
}: ChecklistModalProps) {
  const summary = getSummary(target.records);
  const finalRisk = computeFinalRisk(target.records, checklist);

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/60 p-4 animate-fade-in">
      <div className="max-h-[85vh] w-full max-w-md bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-slate-100 bg-white p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wide text-sky-700">
                {target.sourceType === "section_average" ? "Average Checklist" : "Event Checklist"}
              </div>
              <h3 className="mt-1 text-lg font-extrabold text-slate-900">{target.title}</h3>
              <p className="mt-1 text-xs text-slate-500">
                รวม {target.records.length} event | final risk: {finalRisk}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-50 transition"
            >
              ปิด
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-4 p-4 overflow-y-auto flex-1">
          {/* Average Scores */}
          <div className="rounded-xl bg-slate-50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-bold text-slate-900">ค่าเฉลี่ยในชุดนี้</span>
              <span className={`rounded-full border px-2 py-0.5 text-xs font-bold ${riskClass(finalRisk)}`}>
                {finalRisk}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <Score label="Pneumonia" value={summary.avg.pneumonia} />
              <Score label="Croup" value={summary.avg.croup} />
              <Score label="Bronchitis" value={summary.avg.bronchitis} />
              <Score label="Normal" value={summary.avg.normal} />
            </div>
          </div>

          {/* Checklist items with customized red-border dropdowns */}
          <div className="space-y-4">
            {/* 1. หายใจเร็วผิดปกติ */}
            <CheckItemWithDescription
              label="หายใจเร็วผิดปกติ"
              checked={checklist.fastBreathing}
              onChange={(checked) => onChange({ ...checklist, fastBreathing: checked })}
              description={
                <div className="space-y-2">
                  <div className="font-bold text-red-700 text-sm">
                    ภาวะหายใจเร็วเกินเกณฑ์อายุ (Fast Breathing / Tachypnea)
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">ลักษณะอาการ:</span> อัตราการขยับขึ้น-ลงของทรวงอกหรือหน้าท้องมีความถี่สูงกว่าปกติในขณะที่ร่างกายพักผ่อน
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">เกณฑ์การพิจารณาเพื่อบันทึกข้อมูล:</span>
                    <ul className="list-disc pl-5 mt-1 space-y-1">
                      <li>ผู้ป่วยต้องอยู่ในสภาวะสงบ นอนราบ หรือหลับสนิทเท่านั้น <span className="text-red-600 font-medium">(ห้ามประเมินขณะผู้ป่วยร้องไห้ ดิ้น รับประทานนม หรือหลังทำกิจกรรมทันที)</span></li>
                      <li>ทำการจับเวลาและนับจำนวนครั้งการหายใจ (การยกขึ้นและลงของทรวงอกนับเป็น 1 ครั้ง) ให้ครบ 1 นาทีเต็ม</li>
                    </ul>
                  </div>
                  <div className="border-t border-red-200 pt-2">
                    <span className="font-bold text-red-700">เลือกเครื่องหมายเมื่ออัตราการหายใจสูงกว่าเกณฑ์มาตรฐาน WHO ดังนี้:</span>
                    <ul className="list-disc pl-5 mt-1 font-semibold text-slate-800">
                      <li>กลุ่มอายุ 2 - 11 เดือน: อัตราการหายใจตั้งแต่ 50 ครั้ง/นาที ขึ้นไป</li>
                      <li>กลุ่มอายุ 1 - 5 ปี: อัตราการหายใจตั้งแต่ 40 ครั้ง/นาที ขึ้นไป</li>
                    </ul>
                  </div>
                </div>
              }
            />

            {/* 2. ทรวงอกหรือซี่โครงบุ๋ม */}
            <CheckItemWithDescription
              label="ทรวงอกหรือซี่โครงบุ๋ม"
              checked={checklist.chestRetraction}
              onChange={(checked) => onChange({ ...checklist, chestRetraction: checked })}
              description={
                <div className="space-y-2">
                  <div className="font-bold text-red-700 text-sm">
                    ทรวงอกบุ๋ม / ซี่โครงบุ๋ม (Chest Indrawing)
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">ลักษณะอาการ:</span> การยุบตัวลึกผิดปกติของผิวหนังและเนื้อเยื่อบริเวณใต้ชายโครง หรือรอยต่อระหว่างทรวงอกกับหน้าท้องในจังหวะที่หายใจเข้า
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">เกณฑ์การพิจารณาเพื่อบันทึกข้อมูล:</span>
                    <ul className="list-disc pl-5 mt-1 space-y-1">
                      <li>สังเกตบริเวณใต้ชายโครงในสภาวะที่ผู้ป่วยนอนนิ่งและถอดเสื้อ โดยเนื้อเยื่อบริเวณดังกล่าวต้องมีการยุบตัวลึกลงไปอย่างเด่นชัดและเป็นวงจรตามจังหวะการหายใจเข้า</li>
                    </ul>
                  </div>
                  <div className="border-t border-red-200 pt-2 text-red-600 font-medium">
                    <span className="font-bold text-red-700">ข้อควรระวัง:</span> ปฏิเสธการบันทึกข้อมูล หากอาการบุ๋มเกิดขึ้นเฉพาะขณะผู้ป่วยร้องไห้สะอึก หรือเป็นลักษณะร่องซี่โครงปกติที่พบในเด็กที่มีสรีระผอม
                  </div>
                </div>
              }
            />

            {/* 3. มีเสียงหายใจเข้าแบบ stridor */}
            <CheckItemWithDescription
              label="มีเสียงหายใจเข้าแบบ stridor"
              checked={checklist.stridor}
              onChange={(checked) => onChange({ ...checklist, stridor: checked })}
              description={
                <div className="space-y-2">
                  <div className="font-bold text-red-700 text-sm">
                    เสียงหายใจเข้าดังวี้ดแหลม / ฮึดฮัด (Stridor)
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">ลักษณะอาการ:</span> เสียงทางเดินหายใจส่วนบนตีบแคบ มีลักษณะแหลม สูง หรือเสียงฮึดฮัดก้องสะท้อนที่เล็ดลอดออกมาจากลำคอหรือทรวงอก
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">เกณฑ์การพิจารณาเพื่อบันทึกข้อมูล:</span>
                    <ul className="list-disc pl-5 mt-1 space-y-1">
                      <li>ทำการฟังเสียงบริเวณใกล้ทางเดินหายใจหรือทรวงอกของผู้ป่วยอย่างใกล้ชิด โดยเสียงดังกล่าวต้องเกิดขึ้นเด่นชัดในช่วง "หายใจเข้า" เท่านั้น</li>
                    </ul>
                  </div>
                  <div className="border-t border-red-200 pt-2 text-red-600 font-medium">
                    <span className="font-bold text-red-700">ข้อควรระวัง:</span> ปฏิเสธการบันทึกข้อมูล หากเป็นเสียงครืดคราดจากเสมหะหรือน้ำมูกอุดตันในโพรงจมูกส่วนหน้า (ทดสอบโดยการทำความสะอาดโพรงจมูก หากเสียงดังกล่าวหายไป ไม่ต้องบันทึกข้อนี้)
                  </div>
                </div>
              }
            />

            {/* 4. มีสัญญาณอันตรายรุนแรง */}
            <CheckItemWithDescription
              label="มีสัญญาณอันตรายรุนแรง"
              checked={checklist.dangerSign}
              onChange={(checked) => onChange({ ...checklist, dangerSign: checked })}
              description={
                <div className="space-y-2">
                  <div className="font-bold text-red-700 text-sm">
                    สัญญาณอันตรายรุนแรง (General Danger Signs)
                  </div>
                  <div>
                    <span className="font-bold text-slate-800">ลักษณะอาการ:</span> ภาวะวิกฤตทางระบบร่างกายทั่วไปที่บ่งชี้ถึงการติดเชื้อรุนแรงหรือภาวะขาดออกซิเจนในกระแสเลือด
                  </div>
                  <div className="border-t border-red-200 pt-2">
                    <span className="font-bold text-red-700">เกณฑ์การพิจารณาเพื่อบันทึกข้อมูล:</span>
                    <span className="block mt-1 font-semibold text-slate-800">เลือกเครื่องหมายทันทีหากพบอาการอย่างใดอย่างหนึ่ง ดังต่อไปนี้:</span>
                    <ul className="list-disc pl-5 mt-1 space-y-1 text-slate-800">
                      <li>ผู้ป่วยมีภาวะซึมลงอย่างรุนแรง ไม่ตอบสนองต่อสิ่งเร้า หรือหลับลึกปลุกตื่นยาก</li>
                      <li>ผู้ป่วยปฏิเสธการดูดนมหรือน้ำ หรือมีภาวะอาเจียนพุ่งทุกครั้งหลังการรับประทาน</li>
                      <li>พบภาวะพิมพ์เขียวคล้ำ (Cyanosis) บริเวณริมฝีปาก ปลายลิ้น หรือส่วนปลายของนิ้วมือและนิ้วเท้า</li>
                      <li>ผู้ป่วยมีอาการชักเกร็ง หรือชักกระตุกร่วมด้วยในระหว่างสัปดาห์ที่เจ็บป่วย</li>
                    </ul>
                  </div>
                </div>
              }
            />
          </div>

          {/* Action Button */}
          <div className="pt-2">
            <button
              type="button"
              onClick={onSave}
              className="w-full rounded-lg bg-sky-600 px-4 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-sky-700 active:scale-[0.98]"
            >
              บันทึกลง summary_record
            </button>
            {saveStatus && (
              <p className="mt-2 text-center text-xs font-semibold text-sky-700 bg-sky-50 border border-sky-100 rounded-lg py-2">
                {saveStatus}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckItemWithDescription({
  label,
  checked,
  onChange,
  description,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  description: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-3 shadow-sm hover:border-slate-300 transition">
      <div className="flex items-center justify-between gap-3">
        <label className="flex flex-1 items-center gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={checked}
            onChange={(event) => onChange(event.target.checked)}
            className="checkbox-medical h-5 w-5 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
          />
          <span className="text-sm font-bold text-slate-800">{label}</span>
        </label>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-bold text-sky-600 hover:bg-sky-50 transition border border-sky-100 active:scale-95"
        >
          <span>ดูคำอธิบาย</span>
          <svg
            className={`h-3 w-3 transform transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Dropdown description box with solid red border */}
      {isOpen && (
        <div className="mt-3 border-2 border-red-500 bg-red-50/80 text-slate-700 rounded-xl p-4 text-xs leading-relaxed shadow-inner animate-fade-in">
          {description}
        </div>
      )}
    </div>
  );
}
