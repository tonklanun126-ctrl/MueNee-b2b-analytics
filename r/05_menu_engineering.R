# ==============================================================================
# MueNee B2B Analytics: Phase 5 - Menu Engineering Matrix (r/05_menu_engineering.R)
# ==============================================================================
# สคริปต์วิเคราะห์เมนูตามทฤษฎี Menu Engineering Matrix (Kasavana & Smith, 1982)
# อ้างอิงสมการและทฤษฎีใน SPEC.md §3.4 และเป้าหมายทางธุรกิจใน RPD.md §3.2
#
# สมการหลัก:
#   1. Food Cost ต่อจาน:
#      FC_i = sum_{g} sum_{s in g} (b_{i,s}^{EP} / (1000 * y_s)) * P_{s,base}
#   2. Food Cost %:
#      FC%_i = (FC_i / price_i) * 100
#   3. Contribution Margin (กำไรส่วนเกินต่อจาน):
#      CM_i = price_i - FC_i
#   4. Menu Mix % (ความนิยม):
#      MM_i = q_i / sum_{j in M} q_j
#   5. เกณฑ์การแบ่ง 4 Quadrants (Kasavana & Smith):
#      - Popularity สูง: MM_i >= 0.70 * (1 / N)
#      - Profitability สูง: CM_i >= weighted_mean(CM)
#
# การจัดกลุ่ม 4 Quadrants:
#   ⭐ Stars (ความนิยมสูง, กำไรสูง): รักษาระดับคุณภาพ ห้ามปรับขึ้นราคาแบบสุ่มสี่สุ่มห้า
#   🐴 Plowhorses (ความนิยมสูง, กำไรต่ำ): ปรับสูตร/ลดวัตถุดิบแพง ปรับขึ้นราคาทีละน้อย
#   🧩 Puzzles (ความนิยมต่ำ, กำไรสูง): ทำโปรโมชัน เพิ่มการมองเห็น (Verified Status)
#   🐶 Dogs (ความนิยมต่ำ, กำไรต่ำ): พิจารณาปรับปรุงสูตร ลดความถี่ หรือยกเลิกเมนู
# ==============================================================================

options(encoding = "UTF-8")
options(scipen = 999)

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(purrr)
  library(ggplot2)
  library(scales)
  library(here)
})

message("==================================================================")
message("      MueNee B2B Analytics: Menu Engineering Matrix Engine        ")
message("==================================================================")

root_dir <- here::here()

# ------------------------------------------------------------------------------
# 1. โหลดข้อมูลแคตตาล็อก เมนู บอมบ์ ยอดขาย และราคาขายส่ง
# ------------------------------------------------------------------------------
message("\n--- [Step 1] Loading Catalogs, BOM, Sales Logs & Prices ---")
restaurants_df <- readRDS(file.path(root_dir, "data", "processed", "restaurants_catalog.rds"))
menu_items_df  <- readRDS(file.path(root_dir, "data", "processed", "menu_items_catalog.rds"))
bom_df         <- readRDS(file.path(root_dir, "data", "processed", "menu_bom_matrix.rds"))
prices_df      <- readRDS(file.path(root_dir, "data", "processed", "nakhon_pathom_wholesale_prices.rds"))
meal_logs_df   <- readRDS(file.path(root_dir, "data", "processed", "daily_meal_logs.rds"))

message(sprintf("  ✅ โหลดข้อมูลครบถ้วน: ร้านค้า %d แห่ง, เมนู %d รายการ, ยอดขาย %d รายการ",
                nrow(restaurants_df), nrow(menu_items_df), nrow(meal_logs_df)))

# ------------------------------------------------------------------------------
# 2. คำนวณราคาขายส่งเฉลี่ยฐาน (Baseline Wholesale Price per Sub-Commodity)
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Calculating Baseline Wholesale Costs per Serving ---")

# ใช้ราคาขายส่งเฉลี่ยของตลาดสดนครปฐมใน Scenario 'baseline'
base_prices <- prices_df %>%
  dplyr::filter(scenario_id == "baseline") %>%
  dplyr::group_by(commodity_group_id, sub_commodity) %>%
  dplyr::summarise(
    avg_price_per_unit = mean(price_thb_per_unit, na.rm = TRUE),
    .groups = "drop"
  )

# เชื่อมโยง BOM กับราคาวัตถุดิบเพื่อคำนวณต้นทุนต่อจาน:
# Cost = (grams_ep / (1000 * yield_factor)) * price_per_unit
bom_with_cost <- bom_df %>%
  dplyr::inner_join(base_prices, by = c("commodity_group_id", "sub_commodity")) %>%
  dplyr::mutate(
    # แปลง EP (g) เป็น AP (kg) แล้วคูณด้วยราคาต่อ kg (หรือฟอง)
    kg_ap_per_serving = (grams_ep_per_serving / (1000 * yield_factor)),
    ingredient_cost_thb = kg_ap_per_serving * avg_price_per_unit
  )

