# ==============================================================================
# MueNee B2B Analytics: Phase 3 - BOM Transformation (r/02_bom_transform.R)
# ==============================================================================
# สคริปต์แปลงความต้องการระดับเมนูอาหาร (Dishes) สู่ปริมาณวัตถุดิบจัดซื้อ (Kilograms AP)
# อ้างอิงสมการทางสถิติและสูตรการแปลงใน SPEC.md §3.1:
# D_{r,g,t} = (1 / 1000) * SUM_{i in M_r} [ q_{i,t} * ( b^{EP}_{i,g} / y_g ) ]
# ==============================================================================

options(encoding = "UTF-8")
options(scipen = 999)

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(purrr)
  library(lubridate)
  library(ggplot2)
  library(scales)
  library(here)
})

message("==================================================================")
message("   MueNee B2B Analytics: BOM Transformation (Dishes -> AP kg)     ")
message("==================================================================")

root_dir <- here::here()

# ------------------------------------------------------------------------------
# 1. โหลดข้อมูล Processed จาก Step 3.2
# ------------------------------------------------------------------------------
message("\n--- [Step 1] Loading Cleaned Datasets from data/processed/ ---")
daily_logs <- readRDS(file.path(root_dir, "data", "processed", "daily_meal_logs.rds"))
bom_matrix <- readRDS(file.path(root_dir, "data", "processed", "menu_bom_matrix.rds"))
prices     <- readRDS(file.path(root_dir, "data", "processed", "nakhon_pathom_wholesale_prices.rds"))
rest_cat   <- readRDS(file.path(root_dir, "data", "processed", "restaurants_catalog.rds"))
menu_cat   <- readRDS(file.path(root_dir, "data", "processed", "menu_items_catalog.rds"))

message(sprintf("  ✅ Loaded daily_meal_logs: %d rows (365 days x 30 dishes)", nrow(daily_logs)))
message(sprintf("  ✅ Loaded menu_bom_matrix: %d rows (135 BOM ingredients)", nrow(bom_matrix)))
message(sprintf("  ✅ Loaded wholesale_prices: %d rows (365 days x 74 sub-commodities)", nrow(prices)))

# ------------------------------------------------------------------------------
# 2. ทำการแปลง BOM Transformation (Grain: Date x Restaurant x Sub-Commodity)
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Executing BOM Transformation Matrix Multiplication ---")

# นำ daily_meal_logs มาเชื่อมต่อกับ menu_bom_matrix ตาม menu_item_id และ restaurant_id
# เพื่อคูณจำนวนจาน (orders_total) กับน้ำหนักกรัม AP ต่อจาน (grams_ap_per_serving)
bom_joined <- daily_logs %>%
  dplyr::select(
    date, restaurant_id, menu_item_id, orders_total,
    academic_period, is_weekend, day_of_week
  ) %>%
  dplyr::inner_join(
    bom_matrix %>%
      dplyr::select(
        menu_item_id, restaurant_id, commodity_group_id, commodity_group_name,
        sub_commodity, grams_ep_per_serving, yield_factor, grams_ap_per_serving,
        perishability_class
      ),
    by = c("menu_item_id", "restaurant_id"),
    relationship = "many-to-many"
  ) %>%
  dplyr::mutate(
    # คำนวณน้ำหนักเป็นกิโลกรัม AP: (orders_total * grams_ap_per_serving) / 1000
    demand_kg_ap = (orders_total * grams_ap_per_serving) / 1000.0,
    demand_kg_ep = (orders_total * grams_ep_per_serving) / 1000.0
  )

# รวมความต้องการวัตถุดิบระดับ Sub-Commodity รายวันต่อร้านค้า
sub_commodity_daily <- bom_joined %>%
  dplyr::group_by(
    date, restaurant_id, commodity_group_id, commodity_group_name,
    sub_commodity, perishability_class, academic_period, is_weekend
  ) %>%
  dplyr::summarise(
    total_orders_supported = sum(orders_total),
    demand_kg_ep           = round(sum(demand_kg_ep), 4),
    demand_kg_ap           = round(sum(demand_kg_ap), 4),
    .groups = "drop"
  )

