"use client";

import { useState } from "react";
import Link from "next/link";

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
  const [showLightsDesc, setShowLightsDesc] = useState(false);
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
          {saveStatus === "บันทึก summary_record แล้ว" ? (
            <div className="space-y-4 animate-fade-in border-t border-slate-100 pt-4">
              {/* สัญญาณไฟกลมเรืองแสงขนาดใหญ่ */}
              <div className="flex flex-col items-center justify-center py-4 bg-slate-50 rounded-2xl border border-slate-100">
                <div className={`h-16 w-16 rounded-full mb-3 shadow-lg ${
                  finalRisk === "high"
                    ? "bg-red-500 shadow-[0_0_20px_rgba(239,68,68,0.8)] animate-pulse"
                    : finalRisk === "moderate"
                      ? "bg-amber-500 shadow-[0_0_20px_rgba(245,158,11,0.8)]"
                      : "bg-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.8)]"
                }`} />
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">ระดับความเสี่ยงของเด็ก</span>
                <span className="text-base font-extrabold text-slate-900 mt-1">
                  {finalRisk === "high" && "ความเสี่ยงสูง / วิกฤต (High Risk / Critical)"}
                  {finalRisk === "moderate" && "ความเสี่ยงปานกลาง (Moderate Risk)"}
                  {finalRisk === "low" && "ความเสี่ยงต่ำ (Low Risk)"}
                </span>
              </div>

              {/* ข้อแนะนำหลัก */}
              <div className={`rounded-xl border p-4 text-xs leading-relaxed font-semibold space-y-2 ${
                finalRisk === "high"
                  ? "bg-red-50 border-red-200 text-red-900"
                  : finalRisk === "moderate"
                    ? "bg-amber-50 border-amber-200 text-amber-900"
                    : "bg-emerald-50 border-emerald-200 text-emerald-900"
              }`}>
                <div className="font-extrabold text-sm border-b pb-1">
                  🩺 นิยาม WHO: {
                    finalRisk === "high"
                      ? "โรคปอดบวมขั้นรุนแรงมาก หรือ โรคระบบทางเดินหายใจเฉียบพลันวิกฤต (Severe Pneumonia or Very Severe Disease)"
                      : finalRisk === "moderate"
                        ? "โรคปอดบวมระดับเริ่มต้น (Pneumonia)"
                        : "ไอ หรือ หวัดธรรมดา"
                  }
                </div>
                <div>
                  💡 {
                    finalRisk === "high"
                      ? "อันตรายขั้นวิกฤต! เด็กมีสัญญาณภาวะทางเดินหายใจล้มเหลวเฉียบพลัน โปรดนำเด็กส่งห้องฉุกเฉินของโรงพยาบาลที่ใกล้ที่สุดทันที"
                      : finalRisk === "moderate"
                        ? "เฝ้าระวัง: เด็กมีภาวะหายใจเร็วเข้าเกณฑ์โรคปอดบวม แนะนำให้พาเด็กไปพบแพทย์ที่คลินิกหรือโรงพยาบาลชุมชนเพื่อรับยาปฏิชีวนะชนิดกิน และควรทำประเมินซ้ำในแอปพลิเคชันภายใน 48 ชั่วโมง"
                        : "เด็กมีความเสี่ยงต่ำ ปลอดภัยจากภาวะปอดบวม ให้ดูแลตามอาการที่บ้าน เช่น ดื่มน้ำอุ่นเพื่อละลายเสมหะ และทำประเมินซ้ำหากเด็กเริ่มไอถี่ขึ้น"
                  }
                </div>
              </div>

              {/* Dropdown คำอธิบายระดับไฟ WHO */}
              <div className="border border-slate-200 rounded-xl bg-white overflow-hidden shadow-sm">
                <button
                  type="button"
                  onClick={() => setShowLightsDesc(!showLightsDesc)}
                  className="w-full flex items-center justify-between px-4 py-3 text-xs font-bold text-slate-700 bg-slate-50/50 hover:bg-slate-50 transition"
                >
                  <span>📖 ดูคำอธิบายเกณฑ์สัญญาณไฟของ WHO ทั้งหมด</span>
                  <svg
                    className={`h-3 w-3 transform transition-transform duration-200 ${showLightsDesc ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {showLightsDesc && (
                  <div className="p-4 border-t border-slate-100 bg-white text-[11px] space-y-3.5 leading-relaxed text-slate-700">
                    <div className="border-l-4 border-emerald-500 pl-2.5">
                      <div className="font-extrabold text-emerald-800 text-xs">🟢 ไฟสีเขียว: ความเสี่ยงต่ำ (Low Risk)</div>
                      <div className="text-slate-500 mt-0.5"><strong className="font-bold">นิยาม WHO:</strong> ไอ หรือ หวัดธรรมดา</div>
                      <div className="mt-0.5"><strong className="font-bold">คำแนะนำ:</strong> "เด็กมีความเสี่ยงต่ำ ปลอดภัยจากภาวะปอดบวม ให้ดูแลตามอาการที่บ้าน เช่น ดื่มน้ำอุ่นเพื่อละลายเสมหะ และทำประเมินซ้ำหากเด็กเริ่มไอถี่ขึ้น"</div>
                    </div>
                    <div className="border-l-4 border-amber-500 pl-2.5">
                      <div className="font-extrabold text-amber-800 text-xs">🟡 ไฟสีเหลือง: ความเสี่ยงปานกลาง (Moderate Risk)</div>
                      <div className="text-slate-500 mt-0.5"><strong className="font-bold">นิยาม WHO:</strong> โรคปอดบวมระดับเริ่มต้น (Pneumonia)</div>
                      <div className="mt-0.5"><strong className="font-bold">คำแนะนำ:</strong> "เฝ้าระวัง: เด็กมีภาวะหายใจเร็วเข้าเกณฑ์โรคปอดบวม แนะนำให้พาเด็กไปพบแพทย์ที่คลินิกหรือโรงพยาบาลชุมชนเพื่อรับยาปฏิชีวนะชนิดกิน และควรทำประเมินซ้ำในแอปพลิเคชันภายใน 48 ชั่วโมง"</div>
                    </div>
                    <div className="border-l-4 border-red-500 pl-2.5">
                      <div className="font-extrabold text-red-800 text-xs">🔴 ไฟสีแดง: ความเสี่ยงสูง/วิกฤต (High Risk / Critical)</div>
                      <div className="text-slate-500 mt-0.5"><strong className="font-bold">นิยาม WHO:</strong> โรคปอดบวมขั้นรุนแรงมาก หรือ โรคระบบทางเดินหายใจเฉียบพลันวิกฤต (Severe Pneumonia or Very Severe Disease)</div>
                      <div className="mt-0.5"><strong className="font-bold">คำแนะนำ:</strong> "อันตรายขั้นวิกฤต! เด็กมีสัญญาณภาวะทางเดินหายใจล้มเหลวเฉียบพลัน โปรดนำเด็กส่งห้องฉุกเฉินของโรงพยาบาลที่ใกล้ที่สุดทันที"</div>
                    </div>
                  </div>
                )}
              </div>

              {/* ปุ่มนำทางไปหน้าสรุปผล */}
              <div className="pt-2 space-y-2">
                <Link
                  href="/result"
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-sky-600 to-sky-700 px-4 py-3 text-sm font-extrabold text-white shadow-md hover:from-sky-700 hover:to-sky-800 active:scale-[0.98] transition-all"
                >
                  <span>📊 ดูหน้าสรุปผล / ประวัติทั้งหมด</span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M5 12h14" />
                    <path d="M12 5l7 7-7 7" />
                  </svg>
                </Link>
                <p className="text-center text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg py-2 animate-pulse">
                  ✓ บันทึกข้อมูลและประเมินระดับสัญญาณไฟ WHO สำเร็จ!
                </p>
              </div>
            </div>
          ) : (
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
          )}
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
