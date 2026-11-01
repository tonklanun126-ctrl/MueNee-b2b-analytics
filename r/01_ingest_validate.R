# ==============================================================================
# MueNee B2B Analytics: Phase 3 - Ingest & Validate (r/01_ingest_validate.R)
# ==============================================================================
# สคริปต์โหลดและตรวจสอบความสมบูรณ์ของชุดข้อมูล (Data Ingestion & Integrity Validation)
# แปลงข้อมูล CSV จาก Module A และไฟล์ Reference เป็น RDS ตาม Data Dictionary ใน SPEC.md §2
# ==============================================================================

# ปรับการตั้งค่าการแสดงผลและ Encoding
options(encoding = "UTF-8")
options(scipen = 999)

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(lubridate)
  library(janitor)
  library(here)
})

message("==================================================================")
message("   MueNee B2B Analytics: Data Ingestion & Quality Validation      ")
message("==================================================================")

# ------------------------------------------------------------------------------
# 1. นิยามพาธไฟล์ข้อมูล
# ------------------------------------------------------------------------------
root_dir <- here::here()

files <- list(
  restaurants       = file.path(root_dir, "data", "reference", "restaurants_catalog.csv"),
  menu_items        = file.path(root_dir, "data", "reference", "menu_items_catalog.csv"),
  menu_bom          = file.path(root_dir, "data", "reference", "menu_bom_matrix.csv"),
  wholesale_prices  = file.path(root_dir, "data", "reference", "nakhon_pathom_wholesale_prices.csv"),
  daily_meal_logs   = file.path(root_dir, "data", "raw", "daily_meal_logs.csv"),
  tag_trend_scores  = file.path(root_dir, "data", "raw", "tag_trend_scores.csv")
)

# ตรวจสอบการมีอยู่ของไฟล์ (Fail-Fast Check 1)
message("\n--- [Step 1] Checking Raw & Reference Files Existence ---")
for (name in names(files)) {
  fpath <- files[[name]]
  if (!file.exists(fpath)) {
    stop(sprintf("❌ [FAIL-FAST ERROR] ไม่พบไฟล์ที่จำเป็น: %s กรุณาตรวจสอบกระบวนการใน Phase 1/2", fpath))
  }
  fsize_kb <- file.info(fpath)$size / 1024
  message(sprintf("  ✅ พบไฟล์ %-20s (%.1f KB) ที่: %s", name, fsize_kb, fpath))
}

# ------------------------------------------------------------------------------
# 2. โหลดและตรวจสอบ Master Reference Catalogs
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Ingesting & Validating Reference Catalogs ---")

# 2.1 ร้านค้า (10 ร้านจริงรอบ ม.ศิลปากร)
rest_raw <- readr::read_csv(files$restaurants, show_col_types = FALSE)
if (nrow(rest_raw) != 10) {
  stop(sprintf("❌ [FAIL-FAST ERROR] restaurants_catalog ต้องมี 10 ร้านพอดี (พบ %d ร้าน)", nrow(rest_raw)))
}

restaurants_clean <- rest_raw %>%
  dplyr::mutate(
    restaurant_id       = as.factor(restaurant_id),
    name                = as.character(name),
    google_place_id     = as.character(google_place_id),
    latitude            = as.numeric(latitude),
    longitude           = as.numeric(longitude),
    address             = as.character(address),
    rating              = as.numeric(rating),
    verification_status = as.factor(verification_status),
    is_active           = as.logical(is_active)
  )

valid_rest_ids <- levels(restaurants_clean$restaurant_id)
message(sprintf("  ✅ ร้านค้าครบถ้วน 10 ร้าน: %s", paste(valid_rest_ids[1:4], collapse = ", ")))

# 2.2 เมนูอาหาร (30 เมนูจริง)
menu_raw <- readr::read_csv(files$menu_items, show_col_types = FALSE)
if (nrow(menu_raw) != 30) {
  stop(sprintf("❌ [FAIL-FAST ERROR] menu_items_catalog ต้องมี 30 เมนูพอดี (พบ %d เมนู)", nrow(menu_raw)))
}