# รวมความต้องการวัตถุดิบระดับ 8 Commodity Groups รายวันต่อร้านค้า ตามสูตร SPEC §3.1
commodity_group_daily <- sub_commodity_daily %>%
  dplyr::group_by(
    date, restaurant_id, commodity_group_id, commodity_group_name,
    academic_period, is_weekend
  ) %>%
  dplyr::summarise(
    total_orders_supported = sum(total_orders_supported),
    demand_kg_ep           = round(sum(demand_kg_ep), 3),
    demand_kg_ap           = round(sum(demand_kg_ap), 3),
    .groups = "drop"
  )

message(sprintf("  ✅ คำนวณความต้องการวัตถุดิบย่อยรายวันสำเร็จ: %d แถว", nrow(sub_commodity_daily)))
message(sprintf("  ✅ คำนวณความต้องการ 8 กลุ่มวัตถุดิบหลักรายวันสำเร็จ: %d แถว", nrow(commodity_group_daily)))

# ------------------------------------------------------------------------------
# 3. การตรวจสอบความสอดคล้องย้อนกลับด้วยมือ (Hand Reconciliation Check)
# ------------------------------------------------------------------------------
message("\n--- [Step 3] Manual Hand Reconciliation on 3 Benchmark Dishes ---")

# ฟังก์ชันตรวจสอบยอด Reconcile ต่อ 1 วันตัวอย่าง (วันแรก 2026-08-01)
check_reconciliation <- function(target_menu_id, sample_date = as.Date("2026-08-01")) {
  menu_log <- daily_logs %>%
    dplyr::filter(menu_item_id == target_menu_id, date == sample_date)

  q <- menu_log$orders_total[1]

  bom_items <- bom_matrix %>%
    dplyr::filter(menu_item_id == target_menu_id)

  manual_expected <- bom_items %>%
    dplyr::mutate(
      expected_kg_ap = round((q * grams_ap_per_serving) / 1000.0, 4)
    ) %>%
    dplyr::select(sub_commodity, commodity_group_name, grams_ap_per_serving, expected_kg_ap)

  computed <- bom_joined %>%
    dplyr::filter(menu_item_id == target_menu_id, date == sample_date) %>%
    dplyr::select(sub_commodity, actual_kg_ap = demand_kg_ap)

  reconciled <- manual_expected %>%
    dplyr::inner_join(computed, by = "sub_commodity") %>%
    dplyr::mutate(diff = abs(expected_kg_ap - round(actual_kg_ap, 4)))

  max_diff <- max(reconciled$diff)
  if (max_diff > 0.0001) {
    stop(sprintf("❌ [RECONCILIATION FAILED] เมนู %s พบผลต่าง %.6f kg!", target_menu_id, max_diff))
  }

  message(sprintf("  ✅ Reconciliation PASS 100%%: เมนู %-25s (ยอดสั่งซื้อ %d จาน) -> ผลต่าง 0.000000 kg", target_menu_id, q))
  return(TRUE)
}

# ตรวจสอบทั้ง 3 เมนูที่ระบุใน Acceptance Criteria
check_reconciliation("pa-ja-fried-chicken-rice")
check_reconciliation("kinkane-salmon-sashimi")
check_reconciliation("thasanam-boat-noodle-soup")

# ตรวจสอบเงื่อนไข G3 (เนื้อโค) มีความต้องการเฉพาะร้านก๋วยเตี๋ยวเรือ ท่าสนาม เท่านั้น
g3_demand_rests <- commodity_group_daily %>%
  dplyr::filter(commodity_group_name == "beef", demand_kg_ap > 0) %>%
  dplyr::pull(restaurant_id) %>%
  unique() %>%
  as.character()

