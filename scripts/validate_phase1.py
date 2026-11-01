"""
==============================================================================
MueNee-b2b-analytics: Phase 1 Master Validation & Gate 1 Verifier
==============================================================================
สคริปต์ตรวจสอบความถูกต้องตามเกณฑ์ความสำเร็จ (Acceptance Criteria) ของ Phase 1
ตามที่ระบุไว้ใน TASK.md (Checkpoints 1.1 - 1.5) และ SPEC.md
==============================================================================
"""

import csv
import datetime
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def print_status(check_name, passed, detail=""):
    symbol = "✅ PASS" if passed else "❌ FAIL"
    msg = f"[{symbol}] {check_name}"
    if detail:
        msg += f" - {detail}"
    print(msg)
    if not passed:
        sys.exit(1)


def validate_checkpoint_1_1():
    print("\n--- Validating Checkpoint 1.1: Folder Structure & Version Control ---")

    # 1. ตรวจสอบโฟลเดอร์หลักตาม SDD.md §5
    required_dirs = [
        "colab",
        "config",
        "data/raw",
        "data/reference",
        "data/processed",
        "r",
        "outputs/figures",
        "reports/output",
        "scripts",
    ]
    for d in required_dirs:
        print_status(f"Directory exists: {d}", os.path.isdir(d))

    # 2. ตรวจสอบเอกสารพิมพ์เขียว 5 ฉบับที่ Root
    required_docs = ["RPD.md", "SDD.md", "SPEC.md", "TASK.md", "README.md"]
    for doc in required_docs:
        print_status(f"Root Document exists: {doc}", os.path.isfile(doc))

    # 3. ตรวจสอบ .gitignore
    gitignore_path = ".gitignore"
    print_status(".gitignore exists", os.path.isfile(gitignore_path))
    with open(gitignore_path, encoding="utf-8") as f:
        content = f.read()
    print_status(
        ".gitignore excludes large raw data", "data/raw/*.csv" in content
    )
    print_status(".gitignore excludes R environment", ".Rhistory" in content)
    print_status(
        ".gitignore excludes Python cache", "__pycache__/" in content
    )