# รวมต้นทุนวัตถุดิบทั้งหมดต่อเมนู (Food Cost per Dish FC_i)
menu_food_cost <- bom_with_cost %>%
  dplyr::group_by(menu_item_id) %>%
  dplyr::summarise(
    food_cost_thb = round(sum(ingredient_cost_thb), 2),
    total_ap_grams = round(sum(kg_ap_per_serving * 1000), 1),
    num_ingredients = dplyr::n(),
    .groups = "drop"
  )

# ------------------------------------------------------------------------------
# 3. คำนวณยอดขายรวมรายปี (Annual Sales Volume & Revenue)
# ------------------------------------------------------------------------------
message("\n--- [Step 3] Aggregating Annual Sales Volume & Revenue per Menu ---")

menu_sales_summary <- meal_logs_df %>%
  dplyr::group_by(menu_item_id) %>%
  dplyr::summarise(
    total_orders       = sum(orders_total),
    orders_lunch_sum   = sum(orders_lunch),
    orders_dinner_sum  = sum(orders_dinner),
    orders_late_sum    = sum(orders_late_night),
    total_revenue_thb  = sum(revenue_thb),
    avg_selling_price  = mean(unit_price_thb),
    .groups = "drop"
  )

# ------------------------------------------------------------------------------
# 4. รวมข้อมูลคำนวณ Menu Engineering Metrics (Within-Restaurant & Within-Tier)
# ------------------------------------------------------------------------------
message("\n--- [Step 4] Computing Menu Engineering Metrics & Quadrants ---")

# นำข้อมูลเมนู แคตตาล็อก ต้นทุน และยอดขายมารวมกัน
menu_base <- menu_items_df %>%
  dplyr::inner_join(restaurants_df %>% dplyr::select(restaurant_id, restaurant_name = name), by = "restaurant_id") %>%
  dplyr::inner_join(menu_food_cost, by = "menu_item_id") %>%
  dplyr::inner_join(menu_sales_summary, by = "menu_item_id") %>%
  dplyr::mutate(
    selling_price_thb = price_amount,
    # CM = Price - Food Cost
    contribution_margin_thb = round(selling_price_thb - food_cost_thb, 2),
    # Food Cost % = (Food Cost / Price) * 100
    food_cost_pct = round((food_cost_thb / selling_price_thb) * 100, 2),
    total_cm_thb = round(total_orders * contribution_margin_thb, 2),
    # เพดาน Food Cost % เป้าหมายตาม RPD §3.2
    target_food_cost_pct = dplyr::case_when(
      price_tier == "economy"        ~ 45.0,
      price_tier == "mid"            ~ 40.0,
      price_tier == "premium_social" ~ 35.0,
      TRUE                           ~ 40.0
    ),
    food_cost_exceeds_target = food_cost_pct > target_food_cost_pct
  )

# 4.1 คำนวณเกณฑ์ระดับร้านค้า (Within-Restaurant: N = 3)
restaurant_benchmarks <- menu_base %>%
  dplyr::group_by(restaurant_id) %>%
  dplyr::summarise(
    rest_total_orders = sum(total_orders),
    rest_total_cm     = sum(total_cm_thb),
    # ค่าเฉลี่ยถ่วงน้ำหนัก CM ภายในร้าน
    rest_weighted_cm  = round(sum(contribution_margin_thb * total_orders) / sum(total_orders), 2),
    rest_n_items      = dplyr::n(),
    # เกณฑ์ Popularity = 0.70 * (1 / N) = 70% / 3 = 23.33%
    rest_pop_hurdle   = round((0.70 * (1 / dplyr::n())) * 100, 2),
    .groups = "drop"
  )

# 4.2 คำนวณเกณฑ์ระดับกลุ่มราคา (Within-Tier Benchmark)
tier_benchmarks <- menu_base %>%
  dplyr::group_by(price_tier) %>%
  dplyr::summarise(
    tier_total_orders = sum(total_orders),
    tier_total_cm     = sum(total_cm_thb),
    # ค่าเฉลี่ยถ่วงน้ำหนัก CM ภายในกลุ่มราคา
    tier_weighted_cm  = round(sum(contribution_margin_thb * total_orders) / sum(total_orders), 2),
    tier_n_items      = dplyr::n(),
    # เกณฑ์ Popularity ระดับ Tier = 0.70 * (1 / N_tier)
    tier_pop_hurdle   = round((0.70 * (1 / dplyr::n())) * 100, 2),
    .groups = "drop"
  )

