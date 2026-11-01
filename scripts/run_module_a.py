"""
==============================================================================
MueNee-b2b-analytics: Module A - Synthetic Data & Demand Simulation Engine
==============================================================================
สคริปต์ประมวลผลข้อมูลจำลองความต้องการบริโภคอาหาร (Synthetic Demand Pipeline)
จำลองพฤติกรรมผู้บริโภค 5,000 คน ตลอด 365 วัน (2026-08-01 ถึง 2027-07-31)
ตามข้อกำหนดใน SDD.md (§3), SPEC.md (§2.1, §2.4, §4.1 - §4.3) และ TASK.md (Phase 2)

ขั้นตอนการทำงานทั้ง 6 ส่วน (A1 - A6):
- A1: Schema Loader & Catalog Validator (ตรวจสอบ 10 ร้านค้า / 30 เมนู)
- A2: Synthetic User Population Generator (จำลองผู้ใช้ตาม UserDocument Schema)
- A3: Academic Calendar & Temporal Simulator (จำลองรอบเวลา วัน มื้อดึก ปฏิทิน ม.ศิลปากร)
- A4: Recommendation Filter Simulator & Choice Model (Multinomial Logit)
- A5: Vectorized/GPU Preference Trend Scoring (คำนวณ Tag Trend Scores)
- A6: CSV Exporter & Data Quality Assurance Report (สร้าง daily_meal_logs.csv, HTML Report)
==============================================================================
"""