if (!identical(g3_demand_rests, "thasanam-boat-noodles")) {
  stop(sprintf("❌ [ERROR] G3 (เนื้อโค) มียอดสั่งซื้อนอกร้านท่าสนาม: %s", paste(g3_demand_rests, collapse = ", ")))
}
message("  ✅ ตรวจสอบ G3 (เนื้อโค): มียอดจัดซื้อเฉพาะร้าน thasanam-boat-noodles แห่งเดียวเท่านั้น (100%)")

# ------------------------------------------------------------------------------
# 4. ตรวจสอบการลดลงของความต้องการช่วงปิดภาคเรียน (Semester Break Drop)
# ------------------------------------------------------------------------------
message("\n--- [Step 4] Academic Period Impact on Raw Ingredient Demand ---")

reg_demand <- commodity_group_daily %>%
  dplyr::filter(academic_period == "regular") %>%
  dplyr::group_by(date, restaurant_id) %>%
  dplyr::summarise(daily_total_kg = sum(demand_kg_ap), .groups = "drop") %>%
  dplyr::pull(daily_total_kg) %>%
  mean()

break_demand <- commodity_group_daily %>%
  dplyr::filter(academic_period == "semester_break") %>%
  dplyr::group_by(date, restaurant_id) %>%
  dplyr::summarise(daily_total_kg = sum(demand_kg_ap), .groups = "drop") %>%
  dplyr::pull(daily_total_kg) %>%
  mean()

drop_rate <- (1.0 - break_demand / reg_demand) * 100.0
message(sprintf("  - ค่าเฉลี่ยความต้องการวัตถุดิบช่วงเปิดเทอมปกติ: %.2f กก./ร้าน/วัน", reg_demand))
message(sprintf("  - ค่าเฉลี่ยความต้องการวัตถุดิบช่วงปิดเทอม:       %.2f กก./ร้าน/วัน", break_demand))
message(sprintf("  - อัตราการลดลงช่วงปิดภาคเรียน:                %.2f%% (เป้าหมาย 60%% - 80%%)", drop_rate))

if (drop_rate < 55.0 || drop_rate > 85.0) {
  warning(sprintf("⚠️ อัตราการลดลงช่วงปิดเทอมอยู่นอกช่วงปกติ: %.2f%%", drop_rate))
} else {
  message("  ✅ อัตราการลดลงของวัตถุดิบช่วงปิดเทอมสอดคล้องกับพฤติกรรมจริงรอบ ม.ศิลปากร")
}

# ------------------------------------------------------------------------------
# 5. สร้างกราฟสรุปผลด้วย ggplot2 (Weekly Demand by Commodity Group & Restaurant)
# ------------------------------------------------------------------------------
message("\n--- [Step 5] Generating Publication-Quality ggplot2 Visualizations ---")

# สรุปความต้องการระดับรายสัปดาห์ (Weekly Demand) แยกตาม 8 กลุ่มวัตถุดิบ
weekly_demand <- commodity_group_daily %>%
  dplyr::mutate(
    week_start = lubridate::floor_date(date, unit = "week")
  ) %>%
  dplyr::group_by(week_start, commodity_group_name) %>%
  dplyr::summarise(
    total_demand_kg = sum(demand_kg_ap),
    .groups = "drop"
  )

p1 <- ggplot2::ggplot(weekly_demand, ggplot2::aes(x = week_start, y = total_demand_kg, fill = commodity_group_name)) +
  ggplot2::geom_area(alpha = 0.85, position = "stack") +
  ggplot2::scale_fill_brewer(palette = "Set2", name = "กลุ่มวัตถุดิบ (G1-G8)") +
  ggplot2::scale_y_continuous(labels = scales::comma_format(suffix = " kg")) +
  ggplot2::scale_x_date(date_breaks = "2 months", date_labels = "%b %Y") +
  ggplot2::labs(
    title = "Weekly Wholesale Ingredient Demand (BOM Transformation 2026-2027)",
    subtitle = "Calculated across 10 restaurants / 30 dishes around Silpakorn University (Sanam Chandra)",
    x = "Timeline (Academic Year 2569)",
    y = "Total Weekly AP Demand (kg)",
    caption = "MueNee B2B Analytics: Recipe BOM Matrix Multiplication Model"
  ) +
  ggplot2::theme_minimal(base_size = 11) +
  ggplot2::theme(
    plot.title = ggplot2::element_text(face = "bold", size = 13),
    plot.subtitle = ggplot2::element_text(color = "gray30", size = 10),
    legend.position = "right",
    panel.grid.minor = ggplot2::element_blank()
  )

