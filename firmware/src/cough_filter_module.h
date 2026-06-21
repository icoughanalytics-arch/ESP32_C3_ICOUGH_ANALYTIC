#pragma once
#include <Arduino.h>

// ช่วงเกณฑ์ Zero Crossing Rate (ZCR) ที่ใกล้เคียงกับเสียงไอเด็กของมนุษย์
// ป้องกันเสียงลมเป่าต่ำๆ/เสียงชน (ZCR ต่ำเกินไป) และเสียงเสียดสีแหลมคม (ZCR สูงเกินไป)
#define COUGH_ZCR_MIN  0.05f
#define COUGH_ZCR_MAX  0.32f

/**
 * @brief คำนวณค่า Zero Crossing Rate (ZCR) ของบัฟเฟอร์เสียง PCM 16-bit
 * @param pcm_buf บัฟเฟอร์ของสัญญาณเสียง
 * @param num_samples จำนวนตัวอย่างเสียงในบัฟเฟอร์
 * @return อัตราการข้ามศูนย์ (0.0 ถึง 1.0)
 */
float cough_filter_calc_zcr(const int16_t* pcm_buf, size_t num_samples);

/**
 * @brief วิเคราะห์กรองสัญญาณเสียงเบื้องต้นบนบอร์ดว่าเป็นเสียงไอที่มีนัยสำคัญหรือไม่
 * @param pcm_buf บัฟเฟอร์สัญญาณเสียง PCM 16-bit
 * @param num_samples จำนวนตัวอย่างเสียงในบัฟเฟอร์
 * @param db ระดับความดังของสัญญาณเสียงในหน่วย dBFS
 * @return true หากผ่านเกณฑ์การกรองเบื้องต้น, false หากเป็นเสียงรบกวนทั่วไป
 */
bool cough_filter_validate(const int16_t* pcm_buf, size_t num_samples, float db);
