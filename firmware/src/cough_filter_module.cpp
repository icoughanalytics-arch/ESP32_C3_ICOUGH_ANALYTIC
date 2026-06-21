#include "cough_filter_module.h"

float cough_filter_calc_zcr(const int16_t* pcm_buf, size_t num_samples) {
    if (!pcm_buf || num_samples < 2) {
        return 0.0f;
    }
    
    size_t crossings = 0;
    for (size_t i = 1; i < num_samples; i++) {
        // เช็คการสลับสัญญาณขั้วบวก (+) และขั้วลบ (-)
        if ((pcm_buf[i] >= 0 && pcm_buf[i - 1] < 0) || (pcm_buf[i] < 0 && pcm_buf[i - 1] >= 0)) {
            crossings++;
        }
    }
    
    // อัตราส่วนความถี่ของการตัดผ่านจุดศูนย์
    return (float)crossings / (float)(num_samples - 1);
}

bool cough_filter_validate(const int16_t* pcm_buf, size_t num_samples, float db) {
    // 1. คำนวณค่า ZCR ของเฟรมข้อมูลนี้
    float zcr = cough_filter_calc_zcr(pcm_buf, num_samples);
    
    // 2. ตรวจเช็คว่าค่า ZCR อยู่ในย่านเสียงไอปกติของมนุษย์หรือไม่
    bool zcr_ok = (zcr >= COUGH_ZCR_MIN && zcr <= COUGH_ZCR_MAX);
    
    // พิมพ์วิเคราะห์ลง Serial Monitor
    Serial.printf("[FILTER] Pre-Check: dBFS=%6.1f | ZCR=%5.3f -> %s\n", 
                  db, zcr, zcr_ok ? "PASS (Cough Candidate)" : "REJECT (Noise)");
                  
    return zcr_ok;
}
