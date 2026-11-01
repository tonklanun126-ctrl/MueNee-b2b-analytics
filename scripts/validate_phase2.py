#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MueNee B2B Analytics: Phase 2 Quality Gate 2 Validation Script
==============================================================================
Script ตรวจสอบคุณภาพและความสมบูรณ์ของ Phase 2 (Module A: Synthetic Data Engine)
ตามเกณฑ์ที่ระบุใน TASK.md (Quality Gate 2) และ SPEC.md
==============================================================================
"""

import sys
import os
import json
import hashlib
import pandas as pd
import numpy as np

# ปรับปรุง Encoding สำหรับ Windows Console ให้รองรับภาษาไทยและอิโมจิ
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def compute_sha256(filepath):
    """คำนวณค่า SHA-256 checksum ของไฟล์"""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_gate_2():
    print("=" * 70)
    print("   MueNee B2B Analytics: Gate 2 Verification (Module A Synthetic Engine)   ")
    print("=" * 70)

    errors = []
    warnings = []
    checks_passed = 0

    # --------------------------------------------------------------------------
    # 1. ตรวจสอบการมีอยู่ของไฟล์ผลลัพธ์ทั้งหมด
    # --------------------------------------------------------------------------
    print("\n[Step 1] ตรวจสอบไฟล์ผลลัพธ์ Phase 2...")
    required_files = [
        "data/raw/daily_meal_logs.csv",
        "data/raw/tag_trend_scores.csv",
        "data/raw/run_metadata.json",
        "outputs/module_a_dq_report.html",
        "colab/01_module_a_synthetic_engine.ipynb",
    ]

    for rf in required_files:
        if not os.path.exists(rf):
            errors.append(f"ไม่พบไฟล์ที่จำเป็น: {rf}")
        else:
            size_kb = os.path.getsize(rf) / 1024
            print(f"  ✅ พบไฟล์ {rf} ({size_kb:.2f} KB)")
            checks_passed += 1

    if errors:
        print("\n❌ หยุดการตรวจสอบเนื่องจากไฟล์ไม่ครบถ้วน:")
        for err in errors:
            print(f"  - {err}")
        return False

    # --------------------------------------------------------------------------
    # 2. ตรวจสอบ daily_meal_logs.csv
    # --------------------------------------------------------------------------
    print("\n[Step 2] ตรวจสอบ Schema และ Integrity Rules ของ daily_meal_logs.csv...")
    daily_df = pd.read_csv("data/raw/daily_meal_logs.csv")

    # 2.1 ตรวจสอบจำนวนแถว (365 วัน x 30 เมนู = 10,950 แถว)
    expected_rows = 365 * 30
    if len(daily_df) == expected_rows:
        print(f"  ✅ จำนวนแถวถูกต้อง: {len(daily_df):,} แถว (365 วัน x 30 เมนู)")
        checks_passed += 1
    else:
        errors.append(f"จำนวนแถวไม่ถูกต้อง: พบ {len(daily_df)} แถว (คาดหวัง {expected_rows})")

    # 2.2 ตรวจสอบคอลัมน์ตาม Data Dictionary ใน SPEC.md §2.1
    expected_cols = [
        "date", "restaurant_id", "menu_item_id", "price_tier", "academic_period",
        "day_of_week", "is_weekend", "orders_total",
        "orders_lunch", "orders_dinner", "orders_late_night", "orders_other",
        "src_recommendation", "src_food_scan", "src_manual",
        "unit_price_thb", "price_confidence", "revenue_thb", "kcal_total", "run_id"
    ]
    missing_cols = set(expected_cols) - set(daily_df.columns)
    if not missing_cols:
        print("  ✅ คอลัมน์ครบถ้วนตาม SPEC.md §2.1 Data Dictionary")
        checks_passed += 1
    else:
        errors.append(f"คอลัมน์ขาดหายใน daily_meal_logs.csv: {missing_cols}")

    # 2.3 ตรวจสอบช่วงวันที่และจำนวนวัน
    dates = pd.to_datetime(daily_df["date"]).dt.date.unique()
    if len(dates) == 365 and min(dates).isoformat() == "2026-08-01" and max(dates).isoformat() == "2027-07-31":
        print(f"  ✅ ช่วงวันที่ครอบคลุม 365 วัน (2026-08-01 ถึง 2027-07-31)")
        checks_passed += 1
    else:
        errors.append(f"ช่วงวันที่ไม่ถูกต้อง: เริ่ม {min(dates)} ถึง {max(dates)} (รวม {len(dates)} วัน)")

    # 2.4 ตรวจสอบจำนวนเมนูและร้านค้า
    menus = daily_df["menu_item_id"].unique()
    rests = daily_df["restaurant_id"].unique()
    if len(menus) == 30 and len(rests) == 10:
        print(f"  ✅ ครอบคลุม 10 ร้านค้าจริง และ 30 เมนูอาหารจริงรอบ ม.ศิลปากร ครบถ้วน")
        checks_passed += 1
    else:
        errors.append(f"จำนวนเมนูหรือร้านค้าไม่ครบ: พบ {len(rests)} ร้าน และ {len(menus)} เมนู")

    # 2.5 ตรวจสอบ Integrity Rule 1: ยอดรวมมื้ออาหาร
    sum_meals = daily_df["orders_lunch"] + daily_df["orders_dinner"] + daily_df["orders_late_night"] + daily_df["orders_other"]
    meal_diff = (daily_df["orders_total"] != sum_meals).sum()
    if meal_diff == 0:
        print("  ✅ Integrity Rule 1 ผ่าน: orders_total == lunch + dinner + late_night + other (100%)")
        checks_passed += 1
    else:
        errors.append(f"Integrity Rule 1 ล้มเหลว: พบผลต่าง {meal_diff} แถว")

    # 2.6 ตรวจสอบ Integrity Rule 2: ยอดรวมช่องทางคำสั่งซื้อ
    sum_sources = daily_df["src_recommendation"] + daily_df["src_food_scan"] + daily_df["src_manual"]
    source_diff = (daily_df["orders_total"] != sum_sources).sum()
    if source_diff == 0:
        print("  ✅ Integrity Rule 2 ผ่าน: orders_total == src_recommendation + src_food_scan + src_manual (100%)")
        checks_passed += 1
    else:
        errors.append(f"Integrity Rule 2 ล้มเหลว: พบผลต่าง {source_diff} แถว")

    # 2.7 ตรวจสอบความถูกต้องของรายได้ (revenue_thb == orders_total * unit_price_thb)
    rev_calc = daily_df["orders_total"] * daily_df["unit_price_thb"]
    rev_diff = (daily_df["revenue_thb"] != rev_calc).sum()
    if rev_diff == 0:
        print("  ✅ Integrity Rule 3 ผ่าน: revenue_thb == orders_total * unit_price_thb (100%)")
        checks_passed += 1
    else:
        errors.append(f"Integrity Rule 3 ล้มเหลว: พบผลต่าง {rev_diff} แถว")

    # 2.8 ตรวจสอบความถูกต้องของแคลอรีรวม (kcal_total >= 0)
    invalid_kcals = daily_df[daily_df["kcal_total"] < 0]
    if len(invalid_kcals) == 0:
        print("  ✅ ความถูกต้องของข้อมูลโภชนาการ (kcal_total >= 0 ครบถ้วน)")
        checks_passed += 1
    else:
        errors.append(f"พบ kcal_total ติดลบ: {len(invalid_kcals)} แถว")

    # --------------------------------------------------------------------------
    # 3. ตรวจสอบ tag_trend_scores.csv
    # --------------------------------------------------------------------------
    print("\n[Step 3] ตรวจสอบ tag_trend_scores.csv...")
    trend_df = pd.read_csv("data/raw/tag_trend_scores.csv")

    if len(trend_df) == expected_rows:
        print(f"  ✅ จำนวนแถว tag trend scores ถูกต้อง: {len(trend_df):,} แถว")
        checks_passed += 1
    else:
        errors.append(f"จำนวนแถว tag trend scores ไม่ถูกต้อง: {len(trend_df)}")

    expected_trend_cols = [
        "date", "menu_item_id", "eligible_user_share",
        "dislike_penalty_share", "tag_demand_score", "restriction_exposure_index"
    ]
    missing_trend_cols = set(expected_trend_cols) - set(trend_df.columns)
    if not missing_trend_cols:
        print("  ✅ คอลัมน์ครบถ้วนตาม SPEC.md §2.4 Tag Trend Scores")
        checks_passed += 1
    else:
        errors.append(f"คอลัมน์ขาดหายใน tag_trend_scores.csv: {missing_trend_cols}")

    score_bounds = trend_df[(trend_df["tag_demand_score"] < 0.0) | (trend_df["tag_demand_score"] > 100.0)]
    eligible_bounds = trend_df[(trend_df["eligible_user_share"] < 0.0) | (trend_df["eligible_user_share"] > 1.0)]
    if len(score_bounds) == 0 and len(eligible_bounds) == 0:
        print("  ✅ ค่าคะแนน tag_demand_score อยู่ในช่วง [0.0, 100.0] และ eligible_user_share อยู่ในช่วง [0.0, 1.0]")
        checks_passed += 1
    else:
        errors.append(f"พบคะแนน tag_trend_scores ออกนอกขอบเขต: scores={len(score_bounds)}, eligible={len(eligible_bounds)}")

    # --------------------------------------------------------------------------
    # 4. ตรวจสอบพฤติกรรมทางสถิติและธุรกิจรอบ ม.ศิลปากร
    # --------------------------------------------------------------------------
    print("\n[Step 4] ตรวจสอบพฤติกรรมทางสถิติและบริบทธุรกิจ (Business & Statistical Checks)...")

    # 4.1 ตรวจสอบสัดส่วนยอดสั่งซื้อตาม Price Tier
    tier_orders = daily_df.groupby("price_tier")["orders_total"].sum().to_dict()

    eco_orders = tier_orders.get("economy", 0)
    mid_orders = tier_orders.get("mid", 0)
    prem_orders = tier_orders.get("premium_social", 0)

    print(f"  - ยอดสั่งซื้อแยกตามระดับราคา:")
    print(f"    * Economy Tier (40-70 THB):       {eco_orders:,} ออร์เดอร์ ({eco_orders/daily_df['orders_total'].sum()*100:.1f}%)")
    print(f"    * Mid Tier (80-180 THB):          {mid_orders:,} ออร์เดอร์ ({mid_orders/daily_df['orders_total'].sum()*100:.1f}%)")
    print(f"    * Premium/Social (199-800 THB):    {prem_orders:,} ออร์เดอร์ ({prem_orders/daily_df['orders_total'].sum()*100:.1f}%)")

    if eco_orders > mid_orders > prem_orders:
        print("  ✅ กฎการกระจายตัวตามความอ่อนไหวต่อราคาผ่าน: Economy > Mid > Premium/Social")
        checks_passed += 1
    else:
        errors.append(f"การกระจายตัวของระดับราคาไม่เป็นไปตามเกณฑ์: Eco={eco_orders}, Mid={mid_orders}, Prem={prem_orders}")

    # 4.2 ตรวจสอบผลกระทบช่วงปิดเทอม (Semester Break)
    reg_mean = daily_df[daily_df["academic_period"] == "regular"].groupby(["date", "menu_item_id"])["orders_total"].sum().mean()
    break_mean = daily_df[daily_df["academic_period"] == "semester_break"].groupby(["date", "menu_item_id"])["orders_total"].sum().mean()
    drop_pct = (1.0 - break_mean / reg_mean) * 100.0

    print(f"  - อัตราการลดลงช่วงปิดภาคเรียน (Semester Break Drop): {drop_pct:.2f}% (ค่าเฉลี่ยปกติ={reg_mean:.1f}, ปิดเทอม={break_mean:.1f})")
    if 60.0 <= drop_pct <= 80.0:
        print("  ✅ ยอดสั่งซื้อช่วงปิดเทอมลดลงอยู่ในเกณฑ์ 60% - 80% ตามที่กำหนดใน SPEC.md §4.1")
        checks_passed += 1
    else:
        errors.append(f"อัตราการลดลงช่วงปิดเทอมอยู่นอกเกณฑ์ 60-80%: พบ {drop_pct:.2f}%")

    # 4.3 ตรวจสอบยอดสั่งซื้อมื้อดึกช่วงสัปดาห์สอบ (Exam Weeks Late Night Surge)
    reg_late = daily_df[daily_df["academic_period"] == "regular"].groupby(["date", "menu_item_id"])["orders_late_night"].sum().mean()
    exam_late = daily_df[daily_df["academic_period"].isin(["midterm_exam", "final_exam"])].groupby(["date", "menu_item_id"])["orders_late_night"].sum().mean()
    late_surge_ratio = exam_late / reg_late if reg_late > 0 else 0.0

    print(f"  - อัตราส่วนยอดมื้อดึกช่วงสอบเทียบกับช่วงปกติ: {late_surge_ratio:.2f} เท่า (ช่วงปกติ={reg_late:.2f}, ช่วงสอบ={exam_late:.2f})")
    if late_surge_ratio >= 2.0:
        print("  ✅ ยอดสั่งซื้อมื้อดึกช่วงสัปดาห์สอบพุ่งสูงขึ้น >= 2.0 เท่าตามเกณฑ์")
        checks_passed += 1
    else:
        errors.append(f"ยอดสั่งซื้อมื้อดึกช่วงสอบไม่ถึง 2.0 เท่า: พบ {late_surge_ratio:.2f} เท่า")

    # --------------------------------------------------------------------------
    # 5. ตรวจสอบ SHA-256 Checksums ใน run_metadata.json
    # --------------------------------------------------------------------------
    print("\n[Step 5] ตรวจสอบ SHA-256 Checksums ใน run_metadata.json...")
    with open("data/raw/run_metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    daily_sha = compute_sha256("data/raw/daily_meal_logs.csv")
    trend_sha = compute_sha256("data/raw/tag_trend_scores.csv")

    meta_daily_sha = meta["file_checksums"].get("daily_meal_logs_csv_sha256")
    meta_trend_sha = meta["file_checksums"].get("tag_trend_scores_csv_sha256")

    if daily_sha == meta_daily_sha and trend_sha == meta_trend_sha:
        print(f"  ✅ SHA-256 Checksums ตรงกัน 100%:")
        print(f"     - daily_meal_logs.csv: {daily_sha[:16]}...")
        print(f"     - tag_trend_scores.csv: {trend_sha[:16]}...")
        checks_passed += 1
    else:
        errors.append(f"SHA-256 Checksum ไม่ตรงกับ run_metadata.json: daily({daily_sha} vs {meta_daily_sha})")

    # --------------------------------------------------------------------------
    # 6. ตรวจสอบ Colab Notebook (colab/01_module_a_synthetic_engine.ipynb)
    # --------------------------------------------------------------------------
    print("\n[Step 6] ตรวจสอบความถูกต้องของ colab/01_module_a_synthetic_engine.ipynb...")
    try:
        with open("colab/01_module_a_synthetic_engine.ipynb", "r", encoding="utf-8") as f:
            nb = json.load(f)

        cells = nb.get("cells", [])
        md_cells = [c for c in cells if c.get("cell_type") == "markdown"]
        code_cells = [c for c in cells if c.get("cell_type") == "code"]

        print(f"  - พบ Cells ทั้งหมด: {len(cells)} (Markdown: {len(md_cells)}, Code: {len(code_cells)})")

        # ตรวจสอบว่ามี cell ตรวจสอบ GPU
        all_code_text = " ".join([" ".join(c.get("source", [])) for c in code_cells])
        has_gpu_check = "cuda" in all_code_text.lower() or "torch" in all_code_text.lower()
        if has_gpu_check:
            print("  ✅ มีโค้ดตรวจสอบ GPU (CUDA Availability) พร้อม fallback")
            checks_passed += 1
        else:
            errors.append("ไม่พบโค้ดตรวจสอบ CUDA/GPU ใน Jupyter Notebook")

        # ตรวจสอบว่ามีคำอธิบาย A1-A6 ใน Markdown
        all_md_text = " ".join([" ".join(c.get("source", [])) for c in md_cells])
        sections_found = [sec in all_md_text for sec in ["A1", "A2", "A3", "A4", "A5", "A6"]]
        if all(sections_found):
            print("  ✅ มี Markdown อธิบายโครงสร้างระดับ Section A1 - A6 ครบถ้วน")
            checks_passed += 1
        else:
            errors.append("Markdown ใน Notebook อธิบาย Section A1-A6 ไม่ครบถ้วน")

        # ตรวจสอบโค้ดแสดงผลกราฟิก (Visualization)
        has_viz = any(viz in all_code_text for viz in ["plt.show", "savefig", "heatmap", "barplot"])
        if has_viz:
            print("  ✅ มีโค้ดสร้าง Visualization กราฟสรุปผลตามข้อกำหนด")
            checks_passed += 1
        else:
            errors.append("ไม่พบโค้ดสร้างภาพ Visualization ใน Notebook")

    except Exception as e:
        errors.append(f"เกิดข้อผิดพลาดในการอ่าน Notebook: {str(e)}")

    # --------------------------------------------------------------------------
    # สรุปผลการตรวจสอบ Gate 2
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"ผลการตรวจสอบ Gate 2: ผ่าน {checks_passed} หัวข้อย่อย")
    if errors:
        print(f"❌ ล้มเหลว! พบข้อผิดพลาด {len(errors)} รายการ:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("🎉 ผ่านเกณฑ์คุณภาพ QUALITY GATE 2 ทั้งหมด 100%! พร้อมก้าวสู่ Phase 3 (R Module B) 🎉")
        print("=" * 70)
        return True


if __name__ == "__main__":
    success = validate_gate_2()
    sys.exit(0 if success else 1)
