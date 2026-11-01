"""
==============================================================================
MueNee-b2b-analytics: Nakhon Pathom Wholesale Prices Generator
==============================================================================
สคริปต์จำลองอนุกรมเวลาราคาขายส่งวัตถุดิบ (Synthetic Wholesale Price Series)
สำหรับตลาดสดเทศบาลนครปฐม ครอบคลุม 365 วัน (2026-08-01 ถึง 2027-07-31)
ตามข้อกำหนดใน SPEC.md (§2.3)

หลักการทางสถิติและแบบจำลองราคา:
1. อนุกรมเวลาแบบ Mean-Reverting AR(1) Process:
   - ราคาตลาดสดมีความต่อเนื่องของราคาในระดับวัน (Price Persistence)
   - สมการ: P_{t} = clip( P_bar + rho * (P_{t-1} - P_bar) + eps_t, P_min, P_max )
   - กำหนด rho = 0.95 (Autoregressive persistence parameter)
   - สุ่ม Gaussian white noise: eps_t ~ N(0, sigma^2)
2. ขอบเขตราคาพื้นฐาน (Baseline Price Bounds):
   - ยึดตามช่วงราคาจำลองใน SPEC.md §2.3 อย่างเคร่งครัด
3. ความสามารถในการทำซ้ำ (Reproducibility):
   - ล็อก Random Seed = 20260101 ตาม config/simulation_params.yaml
==============================================================================
"""

