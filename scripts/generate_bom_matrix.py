"""
==============================================================================
MueNee-b2b-analytics: Bill of Materials (BOM) Matrix Generator & Validator
==============================================================================
สคริปต์สร้างและสอบเทียบเมทริกซ์สูตรวัตถุดิบ (Recipe BOM Matrix) สำหรับ 30 เมนู
ตามข้อกำหนดทางสถิติและโภชนาการใน SPEC.md (§1.1 - §1.5 และ §2.2)

หลักการทางวิศวกรรมและสถิติ:
1. การสอบเทียบสารอาหาร (Macro Anchor Calibration):
   - โปรตีน (Protein) และ คาร์โบไฮเดรต (Carbohydrates) ที่คำนวณย้อนกลับจาก
     ผลรวม (น้ำหนักวัตถุดิบ EP x ค่าความหนาแน่นสารอาหาร) ต้องอยู่ในช่วง ±20%
     ของค่าในระบบจริง (menu_items.nutrition)
2. As-Purchased (AP) vs Edible Portion (EP):
   - AP = EP / Yield Factor เพื่อสะท้อนปริมาณสูญเสียจากการตัดแต่ง/ปรุงจริง
3. ความโปร่งใสของสมมติฐาน (Assumption Flags):
   - เมนูที่ไม่มีข้อมูลวัตถุดิบครบถ้วนจะถูกติดธง ingredients_unknown หรือ name_inferred
==============================================================================
"""

import csv
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# นิยามค่าความหนาแน่นสารอาหารต่อ 1 กรัม EP (Nutrient Density Anchor Table ตาม SPEC.md §1.4)
NUTRIENT_DENSITY = {
    # G1: หมูและชิ้นส่วน (SPEC §1.4: หมูเนื้อแดง/เครื่องใน pro 0.20, carb 0.00; หมูสามชั้น pro 0.14)
    "pork_sliced": {"pro": 0.20, "carb": 0.00},
    "pork_minced": {"pro": 0.20, "carb": 0.00},
    "pork_collar_red": {"pro": 0.20, "carb": 0.00},
    "pork_belly_crispy": {"pro": 0.14, "carb": 0.00},
    "pork_marinated": {"pro": 0.20, "carb": 0.00},
    "pork_heart": {"pro": 0.20, "carb": 0.00},
    "pork_liver_fresh": {"pro": 0.20, "carb": 0.00},
    # G2: สัตว์ปีก (SPEC §1.4: ไก่ pro 0.20, carb 0.00; เป็ด pro 0.19)
    "chicken_wings": {"pro": 0.20, "carb": 0.00},
    "chicken_thigh": {"pro": 0.20, "carb": 0.00},
    "chicken_breast": {"pro": 0.20, "carb": 0.00},
    "chicken_meat_fresh": {"pro": 0.20, "carb": 0.00},
    "roast_duck_meat": {"pro": 0.19, "carb": 0.00},
    # G3: เนื้อโค (SPEC §1.4: เนื้อวัว/ลูกชิ้น pro 0.20, carb 0.00)
    "beef_meat_balls": {"pro": 0.20, "carb": 0.00},
    # G4: สัตว์น้ำและอาหารทะเล (SPEC §1.4: กุ้ง/แซลมอน pro 0.20; ฮามาจิ 0.22; ปลาบึก/ปู 0.18; ปูคานิ 0.17; หอยเชลล์ pro 0.17, carb 0.03)
    "river_prawn": {"pro": 0.20, "carb": 0.00},
    "mixed_seafood": {"pro": 0.20, "carb": 0.00},
    "white_fish_fillet": {"pro": 0.20, "carb": 0.00},
    "catfish_meat": {"pro": 0.18, "carb": 0.00},
    "crab_meat": {"pro": 0.18, "carb": 0.00},
    "kani_miso_paste": {"pro": 0.17, "carb": 0.00},
    "salmon_fillet": {"pro": 0.20, "carb": 0.00},
    "salmon_sashimi_grade": {"pro": 0.20, "carb": 0.00},
    "hamachi_sashimi_grade": {"pro": 0.22, "carb": 0.00},
    "hotate_scallop_grade": {"pro": 0.17, "carb": 0.03},
    "ebiko_shrimp_roe": {"pro": 0.20, "carb": 0.00},
    # G5: ไข่และเต้าหู้ (SPEC §1.4: ไข่ไก่ pro 0.125, carb 0.00; เต้าหู้ pro 0.07, carb 0.02)
    "chicken_egg": {"pro": 0.125, "carb": 0.00},
    "tofu_firm": {"pro": 0.07, "carb": 0.02},
    "tofu_egg_tube": {"pro": 0.07, "carb": 0.02},
    # G6: คาร์โบไฮเดรตหลัก (SPEC §1.4: ข้าว/แป้ง pro 0.07, carb 0.78; เส้น pro 0.06, carb 0.80; ขนมปัง pro 0.09, carb 0.50; โอ๊ต+แป้ง pro 0.10, carb 0.70; วุ้นเส้น carb 0.86)
    "jasmine_rice": {"pro": 0.07, "carb": 0.78},
    "japanese_rice": {"pro": 0.07, "carb": 0.78},
    "pho_noodles_dry": {"pro": 0.06, "carb": 0.80},
    "rice_noodles_dry": {"pro": 0.06, "carb": 0.80},
    "glass_noodles_dry": {"pro": 0.00, "carb": 0.86},
    "sandwich_bread": {"pro": 0.09, "carb": 0.50},
    "rolled_oats": {"pro": 0.10, "carb": 0.70},
    "wheat_flour": {"pro": 0.10, "carb": 0.70},
    "frying_wheat_flour": {"pro": 0.07, "carb": 0.78},
    "toasted_rice_powder": {"pro": 0.07, "carb": 0.78},
    # G7: ผักสดและสมุนไพร (SPEC §1.4: ผักสด/สมุนไพร pro 0.02, carb 0.06; กล้วยน้ำว้า pro 0.01, carb 0.23)
    "hotpot_vegetables": {"pro": 0.02, "carb": 0.06},
    "cha_om_curry_vegetables": {"pro": 0.02, "carb": 0.06},
    "jungle_curry_vegetables": {"pro": 0.02, "carb": 0.06},
    "salad_vegetables_herbs": {"pro": 0.02, "carb": 0.06},
    "hydroponic_salad_greens": {"pro": 0.02, "carb": 0.06},
    "namwa_banana": {"pro": 0.01, "carb": 0.23},
    "cucumber_ginger_garlic": {"pro": 0.02, "carb": 0.06},
    "cucumber_scallion": {"pro": 0.02, "carb": 0.06},
    "scallion_garnish": {"pro": 0.02, "carb": 0.06},
    "scallion_lime_cucumber": {"pro": 0.02, "carb": 0.06},
    "aromatic_herbs": {"pro": 0.02, "carb": 0.06},
    "garlic_condiments": {"pro": 0.02, "carb": 0.06},
    "radish_wasabi": {"pro": 0.02, "carb": 0.06},
    "side_vegetables": {"pro": 0.02, "carb": 0.06},
    "soup_greens_herbs": {"pro": 0.02, "carb": 0.06},
    "boat_noodle_greens": {"pro": 0.02, "carb": 0.06},
    # G8: ซอสและเครื่องปรุง (SPEC §1.4: ซอสทั่วไป pro 0.03, carb 0.25; มายองเนส 0.01/0.04; โชยุ 0.03/0.10; พริกแกง 0.03/0.20; น้ำซุปน้ำตก 0.05/0.15; เบเกอรี่ 0.02/0.33)
    "hotpot_broth_seasoning": {"pro": 0.03, "carb": 0.25},
    "baked_sauce_seasoning": {"pro": 0.03, "carb": 0.25},
    "spicy_salad_dressing": {"pro": 0.03, "carb": 0.20},
    "sour_curry_paste_seasoning": {"pro": 0.03, "carb": 0.20},
    "jungle_curry_paste_fishsauce": {"pro": 0.03, "carb": 0.20},
    "soy_garlic_sauce_oil": {"pro": 0.03, "carb": 0.25},
    "hot_sauce_oil": {"pro": 0.03, "carb": 0.25},
    "sweet_chili_sauce_oil": {"pro": 0.03, "carb": 0.25},
    "bean_paste_sauce": {"pro": 0.03, "carb": 0.25},
    "mayonnaise_butter": {"pro": 0.01, "carb": 0.04},
    "bakery_dairy_sugar": {"pro": 0.02, "carb": 0.33},
    "sesame_salad_dressing": {"pro": 0.03, "carb": 0.25},
    "shoyu_mayo_seasoning": {"pro": 0.02, "carb": 0.10},
    "ebiko_sauce_seasoning": {"pro": 0.03, "carb": 0.15},
    "japanese_mayo_shoyu": {"pro": 0.02, "carb": 0.10},
    "clear_soup_seasoning": {"pro": 0.03, "carb": 0.25},
    "fried_rice_seasoning_oil": {"pro": 0.03, "carb": 0.25},
    "sashimi_shoyu": {"pro": 0.03, "carb": 0.10},
    "red_pork_gravy_sauce": {"pro": 0.03, "carb": 0.25},
    "duck_gravy_sauce": {"pro": 0.03, "carb": 0.25},
    "boat_noodle_soup_blood": {"pro": 0.05, "carb": 0.15},
}