# รวมเกณฑ์และจัด Quadrant ทั้ง 2 ระดับ
menu_matrix_df <- menu_base %>%
  dplyr::inner_join(restaurant_benchmarks, by = "restaurant_id") %>%
  dplyr::inner_join(tier_benchmarks, by = "price_tier") %>%
  dplyr::mutate(
    # Menu Mix % ภายในร้าน
    menu_mix_restaurant_pct = round((total_orders / rest_total_orders) * 100, 2),
    # Menu Mix % ภายในกลุ่มราคา
    menu_mix_tier_pct       = round((total_orders / tier_total_orders) * 100, 2),

    # การจัดกลุ่ม Within-Restaurant Quadrant
    is_high_pop_rest = menu_mix_restaurant_pct >= rest_pop_hurdle,
    is_high_cm_rest  = contribution_margin_thb >= rest_weighted_cm,
    quadrant_within_restaurant = dplyr::case_when(
      is_high_pop_rest & is_high_cm_rest   ~ "Stars",
      is_high_pop_rest & !is_high_cm_rest  ~ "Plowhorses",
      !is_high_pop_rest & is_high_cm_rest  ~ "Puzzles",
      TRUE                                 ~ "Dogs"
    ),

    # การจัดกลุ่ม Within-Tier Quadrant
    is_high_pop_tier = menu_mix_tier_pct >= tier_pop_hurdle,
    is_high_cm_tier  = contribution_margin_thb >= tier_weighted_cm,
    quadrant_within_tier = dplyr::case_when(
      is_high_pop_tier & is_high_cm_tier   ~ "Stars",
      is_high_pop_tier & !is_high_cm_tier  ~ "Plowhorses",
      !is_high_pop_tier & is_high_cm_tier  ~ "Puzzles",
      TRUE                                 ~ "Dogs"
    ),

    # กลยุทธ์ทางธุรกิจที่แนะนำ (Actionable Strategic Recommendation)
    strategic_recommendation = dplyr::case_when(
      quadrant_within_restaurant == "Stars" & food_cost_exceeds_target ~
        "⭐ เมนูดาวเด่น (ขายดี+กำไรสูง) แต่ Food Cost เกินเพดานเป้าหมาย: ควรรักษาตำแหน่งเมนู ลดต้นทุนด้วยการเจรจาซื้อวัตถุดิบร่วมหรือปรับลดขนาดผักตกแต่ง ห้ามขึ้นราคาเด็ดขาด",
      quadrant_within_restaurant == "Stars" ~
        "⭐ เมนูดาวเด่น (ขายดี+กำไรสูง): รักษาสูตร คุณภาพ และตำแหน่งในเมนู เป็นตัวชูโรงสร้างกระแสเงินสด ไม่ควรขึ้นราคาหากไม่จำเป็น",
      quadrant_within_restaurant == "Plowhorses" ~
        "🐴 ม้างาน (ขายดีมากแต่กำไรต่ำ): ปรับสัดส่วนวัตถุดิบแพง เพิ่มคาร์บหรือผัก ปรับขึ้นราคา 3-5 บาทแบบค่อยเป็นค่อยไป หรือจับคู่ Bundle กับเมนูกำไรสูง",
      quadrant_within_restaurant == "Puzzles" ~
        "🧩 ปริศนา (กำไรดีมากแต่ยอดขายน้อย): เร่งโปรโมชัน เพิ่มการมองเห็นในแอป MueNee ตรวจสอบและยืนยันข้อมูลราคา (Verified) และสารก่อภูมิแพ้เพื่อปลดล็อกฟิลเตอร์ผู้ใช้",
      quadrant_within_restaurant == "Dogs" & food_cost_exceeds_target ~
        "🐶 สุนัขเฝ้าบ้าน (ขายน้อย+กำไรต่ำ+ต้นทุนเกินเป้า): เป็นเมนูเปราะบางสูงสุด ควรปรับสูตรขนานใหญ่ หรือพิจารณาตัดออกจากเมนูหลักแล้วขายเฉพาะช่วงเทศกาล",
      TRUE ~
        "🐶 สุนัขเฝ้าบ้าน (ขายน้อย+กำไรต่ำ): ปรับตำแหน่งการวางในเมนู หรือปรับสูตรเพื่อลดของสดเหลือทิ้ง"
    )
  )

# เรียงลำดับตามร้านค้า และยอดขาย
menu_matrix_df <- menu_matrix_df %>%
  dplyr::arrange(restaurant_id, desc(total_orders))