def validate_checkpoint_1_2():
    print("\n--- Validating Checkpoint 1.2: Seed Reference Catalogs ---")

    rest_path = "data/reference/restaurants_catalog.csv"
    menu_path = "data/reference/menu_items_catalog.csv"

    print_status(f"File exists: {rest_path}", os.path.isfile(rest_path))
    print_status(f"File exists: {menu_path}", os.path.isfile(menu_path))

    # ตรวจสอบ restaurants_catalog.csv
    with open(rest_path, encoding="utf-8") as f:
        restaurants = list(csv.DictReader(f))

    print_status(
        "Restaurant count is exactly 10",
        len(restaurants) == 10,
        f"Count = {len(restaurants)}",
    )

    rest_ids = set(r["restaurant_id"] for r in restaurants)
    expected_rest_ids = {
        "madam-ho-sanamchan",
        "volcano-prawn",
        "bonchon-sanamchan",
        "pa-ja-23-hours",
        "good-food-nakhon-pathom",
        "tama-nakhon-pathom",
        "loong-loy-pa-lan",
        "kinkane-89",
        "hinn-red-pork-rice",
        "thasanam-boat-noodles",
    }
    print_status(
        "Restaurant IDs match seed catalog exactly", rest_ids == expected_rest_ids
    )

    # ตรวจสอบพิกัดให้อยู่ในรัศมี 3.0 กม. จาก ม.ศิลปากร (13.8199, 100.0443)
    center_lat, center_lng = 13.8199, 100.0443
    for r in restaurants:
        lat, lng = float(r["latitude"]), float(r["longitude"])
        # ประมาณการระยะทาง Haversine แบบคร่าวๆ
        d_lat = math.radians(lat - center_lat)
        d_lng = math.radians(lng - center_lng)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(center_lat))
            * math.cos(math.radians(lat))
            * math.sin(d_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371.0 * c
        print_status(
            f"Radius check for {r['restaurant_id']}",
            dist_km <= 3.0,
            f"Distance = {dist_km:.2f} km",
        )

    # ตรวจสอบ menu_items_catalog.csv
    with open(menu_path, encoding="utf-8") as f:
        menus = list(csv.DictReader(f))

    print_status(
        "Menu items count is exactly 30",
        len(menus) == 30,
        f"Count = {len(menus)}",
    )

    # ตรวจสอบ 3 เมนูต่อร้าน
    menu_by_rest = {}
    for m in menus:
        r_id = m["restaurant_id"]
        menu_by_rest[r_id] = menu_by_rest.get(r_id, 0) + 1
    print_status(
        "Every restaurant has exactly 3 menus",
        all(count == 3 for count in menu_by_rest.values())
        and len(menu_by_rest) == 10,
    )

    # ตรวจสอบ verified = 15, unverified = 15
    conf_counts = {}
    for m in menus:
        c = m["price_confidence"]
        conf_counts[c] = conf_counts.get(c, 0) + 1
    print_status(
        "Price confidence balance: verified=15, unverified=15",
        conf_counts.get("verified") == 15
        and conf_counts.get("unverified") == 15,
        f"verified={conf_counts.get('verified')}, unverified={conf_counts.get('unverified')}",
    )

    # ตรวจสอบคอลัมน์สำคัญไม่มีค่าว่าง
    mandatory_fields = [
        "restaurant_id",
        "menu_item_id",
        "name",
        "price_tier",
        "price_amount",
        "calories",
        "protein_grams",
        "carbs_grams",
        "fat_grams",
    ]
    all_fields_present = all(
        all(m[f] != "" for f in mandatory_fields) for m in menus
    )
    print_status("No empty values in mandatory menu fields", all_fields_present)


def validate_checkpoint_1_3():
    print("\n--- Validating Checkpoint 1.3: Recipe BOM Matrix ---")

    bom_path = "data/reference/menu_bom_matrix.csv"
    print_status(f"File exists: {bom_path}", os.path.isfile(bom_path))

    with open(bom_path, encoding="utf-8") as f:
        bom_rows = list(csv.DictReader(f))

    print_status(
        "BOM entries loaded", len(bom_rows) > 0, f"Total rows = {len(bom_rows)}"
    )

    # ตรวจสอบความถูกต้องของ Foreign Key ไปยัง menu_items_catalog.csv
    with open(
        "data/reference/menu_items_catalog.csv", encoding="utf-8"
    ) as f:
        valid_menus = set(r["menu_item_id"] for r in csv.DictReader(f))

    bom_menus = set(r["menu_item_id"] for r in bom_rows)
    print_status(
        "BOM covers all 30 menus without foreign key errors",
        bom_menus == valid_menus,
    )

    # ตรวจสอบ yield_factor (0, 1] และ grams_ap >= grams_ep
    ap_valid = True
    for r in bom_rows:
        ep = float(r["grams_ep_per_serving"])
        yield_f = float(r["yield_factor"])
        ap = float(r["grams_ap_per_serving"])
        if yield_f <= 0 or yield_f > 1.0 or ap < ep - 0.1:
            ap_valid = False
            break
    print_status("Yield factor (0, 1] and AP >= EP consistency", ap_valid)

    # ตรวจสอบ Assumption Flags พิเศษ
    flags = {r["menu_item_id"]: r["assumption_flag"] for r in bom_rows}
    print_status(
        "madam-ho-paper-pot-pho has ingredients_unknown flag",
        flags.get("madam-ho-paper-pot-pho") == "ingredients_unknown",
    )
    print_status(
        "good-food-custom-sandwich has ingredients_unknown flag",
        flags.get("good-food-custom-sandwich") == "ingredients_unknown",
    )
    print_status(
        "hinn-roast-duck-rice has name_inferred flag",
        flags.get("hinn-roast-duck-rice") == "name_inferred",
    )


def validate_checkpoint_1_4():
    print("\n--- Validating Checkpoint 1.4: Configuration YAML Files ---")

    configs = [
        "config/academic_calendar.yaml",
        "config/inventory_params.yaml",
        "config/simulation_params.yaml",
    ]
    for c in configs:
        print_status(f"Config file exists: {c}", os.path.isfile(c))

    # ตรวจสอบ academic_calendar.yaml
    with open("config/academic_calendar.yaml", encoding="utf-8") as f:
        cal_content = f.read()

    print_status(
        "Calendar covers 365 days", "total_days: 365" in cal_content
    )
    print_status(
        "Calendar references Silpakorn University official source",
        "https://reg.su.ac.th/" in cal_content,
    )
    periods = [
        "regular",
        "midterm_exam",
        "final_exam",
        "semester_break",
        "summer_session",
        "public_holiday",
    ]
    for p in periods:
        print_status(f"Calendar contains period '{p}'", p in cal_content)

    # ตรวจสอบ inventory_params.yaml
    with open("config/inventory_params.yaml", encoding="utf-8") as f:
        inv_content = f.read()

    for g in [f"G{i}" for i in range(1, 9)]:
        print_status(f"Inventory params cover {g}", f"{g}:" in inv_content)

    print_status(
        "Inventory params contain Z_alpha quantiles", "z_alpha:" in inv_content
    )
    print_status(
        "Inventory params contain shelf life", "shelf_life_days" in inv_content
    )

    # ตรวจสอบ simulation_params.yaml
    with open("config/simulation_params.yaml", encoding="utf-8") as f:
        sim_content = f.read()

    print_status(
        "Simulation seed locked to 20260101", "random_seed: 20260101" in sim_content
    )
    print_status(
        "Run ID follows 'A-YYYYMMDD-vN' pattern",
        'run_id: "A-20260101-v1"' in sim_content,
    )
    print_status(
        "Contains Choice Model lambda unverified penalty",
        "lambda_unverified_penalty:" in sim_content,
    )
    print_status(
        "Contains Price Shock scenarios (SPEC §4.3)",
        "shock_pork_30:" in sim_content and "shock_seafood_40:" in sim_content,
    )


def validate_checkpoint_1_5():
    print("\n--- Validating Checkpoint 1.5: Wholesale Prices Time Series ---")

    price_path = "data/reference/nakhon_pathom_wholesale_prices.csv"
    print_status(f"File exists: {price_path}", os.path.isfile(price_path))

    with open(price_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        dates = set()
        sub_commodities = set()
        total_rows = 0
        all_synthetic = True
        all_baseline = True
        all_market = True

        for row in reader:
            total_rows += 1
            dates.add(row["date"])
            sub_commodities.add(row["sub_commodity"])
            if row["price_source_type"] != "synthetic":
                all_synthetic = False
            if row["scenario_id"] != "baseline":
                all_baseline = False
            if row["market_ref"] != "nakhon_pathom_fresh_market":
                all_market = False

    print_status(
        "Total days covered is exactly 365",
        len(dates) == 365,
        f"Distinct dates = {len(dates)}",
    )
    print_status(
        "Total sub-commodities is exactly 74",
        len(sub_commodities) == 74,
        f"Distinct sub-commodities = {len(sub_commodities)}",
    )

    expected_total = 365 * 74  # 27,010
    print_status(
        f"Total price rows equals 365 * 74 = {expected_total}",
        total_rows == expected_total,
        f"Actual rows = {total_rows}",
    )
    print_status(
        "All price_source_type are 'synthetic'", all_synthetic
    )
    print_status("All scenario_id are 'baseline'", all_baseline)
    print_status(
        "All market_ref are 'nakhon_pathom_fresh_market'", all_market
    )

    # ตรวจสอบว่าวันที่เริ่มต้นและสิ้นสุดตรงตามที่กำหนด
    sorted_dates = sorted(dates)
    print_status(
        "Start date is 2026-08-01", sorted_dates[0] == "2026-08-01"
    )
    print_status(
        "End date is 2027-07-31", sorted_dates[-1] == "2027-07-31"
    )


def main():
    print("=================================================================")
    print("      MueNee B2B Analytics: Phase 1 Gate Verification           ")
    print("=================================================================")
    validate_checkpoint_1_1()
    validate_checkpoint_1_2()
    validate_checkpoint_1_3()
    validate_checkpoint_1_4()
    validate_checkpoint_1_5()
    print("\n=================================================================")
    print(" 🎉 ALL PHASE 1 CRITERIA PASSED! GATE 1 IS OFFICIALLY CLEARED. 🎉")
    print("=================================================================\n")


if __name__ == "__main__":
    main()