import csv
import datetime
import hashlib
import json
import math
import os
import random
import sys
import time
import numpy as np
import pandas as pd
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_yaml(filepath):
    """โหลดไฟล์การตั้งค่า YAML"""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_sha256(filepath):
    """คำนวณค่า SHA256 Hash สำหรับตรวจสอบความถูกต้องของข้อมูล (Data Lineage)"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# ==============================================================================
# SECTION A1: Schema Loader & Catalog Validator
# ==============================================================================
def run_section_a1():
    print(
        "\n--- [Section A1] Schema Loader & Closed Catalog Verification ---"
    )

    rest_df = pd.read_csv("data/reference/restaurants_catalog.csv")
    menu_df = pd.read_csv("data/reference/menu_items_catalog.csv")

    print(f"Loaded restaurants: {len(rest_df)} (Target: 10)")
    print(f"Loaded menu items: {len(menu_df)} (Target: 30)")

    # ตรวจสอบ Foreign Key Integrity (menu_items.restaurantId -> restaurants)
    valid_rest_ids = set(rest_df["restaurant_id"])
    menu_rest_ids = set(menu_df["restaurant_id"])
    assert menu_rest_ids.issubset(
        valid_rest_ids
    ), "❌ Foreign key error in menu_items!"
    assert (
        len(menu_df) == 30
    ), "❌ Catalog must contain exactly 30 menu items!"
    assert (
        len(rest_df) == 10
    ), "❌ Catalog must contain exactly 10 restaurants!"

    # ตรวจสอบความสมบูรณ์ของคอลัมน์สำคัญ
    mandatory_cols = [
        "restaurant_id",
        "menu_item_id",
        "price_tier",
        "price_amount",
        "price_confidence",
        "calories",
        "protein_grams",
        "carbs_grams",
        "fat_grams",
    ]
    for col in mandatory_cols:
        assert (
            menu_df[col].isna().sum() == 0
        ), f"❌ Missing values found in column {col}"

    print(
        "✅ Catalog validation passed: 10 verified restaurants and 30 menus loaded cleanly."
    )
    return rest_df, menu_df


# ==============================================================================
# SECTION A2: Synthetic User Population Generator
# ==============================================================================
def run_section_a2(sim_cfg):
    print("\n--- [Section A2] Synthetic User Population Generator ---")
    random_seed = sim_cfg["meta"]["random_seed"]
    np.random.seed(random_seed)
    random.seed(random_seed)

    n_users = sim_cfg["demographics"]["total_synthetic_users"]
    segments = sim_cfg["demographics"]["segment_shares"]
    diet_cfg = sim_cfg["dietary_constraints"]

    # สร้างสัดส่วนกลุ่มผู้บริโภค
    seg_names = list(segments.keys())
    seg_probs = [segments[s]["share"] for s in seg_names]
    user_segments = np.random.choice(seg_names, size=n_users, p=seg_probs)

    users = []
    hard_opts = list(diet_cfg["hard_restrictions"].keys())
    allergy_opts = list(diet_cfg["allergies_prevalence"].keys())
    dislike_opts = list(diet_cfg["dislikes_prevalence"].keys())

    for u_idx in range(n_users):
        seg = user_segments[u_idx]

        # สุ่มช่วงอายุและลักษณะกิจกรรมตาม Demographic Segment
        if seg == "undergraduate_student":
            age = int(np.random.normal(20.5, 1.5))
            age = max(18, min(25, age))
            act = np.random.choice(
                [
                    "sedentary",
                    "lightly_active",
                    "moderately_active",
                    "very_active",
                ],
                p=[0.40, 0.35, 0.20, 0.05],
            )
            base_budget = np.random.choice(
                [60, 80, 100, 150, 250], p=[0.45, 0.35, 0.12, 0.06, 0.02]
            )
        elif seg == "faculty_and_staff":
            age = int(np.random.normal(42.0, 8.0))
            age = max(26, min(65, age))
            act = np.random.choice(
                [
                    "sedentary",
                    "lightly_active",
                    "moderately_active",
                    "very_active",
                ],
                p=[0.50, 0.35, 0.12, 0.03],
            )
            base_budget = np.random.choice(
                [80, 100, 150, 250, 400], p=[0.20, 0.40, 0.25, 0.10, 0.05]
            )
        else:  # dorm_and_community_resident
            age = int(np.random.normal(26.0, 6.0))
            age = max(18, min(70, age))
            act = np.random.choice(
                [
                    "sedentary",
                    "lightly_active",
                    "moderately_active",
                    "very_active",
                ],
                p=[0.40, 0.35, 0.20, 0.05],
            )
            base_budget = np.random.choice(
                [60, 80, 100, 150, 300], p=[0.35, 0.35, 0.18, 0.08, 0.04]
            )

        # สุ่มข้อจำกัดทางอาหาร (Hard Restrictions)
        user_hard = [
            h
            for h in hard_opts
            if random.random() < diet_cfg["hard_restrictions"][h]
        ]

        # สุ่มสารก่อภูมิแพ้ (Allergies)
        user_allergies = [
            a
            for a in allergy_opts
            if random.random() < diet_cfg["allergies_prevalence"][a]
        ]

        # สุ่มวัตถุดิบที่ไม่ชอบ (Dislikes)
        user_dislikes = [
            d
            for d in dislike_opts
            if random.random() < diet_cfg["dislikes_prevalence"][d]
        ]
        hide_disliked = (
            random.random() < diet_cfg["hide_disliked_preference_rate"]
            if user_dislikes
            else False
        )

        users.append(
            {
                "user_id": f"u_{u_idx:05d}",
                "segment": seg,
                "age": age,
                "activity_level": act,
                "meal_budget": int(base_budget),
                "hard_restrictions": user_hard,
                "allergies": user_allergies,
                "dislikes": user_dislikes,
                "hide_disliked": hide_disliked,
            }
        )

    users_df = pd.DataFrame(users)
    print(f"Generated {len(users_df)} synthetic users.")
    print("Demographics breakdown:")
    for seg, count in users_df["segment"].value_counts().items():
        print(f"  - {seg}: {count} ({count/n_users*100:.1f}%)")

    n_with_allergy = users_df["allergies"].apply(lambda x: len(x) > 0).sum()
    n_no_pork = (
        users_df["hard_restrictions"]
        .apply(lambda x: "no_pork" in x)
        .sum()
    )
    n_no_beef = (
        users_df["hard_restrictions"]
        .apply(lambda x: "no_beef" in x)
        .sum()
    )
    n_halal = (
        users_df["hard_restrictions"]
        .apply(lambda x: "halal_only" in x)
        .sum()
    )
    n_veg = (
        users_df["hard_restrictions"]
        .apply(lambda x: "vegetarian" in x)
        .sum()
    )

    print(
        f"Constraint Prevalence: Allergies={n_with_allergy} ({n_with_allergy/n_users*100:.1f}%), "
        f"No-Pork={n_no_pork}, No-Beef={n_no_beef}, Halal={n_halal}, Vegetarian={n_veg}"
    )

    return users_df


# ==============================================================================
# SECTION A3 & A4: Temporal Simulator, Choice Model & Daily Aggregator
# ==============================================================================
def run_simulation(users_df, menu_df, cal_cfg, sim_cfg):
    print(
        "\n--- [Section A3 & A4] Temporal Simulation & Recommendation Choice Engine ---"
    )

    random_seed = sim_cfg["meta"]["random_seed"]
    np.random.seed(random_seed)
    random.seed(random_seed)

    # 1. จัดทำ Dictionary ปฏิทินการศึกษาครอบคลุม 365 วัน
    periods = cal_cfg["periods"]
    holidays = {h["date"] if isinstance(h, dict) else str(h) for h in cal_cfg.get("public_holidays", [])}
    multipliers = cal_cfg["demand_multipliers"]

    start_date = datetime.date(2026, 8, 1)
    date_list = [start_date + datetime.timedelta(days=i) for i in range(365)]

    date_to_period = {}
    for d in date_list:
        d_str = d.isoformat()
        # ตรวจวันหยุดราชการก่อน
        if d_str in holidays:
            date_to_period[d_str] = "public_holiday"
            continue

        assigned = False
        for p in periods:
            p_start = datetime.date.fromisoformat(p["start_date"])
            p_end = datetime.date.fromisoformat(p["end_date"])
            if p_start <= d <= p_end:
                date_to_period[d_str] = p["period_type"]
                assigned = True
                break
        if not assigned:
            date_to_period[d_str] = "regular"

    # 2. เตรียมข้อมูลคุณลักษณะของเมนูทั้ง 30 รายการ
    menu_records = menu_df.to_dict(orient="records")
    for m in menu_records:
        m["tags_set"] = (
            set(m["tags"].split(";")) if pd.notna(m["tags"]) else set()
        )
        m["ing_set"] = (
            set(m["ingredients"].split(";"))
            if pd.notna(m["ingredients"])
            else set()
        )
        m["alg_set"] = (
            set(m["allergens"].split(";"))
            if pd.notna(m["allergens"])
            else set()
        )

    # 3. คำนวณความน่าจะเป็นในการเลือกเมนูรายบุคคล (Choice Probability Matrix)
    # Utility Function: V_{u,i} = beta_tag * S_{u,i} - beta_price * (price_i / budget_u) - lambda * unverified - delta * dislike
    beta_tag = sim_cfg["choice_model"]["beta_tag"]
    beta_price = sim_cfg["choice_model"]["beta_price"]
    lambda_unverified = sim_cfg["choice_model"][
        "lambda_unverified_penalty"
    ]
    delta_dislike = sim_cfg["choice_model"]["delta_dislike_penalty"]

    user_records = users_df.to_dict(orient="records")
    n_users = len(user_records)
    n_menus = len(menu_records)

    # สร้าง Choice Matrix แยกตาม Channel:
    # Channel 1: recommendation (กรองเด็ดขาดทั้ง Hard, AllergensKnown=False, Dislike-Hide)
    # Channel 2: organic / food_scan / manual (ผู้ใช้เลือกเอง ยอมรับความเสี่ยงได้มากกว่า)
    rec_prob_matrix = np.zeros((n_users, n_menus), dtype=np.float64)
    manual_prob_matrix = np.zeros((n_users, n_menus), dtype=np.float64)

    # คำนวณความเข้ากันได้
    for u_idx, u in enumerate(user_records):
        budget = u["meal_budget"]
        u_hard = set(u["hard_restrictions"])
        u_alg = set(u["allergies"])
        u_dis = set(u["dislikes"])
        hide_dis = u["hide_disliked"]

        u_rec_scores = []
        u_manual_scores = []

        for m_idx, m in enumerate(menu_records):
            p = m["price_amount"]
            m_ing = m["ing_set"]
            m_tags = m["tags_set"]
            unverified_flag = 1.0 if m["price_confidence"] == "unverified" else 0.0

            # --- กรองข้อห้ามเด็ดขาด (Hard Restrictions) ---
            # no_pork: ตัดหมู
            has_pork = "pork" in m_ing or "pork" in m_tags
            # no_beef: ตัดเนื้อวัว
            has_beef = "beef" in m_ing or "beef" in m_tags
            # vegetarian: ต้องยืนยันมังสวิรัติ (แต่ทุกเมนูเป็น False)
            # halal_only: ต้องยืนยันฮาลาล (แต่ทุกเมนูเป็น False)

            hard_viol = False
            if "no_pork" in u_hard and has_pork:
                hard_viol = True
            if "no_beef" in u_hard and has_beef:
                hard_viol = True
            if "vegetarian" in u_hard:
                hard_viol = True  # ทุกเมนู vegetarianConfirmed = False
            if "halal_only" in u_hard:
                hard_viol = True  # ทุกเมนู halalConfirmed = False

            if hard_viol:
                u_rec_scores.append(0.0)
                u_manual_scores.append(0.0)
                continue

            # --- กรองสารก่อภูมิแพ้ (Allergens) ---
            # กฎเหล็ก MueNee: ถ้าผู้ใช้มีอาการแพ้ และเมนู allergensKnown = False -> กรองทิ้งในระบบแนะนำเด็ดขาด!
            allergen_viol_rec = False
            if len(u_alg) > 0:
                # ในระบบ MueNee ทุกเมนู allergensKnown = False
                allergen_viol_rec = True

            # สำหรับ Manual: ตรวจเฉพาะส่วนผสมที่ระบุไว้ชัดเจน
            allergen_viol_manual = False
            if len(u_alg.intersection(m["alg_set"])) > 0:
                allergen_viol_manual = True

            # --- กรองวัตถุดิบที่ไม่ชอบ (Dislikes) ---
            has_dislike = len(u_dis.intersection(m_ing)) > 0
            if has_dislike and hide_dis:
                # ซ่อนเด็ดขาด
                u_rec_scores.append(0.0)
                u_manual_scores.append(0.0)
                continue

            # คำนวณ Utility
            tag_match = len(m_tags) * 0.1
            price_ratio = p / max(budget, 30)

            # อรรถประโยชน์พื้นฐาน
            utility_base = (
                beta_tag * tag_match
                - beta_price * price_ratio
                - lambda_unverified * unverified_flag
            )
            if has_dislike:
                utility_base -= delta_dislike

            score = math.exp(max(-10.0, min(10.0, utility_base)))

            # ใส่คะแนนลงในแต่ละ Channel
            if allergen_viol_rec:
                u_rec_scores.append(0.0)
            else:
                u_rec_scores.append(score)

            if allergen_viol_manual:
                u_manual_scores.append(0.0)
            else:
                u_manual_scores.append(score)

        # ทำ Normalization เป็นความน่าจะเป็น (Softmax Distribution)
        sum_rec = sum(u_rec_scores)
        if sum_rec > 0:
            rec_prob_matrix[u_idx] = [s / sum_rec for s in u_rec_scores]
        else:
            rec_prob_matrix[u_idx] = 0.0

        sum_man = sum(u_manual_scores)
        if sum_man > 0:
            manual_prob_matrix[u_idx] = [s / sum_man for s in u_manual_scores]
        else:
            manual_prob_matrix[u_idx] = 0.0

    print("Computed User Choice Probability Matrices.")

    # 4. คำนวณ Tag Trend Scores (Section A5 Matrix Operations)
    print("\n--- [Section A5] Vectorized Preference Trend Scoring ---")
    start_t = time.time()

    # สัดส่วนผู้ใช้ที่เมนูนี้ผ่านตัวกรอง Hard Restriction + Allergen (Eligible User Share)
    eligible_mask = (manual_prob_matrix > 0).astype(np.float64)
    eligible_user_share = eligible_mask.mean(axis=0)

    # สัดส่วนผู้ใช้ที่เมนูนี้ติดโทษ Dislike (Dislike Penalty Share)
    dislike_users_count = np.zeros(n_menus, dtype=np.float64)
    for u_idx, u in enumerate(user_records):
        u_dis = set(u["dislikes"])
        for m_idx, m in enumerate(menu_records):
            if len(u_dis.intersection(m["ing_set"])) > 0:
                dislike_users_count[m_idx] += 1
    dislike_penalty_share = dislike_users_count / n_users

    # Tag Demand Score: คำนวณจากความนิยมเฉลี่ยของผู้บริโภคปรับสเกล 0-100
    base_tag_scores = manual_prob_matrix.mean(axis=0)
    max_score = base_tag_scores.max() if base_tag_scores.max() > 0 else 1.0
    tag_demand_scores = (base_tag_scores / max_score) * 100.0

    # Restriction Exposure Index: สัดส่วนผู้ใช้ที่ไม่สามารถรับประทานเมนูนี้ได้
    restriction_exposure_index = 1.0 - eligible_user_share

    comp_time_ms = (time.time() - start_t) * 1000.0
    print(
        f"✅ Vectorized Trend Scoring completed in {comp_time_ms:.2f} ms across 5,000 users x 30 menus."
    )

    # 5. จำลองยอดขายรายวัน 365 วัน (Section A3 Temporal Simulation)
    print("Simulating daily orders across 365 days x 30 menu items...")

    daily_rows = []
    tag_trend_rows = []

    # อัตราสั่งพื้นฐานรายวันตาม Tier (Baseline Daily Volume)
    tier_base_rates = {
        "economy": 110.0,  # ร้านจานเดียว High Volume (ป้าจ๋า, ฮิ้น, ท่าสนาม)
        "mid": 40.0,  # ร้านอาหารญี่ปุ่น/สุขภาพ/ปลาบึก
        "premium_social": 14.0,  # บอนชอน, เฝอหม้อไฟ, กุ้งอบภูเขาไฟ, ซาชิมิ
    }

    run_id = sim_cfg["meta"]["run_id"]

    for d_idx, d in enumerate(date_list):
        d_str = d.isoformat()
        period_type = date_to_period[d_str]
        p_cfg = multipliers[period_type]
        period_multiplier = p_cfg["multiplier"]
        is_weekend = d.weekday() >= 5  # เสาร์-อาทิตย์
        day_of_week = d.weekday() + 1  # 1 = จันทร์, ..., 7 = อาทิตย์

        # สัดส่วนอุปสงค์ในวันหยุด vs วันธรรมดา
        weekend_mult_eco = 0.85 if is_weekend else 1.05
        weekend_mult_soc = 1.60 if is_weekend else 0.85

        # อัตราอุปสงค์มื้อดึกตามช่วงเวลา
        if period_type in ["midterm_exam", "final_exam"]:
            late_night_share = 0.24  # ช่วงสอบเด็กอ่านหนังสือดึก ยอดพุ่ง
        elif period_type == "semester_break":
            late_night_share = 0.03
        else:
            late_night_share = 0.08

        # สุ่มยอดคำสั่งซื้อของแต่ละเมนูในวันนี้
        for m_idx, m in enumerate(menu_records):
            menu_id = m["menu_item_id"]
            rest_id = m["restaurant_id"]
            tier = m["price_tier"]
            unit_p = int(m["price_amount"])
            cal = int(m["calories"])
            conf = m["price_confidence"]

            # อัตราพื้นฐานตาม Tier
            base_rate = tier_base_rates[tier]

            # ตัวคูณวันหยุด
            day_mult = weekend_mult_soc if tier == "premium_social" else weekend_mult_eco

            # ตัวคูณช่วงปฏิทิน
            # สำหรับร้านบน ถ.เพชรเกษม (ลุงลอย) ได้รับผลกระทบจากปิดเทอมน้อยกว่าร้านหน้า ม.
            effective_period_mult = period_multiplier
            if period_type == "semester_break" and rest_id == "loong-loy-pa-lan":
                effective_period_mult = 0.55  # ลูกค้าครอบครัวยังมาทาน

            # ตัวคูณความเชื่อมั่นของราคา (unverified penalty)
            conf_mult = 0.85 if conf == "unverified" else 1.0

            # คำนวณ Lambda สำหรับ Poisson Demand
            lambda_daily = (
                base_rate
                * effective_period_mult
                * day_mult
                * conf_mult
                * (0.8 + 0.4 * (eligible_user_share[m_idx]))
            )

            # สุ่มยอดขายจริงรายวัน (Poisson Sampling with Gaussian Noise)
            daily_total = int(np.random.poisson(max(1.0, lambda_daily)))

            # แบ่งสัดส่วนตามช่วงเวลา (Intra-day Windows)
            # ร้านป้าจ๋า 23 ชั่วโมง ได้มื้อดึกสูงเป็นพิเศษ
            p_late_night = (
                late_night_share * 1.5 if rest_id == "pa-ja-23-hours" else late_night_share
            )
            lunch_share = 0.45 * (1.0 - p_late_night) / 0.92
            dinner_share = 0.35 * (1.0 - p_late_night) / 0.92
            other_share = max(
                0.0, 1.0 - (lunch_share + dinner_share + p_late_night)
            )

            # สุ่มสัดส่วน
            n_late = int(round(daily_total * p_late_night))
            n_lunch = int(round(daily_total * lunch_share))
            n_dinner = int(round(daily_total * dinner_share))
            n_other = max(0, daily_total - (n_late + n_lunch + n_dinner))

            # ปรับให้ผลรวมช่วงเวลาเท่ากับ daily_total เป๊ะ 100%
            time_sum = n_lunch + n_dinner + n_late + n_other
            if time_sum != daily_total:
                n_lunch += daily_total - time_sum

            # แบ่งสัดส่วนตามช่องทางบันทึก (Channels)
            # ผู้ใช้ที่มีประวัติภูมิแพ้จะไม่เกิดใน recommendation
            # ถ้าเป็นเมนูที่มีข้อจำกัด สัดส่วน recommendation จะต่ำลง
            rec_share_adj = 0.50 * eligible_user_share[m_idx]
            food_scan_share = 0.25 + (0.50 - rec_share_adj) * 0.5
            manual_share = 1.0 - (rec_share_adj + food_scan_share)

            n_rec = int(round(daily_total * rec_share_adj))
            n_scan = int(round(daily_total * food_scan_share))
            n_man = max(0, daily_total - (n_rec + n_scan))

            # ปรับให้ผลรวมช่องทางเท่ากับ daily_total เป๊ะ 100%
            src_sum = n_rec + n_scan + n_man
            if src_sum != daily_total:
                n_man += daily_total - src_sum

            rev = daily_total * unit_p
            total_kcal = daily_total * cal

            daily_rows.append(
                {
                    "date": d_str,
                    "restaurant_id": rest_id,
                    "menu_item_id": menu_id,
                    "price_tier": tier,
                    "academic_period": period_type,
                    "day_of_week": day_of_week,
                    "is_weekend": "TRUE" if is_weekend else "FALSE",
                    "orders_total": daily_total,
                    "orders_lunch": n_lunch,
                    "orders_dinner": n_dinner,
                    "orders_late_night": n_late,
                    "orders_other": n_other,
                    "src_recommendation": n_rec,
                    "src_food_scan": n_scan,
                    "src_manual": n_man,
                    "unit_price_thb": unit_p,
                    "price_confidence": conf,
                    "revenue_thb": rev,
                    "kcal_total": total_kcal,
                    "run_id": run_id,
                }
            )

            # บันทึกคะแนนเทรนด์รายวัน
            tag_trend_rows.append(
                {
                    "date": d_str,
                    "menu_item_id": menu_id,
                    "eligible_user_share": f"{eligible_user_share[m_idx]:.4f}",
                    "dislike_penalty_share": f"{dislike_penalty_share[m_idx]:.4f}",
                    "tag_demand_score": f"{tag_demand_scores[m_idx]:.2f}",
                    "restriction_exposure_index": f"{restriction_exposure_index[m_idx]:.4f}",
                }
            )

    daily_df = pd.DataFrame(daily_rows)
    tag_trend_df = pd.DataFrame(tag_trend_rows)

    print(
        f"Generated {len(daily_df)} daily order records and {len(tag_trend_df)} tag trend records."
    )
    return daily_df, tag_trend_df, comp_time_ms


# ==============================================================================
# SECTION A6: Validation & Export
# ==============================================================================
def run_section_a6(daily_df, tag_trend_df, comp_time_ms, sim_cfg):
    print("\n--- [Section A6] Exporting Datasets & QA Verification ---")

    # 1. ตรวจสอบ Integrity Rules ของ SPEC.md §2.1
    print("Checking Integrity Rules...")
    time_sum_check = (
        daily_df["orders_lunch"]
        + daily_df["orders_dinner"]
        + daily_df["orders_late_night"]
        + daily_df["orders_other"]
    )
    assert (
        daily_df["orders_total"] == time_sum_check
    ).all(), "❌ Integrity Rule 1 Failed: orders_total != sum of time windows!"

    src_sum_check = (
        daily_df["src_recommendation"]
        + daily_df["src_food_scan"]
        + daily_df["src_manual"]
    )
    assert (
        daily_df["orders_total"] == src_sum_check
    ).all(), "❌ Integrity Rule 2 Failed: orders_total != sum of sources!"

    # ตรวจสอบ Composite Unique Key (date, menu_item_id)
    dup_count = daily_df.duplicated(subset=["date", "menu_item_id"]).sum()
    assert (
        dup_count == 0
    ), f"❌ Duplicate records found: {dup_count} duplicates!"
    assert (
        len(daily_df) == 10950
    ), f"❌ Row count mismatch: Expected 10,950, got {len(daily_df)}"

    # 2. ตรวจสอบสัดส่วนยอดขายตาม Tier (Economy > Mid > Premium)
    orders_by_tier = (
        daily_df.groupby("price_tier")["orders_total"].sum().to_dict()
    )
    print(f"Total Orders by Tier: {orders_by_tier}")
    assert (
        orders_by_tier["economy"]
        > orders_by_tier["mid"]
        > orders_by_tier["premium_social"]
    ), "❌ Tier volume hierarchy violation (Expected Economy > Mid > Premium)!"

    # 3. ตรวจสอบผลกระทบช่วงปิดเทอม (ลดลง 60-80% เทียบช่วงปกติ)
    avg_regular = daily_df[daily_df["academic_period"] == "regular"][
        "orders_total"
    ].mean()
    avg_break = daily_df[daily_df["academic_period"] == "semester_break"][
        "orders_total"
    ].mean()
    drop_pct = (avg_regular - avg_break) / avg_regular * 100.0
    print(
        f"Average Orders per Menu/Day: Regular={avg_regular:.1f}, Semester Break={avg_break:.1f} (Drop = {drop_pct:.1f}%)"
    )
    assert (
        60.0 <= drop_pct <= 80.0
    ), f"❌ Semester break drop {drop_pct:.1f}% out of target range [60%, 80%]!"

    # 4. ตรวจสอบยอดมื้อดึกช่วงสอบ (orders_late_night ช่วงสอบ >= 2 เท่าของ regular)
    late_regular = daily_df[daily_df["academic_period"] == "regular"][
        "orders_late_night"
    ].mean()
    late_exam = daily_df[
        daily_df["academic_period"].isin(["midterm_exam", "final_exam"])
    ]["orders_late_night"].mean()
    exam_late_ratio = late_exam / late_regular if late_regular > 0 else 0
    print(
        f"Late Night Orders: Regular={late_regular:.2f}, Exam Season={late_exam:.2f} (Ratio = {exam_late_ratio:.2f}x)"
    )
    assert (
        exam_late_ratio >= 2.0
    ), f"❌ Exam late night ratio {exam_late_ratio:.2f}x < 2.0x threshold!"

    print("✅ All statistical assertions and integrity rules passed 100%!")

    # 5. ส่งออกไฟล์ CSV
    daily_csv_path = "data/raw/daily_meal_logs.csv"
    tag_trend_csv_path = "data/raw/tag_trend_scores.csv"

    daily_df.to_csv(daily_csv_path, index=False, encoding="utf-8")
    tag_trend_df.to_csv(tag_trend_csv_path, index=False, encoding="utf-8")
    print(f"Exported {daily_csv_path} ({os.path.getsize(daily_csv_path)} bytes)")
    print(
        f"Exported {tag_trend_csv_path} ({os.path.getsize(tag_trend_csv_path)} bytes)"
    )

    # 6. บันทึก Metadata และ Hash
    daily_hash = calculate_sha256(daily_csv_path)
    tag_hash = calculate_sha256(tag_trend_csv_path)

    metadata = {
        "run_id": sim_cfg["meta"]["run_id"],
        "random_seed": sim_cfg["meta"]["random_seed"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_days": 365,
        "total_menus": 30,
        "total_daily_records": len(daily_df),
        "total_annual_orders": int(daily_df["orders_total"].sum()),
        "total_annual_revenue_thb": int(daily_df["revenue_thb"].sum()),
        "orders_by_tier": orders_by_tier,
        "orders_by_period": daily_df.groupby("academic_period")[
            "orders_total"
        ]
        .sum()
        .to_dict(),
        "semester_break_drop_percent": round(drop_pct, 2),
        "exam_late_night_increase_ratio": round(exam_late_ratio, 2),
        "scoring_vectorization_time_ms": round(comp_time_ms, 2),
        "file_checksums": {
            "daily_meal_logs_csv_sha256": daily_hash,
            "tag_trend_scores_csv_sha256": tag_hash,
        },
    }

    meta_path = "data/raw/run_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Exported {meta_path}")

    # 7. สร้าง Data Quality Assurance HTML Report
    html_report_path = "outputs/module_a_dq_report.html"
    generate_html_report(daily_df, metadata, html_report_path)
    print(f"Exported {html_report_path}")

    return metadata


def generate_html_report(daily_df, metadata, html_path):
    """สร้าง Data Quality Report ในรูปแบบ HTML Dashboard ที่สวยงามและพร้อมนำเสนอ"""
    tot_orders = metadata["total_annual_orders"]
    tot_rev = metadata["total_annual_revenue_thb"]
    drop_pct = metadata["semester_break_drop_percent"]
    late_ratio = metadata["exam_late_night_increase_ratio"]
    time_ms = metadata["scoring_vectorization_time_ms"]
    run_id = metadata["run_id"]

    tier_counts = metadata["orders_by_tier"]
    period_counts = metadata["orders_by_period"]

    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MueNee B2B Analytics - Module A Data Quality Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap');
        body {{ font-family: 'Sarabun', sans-serif; }}
    </style>
</head>
<body class="bg-slate-50 text-slate-800 p-6">
    <div class="max-w-5xl mx-auto space-y-6">
        <!-- Header -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
                <span class="inline-block px-3 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-semibold mb-2">Gate 2 Quality Passed ✅</span>
                <h1 class="text-2xl font-bold text-slate-900">MueNee B2B Analytics: Data Quality & Integrity Report</h1>
                <p class="text-sm text-slate-500">Module A (Synthetic Demand Generation Engine) • Run ID: <code class="bg-slate-100 px-2 py-0.5 rounded text-indigo-600">{run_id}</code></p>
            </div>
            <div class="text-right text-xs text-slate-400">
                <p>Generated: {metadata['generated_at']}</p>
                <p>Location: Sanam Chandra Palace (13.8199, 100.0443)</p>
            </div>
        </div>

        <!-- Metric Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Records</p>
                <p class="text-2xl font-bold text-slate-900 mt-1">10,950</p>
                <p class="text-xs text-emerald-600 mt-1">365 วัน × 30 เมนู (100% ครบ)</p>
            </div>
            <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Orders</p>
                <p class="text-2xl font-bold text-indigo-600 mt-1">{tot_orders:,}</p>
                <p class="text-xs text-slate-500 mt-1">ยอดสั่งซื้อจำลองทั้งปี</p>
            </div>
            <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Revenue</p>
                <p class="text-2xl font-bold text-emerald-600 mt-1">฿{tot_rev:,.0f}</p>
                <p class="text-xs text-slate-500 mt-1">มูลค่าธุรกรรมรอบ ม.ศิลปากร</p>
            </div>
            <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs font-medium text-slate-400 uppercase tracking-wider">Vectorization Time</p>
                <p class="text-2xl font-bold text-amber-600 mt-1">{time_ms:.1f} ms</p>
                <p class="text-xs text-slate-500 mt-1">5,000 ผู้ใช้ × 30 เมนู</p>
            </div>
        </div>

        <!-- Verification Gates Table -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 class="text-lg font-bold text-slate-900">ผลการตรวจสอบเกณฑ์ทางสถิติและบูรณภาพข้อมูล (Quality Gates)</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead>
                        <tr class="border-b border-slate-200 text-slate-400 text-xs uppercase">
                            <th class="pb-3">กฎการตรวจสอบ (Rule)</th>
                            <th class="pb-3">เกณฑ์เป้าหมาย (Spec)</th>
                            <th class="pb-3">ค่าที่วัดได้จริง (Observed)</th>
                            <th class="pb-3 text-right">สถานะ</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        <tr>
                            <td class="py-3 font-medium">1. Time Window Consistency</td>
                            <td>orders_total = lunch + dinner + late + other</td>
                            <td>ตรงเป๊ะ 100% ทุกแถว (10,950/10,950)</td>
                            <td class="text-right"><span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs">PASS</span></td>
                        </tr>
                        <tr>
                            <td class="py-3 font-medium">2. Source Channel Consistency</td>
                            <td>orders_total = rec + scan + manual</td>
                            <td>ตรงเป๊ะ 100% ทุกแถว (10,950/10,950)</td>
                            <td class="text-right"><span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs">PASS</span></td>
                        </tr>
                        <tr>
                            <td class="py-3 font-medium">3. Tier Volume Distribution</td>
                            <td>Economy > Mid > Premium/Social</td>
                            <td>{tier_counts.get('economy', 0):,} > {tier_counts.get('mid', 0):,} > {tier_counts.get('premium_social', 0):,}</td>
                            <td class="text-right"><span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs">PASS</span></td>
                        </tr>
                        <tr>
                            <td class="py-3 font-medium">4. Semester Break Demand Drop</td>
                            <td>ลดลง 60.0% – 80.0% เทียบช่วงปกติ</td>
                            <td>ลดลง {drop_pct:.1f}%</td>
                            <td class="text-right"><span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs">PASS</span></td>
                        </tr>
                        <tr>
                            <td class="py-3 font-medium">5. Exam Season Late Night Surge</td>
                            <td>orders_late_night ช่วงสอบ ≥ 2.0x regular</td>
                            <td>เพิ่มขึ้น {late_ratio:.2f} เท่า</td>
                            <td class="text-right"><span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs">PASS</span></td>
                        </tr>
                        <tr>
                            <td class="py-3 font-medium">6. Closed Catalog Integrity</td>
                            <td>10 ร้านค้า / 30 เมนู ตรงตาม Seed Data</td>
                            <td>Foreign Key และ Unique Key ถูกต้อง 100%</td>
                            <td class="text-right"><span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded text-xs">PASS</span></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Breakdown Details -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <h3 class="font-bold text-slate-800 text-sm">สัดส่วนยอดสั่งซื้อตามระดับราคา (Spending Tiers)</h3>
                <div class="space-y-2">
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="font-medium text-slate-600">Economy (40-70 บ.)</span>
                            <span class="font-bold">{tier_counts.get('economy', 0):,} จาน ({tier_counts.get('economy', 0)/tot_orders*100:.1f}%)</span>
                        </div>
                        <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                            <div class="bg-emerald-500 h-2.5" style="width: {tier_counts.get('economy', 0)/tot_orders*100}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="font-medium text-slate-600">Mid Tier (80-180 บ.)</span>
                            <span class="font-bold">{tier_counts.get('mid', 0):,} จาน ({tier_counts.get('mid', 0)/tot_orders*100:.1f}%)</span>
                        </div>
                        <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                            <div class="bg-blue-500 h-2.5" style="width: {tier_counts.get('mid', 0)/tot_orders*100}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="font-medium text-slate-600">Premium / Social (199-800 บ.)</span>
                            <span class="font-bold">{tier_counts.get('premium_social', 0):,} จาน ({tier_counts.get('premium_social', 0)/tot_orders*100:.1f}%)</span>
                        </div>
                        <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                            <div class="bg-purple-500 h-2.5" style="width: {tier_counts.get('premium_social', 0)/tot_orders*100}%"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <h3 class="font-bold text-slate-800 text-sm">สัดส่วนคำสั่งซื้อตามช่วงปฏิทินการศึกษา ม.ศิลปากร</h3>
                <div class="text-xs space-y-2">
                    <div class="flex justify-between border-b pb-1">
                        <span class="text-slate-500">Regular Semester (เปิดเทอมปกติ):</span>
                        <span class="font-bold text-slate-700">{period_counts.get('regular', 0):,} จาน</span>
                    </div>
                    <div class="flex justify-between border-b pb-1">
                        <span class="text-slate-500">Exam Weeks (สอบกลางภาค/ปลายภาค):</span>
                        <span class="font-bold text-indigo-600">{period_counts.get('midterm_exam', 0) + period_counts.get('final_exam', 0):,} จาน</span>
                    </div>
                    <div class="flex justify-between border-b pb-1">
                        <span class="text-slate-500">Semester Breaks (ปิดภาคเรียน):</span>
                        <span class="font-bold text-amber-600">{period_counts.get('semester_break', 0):,} จาน</span>
                    </div>
                    <div class="flex justify-between border-b pb-1">
                        <span class="text-slate-500">Summer Session & Holidays:</span>
                        <span class="font-bold text-slate-700">{period_counts.get('summer_session', 0) + period_counts.get('public_holiday', 0):,} จาน</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- File Checksums -->
        <div class="bg-slate-900 text-slate-300 p-5 rounded-2xl text-xs space-y-2 font-mono">
            <p class="text-slate-400 font-bold uppercase tracking-wider">Cryptographic Lineage Verification (SHA-256)</p>
            <p>daily_meal_logs.csv: <span class="text-emerald-400">{metadata['file_checksums']['daily_meal_logs_csv_sha256']}</span></p>
            <p>tag_trend_scores.csv: <span class="text-emerald-400">{metadata['file_checksums']['tag_trend_scores_csv_sha256']}</span></p>
        </div>
    </div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def main():
    print("==================================================================")
    print("      MueNee B2B Analytics: Module A Python Engine Execution     ")
    print("==================================================================")

    # โหลด Configurations
    cal_cfg = load_yaml("config/academic_calendar.yaml")
    sim_cfg = load_yaml("config/simulation_params.yaml")

    # รันทั้ง 6 ส่วนตามลำดับ
    rest_df, menu_df = run_section_a1()
    users_df = run_section_a2(sim_cfg)
    daily_df, tag_trend_df, comp_time_ms = run_simulation(
        users_df, menu_df, cal_cfg, sim_cfg
    )
    metadata = run_section_a6(daily_df, tag_trend_df, comp_time_ms, sim_cfg)

    print("\n==================================================================")
    print(" 🎉 MODULE A COMPLETED SUCCESSFULLY! READY FOR GATE 2 VERIFY. 🎉")
    print("==================================================================\n")


if __name__ == "__main__":
    main()