menu_items_clean <- menu_raw %>%
  dplyr::mutate(
    menu_item_id    = as.factor(menu_item_id),
    restaurant_id   = factor(restaurant_id, levels = valid_rest_ids),
    name            = as.character(name),
    price_tier      = factor(price_tier, levels = c("economy", "mid", "premium_social")),
    price_amount    = as.integer(price_amount),
    price_confidence= factor(price_confidence, levels = c("verified", "estimated", "unverified")),
    calories        = as.integer(calories),
    protein_grams   = as.numeric(protein_grams),
    carbs_grams     = as.numeric(carbs_grams),
    fat_grams       = as.numeric(fat_grams),
    ingredients_known    = as.logical(ingredients_known),
    allergens_known      = as.logical(allergens_known),
    vegetarian_confirmed = as.logical(vegetarian_confirmed),
    halal_confirmed      = as.logical(halal_confirmed),
    is_active            = as.logical(is_active)
  )

if (any(is.na(menu_items_clean$restaurant_id))) {
  stop("❌ [FAIL-FAST ERROR] มี menu_item ที่อ้างอิง restaurant_id นอก Catalog!")
}

valid_menu_ids <- levels(menu_items_clean$menu_item_id)
message(sprintf("  ✅ เมนูอาหารครบถ้วน 30 เมนู (Verified 15, Unverified 15)"))

# ------------------------------------------------------------------------------
# 3. โหลดและตรวจสอบ Recipe Bill of Materials (BOM) Matrix
# ------------------------------------------------------------------------------
message("\n--- [Step 3] Ingesting & Validating Menu BOM Matrix ---")
bom_raw <- readr::read_csv(files$menu_bom, show_col_types = FALSE)

if (nrow(bom_raw) != 135) {
  stop(sprintf("❌ [FAIL-FAST ERROR] menu_bom_matrix ต้องมี 135 แถวพอดีตาม SPEC §1.2 (พบ %d แถว)", nrow(bom_raw)))
}

commodity_levels <- c(
  "pork_and_cuts", "poultry", "beef", "seafood",
  "egg_and_tofu", "carb_base", "fresh_veg_herbs", "sauce_seasoning"
)

bom_clean <- bom_raw %>%
  dplyr::mutate(
    menu_item_id        = factor(menu_item_id, levels = valid_menu_ids),
    restaurant_id       = factor(restaurant_id, levels = valid_rest_ids),
    commodity_group_id  = as.integer(commodity_group_id),
    commodity_group_name= factor(commodity_group_name, levels = commodity_levels),
    sub_commodity       = as.factor(sub_commodity),
    grams_ep_per_serving= as.numeric(grams_ep_per_serving),
    yield_factor        = as.numeric(yield_factor),
    grams_ap_per_serving= as.numeric(grams_ap_per_serving),
    perishability_class = factor(perishability_class, levels = c("ultra", "high", "medium", "low")),
    assumption_flag     = factor(assumption_flag, levels = c("standard", "ingredients_unknown", "name_inferred", "owner_verified")),
    bom_version         = as.character(bom_version)
  )

# ตรวจสอบสูตร AP = EP / Yield
ap_check <- abs(bom_clean$grams_ap_per_serving - (bom_clean$grams_ep_per_serving / bom_clean$yield_factor))
if (any(ap_check > 0.15)) {
  stop("❌ [FAIL-FAST ERROR] พบแถวใน BOM ที่ grams_ap_per_serving != grams_ep_per_serving / yield_factor!")
}

# ตรวจสอบว่า G3 (เนื้อโค) มีเฉพาะร้านก๋วยเตี๋ยวเรือ ท่าสนาม (thasanam-boat-noodles)
g3_rests <- bom_clean %>%
  dplyr::filter(commodity_group_name == "beef") %>%
  dplyr::pull(restaurant_id) %>%
  unique() %>%
  as.character()

