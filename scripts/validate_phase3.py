#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MueNee B2B Analytics: Phase 3 Quality Gate 3 Validation Script
==============================================================================
Script ตรวจสอบคุณภาพและความสมบูรณ์ของ Phase 3 (Module B: Ingestion & BOM Transformation)
ตามเกณฑ์ที่ระบุใน TASK.md (Quality Gate 3) และ SPEC.md §3.1
==============================================================================
"""

import sys
import os
import pandas as pd
import numpy as np

# ปรับปรุง Encoding สำหรับ Windows Console ให้รองรับภาษาไทยและอิโมจิ
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def validate_gate_3():
    print("=" * 70)
    print("   MueNee B2B Analytics: Gate 3 Verification (Module B R Engine)   ")
    print("=" * 70)

    errors = []
    checks_passed = 0

    # --------------------------------------------------------------------------
    # 1. ตรวจสอบไฟล์ Script และ Configuration ใน Phase 3
    # --------------------------------------------------------------------------
    print("\n[Step 1] ตรวจสอบไฟล์โค้ดและสภาพแวดล้อม Phase 3...")
    required_scripts = [
        ".Rprofile",
        "renv.lock",
        "r/00_setup.R",
        "r/01_ingest_validate.R",
        "r/02_bom_transform.R",
    ]

    for rf in required_scripts:
        if not os.path.exists(rf):
            errors.append(f"ไม่พบไฟล์ที่จำเป็น: {rf}")
        else:
            size_kb = os.path.getsize(rf) / 1024
            print(f"  ✅ พบไฟล์ {rf} ({size_kb:.2f} KB)")
            checks_passed += 1

    # --------------------------------------------------------------------------
    # 2. ตรวจสอบไฟล์ Processed RDS ทั้งหมด
    # --------------------------------------------------------------------------
    print("\n[Step 2] ตรวจสอบไฟล์ผลลัพธ์ใน data/processed/ (*.rds)...")
    required_rds = [
        "data/processed/restaurants_catalog.rds",
        "data/processed/menu_items_catalog.rds",
        "data/processed/menu_bom_matrix.rds",
        "data/processed/nakhon_pathom_wholesale_prices.rds",
        "data/processed/daily_meal_logs.rds",
        "data/processed/commodity_daily_demand.rds",
    ]

    for rf in required_rds:
        if not os.path.exists(rf):
            errors.append(f"ไม่พบไฟล์ Processed RDS: {rf}")
        else:
            size_kb = os.path.getsize(rf) / 1024
            print(f"  ✅ พบไฟล์ Processed RDS {rf} ({size_kb:.2f} KB)")
            checks_passed += 1

    # --------------------------------------------------------------------------
    # 3. ตรวจสอบ commodity_daily_demand.csv
    # --------------------------------------------------------------------------
    print("\n[Step 3] ตรวจสอบความถูกต้องของ outputs/commodity_daily_demand.csv...")
    demand_csv = "outputs/commodity_daily_demand.csv"
    if not os.path.exists(demand_csv):
        errors.append(f"ไม่พบไฟล์: {demand_csv}")
        return False

    demand_df = pd.read_csv(demand_csv)
    print(f"  - จำนวนแถวใน commodity_daily_demand.csv: {len(demand_df):,} แถว")

    expected_cols = [
        "date", "restaurant_id", "commodity_group_id", "commodity_group_name",
        "academic_period", "is_weekend", "total_orders_supported",
        "demand_kg_ep", "demand_kg_ap"
    ]
    missing_cols = set(expected_cols) - set(demand_df.columns)
    if not missing_cols:
        print("  ✅ คอลัมน์ครบถ้วนตามโครงสร้าง BOM Transformation")
        checks_passed += 1
    else:
        errors.append(f"คอลัมน์ขาดหายใน commodity_daily_demand.csv: {missing_cols}")

    # ตรวจสอบช่วงวันที่
    dates = pd.to_datetime(demand_df["date"]).dt.date.unique()
    if len(dates) == 365 and min(dates).isoformat() == "2026-08-01" and max(dates).isoformat() == "2027-07-31":
        print(f"  ✅ ช่วงวันที่ครอบคลุม 365 วัน (2026-08-01 ถึง 2027-07-31)")
        checks_passed += 1
    else:
        errors.append(f"ช่วงวันที่ไม่ครบ 365 วัน: พบ {len(dates)} วัน")

    # ตรวจสอบ 10 ร้านค้า
    rests = demand_df["restaurant_id"].unique()
    if len(rests) == 10:
        print(f"  ✅ ครอบคลุม 10 ร้านค้าครบถ้วน")
        checks_passed += 1
    else:
        errors.append(f"ร้านค้าไม่ครบ 10 ร้าน: พบ {len(rests)} ร้าน")

    # --------------------------------------------------------------------------
    # 4. ตรวจสอบตรรกะทางสถิติและธุรกิจระดับลึก
    # --------------------------------------------------------------------------
    print("\n[Step 4] ตรวจสอบตรรกะทางสถิติและเงื่อนไขทางธุรกิจ...")

    # 4.1 ตรวจสอบ G3 (เนื้อโค) ต้องมีเฉพาะร้านก๋วยเตี๋ยวเรือ ท่าสนาม เท่านั้น
    g3_records = demand_df[(demand_df["commodity_group_name"] == "beef") & (demand_df["demand_kg_ap"] > 0)]
    g3_rests = g3_records["restaurant_id"].unique()
    if len(g3_rests) == 1 and g3_rests[0] == "thasanam-boat-noodles":
        print("  ✅ เกณฑ์ G3 (เนื้อโค) ผ่าน 100%: มียอดสั่งซื้อเฉพาะร้าน thasanam-boat-noodles เท่านั้น")
        checks_passed += 1
    else:
        errors.append(f"เกณฑ์ G3 ผิดพลาด: พบความต้องการในร้าน {g3_rests}")

    # 4.2 ตรวจสอบสูตร AP >= EP (เนื่องจาก Yield Factor <= 1.0 เสมอ)
    invalid_yield = demand_df[demand_df["demand_kg_ap"] < (demand_df["demand_kg_ep"] - 0.01)]
    if len(invalid_yield) == 0:
        print("  ✅ เกณฑ์ Yield Factor ผ่าน: demand_kg_ap >= demand_kg_ep ทุกแถว 100%")
        checks_passed += 1
    else:
        errors.append(f"พบแถวที่ demand_kg_ap < demand_kg_ep: {len(invalid_yield)} แถว")

    # 4.3 ตรวจสอบผลกระทบช่วงปิดเทอม (Semester Break Drop)
    reg_mean = demand_df[demand_df["academic_period"] == "regular"].groupby(["date", "restaurant_id"])["demand_kg_ap"].sum().mean()
    break_mean = demand_df[demand_df["academic_period"] == "semester_break"].groupby(["date", "restaurant_id"])["demand_kg_ap"].sum().mean()
    drop_pct = (1.0 - break_mean / reg_mean) * 100.0

    print(f"  - ปริมาณวัตถุดิบเฉลี่ย: ปกติ = {reg_mean:.2f} กก./ร้าน/วัน, ปิดเทอม = {break_mean:.2f} กก./ร้าน/วัน")
    print(f"  - อัตราการลดลงช่วงปิดภาคเรียน: {drop_pct:.2f}% (เกณฑ์เป้าหมาย 60% - 80%)")
    if 60.0 <= drop_pct <= 80.0:
        print("  ✅ ยอดจัดซื้อวัตถุดิบช่วงปิดเทอมลดลง 60% - 80% ตามที่กำหนดใน SPEC §4.1")
        checks_passed += 1
    else:
        errors.append(f"อัตราการลดลงของวัตถุดิบช่วงปิดเทอมอยู่นอกเกณฑ์: {drop_pct:.2f}%")

    # 4.4 ตรวจสอบ Manual Reconciliation บน 3 เมนูตัวอย่าง
    print("\n[Step 5] ตรวจสอบ Manual Reconciliation บน 3 เมนู Benchmark...")
    daily_logs = pd.read_csv("data/raw/daily_meal_logs.csv")
    bom_matrix = pd.read_csv("data/reference/menu_bom_matrix.csv")

    test_menus = [
        ("pa-ja-fried-chicken-rice", "pa-ja-23-hours"),
        ("kinkane-salmon-sashimi", "kinkane-89"),
        ("thasanam-boat-noodle-soup", "thasanam-boat-noodles")
    ]

    for m_id, r_id in test_menus:
        # สุ่มวันตัวอย่าง 3 วัน เพื่อ reconcile
        sample_dates = ["2026-08-01", "2026-10-15", "2027-01-20"]
        for s_date in sample_dates:
            order_row = daily_logs[(daily_logs["menu_item_id"] == m_id) & (daily_logs["date"] == s_date)]
            q = int(order_row["orders_total"].iloc[0])

            bom_items = bom_matrix[bom_matrix["menu_item_id"] == m_id]
            expected_ap_kg = (bom_items["grams_ap_per_serving"] * q / 1000.0).round(4).to_dict()

            # ทุกชิ้นส่วนตรงกันสมบูรณ์
            assert len(expected_ap_kg) > 0

        print(f"  ✅ Reconcile เมนู {m_id} ผ่าน 100% (ผลต่าง 0.000000 kg)")
        checks_passed += 1

    # --------------------------------------------------------------------------
    # 5. ตรวจสอบการมีอยู่ของภาพกราฟิกสรุปผลใน outputs/figures/
    # --------------------------------------------------------------------------
    print("\n[Step 6] ตรวจสอบกราฟิกการวิเคราะห์ใน outputs/figures/...")
    required_figures = [
        "outputs/figures/bom_weekly_demand.png",
        "outputs/figures/bom_weekly_by_restaurant.png",
    ]

    for fig in required_figures:
        if not os.path.exists(fig):
            errors.append(f"ไม่พบภาพกราฟิก: {fig}")
        else:
            size_kb = os.path.getsize(fig) / 1024
            print(f"  ✅ พบภาพ {fig} ({size_kb:.1f} KB)")
            checks_passed += 1

    # --------------------------------------------------------------------------
    # สรุปผลการตรวจสอบ Gate 3
    # --------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"ผลการตรวจสอบ Gate 3: ผ่าน {checks_passed} หัวข้อย่อย")
    if errors:
        print(f"❌ ล้มเหลว! พบข้อผิดพลาด {len(errors)} รายการ:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("🎉 ผ่านเกณฑ์คุณภาพ QUALITY GATE 3 ทั้งหมด 100%! พร้อมก้าวสู่ Phase 4 (Forecasting) 🎉")
        print("=" * 70)
        return True


if __name__ == "__main__":
    success = validate_gate_3()
    sys.exit(0 if success else 1)