import csv
import datetime
import os
import random
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# กำหนดช่วงราคาจำลองตั้งต้น (THB per unit) และหน่วยวัด ตาม SPEC.md §2.3
WHOLESALE_BASE_CONFIG = {
    # --------------------------------------------------------------------------
    # G1: กลุ่มเนื้อสุกรและชิ้นส่วน (Pork & Cuts)
    # --------------------------------------------------------------------------
    "pork_sliced": {"min": 140.0, "max": 170.0, "unit": "kg"},
    "pork_minced": {"min": 130.0, "max": 150.0, "unit": "kg"},
    "pork_collar_red": {"min": 140.0, "max": 170.0, "unit": "kg"},
    "pork_belly_crispy": {"min": 160.0, "max": 190.0, "unit": "kg"},
    "pork_marinated": {"min": 140.0, "max": 170.0, "unit": "kg"},
    "pork_heart": {"min": 90.0, "max": 120.0, "unit": "kg"},
    "pork_liver_fresh": {"min": 80.0, "max": 110.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G2: กลุ่มสัตว์ปีก (Poultry)
    # --------------------------------------------------------------------------
    "chicken_wings": {"min": 90.0, "max": 120.0, "unit": "kg"},
    "chicken_thigh": {"min": 70.0, "max": 90.0, "unit": "kg"},
    "chicken_breast": {"min": 70.0, "max": 90.0, "unit": "kg"},
    "chicken_meat_fresh": {"min": 70.0, "max": 90.0, "unit": "kg"},
    "roast_duck_meat": {"min": 110.0, "max": 150.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G3: กลุ่มเนื้อโค (Beef)
    # --------------------------------------------------------------------------
    "beef_meat_balls": {"min": 250.0, "max": 320.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G4: กลุ่มสัตว์น้ำและอาหารทะเลสด (Seafood)
    # --------------------------------------------------------------------------
    "river_prawn": {"min": 180.0, "max": 380.0, "unit": "kg"},
    "mixed_seafood": {"min": 180.0, "max": 300.0, "unit": "kg"},
    "white_fish_fillet": {"min": 120.0, "max": 180.0, "unit": "kg"},
    "catfish_meat": {"min": 100.0, "max": 160.0, "unit": "kg"},
    "crab_meat": {"min": 600.0, "max": 900.0, "unit": "kg"},
    "kani_miso_paste": {"min": 600.0, "max": 900.0, "unit": "kg"},
    "salmon_fillet": {"min": 550.0, "max": 750.0, "unit": "kg"},
    "salmon_sashimi_grade": {"min": 550.0, "max": 750.0, "unit": "kg"},
    "hamachi_sashimi_grade": {"min": 900.0, "max": 1200.0, "unit": "kg"},
    "hotate_scallop_grade": {"min": 900.0, "max": 1300.0, "unit": "kg"},
    "ebiko_shrimp_roe": {"min": 800.0, "max": 1100.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G5: กลุ่มไข่และเต้าหู้ (Egg & Tofu)
    # --------------------------------------------------------------------------
    "chicken_egg": {"min": 3.50, "max": 5.00, "unit": "egg"},
    "tofu_firm": {"min": 40.0, "max": 60.0, "unit": "kg"},
    "tofu_egg_tube": {"min": 40.0, "max": 60.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G6: กลุ่มคาร์โบไฮเดรตหลัก (Carb Base)
    # --------------------------------------------------------------------------
    "jasmine_rice": {"min": 25.0, "max": 40.0, "unit": "kg"},
    "japanese_rice": {"min": 60.0, "max": 90.0, "unit": "kg"},
    "pho_noodles_dry": {"min": 40.0, "max": 60.0, "unit": "kg"},
    "rice_noodles_dry": {"min": 40.0, "max": 60.0, "unit": "kg"},
    "glass_noodles_dry": {"min": 50.0, "max": 80.0, "unit": "kg"},
    "sandwich_bread": {"min": 60.0, "max": 90.0, "unit": "kg"},
    "rolled_oats": {"min": 80.0, "max": 120.0, "unit": "kg"},
    "wheat_flour": {"min": 30.0, "max": 45.0, "unit": "kg"},
    "frying_wheat_flour": {"min": 30.0, "max": 45.0, "unit": "kg"},
    "toasted_rice_powder": {"min": 40.0, "max": 60.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G7: กลุ่มผักสดและสมุนไพรพื้นฐาน (Fresh Veg & Herbs)
    # --------------------------------------------------------------------------
    "hotpot_vegetables": {"min": 30.0, "max": 70.0, "unit": "kg"},
    "cha_om_curry_vegetables": {"min": 60.0, "max": 120.0, "unit": "kg"},
    "jungle_curry_vegetables": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "salad_vegetables_herbs": {"min": 40.0, "max": 80.0, "unit": "kg"},
    "hydroponic_salad_greens": {"min": 120.0, "max": 180.0, "unit": "kg"},
    "namwa_banana": {"min": 25.0, "max": 40.0, "unit": "kg"},
    "cucumber_ginger_garlic": {"min": 30.0, "max": 60.0, "unit": "kg"},
    "cucumber_scallion": {"min": 30.0, "max": 60.0, "unit": "kg"},
    "scallion_garnish": {"min": 40.0, "max": 80.0, "unit": "kg"},
    "scallion_lime_cucumber": {"min": 35.0, "max": 70.0, "unit": "kg"},
    "aromatic_herbs": {"min": 40.0, "max": 80.0, "unit": "kg"},
    "garlic_condiments": {"min": 40.0, "max": 70.0, "unit": "kg"},
    "radish_wasabi": {"min": 50.0, "max": 100.0, "unit": "kg"},
    "side_vegetables": {"min": 30.0, "max": 60.0, "unit": "kg"},
    "soup_greens_herbs": {"min": 30.0, "max": 60.0, "unit": "kg"},
    "boat_noodle_greens": {"min": 30.0, "max": 60.0, "unit": "kg"},
    # --------------------------------------------------------------------------
    # G8: กลุ่มซอสและเครื่องปรุง (Sauces & Seasonings)
    # --------------------------------------------------------------------------
    "hotpot_broth_seasoning": {"min": 40.0, "max": 80.0, "unit": "kg"},
    "baked_sauce_seasoning": {"min": 60.0, "max": 100.0, "unit": "kg"},
    "spicy_salad_dressing": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "sour_curry_paste_seasoning": {"min": 70.0, "max": 120.0, "unit": "kg"},
    "jungle_curry_paste_fishsauce": {"min": 70.0, "max": 120.0, "unit": "kg"},
    "soy_garlic_sauce_oil": {"min": 90.0, "max": 150.0, "unit": "kg"},
    "hot_sauce_oil": {"min": 80.0, "max": 140.0, "unit": "kg"},
    "sweet_chili_sauce_oil": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "bean_paste_sauce": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "mayonnaise_butter": {"min": 80.0, "max": 140.0, "unit": "kg"},
    "bakery_dairy_sugar": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "sesame_salad_dressing": {"min": 90.0, "max": 150.0, "unit": "kg"},
    "shoyu_mayo_seasoning": {"min": 80.0, "max": 140.0, "unit": "kg"},
    "ebiko_sauce_seasoning": {"min": 100.0, "max": 160.0, "unit": "kg"},
    "japanese_mayo_shoyu": {"min": 80.0, "max": 140.0, "unit": "kg"},
    "clear_soup_seasoning": {"min": 40.0, "max": 80.0, "unit": "kg"},
    "fried_rice_seasoning_oil": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "sashimi_shoyu": {"min": 60.0, "max": 110.0, "unit": "kg"},
    "red_pork_gravy_sauce": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "duck_gravy_sauce": {"min": 50.0, "max": 90.0, "unit": "kg"},
    "boat_noodle_soup_blood": {"min": 40.0, "max": 80.0, "unit": "kg"},
}


def main():
    print("=== MueNee B2B Analytics: Generating Nakhon Pathom Wholesale Prices ===")

    # 1. โหลด sub_commodity ทั้งหมดจาก menu_bom_matrix.csv เพื่อตรวจความครบถ้วน
    bom_path = "data/reference/menu_bom_matrix.csv"
    if not os.path.exists(bom_path):
        print(f"Error: {bom_path} not found.")
        sys.exit(1)

    bom_sub_commodities = {}
    with open(bom_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            g_id = int(row["commodity_group_id"])
            sub = row["sub_commodity"]
            bom_sub_commodities[sub] = g_id

    print(
        f"Unique sub-commodities required by BOM: {len(bom_sub_commodities)}"
    )

    # ตรวจสอบว่าทุก sub_commodity ใน BOM มีการกำหนดช่วงราคาไว้
    missing_configs = [
        s for s in bom_sub_commodities if s not in WHOLESALE_BASE_CONFIG
    ]
    if missing_configs:
        print(f"❌ Error: Missing price config for: {missing_configs}")
        sys.exit(1)
    else:
        print("✅ All sub-commodities from BOM have baseline price configs.")

    # 2. ตั้งค่าช่วงเวลา 365 วัน (2026-08-01 ถึง 2027-07-31)
    start_date = datetime.date(2026, 8, 1)
    total_days = 365
    date_list = [
        start_date + datetime.timedelta(days=i) for i in range(total_days)
    ]

    # ตั้งค่า Random Seed เพื่อความแน่นอนในการจำลอง
    random.seed(20260101)

    # 3. จำลองอนุกรมเวลาราคาด้วย AR(1) Process
    rho = 0.95  # Autoregressive persistence
    output_rows = []

    # เรียงลำดับ sub_commodity ตาม commodity_group_id แล้วตามชื่อ
    sorted_items = sorted(
        bom_sub_commodities.items(), key=lambda x: (x[1], x[0])
    )

    for sub_comm, g_id in sorted_items:
        cfg = WHOLESALE_BASE_CONFIG[sub_comm]
        p_min = cfg["min"]
        p_max = cfg["max"]
        p_unit = cfg["unit"]
        p_mean = (p_min + p_max) / 2.0
        # ส่วนเบี่ยงเบนมาตรฐานของสัญญาณรบกวนต่อวัน (Daily Shock Sigma)
        sigma = (p_max - p_min) * 0.04

        # ค่าเริ่มต้นในวันแรก
        current_price = p_mean + random.gauss(0, sigma * 2)
        current_price = max(p_min, min(p_max, current_price))

        for d in date_list:
            # คำนวณราคาของวันถัดไปด้วย AR(1)
            shock = random.gauss(0, sigma)
            current_price = p_mean + rho * (current_price - p_mean) + shock
            # บังคับให้อยู่ในกรอบ Baseline อย่างเคร่งครัด
            current_price = max(p_min, min(p_max, current_price))

            output_rows.append(
                {
                    "date": d.isoformat(),
                    "commodity_group_id": g_id,
                    "sub_commodity": sub_comm,
                    "unit": p_unit,
                    "price_thb_per_unit": f"{current_price:.2f}",
                    "price_source_type": "synthetic",
                    "market_ref": "nakhon_pathom_fresh_market",
                    "scenario_id": "baseline",
                }
            )

    # 4. ตรวจสอบคุณภาพและความสมบูรณ์ของชุดข้อมูล (Assertion Checkpoints)
    expected_rows = total_days * len(sorted_items)
    print(f"\n[Verification Checkpoints]")
    print(
        f"Total generated rows: {len(output_rows)} (Expected: {expected_rows})"
    )
    assert len(output_rows) == expected_rows, "Row count mismatch!"

    # ตรวจสอบว่าไม่มีค่าว่าง และราคาทุกแถวอยู่ในช่วงที่ถูกต้อง
    for r in output_rows:
        val = float(r["price_thb_per_unit"])
        sub = r["sub_commodity"]
        cfg = WHOLESALE_BASE_CONFIG[sub]
        assert (
            cfg["min"] <= val <= cfg["max"]
        ), f"Price out of bounds for {sub}: {val}"
        assert r["price_source_type"] == "synthetic"
        assert r["scenario_id"] == "baseline"

    print("✅ 100% rows are strictly within synthetic baseline price bounds.")
    print("✅ All price_source_type = 'synthetic' and scenario_id = 'baseline'.")

    # 5. เขียนไฟล์ CSV
    out_path = "data/reference/nakhon_pathom_wholesale_prices.csv"
    fieldnames = [
        "date",
        "commodity_group_id",
        "sub_commodity",
        "unit",
        "price_thb_per_unit",
        "price_source_type",
        "market_ref",
        "scenario_id",
    ]

    with open(out_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\n🎉 Successfully wrote {len(output_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