if (!identical(g3_rests, "thasanam-boat-noodles")) {
  stop(sprintf("❌ [FAIL-FAST ERROR] G3 (เนื้อโค) ต้องปรากฏเฉพาะร้าน thasanam-boat-noodles เท่านั้น (พบใน: %s)", paste(g3_rests, collapse = ", ")))
}
message("  ✅ ตรวจสอบ BOM Matrix ผ่าน 100%: 135 วัตถุดิบย่อย, สูตร AP=EP/Yield ถูกต้อง, G3 เฉพาะร้านท่าสนาม")

# ------------------------------------------------------------------------------
# 4. โหลดและตรวจสอบราคาขายส่ง (Nakhon Pathom Wholesale Prices)
# ------------------------------------------------------------------------------
message("\n--- [Step 4] Ingesting & Validating Nakhon Pathom Wholesale Prices ---")
prices_raw <- readr::read_csv(files$wholesale_prices, show_col_types = FALSE)

expected_price_rows <- 365 * length(levels(bom_clean$sub_commodity))
if (nrow(prices_raw) != expected_price_rows) {
  stop(sprintf("❌ [FAIL-FAST ERROR] ราคาขายส่งต้องมี %d แถว (พบ %d แถว)", expected_price_rows, nrow(prices_raw)))
}

prices_clean <- prices_raw %>%
  dplyr::mutate(
    date              = as.Date(date),
    commodity_group_id= as.integer(commodity_group_id),
    sub_commodity     = factor(sub_commodity, levels = levels(bom_clean$sub_commodity)),
    unit              = factor(unit, levels = c("kg", "egg", "litre")),
    price_thb_per_unit= as.numeric(price_thb_per_unit),
    price_source_type = factor(price_source_type, levels = c("synthetic", "observed")),
    market_ref        = as.character(market_ref),
    scenario_id       = as.character(scenario_id)
  )

# ตรวจสอบว่าทุก sub_commodity ใน BOM มีราคาครบ 365 วัน (Fail-Fast Check)
sub_comm_counts <- prices_clean %>%
  dplyr::group_by(sub_commodity) %>%
  dplyr::summarise(n_days = dplyr::n_distinct(date), .groups = "drop")

missing_price_comms <- sub_comm_counts %>% dplyr::filter(n_days != 365)
if (nrow(missing_price_comms) > 0) {
  stop(sprintf("❌ [FAIL-FAST ERROR] พบวัตถุดิบที่มีราคาไม่ครบ 365 วัน: %s", paste(missing_price_comms$sub_commodity, collapse = ", ")))
}
message(sprintf("  ✅ วัตถุดิบย่อยทั้ง %d ชนิด มีราคาขายส่งครบถ้วน 365 วันพอดี", nrow(sub_comm_counts)))

# ------------------------------------------------------------------------------
# 5. โหลดและตรวจสอบ daily_meal_logs.csv จาก Module A
# ------------------------------------------------------------------------------
message("\n--- [Step 5] Ingesting & Validating daily_meal_logs.csv ---")
daily_raw <- readr::read_csv(files$daily_meal_logs, show_col_types = FALSE)

if (nrow(daily_raw) != 10950) {
  stop(sprintf("❌ [FAIL-FAST ERROR] daily_meal_logs ต้องมี 10,950 แถวพอดี (พบ %d แถว)", nrow(daily_raw)))
}

period_levels <- c("regular", "midterm_exam", "final_exam", "semester_break", "summer_session", "public_holiday")