# ------------------------------------------------------------------------------
# 5. ส่งออกไฟล์รายงาน outputs/menu_engineering.csv
# ------------------------------------------------------------------------------
message("\n--- [Step 5] Exporting outputs/menu_engineering.csv ---")
out_csv_path <- file.path(root_dir, "outputs", "menu_engineering.csv")

export_cols_df <- menu_matrix_df %>%
  dplyr::select(
    menu_item_id,
    menu_name_th = name,
    restaurant_id,
    restaurant_name,
    price_tier,
    price_confidence,
    selling_price_thb,
    food_cost_thb,
    food_cost_pct,
    target_food_cost_pct,
    food_cost_exceeds_target,
    contribution_margin_thb,
    total_orders,
    menu_mix_restaurant_pct,
    quadrant_within_restaurant,
    menu_mix_tier_pct,
    quadrant_within_tier,
    total_revenue_thb,
    total_cm_thb,
    strategic_recommendation
  )

readr::write_csv(export_cols_df, out_csv_path)
message(sprintf("  📄 บันทึกผลลัพธ์ Menu Engineering Matrix: %s (%d เมนู)", out_csv_path, nrow(export_cols_df)))

# ------------------------------------------------------------------------------
# 6. สร้างกราฟิก Matrix Quadrants (Within-Restaurant 10 ร้าน + Overall Plot)
# ------------------------------------------------------------------------------
message("\n--- [Step 6] Generating Quadrant Plots for all 10 Restaurants ---")

# กำหนดธีมสีเฉพาะสำหรับ 4 Quadrants
quadrant_colors <- c(
  "Stars"      = "#2a9d8f", # เขียวอมฟ้า เด่นและมีคุณค่า
  "Plowhorses" = "#e76f51", # ส้มอิฐ ขายดีแต่เหนื่อยกำไรน้อย
  "Puzzles"    = "#457b9d", # น้ำเงินสุขุม กำไรดีแต่นิ่ง
  "Dogs"       = "#e63946"  # แดง เตือนภัย
)

# 6.1 วาดกราฟแยกรายร้าน 10 ร้าน
for (r_id in unique(menu_matrix_df$restaurant_id)) {
  r_data <- menu_matrix_df %>% dplyr::filter(restaurant_id == r_id)
  r_name <- r_data$restaurant_name[1]
  pop_hurdle <- r_data$rest_pop_hurdle[1]
  cm_hurdle  <- r_data$rest_weighted_cm[1]

  p_quad <- ggplot2::ggplot(r_data, ggplot2::aes(x = menu_mix_restaurant_pct, y = contribution_margin_thb)) +
    # เส้นแบ่งเกณฑ์ Popularity (MM %) และ Profitability (CM)
    ggplot2::geom_vline(xintercept = pop_hurdle, linetype = "dashed", color = "#6c757d", linewidth = 0.7) +
    ggplot2::geom_hline(yintercept = cm_hurdle, linetype = "dashed", color = "#6c757d", linewidth = 0.7) +
    # จุดข้อมูลเมนู
    ggplot2::geom_point(ggplot2::aes(color = quadrant_within_restaurant, size = total_orders), alpha = 0.85) +
    # ป้ายกำกับชื่อเมนู
    ggplot2::geom_text(
      ggplot2::aes(label = sprintf("%s\n(FC %.1f%%)", name, food_cost_pct), color = quadrant_within_restaurant),
      size = 3.3, fontface = "bold", vjust = -0.7, check_overlap = FALSE
    ) +
    ggplot2::scale_color_manual(name = "Quadrant", values = quadrant_colors) +
    ggplot2::scale_size_continuous(name = "Annual Orders", range = c(4, 9), labels = scales::comma) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(scale = 1), limits = c(0, max(65, max(r_data$menu_mix_restaurant_pct) + 12))) +
    ggplot2::scale_y_continuous(labels = scales::dollar_format(prefix = "฿", accuracy = 1), expand = ggplot2::expansion(mult = c(0.1, 0.2))) +
    ggplot2::labs(
      title = sprintf("Menu Engineering Matrix: %s", r_name),
      subtitle = sprintf("Hurdles: Popularity >= %.1f%% | Weighted Avg CM >= ฿%.2f", pop_hurdle, cm_hurdle),
      x = "Popularity (Menu Mix % within Restaurant)",
      y = "Profitability (Contribution Margin ฿/Dish)",
      caption = "MueNee B2B Analytics: SPEC.md §3.4 Kasavana & Smith Matrix"
    ) +
    ggplot2::theme_minimal(base_size = 11) +
    ggplot2::theme(
      legend.position = "bottom",
      plot.title = ggplot2::element_text(face = "bold", size = 12, color = "#1d3557"),
      panel.grid.minor = ggplot2::element_blank()
    )

  fig_r_path <- file.path(root_dir, "outputs", "figures", sprintf("menu_quadrant_%s.png", r_id))
  ggplot2::ggsave(fig_r_path, plot = p_quad, width = 8, height = 6, dpi = 300)
}
message("  🖼️ บันทึกกราฟิก Quadrant แยกรายร้านครบทั้ง 10 ร้านที่ outputs/figures/menu_quadrant_<restaurant_id>.png")