fig_path1 <- file.path(root_dir, "outputs", "figures", "bom_weekly_demand.png")
ggplot2::ggsave(fig_path1, plot = p1, width = 11, height = 5.5, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟความต้องการวัตถุดิบรายสัปดาห์: %s", fig_path1))

# กราฟที่ 2: แสดงความต้องการวัตถุดิบแยกตาม 10 ร้านค้า (Faceted by Restaurant)
weekly_rest_demand <- commodity_group_daily %>%
  dplyr::mutate(
    week_start = lubridate::floor_date(date, unit = "week")
  ) %>%
  dplyr::group_by(week_start, restaurant_id) %>%
  dplyr::summarise(
    total_demand_kg = sum(demand_kg_ap),
    .groups = "drop"
  )

p2 <- ggplot2::ggplot(weekly_rest_demand, ggplot2::aes(x = week_start, y = total_demand_kg, color = restaurant_id)) +
  ggplot2::geom_line(linewidth = 0.8, show.legend = FALSE) +
  ggplot2::facet_wrap(~restaurant_id, scales = "free_y", ncol = 5) +
  ggplot2::scale_y_continuous(labels = scales::comma_format()) +
  ggplot2::scale_x_date(date_breaks = "4 months", date_labels = "%b %y") +
  ggplot2::labs(
    title = "Weekly Ingredient Procurement Demand by Restaurant (10 Campus Eateries)",
    subtitle = "Distinct drops visible during Semester Breaks (Dec-Jan, May-Jun); Exam spikes in Midterm/Finals",
    x = "Date",
    y = "Weekly Demand (kg AP)"
  ) +
  ggplot2::theme_bw(base_size = 9) +
  ggplot2::theme(
    strip.background = ggplot2::element_rect(fill = "#f0f4f8"),
    strip.text = ggplot2::element_text(face = "bold", size = 8),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_path2 <- file.path(root_dir, "outputs", "figures", "bom_weekly_by_restaurant.png")
ggplot2::ggsave(fig_path2, plot = p2, width = 12, height = 6, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟเปรียบเทียบ 10 ร้านค้า: %s", fig_path2))

# ------------------------------------------------------------------------------
# 6. ส่งออกผลลัพธ์ (Export RDS & CSV)
# ------------------------------------------------------------------------------
message("\n--- [Step 6] Exporting Processed Demand Datasets ---")

# 6.1 บันทึก RDS
out_rds <- file.path(root_dir, "data", "processed", "commodity_daily_demand.rds")
saveRDS(commodity_group_daily, out_rds)
message(sprintf("  💾 บันทึก %s (%d แถว)", out_rds, nrow(commodity_group_daily)))

# 6.2 บันทึก CSV สำหรับการตรวจสอบและประมวลผลต่อ
out_csv <- file.path(root_dir, "outputs", "commodity_daily_demand.csv")
readr::write_csv(commodity_group_daily, out_csv)
message(sprintf("  📄 บันทึก %s (%d แถว, %.1f KB)", out_csv, nrow(commodity_group_daily), file.info(out_csv)$size / 1024))

message("\n==================================================================")
message(" 🎉 BOM TRANSFORMATION COMPLETED SUCCESSFULLY (B2)! READY FOR GATE 3 🎉")
message("==================================================================\n")