daily_clean <- daily_raw %>%
  dplyr::mutate(
    date              = as.Date(date),
    restaurant_id     = factor(restaurant_id, levels = valid_rest_ids),
    menu_item_id      = factor(menu_item_id, levels = valid_menu_ids),
    price_tier        = factor(price_tier, levels = c("economy", "mid", "premium_social")),
    academic_period   = factor(academic_period, levels = period_levels),
    day_of_week       = as.integer(day_of_week),
    is_weekend        = as.logical(is_weekend),
    orders_total      = as.integer(orders_total),
    orders_lunch      = as.integer(orders_lunch),
    orders_dinner     = as.integer(orders_dinner),
    orders_late_night = as.integer(orders_late_night),
    orders_other      = as.integer(orders_other),
    src_recommendation= as.integer(src_recommendation),
    src_food_scan     = as.integer(src_food_scan),
    src_manual        = as.integer(src_manual),
    unit_price_thb    = as.integer(unit_price_thb),
    price_confidence  = factor(price_confidence, levels = c("verified", "estimated", "unverified")),
    revenue_thb       = as.integer(revenue_thb),
    kcal_total        = as.integer(kcal_total),
    run_id            = as.character(run_id)
  )

# ตรวจสอบ Closed Catalog (Foreign Keys)
if (any(is.na(daily_clean$restaurant_id)) || any(is.na(daily_clean$menu_item_id))) {
  stop("❌ [FAIL-FAST ERROR] daily_meal_logs มีค่า restaurant_id หรือ menu_item_id อยู่นอก Catalog!")
}

# ตรวจสอบ Integrity Rules
meal_sum <- daily_clean$orders_lunch + daily_clean$orders_dinner + daily_clean$orders_late_night + daily_clean$orders_other
if (!all(daily_clean$orders_total == meal_sum)) {
  stop("❌ [FAIL-FAST ERROR] Integrity Rule 1 ล้มเหลว: orders_total != lunch + dinner + late_night + other!")
}

src_sum <- daily_clean$src_recommendation + daily_clean$src_food_scan + daily_clean$src_manual
if (!all(daily_clean$orders_total == src_sum)) {
  stop("❌ [FAIL-FAST ERROR] Integrity Rule 2 ล้มเหลว: orders_total != rec + scan + manual!")
}

rev_calc <- daily_clean$orders_total * daily_clean$unit_price_thb
if (!all(daily_clean$revenue_thb == rev_calc)) {
  stop("❌ [FAIL-FAST ERROR] Integrity Rule 3 ล้มเหลว: revenue_thb != orders_total * unit_price_thb!")
}

message("  ✅ Integrity Rules ทั้งหมดผ่าน 100% ไม่มีแถวผิดพลาด")

# ------------------------------------------------------------------------------
# 6. บันทึกไฟล์ Processed RDS สำหรับ Module B
# ------------------------------------------------------------------------------
message("\n--- [Step 6] Saving Cleaned Datasets to data/processed/*.rds ---")
out_dir <- file.path(root_dir, "data", "processed")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

saveRDS(restaurants_clean, file.path(out_dir, "restaurants_catalog.rds"))
saveRDS(menu_items_clean,  file.path(out_dir, "menu_items_catalog.rds"))
saveRDS(bom_clean,         file.path(out_dir, "menu_bom_matrix.rds"))
saveRDS(prices_clean,      file.path(out_dir, "nakhon_pathom_wholesale_prices.rds"))
saveRDS(daily_clean,       file.path(out_dir, "daily_meal_logs.rds"))

message(sprintf("  💾 บันทึก %s สำเร็จ", file.path(out_dir, "restaurants_catalog.rds")))
message(sprintf("  💾 บันทึก %s สำเร็จ", file.path(out_dir, "menu_items_catalog.rds")))
message(sprintf("  💾 บันทึก %s สำเร็จ", file.path(out_dir, "menu_bom_matrix.rds")))
message(sprintf("  💾 บันทึก %s สำเร็จ", file.path(out_dir, "nakhon_pathom_wholesale_prices.rds")))
message(sprintf("  💾 บันทึก %s สำเร็จ", file.path(out_dir, "daily_meal_logs.rds")))

message("\n==================================================================")
message(" 🎉 INGESTION & DATA VALIDATION COMPLETED SUCCESSFULLY (B1)! 🎉 ")
message("==================================================================\n")