# 6.2 วาดกราฟิกสรุปภาพรวมทั้ง 30 เมนู (Overall Menu Engineering Matrix)
p_overall <- ggplot2::ggplot(menu_matrix_df, ggplot2::aes(x = menu_mix_tier_pct, y = contribution_margin_thb)) +
  ggplot2::geom_point(ggplot2::aes(color = quadrant_within_tier, shape = price_tier, size = total_orders), alpha = 0.8) +
  ggplot2::geom_text(
    ggplot2::aes(label = sprintf("%s (%s)", name, restaurant_name), color = quadrant_within_tier),
    size = 2.6, vjust = -0.8, check_overlap = TRUE
  ) +
  ggplot2::scale_color_manual(name = "Within-Tier Quadrant", values = quadrant_colors) +
  ggplot2::scale_shape_manual(name = "Price Tier", values = c("economy" = 16, "mid" = 17, "premium_social" = 15)) +
  ggplot2::scale_size_continuous(name = "Orders Volume", range = c(3, 8), labels = scales::comma) +
  ggplot2::scale_y_log10(labels = scales::dollar_format(prefix = "฿", accuracy = 1)) +
  ggplot2::scale_x_continuous(labels = scales::percent_format(scale = 1)) +
  ggplot2::labs(
    title = "MueNee B2B Analytics: Overall 30 Menus Engineering Matrix (Log Scale CM)",
    subtitle = "Benchmarked within respective price tiers (Economy, Mid, Premium/Social)",
    x = "Menu Mix % (Within Tier Benchmark)",
    y = "Contribution Margin per Dish (THB, Log Scale)",
    caption = "MueNee B2B Analytics: SPEC.md §3.4"
  ) +
  ggplot2::theme_minimal(base_size = 11) +
  ggplot2::theme(
    legend.position = "bottom",
    legend.box = "vertical",
    plot.title = ggplot2::element_text(face = "bold", size = 13, color = "#1d3557")
  )

overall_fig_path <- file.path(root_dir, "outputs", "figures", "menu_quadrant_overall.png")
ggplot2::ggsave(overall_fig_path, plot = p_overall, width = 11, height = 8, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟิกสรุป 30 เมนู: %s", overall_fig_path))

# ------------------------------------------------------------------------------
# 7. สรุปผลการวิเคราะห์และตรวจสอบ KPI
# ------------------------------------------------------------------------------
message("\n--- [Step 7] Menu Engineering Summary & KPI Verification ---")

stars_count <- sum(menu_matrix_df$quadrant_within_restaurant == "Stars")
plow_count  <- sum(menu_matrix_df$quadrant_within_restaurant == "Plowhorses")
puzz_count  <- sum(menu_matrix_df$quadrant_within_restaurant == "Puzzles")
dogs_count  <- sum(menu_matrix_df$quadrant_within_restaurant == "Dogs")

stars_per_rest <- menu_matrix_df %>%
  dplyr::group_by(restaurant_id) %>%
  dplyr::summarise(has_star = any(quadrant_within_restaurant == "Stars"), .groups = "drop")

exceed_count <- sum(menu_matrix_df$food_cost_exceeds_target)

message(sprintf("  ⭐ Stars: %d เมนู | 🐴 Plowhorses: %d เมนู | 🧩 Puzzles: %d เมนู | 🐶 Dogs: %d เมนู",
                stars_count, plow_count, puzz_count, dogs_count))
message(sprintf("  📊 ร้านที่มีอย่างน้อย 1 Star (RPD §3.2): %d / 10 ร้าน", sum(stars_per_rest$has_star)))
message(sprintf("  ⚠️ เมนูที่ Food Cost %% เกินเกณฑ์เพดานเป้าหมาย: %d เมนู", exceed_count))

message("\n==================================================================")
message("   🎉 TASK 5.1 MENU ENGINEERING MATRIX COMPLETED SUCCESSFULLY! 🎉  ")
message("==================================================================\n")