# นิยาม BOM ละเอียดระดับรายการวัตถุดิบย่อยสำหรับ 30 เมนู
# (ตรวจสอบให้ผลรวมรายกลุ่ม G1-G8 เท่ากับตารางใน SPEC.md §1.2 ทุกประการ)
BOM_ENTRIES = [
    # 1. madam-ho-pork-crunch-set
    ("madam-ho-sanamchan", "madam-ho-pork-crunch-set", 1, "pork_and_cuts", "pork_sliced", 220.0, 0.90, "high", "standard"),
    ("madam-ho-sanamchan", "madam-ho-pork-crunch-set", 5, "egg_and_tofu", "tofu_firm", 40.0, 1.00, "high", "standard"),
    ("madam-ho-sanamchan", "madam-ho-pork-crunch-set", 6, "carb_base", "pho_noodles_dry", 70.0, 1.00, "low", "standard"),
    ("madam-ho-sanamchan", "madam-ho-pork-crunch-set", 7, "fresh_veg_herbs", "hotpot_vegetables", 150.0, 0.80, "high", "standard"),
    ("madam-ho-sanamchan", "madam-ho-pork-crunch-set", 8, "sauce_seasoning", "hotpot_broth_seasoning", 60.0, 1.00, "low", "standard"),

    # 2. madam-ho-paper-pot-pho (ingredients_unknown)
    ("madam-ho-sanamchan", "madam-ho-paper-pot-pho", 1, "pork_and_cuts", "pork_sliced", 140.0, 0.90, "high", "ingredients_unknown"),
    ("madam-ho-sanamchan", "madam-ho-paper-pot-pho", 5, "egg_and_tofu", "chicken_egg", 50.0, 0.88, "medium", "ingredients_unknown"),
    ("madam-ho-sanamchan", "madam-ho-paper-pot-pho", 6, "carb_base", "pho_noodles_dry", 110.0, 1.00, "low", "ingredients_unknown"),
    ("madam-ho-sanamchan", "madam-ho-paper-pot-pho", 7, "fresh_veg_herbs", "hotpot_vegetables", 150.0, 0.80, "high", "ingredients_unknown"),
    ("madam-ho-sanamchan", "madam-ho-paper-pot-pho", 8, "sauce_seasoning", "hotpot_broth_seasoning", 60.0, 1.00, "low", "ingredients_unknown"),

    # 3. madam-ho-soft-pork-heart-set (G1 = 220 + 60 = 280)
    ("madam-ho-sanamchan", "madam-ho-soft-pork-heart-set", 1, "pork_and_cuts", "pork_sliced", 220.0, 0.90, "high", "standard"),
    ("madam-ho-sanamchan", "madam-ho-soft-pork-heart-set", 1, "pork_and_cuts", "pork_heart", 60.0, 0.95, "ultra", "standard"),
    ("madam-ho-sanamchan", "madam-ho-soft-pork-heart-set", 5, "egg_and_tofu", "tofu_firm", 50.0, 1.00, "high", "standard"),
    ("madam-ho-sanamchan", "madam-ho-soft-pork-heart-set", 6, "carb_base", "pho_noodles_dry", 75.0, 1.00, "low", "standard"),
    ("madam-ho-sanamchan", "madam-ho-soft-pork-heart-set", 7, "fresh_veg_herbs", "hotpot_vegetables", 180.0, 0.80, "high", "standard"),
    ("madam-ho-sanamchan", "madam-ho-soft-pork-heart-set", 8, "sauce_seasoning", "hotpot_broth_seasoning", 60.0, 1.00, "low", "standard"),

    # 4. volcano-baked-prawn
    ("volcano-prawn", "volcano-baked-prawn", 4, "seafood", "river_prawn", 420.0, 0.55, "high", "standard"),
    ("volcano-prawn", "volcano-baked-prawn", 6, "carb_base", "glass_noodles_dry", 20.0, 1.00, "low", "standard"),
    ("volcano-prawn", "volcano-baked-prawn", 7, "fresh_veg_herbs", "aromatic_herbs", 80.0, 0.80, "high", "standard"),
    ("volcano-prawn", "volcano-baked-prawn", 8, "sauce_seasoning", "baked_sauce_seasoning", 30.0, 1.00, "low", "standard"),

    # 5. volcano-three-armies-salad (G4 = 90 + 90 = 180)
    ("volcano-prawn", "volcano-three-armies-salad", 4, "seafood", "river_prawn", 90.0, 0.55, "high", "standard"),
    ("volcano-prawn", "volcano-three-armies-salad", 4, "seafood", "mixed_seafood", 90.0, 0.80, "high", "standard"),
    ("volcano-prawn", "volcano-three-armies-salad", 6, "carb_base", "glass_noodles_dry", 20.0, 1.00, "low", "standard"),
    ("volcano-prawn", "volcano-three-armies-salad", 7, "fresh_veg_herbs", "salad_vegetables_herbs", 150.0, 0.80, "high", "standard"),
    ("volcano-prawn", "volcano-three-armies-salad", 8, "sauce_seasoning", "spicy_salad_dressing", 30.0, 1.00, "low", "standard"),

    # 6. volcano-sour-curry-prawn-omelette
    ("volcano-prawn", "volcano-sour-curry-prawn-omelette", 4, "seafood", "river_prawn", 90.0, 0.55, "high", "standard"),
    ("volcano-prawn", "volcano-sour-curry-prawn-omelette", 5, "egg_and_tofu", "chicken_egg", 100.0, 0.88, "medium", "standard"),
    ("volcano-prawn", "volcano-sour-curry-prawn-omelette", 7, "fresh_veg_herbs", "cha_om_curry_vegetables", 220.0, 0.80, "high", "standard"),
    ("volcano-prawn", "volcano-sour-curry-prawn-omelette", 8, "sauce_seasoning", "sour_curry_paste_seasoning", 70.0, 1.00, "low", "standard"),

    # 7. bonchon-wings-6
    ("bonchon-sanamchan", "bonchon-wings-6", 2, "poultry", "chicken_wings", 200.0, 0.75, "high", "standard"),
    ("bonchon-sanamchan", "bonchon-wings-6", 6, "carb_base", "frying_wheat_flour", 45.0, 1.00, "low", "standard"),
    ("bonchon-sanamchan", "bonchon-wings-6", 7, "fresh_veg_herbs", "garlic_condiments", 20.0, 0.80, "medium", "standard"),
    ("bonchon-sanamchan", "bonchon-wings-6", 8, "sauce_seasoning", "soy_garlic_sauce_oil", 35.0, 1.00, "low", "standard"),

    # 8. bonchon-chicken-rice-soy-garlic (G6 = 100 + 15 = 115)
    ("bonchon-sanamchan", "bonchon-chicken-rice-soy-garlic", 2, "poultry", "chicken_thigh", 160.0, 0.85, "high", "standard"),
    ("bonchon-sanamchan", "bonchon-chicken-rice-soy-garlic", 6, "carb_base", "jasmine_rice", 100.0, 1.00, "low", "standard"),
    ("bonchon-sanamchan", "bonchon-chicken-rice-soy-garlic", 6, "carb_base", "frying_wheat_flour", 15.0, 1.00, "low", "standard"),
    ("bonchon-sanamchan", "bonchon-chicken-rice-soy-garlic", 7, "fresh_veg_herbs", "side_vegetables", 40.0, 0.80, "high", "standard"),
    ("bonchon-sanamchan", "bonchon-chicken-rice-soy-garlic", 8, "sauce_seasoning", "soy_garlic_sauce_oil", 35.0, 1.00, "low", "standard"),

    # 9. bonchon-fish-rice-hot (G6 = 105 + 20 = 125)
    ("bonchon-sanamchan", "bonchon-fish-rice-hot", 4, "seafood", "white_fish_fillet", 130.0, 0.90, "high", "standard"),
    ("bonchon-sanamchan", "bonchon-fish-rice-hot", 6, "carb_base", "jasmine_rice", 105.0, 1.00, "low", "standard"),
    ("bonchon-sanamchan", "bonchon-fish-rice-hot", 6, "carb_base", "frying_wheat_flour", 20.0, 1.00, "low", "standard"),
    ("bonchon-sanamchan", "bonchon-fish-rice-hot", 7, "fresh_veg_herbs", "side_vegetables", 40.0, 0.80, "high", "standard"),
    ("bonchon-sanamchan", "bonchon-fish-rice-hot", 8, "sauce_seasoning", "hot_sauce_oil", 30.0, 1.00, "low", "standard"),

    # 10. pa-ja-boiled-chicken-rice
    ("pa-ja-23-hours", "pa-ja-boiled-chicken-rice", 2, "poultry", "chicken_meat_fresh", 125.0, 0.85, "high", "standard"),
    ("pa-ja-23-hours", "pa-ja-boiled-chicken-rice", 6, "carb_base", "jasmine_rice", 95.0, 1.00, "low", "standard"),
    ("pa-ja-23-hours", "pa-ja-boiled-chicken-rice", 7, "fresh_veg_herbs", "cucumber_ginger_garlic", 30.0, 0.80, "high", "standard"),
    ("pa-ja-23-hours", "pa-ja-boiled-chicken-rice", 8, "sauce_seasoning", "bean_paste_sauce", 25.0, 1.00, "low", "standard"),

    # 11. pa-ja-fried-chicken-rice (G6 = 90 + 15 = 105)
    ("pa-ja-23-hours", "pa-ja-fried-chicken-rice", 2, "poultry", "chicken_thigh", 130.0, 0.85, "high", "standard"),
    ("pa-ja-23-hours", "pa-ja-fried-chicken-rice", 6, "carb_base", "jasmine_rice", 90.0, 1.00, "low", "standard"),
    ("pa-ja-23-hours", "pa-ja-fried-chicken-rice", 6, "carb_base", "frying_wheat_flour", 15.0, 1.00, "low", "standard"),
    ("pa-ja-23-hours", "pa-ja-fried-chicken-rice", 7, "fresh_veg_herbs", "cucumber_ginger_garlic", 30.0, 0.80, "high", "standard"),
    ("pa-ja-23-hours", "pa-ja-fried-chicken-rice", 8, "sauce_seasoning", "sweet_chili_sauce_oil", 25.0, 1.00, "low", "standard"),

    # 12. pa-ja-spicy-chicken-rice
    ("pa-ja-23-hours", "pa-ja-spicy-chicken-rice", 2, "poultry", "chicken_meat_fresh", 135.0, 0.85, "high", "standard"),
    ("pa-ja-23-hours", "pa-ja-spicy-chicken-rice", 6, "carb_base", "jasmine_rice", 105.0, 1.00, "low", "standard"),
    ("pa-ja-23-hours", "pa-ja-spicy-chicken-rice", 7, "fresh_veg_herbs", "salad_vegetables_herbs", 60.0, 0.80, "high", "standard"),
    ("pa-ja-23-hours", "pa-ja-spicy-chicken-rice", 8, "sauce_seasoning", "spicy_salad_dressing", 30.0, 1.00, "low", "standard"),

    # 13. good-food-custom-sandwich (ingredients_unknown)
    ("good-food-nakhon-pathom", "good-food-custom-sandwich", 2, "poultry", "chicken_breast", 35.0, 0.85, "high", "ingredients_unknown"),
    ("good-food-nakhon-pathom", "good-food-custom-sandwich", 5, "egg_and_tofu", "chicken_egg", 60.0, 0.88, "medium", "ingredients_unknown"),
    ("good-food-nakhon-pathom", "good-food-custom-sandwich", 6, "carb_base", "sandwich_bread", 80.0, 1.00, "medium", "ingredients_unknown"),
    ("good-food-nakhon-pathom", "good-food-custom-sandwich", 7, "fresh_veg_herbs", "hydroponic_salad_greens", 60.0, 0.80, "high", "ingredients_unknown"),
    ("good-food-nakhon-pathom", "good-food-custom-sandwich", 8, "sauce_seasoning", "mayonnaise_butter", 25.0, 1.00, "low", "ingredients_unknown"),

    # 14. good-food-banana-oat-loaf (G6 = 25 + 15 = 40)
    ("good-food-nakhon-pathom", "good-food-banana-oat-loaf", 5, "egg_and_tofu", "chicken_egg", 15.0, 0.88, "medium", "standard"),
    ("good-food-nakhon-pathom", "good-food-banana-oat-loaf", 6, "carb_base", "rolled_oats", 25.0, 1.00, "low", "standard"),
    ("good-food-nakhon-pathom", "good-food-banana-oat-loaf", 6, "carb_base", "wheat_flour", 15.0, 1.00, "low", "standard"),
    ("good-food-nakhon-pathom", "good-food-banana-oat-loaf", 7, "fresh_veg_herbs", "namwa_banana", 50.0, 0.80, "medium", "standard"),
    ("good-food-nakhon-pathom", "good-food-banana-oat-loaf", 8, "sauce_seasoning", "bakery_dairy_sugar", 15.0, 1.00, "low", "standard"),

    # 15. good-food-salmon-salad-rice
    ("good-food-nakhon-pathom", "good-food-salmon-salad-rice", 4, "seafood", "salmon_fillet", 120.0, 0.90, "high", "standard"),
    ("good-food-nakhon-pathom", "good-food-salmon-salad-rice", 6, "carb_base", "jasmine_rice", 70.0, 1.00, "low", "standard"),
    ("good-food-nakhon-pathom", "good-food-salmon-salad-rice", 7, "fresh_veg_herbs", "hydroponic_salad_greens", 100.0, 0.80, "high", "standard"),
    ("good-food-nakhon-pathom", "good-food-salmon-salad-rice", 8, "sauce_seasoning", "sesame_salad_dressing", 20.0, 1.00, "low", "standard"),

    # 16. tama-kani-miso-set (G4 = 60 + 30 = 90)
    ("tama-nakhon-pathom", "tama-kani-miso-set", 4, "seafood", "crab_meat", 60.0, 0.85, "high", "standard"),
    ("tama-nakhon-pathom", "tama-kani-miso-set", 4, "seafood", "kani_miso_paste", 30.0, 1.00, "high", "standard"),
    ("tama-nakhon-pathom", "tama-kani-miso-set", 5, "egg_and_tofu", "chicken_egg", 30.0, 0.88, "medium", "standard"),
    ("tama-nakhon-pathom", "tama-kani-miso-set", 6, "carb_base", "japanese_rice", 85.0, 1.00, "low", "standard"),
    ("tama-nakhon-pathom", "tama-kani-miso-set", 7, "fresh_veg_herbs", "scallion_garnish", 20.0, 0.80, "high", "standard"),
    ("tama-nakhon-pathom", "tama-kani-miso-set", 8, "sauce_seasoning", "shoyu_mayo_seasoning", 25.0, 1.00, "low", "standard"),

    # 17. tama-salmon-ebiko-sauce-rice (G4 = 110 + 15 = 125)
    ("tama-nakhon-pathom", "tama-salmon-ebiko-sauce-rice", 4, "seafood", "salmon_fillet", 110.0, 0.90, "high", "standard"),
    ("tama-nakhon-pathom", "tama-salmon-ebiko-sauce-rice", 4, "seafood", "ebiko_shrimp_roe", 15.0, 1.00, "high", "standard"),
    ("tama-nakhon-pathom", "tama-salmon-ebiko-sauce-rice", 6, "carb_base", "japanese_rice", 95.0, 1.00, "low", "standard"),
    ("tama-nakhon-pathom", "tama-salmon-ebiko-sauce-rice", 7, "fresh_veg_herbs", "scallion_garnish", 15.0, 0.80, "high", "standard"),
    ("tama-nakhon-pathom", "tama-salmon-ebiko-sauce-rice", 8, "sauce_seasoning", "ebiko_sauce_seasoning", 30.0, 1.00, "low", "standard"),

    # 18. tama-torched-salmon-mayo-rice
    ("tama-nakhon-pathom", "tama-torched-salmon-mayo-rice", 4, "seafood", "salmon_fillet", 120.0, 0.90, "high", "standard"),
    ("tama-nakhon-pathom", "tama-torched-salmon-mayo-rice", 5, "egg_and_tofu", "chicken_egg", 10.0, 0.88, "medium", "standard"),
    ("tama-nakhon-pathom", "tama-torched-salmon-mayo-rice", 6, "carb_base", "japanese_rice", 95.0, 1.00, "low", "standard"),
    ("tama-nakhon-pathom", "tama-torched-salmon-mayo-rice", 7, "fresh_veg_herbs", "scallion_garnish", 15.0, 0.80, "high", "standard"),
    ("tama-nakhon-pathom", "tama-torched-salmon-mayo-rice", 8, "sauce_seasoning", "japanese_mayo_shoyu", 35.0, 1.00, "low", "standard"),

    # 19. loong-loy-tofu-pork-soup
    ("loong-loy-pa-lan", "loong-loy-tofu-pork-soup", 1, "pork_and_cuts", "pork_minced", 70.0, 0.90, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-tofu-pork-soup", 5, "egg_and_tofu", "tofu_egg_tube", 120.0, 1.00, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-tofu-pork-soup", 7, "fresh_veg_herbs", "soup_greens_herbs", 100.0, 0.80, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-tofu-pork-soup", 8, "sauce_seasoning", "clear_soup_seasoning", 20.0, 1.00, "low", "standard"),

    # 20. loong-loy-large-crab-fried-rice
    ("loong-loy-pa-lan", "loong-loy-large-crab-fried-rice", 4, "seafood", "crab_meat", 90.0, 0.85, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-large-crab-fried-rice", 5, "egg_and_tofu", "chicken_egg", 100.0, 0.88, "medium", "standard"),
    ("loong-loy-pa-lan", "loong-loy-large-crab-fried-rice", 6, "carb_base", "jasmine_rice", 140.0, 1.00, "low", "standard"),
    ("loong-loy-pa-lan", "loong-loy-large-crab-fried-rice", 7, "fresh_veg_herbs", "scallion_lime_cucumber", 50.0, 0.80, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-large-crab-fried-rice", 8, "sauce_seasoning", "fried_rice_seasoning_oil", 30.0, 1.00, "low", "standard"),

    # 21. loong-loy-jungle-catfish-curry
    ("loong-loy-pa-lan", "loong-loy-jungle-catfish-curry", 4, "seafood", "catfish_meat", 150.0, 0.85, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-jungle-catfish-curry", 7, "fresh_veg_herbs", "jungle_curry_vegetables", 180.0, 0.80, "high", "standard"),
    ("loong-loy-pa-lan", "loong-loy-jungle-catfish-curry", 8, "sauce_seasoning", "jungle_curry_paste_fishsauce", 40.0, 1.00, "low", "standard"),

    # 22. kinkane-salmon-sashimi
    ("kinkane-89", "kinkane-salmon-sashimi", 4, "seafood", "salmon_sashimi_grade", 150.0, 0.90, "ultra", "standard"),
    ("kinkane-89", "kinkane-salmon-sashimi", 7, "fresh_veg_herbs", "radish_wasabi", 15.0, 0.80, "medium", "standard"),
    ("kinkane-89", "kinkane-salmon-sashimi", 8, "sauce_seasoning", "sashimi_shoyu", 10.0, 1.00, "low", "standard"),

    # 23. kinkane-hamachi-sashimi
    ("kinkane-89", "kinkane-hamachi-sashimi", 4, "seafood", "hamachi_sashimi_grade", 130.0, 0.90, "ultra", "standard"),
    ("kinkane-89", "kinkane-hamachi-sashimi", 7, "fresh_veg_herbs", "radish_wasabi", 15.0, 0.80, "medium", "standard"),
    ("kinkane-89", "kinkane-hamachi-sashimi", 8, "sauce_seasoning", "sashimi_shoyu", 10.0, 1.00, "low", "standard"),

    # 24. kinkane-scallop-sashimi
    ("kinkane-89", "kinkane-scallop-sashimi", 4, "seafood", "hotate_scallop_grade", 160.0, 0.95, "ultra", "standard"),
    ("kinkane-89", "kinkane-scallop-sashimi", 7, "fresh_veg_herbs", "radish_wasabi", 15.0, 0.80, "medium", "standard"),
    ("kinkane-89", "kinkane-scallop-sashimi", 8, "sauce_seasoning", "sashimi_shoyu", 10.0, 1.00, "low", "standard"),

    # 25. hinn-red-pork-rice
    ("hinn-red-pork-rice", "hinn-red-pork-rice", 1, "pork_and_cuts", "pork_collar_red", 80.0, 0.90, "high", "standard"),
    ("hinn-red-pork-rice", "hinn-red-pork-rice", 5, "egg_and_tofu", "chicken_egg", 50.0, 0.88, "medium", "standard"),
    ("hinn-red-pork-rice", "hinn-red-pork-rice", 6, "carb_base", "jasmine_rice", 95.0, 1.00, "low", "standard"),
    ("hinn-red-pork-rice", "hinn-red-pork-rice", 7, "fresh_veg_herbs", "cucumber_scallion", 20.0, 0.80, "high", "standard"),
    ("hinn-red-pork-rice", "hinn-red-pork-rice", 8, "sauce_seasoning", "red_pork_gravy_sauce", 45.0, 1.00, "low", "standard"),

    # 26. hinn-crispy-pork-rice
    ("hinn-red-pork-rice", "hinn-crispy-pork-rice", 1, "pork_and_cuts", "pork_belly_crispy", 110.0, 0.85, "high", "standard"),
    ("hinn-red-pork-rice", "hinn-crispy-pork-rice", 5, "egg_and_tofu", "chicken_egg", 50.0, 0.88, "medium", "standard"),
    ("hinn-red-pork-rice", "hinn-crispy-pork-rice", 6, "carb_base", "jasmine_rice", 95.0, 1.00, "low", "standard"),
    ("hinn-red-pork-rice", "hinn-crispy-pork-rice", 7, "fresh_veg_herbs", "cucumber_scallion", 20.0, 0.80, "high", "standard"),
    ("hinn-red-pork-rice", "hinn-crispy-pork-rice", 8, "sauce_seasoning", "red_pork_gravy_sauce", 45.0, 1.00, "low", "standard"),

    # 27. hinn-roast-duck-rice (name_inferred)
    ("hinn-red-pork-rice", "hinn-roast-duck-rice", 2, "poultry", "roast_duck_meat", 110.0, 0.55, "high", "name_inferred"),
    ("hinn-red-pork-rice", "hinn-roast-duck-rice", 5, "egg_and_tofu", "chicken_egg", 50.0, 0.88, "medium", "name_inferred"),
    ("hinn-red-pork-rice", "hinn-roast-duck-rice", 6, "carb_base", "jasmine_rice", 95.0, 1.00, "low", "name_inferred"),
    ("hinn-red-pork-rice", "hinn-roast-duck-rice", 7, "fresh_veg_herbs", "cucumber_scallion", 20.0, 0.80, "high", "name_inferred"),
    ("hinn-red-pork-rice", "hinn-roast-duck-rice", 8, "sauce_seasoning", "duck_gravy_sauce", 40.0, 1.00, "low", "name_inferred"),

    # 28. thasanam-boat-noodle-soup
    ("thasanam-boat-noodles", "thasanam-boat-noodle-soup", 1, "pork_and_cuts", "pork_marinated", 40.0, 0.90, "high", "standard"),
    ("thasanam-boat-noodles", "thasanam-boat-noodle-soup", 3, "beef", "beef_meat_balls", 35.0, 0.85, "high", "standard"),
    ("thasanam-boat-noodles", "thasanam-boat-noodle-soup", 6, "carb_base", "rice_noodles_dry", 60.0, 1.00, "low", "standard"),
    ("thasanam-boat-noodles", "thasanam-boat-noodle-soup", 7, "fresh_veg_herbs", "boat_noodle_greens", 50.0, 0.80, "high", "standard"),
    ("thasanam-boat-noodles", "thasanam-boat-noodle-soup", 8, "sauce_seasoning", "boat_noodle_soup_blood", 35.0, 1.00, "ultra", "standard"),

    # 29. thasanam-spicy-pork
    ("thasanam-boat-noodles", "thasanam-spicy-pork", 1, "pork_and_cuts", "pork_sliced", 150.0, 0.90, "high", "standard"),
    ("thasanam-boat-noodles", "thasanam-spicy-pork", 6, "carb_base", "toasted_rice_powder", 10.0, 1.00, "low", "standard"),
    ("thasanam-boat-noodles", "thasanam-spicy-pork", 7, "fresh_veg_herbs", "salad_vegetables_herbs", 120.0, 0.80, "high", "standard"),
    ("thasanam-boat-noodles", "thasanam-spicy-pork", 8, "sauce_seasoning", "spicy_salad_dressing", 40.0, 1.00, "low", "standard"),

    # 30. thasanam-spicy-liver
    ("thasanam-boat-noodles", "thasanam-spicy-liver", 1, "pork_and_cuts", "pork_liver_fresh", 140.0, 0.95, "ultra", "standard"),
    ("thasanam-boat-noodles", "thasanam-spicy-liver", 6, "carb_base", "toasted_rice_powder", 10.0, 1.00, "low", "standard"),
    ("thasanam-boat-noodles", "thasanam-spicy-liver", 7, "fresh_veg_herbs", "salad_vegetables_herbs", 110.0, 0.80, "high", "standard"),
    ("thasanam-boat-noodles", "thasanam-spicy-liver", 8, "sauce_seasoning", "spicy_salad_dressing", 35.0, 1.00, "low", "standard"),
]

# ตารางอ้างอิงค่ารวม G1-G8 ต่อเมนู จาก SPEC.md §1.2
SPEC_G_SUMS = {
    "madam-ho-pork-crunch-set": {1: 220, 2: 0, 3: 0, 4: 0, 5: 40, 6: 70, 7: 150, 8: 60},
    "madam-ho-paper-pot-pho": {1: 140, 2: 0, 3: 0, 4: 0, 5: 50, 6: 110, 7: 150, 8: 60},
    "madam-ho-soft-pork-heart-set": {1: 280, 2: 0, 3: 0, 4: 0, 5: 50, 6: 75, 7: 180, 8: 60},
    "volcano-baked-prawn": {1: 0, 2: 0, 3: 0, 4: 420, 5: 0, 6: 20, 7: 80, 8: 30},
    "volcano-three-armies-salad": {1: 0, 2: 0, 3: 0, 4: 180, 5: 0, 6: 20, 7: 150, 8: 30},
    "volcano-sour-curry-prawn-omelette": {1: 0, 2: 0, 3: 0, 4: 90, 5: 100, 6: 0, 7: 220, 8: 70},
    "bonchon-wings-6": {1: 0, 2: 200, 3: 0, 4: 0, 5: 0, 6: 45, 7: 20, 8: 35},
    "bonchon-chicken-rice-soy-garlic": {1: 0, 2: 160, 3: 0, 4: 0, 5: 0, 6: 115, 7: 40, 8: 35},
    "bonchon-fish-rice-hot": {1: 0, 2: 0, 3: 0, 4: 130, 5: 0, 6: 125, 7: 40, 8: 30},
    "pa-ja-boiled-chicken-rice": {1: 0, 2: 125, 3: 0, 4: 0, 5: 0, 6: 95, 7: 30, 8: 25},
    "pa-ja-fried-chicken-rice": {1: 0, 2: 130, 3: 0, 4: 0, 5: 0, 6: 105, 7: 30, 8: 25},
    "pa-ja-spicy-chicken-rice": {1: 0, 2: 135, 3: 0, 4: 0, 5: 0, 6: 105, 7: 60, 8: 30},
    "good-food-custom-sandwich": {1: 0, 2: 35, 3: 0, 4: 0, 5: 60, 6: 80, 7: 60, 8: 25},
    "good-food-banana-oat-loaf": {1: 0, 2: 0, 3: 0, 4: 0, 5: 15, 6: 40, 7: 50, 8: 15},
    "good-food-salmon-salad-rice": {1: 0, 2: 0, 3: 0, 4: 120, 5: 0, 6: 70, 7: 100, 8: 20},
    "tama-kani-miso-set": {1: 0, 2: 0, 3: 0, 4: 90, 5: 30, 6: 85, 7: 20, 8: 25},
    "tama-salmon-ebiko-sauce-rice": {1: 0, 2: 0, 3: 0, 4: 125, 5: 0, 6: 95, 7: 15, 8: 30},
    "tama-torched-salmon-mayo-rice": {1: 0, 2: 0, 3: 0, 4: 120, 5: 10, 6: 95, 7: 15, 8: 35},
    "loong-loy-tofu-pork-soup": {1: 70, 2: 0, 3: 0, 4: 0, 5: 120, 6: 0, 7: 100, 8: 20},
    "loong-loy-large-crab-fried-rice": {1: 0, 2: 0, 3: 0, 4: 90, 5: 100, 6: 140, 7: 50, 8: 30},
    "loong-loy-jungle-catfish-curry": {1: 0, 2: 0, 3: 0, 4: 150, 5: 0, 6: 0, 7: 180, 8: 40},
    "kinkane-salmon-sashimi": {1: 0, 2: 0, 3: 0, 4: 150, 5: 0, 6: 0, 7: 15, 8: 10},
    "kinkane-hamachi-sashimi": {1: 0, 2: 0, 3: 0, 4: 130, 5: 0, 6: 0, 7: 15, 8: 10},
    "kinkane-scallop-sashimi": {1: 0, 2: 0, 3: 0, 4: 160, 5: 0, 6: 0, 7: 15, 8: 10},
    "hinn-red-pork-rice": {1: 80, 2: 0, 3: 0, 4: 0, 5: 50, 6: 95, 7: 20, 8: 45},
    "hinn-crispy-pork-rice": {1: 110, 2: 0, 3: 0, 4: 0, 5: 50, 6: 95, 7: 20, 8: 45},
    "hinn-roast-duck-rice": {1: 0, 2: 110, 3: 0, 4: 0, 5: 50, 6: 95, 7: 20, 8: 40},
    "thasanam-boat-noodle-soup": {1: 40, 2: 0, 3: 35, 4: 0, 5: 0, 6: 60, 7: 50, 8: 35},
    "thasanam-spicy-pork": {1: 150, 2: 0, 3: 0, 4: 0, 5: 0, 6: 10, 7: 120, 8: 40},
    "thasanam-spicy-liver": {1: 140, 2: 0, 3: 0, 4: 0, 5: 0, 6: 10, 7: 110, 8: 35},
}


def main():
    print("=== MueNee B2B Analytics: Generating BOM Matrix ===")

    # 1. โหลดข้อมูลเมนูจาก Catalog เพื่อสอบเทียบค่าโภชนาการจริง
    catalog_path = "data/reference/menu_items_catalog.csv"
    if not os.path.exists(catalog_path):
        print(f"Error: {catalog_path} not found.")
        sys.exit(1)

    catalog_macros = {}
    with open(catalog_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            catalog_macros[row["menu_item_id"]] = {
                "pro": float(row["protein_grams"]),
                "carb": float(row["carbs_grams"]),
                "name": row["name"],
            }

    # 2. ตรวจสอบความถูกต้องของผลรวมกลุ่ม G1-G8 ต่อเมนูเทียบกับ SPEC.md §1.2
    actual_g_sums = {m: {g: 0.0 for g in range(1, 9)} for m in SPEC_G_SUMS}
    macro_estimates = {m: {"pro": 0.0, "carb": 0.0} for m in SPEC_G_SUMS}

    output_rows = []
    bom_version = "bom-v1.0"

    for entry in BOM_ENTRIES:
        (
            rest_id,
            menu_id,
            g_id,
            g_name,
            sub_comm,
            grams_ep,
            yield_fac,
            perish_class,
            assump_flag,
        ) = entry

        # คำนวณ As-Purchased (AP)
        grams_ap = round(grams_ep / yield_fac, 1)

        # สะสมผลรวมกลุ่ม
        actual_g_sums[menu_id][g_id] += grams_ep

        # สะสมสารอาหารที่ประเมินได้จากวัตถุดิบ
        if sub_comm in NUTRIENT_DENSITY:
            density = NUTRIENT_DENSITY[sub_comm]
            macro_estimates[menu_id]["pro"] += grams_ep * density["pro"]
            macro_estimates[menu_id]["carb"] += grams_ep * density["carb"]
        else:
            print(f"Warning: No nutrient density for {sub_comm}")

        output_rows.append(
            {
                "menu_item_id": menu_id,
                "restaurant_id": rest_id,
                "commodity_group_id": g_id,
                "commodity_group_name": g_name,
                "sub_commodity": sub_comm,
                "grams_ep_per_serving": f"{grams_ep:.1f}",
                "yield_factor": f"{yield_fac:.2f}",
                "grams_ap_per_serving": f"{grams_ap:.1f}",
                "perishability_class": perish_class,
                "assumption_flag": assump_flag,
                "bom_version": bom_version,
            }
        )

    # 3. ตรวจสอบผลรวมกรัมรายกลุ่ม G1-G8 (Assert Zero Tolerance)
    print("\n[Step 1] Verifying G1-G8 Commodity Group Sums against SPEC.md §1.2...")
    sum_errors = 0
    for menu_id, expected_groups in SPEC_G_SUMS.items():
        for g_id, expected_val in expected_groups.items():
            actual_val = actual_g_sums[menu_id][g_id]
            if abs(actual_val - expected_val) > 0.01:
                print(
                    f"❌ Sum Mismatch for {menu_id} G{g_id}: Expected {expected_val}g, Got {actual_val}g"
                )
                sum_errors += 1

    if sum_errors == 0:
        print("✅ All 30 menus match SPEC.md §1.2 commodity group sums perfectly!")
    else:
        print(f"❌ Found {sum_errors} group sum mismatches. Stopping.")
        sys.exit(1)

    # 4. ตรวจสอบเกณฑ์การสอบเทียบสารอาหาร (Macro Anchor within ±20%)
    print("\n[Step 2] Verifying Macro Nutrients (Protein & Carbs within ±20%)...")
    macro_errors = 0
    for menu_id, actual_macro in catalog_macros.items():
        est_pro = macro_estimates[menu_id]["pro"]
        est_carb = macro_estimates[menu_id]["carb"]
        act_pro = actual_macro["pro"]
        act_carb = actual_macro["carb"]

        pro_diff_pct = (est_pro - act_pro) / act_pro * 100 if act_pro > 0 else 0
        # เมนูที่มีคาร์บต่ำมาก (<5g เช่น ซาชิมิ) อนุญาตให้ดูค่าสัมบูรณ์แทน percentage
        carb_diff_pct = (est_carb - act_carb) / act_carb * 100 if act_carb >= 5 else 0
        carb_diff_abs = abs(est_carb - act_carb)

        pro_ok = abs(pro_diff_pct) <= 20.0
        carb_ok = abs(carb_diff_pct) <= 20.0 or (act_carb < 5 and carb_diff_abs <= 2.0)

        status_icon = "✅" if (pro_ok and carb_ok) else "❌"
        if not (pro_ok and carb_ok):
            macro_errors += 1
            print(
                f"{status_icon} {menu_id} ({actual_macro['name']}): "
                f"Pro Act={act_pro}g Est={est_pro:.1f}g ({pro_diff_pct:+.1f}%), "
                f"Carb Act={act_carb}g Est={est_carb:.1f}g ({carb_diff_pct:+.1f}%)"
            )

    if macro_errors == 0:
        print("✅ All 30 menus pass nutritional macro calibration within ±20% tolerance!")
    else:
        print(f"❌ Found {macro_errors} macro tolerance violations.")
        sys.exit(1)

    # 5. ตรวจสอบ Assumption Flags
    print("\n[Step 3] Verifying Special Assumption Flags...")
    for row in output_rows:
        m = row["menu_item_id"]
        flag = row["assumption_flag"]
        if m in ["madam-ho-paper-pot-pho", "good-food-custom-sandwich"]:
            assert flag == "ingredients_unknown", f"Expected ingredients_unknown for {m}"
        elif m == "hinn-roast-duck-rice":
            assert flag == "name_inferred", f"Expected name_inferred for {m}"

    print("✅ Special assumption flags verified (ingredients_unknown & name_inferred).")

    # 6. เขียนไฟล์ data/reference/menu_bom_matrix.csv
    out_path = "data/reference/menu_bom_matrix.csv"
    fieldnames = [
        "menu_item_id",
        "restaurant_id",
        "commodity_group_id",
        "commodity_group_name",
        "sub_commodity",
        "grams_ep_per_serving",
        "yield_factor",
        "grams_ap_per_serving",
        "perishability_class",
        "assumption_flag",
        "bom_version",
    ]

    with open(out_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\n🎉 Successfully wrote {len(output_rows)} BOM rows to {out_path}")


if __name__ == "__main__":
    main()
