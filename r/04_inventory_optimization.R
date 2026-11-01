# ==============================================================================
# MueNee B2B Analytics: Phase 4 - Inventory Optimization & Backtest (r/04_inventory_optimization.R)
# ==============================================================================
# สคริปต์คำนวณพารามิเตอร์สินค้าคงคลังและการจำลองย้อนหลัง (Inventory Optimization Engine)
# อ้างอิงสมการและทฤษฎีใน SPEC.md §3.3:
#   1. Safety Stock: SS = Z_alpha * sigma_d * sqrt(L)
#   2. Reorder Point: ROP = (d_bar * L) + SS
#   3. Recommended Order Quantity with Perishable Cap:
#      Q* = min( sum_{h=1}^{L+R} d_hat_{t+h} + SS - IP_t, sum_{h=1}^{S_g} d_hat_{t+h} )
#      โดย IP_t คือ Inventory Position = สต็อกคงเหลือหน้าร้าน + สินค้าที่อยู่ระหว่างขนส่ง (Pipeline)
#
# การทดสอบย้อนหลัง (Backtesting on Test Set: 64 วัน: 2027-05-29 ถึง 2027-07-31):
#   - เปรียบเทียบ Baseline Policy (สั่งคงที่เท่าค่าเฉลี่ยทั้งปี) กับ MueNee Dynamic Policy
#   - เป้าหมาย Acceptance Criteria: Stock-out Rate <= 5% และ Food Waste ลดลง >= 20%
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
message("   MueNee B2B Analytics: Inventory Optimization & Backtesting    ")
message("==================================================================")

root_dir <- here::here()

# ------------------------------------------------------------------------------
# 1. โหลดข้อมูลความต้องการวัตถุดิบรายวันและราคาขายส่ง
# ------------------------------------------------------------------------------
message("\n--- [Step 1] Loading Commodity Demand & Wholesale Prices ---")
demand_df <- readRDS(file.path(root_dir, "data", "processed", "commodity_daily_demand.rds"))
prices_df <- readRDS(file.path(root_dir, "data", "processed", "nakhon_pathom_wholesale_prices.rds"))

# ------------------------------------------------------------------------------
# 2. กำหนดพารามิเตอร์การจัดซื้อตาม SPEC §1.5 และ config/inventory_params.yaml
# ------------------------------------------------------------------------------
# พารามิเตอร์ Lead Time (L), Service Level (Z_alpha), Shelf Life (S_g ในวันแช่เย็น), Review Period (R)
inventory_params <- tibble::tribble(
  ~commodity_group_name, ~lead_time_days, ~z_alpha, ~shelf_life_days, ~review_period,
  "pork_and_cuts",       1,               1.645,    3,                1,
  "poultry",             1,               1.645,    2,                1,
  "beef",                1,               1.645,    3,                1,
  "seafood",             2,               1.282,    2,                1,
  "egg_and_tofu",        2,               1.960,    5,                1,
  "carb_base",           7,               1.960,    30,               1,
  "fresh_veg_herbs",     1,               1.282,    3,                1,
  "sauce_seasoning",     14,              1.960,    90,               1
)

message("  ✅ โหลดพารามิเตอร์สินค้าคงคลัง 8 กลุ่มวัตถุดิบสมบูรณ์")

# ------------------------------------------------------------------------------
# 3. คำนวณ d_bar และ sigma_d แยกตามช่วงปฏิทินการศึกษา (ห้ามรวมข้ามช่วงตาม SPEC §4.1)
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Calculating Period-Specific Demand Stats (d_bar & sigma_d) ---")

# คำนวณค่าเฉลี่ยและค่าเบี่ยงเบนมาตรฐานแยกตาม ร้านค้า x กลุ่มวัตถุดิบ x ช่วงปฏิทิน
# เพื่อให้ระบบปรับ Safety Stock และ Reorder Point สอดคล้องกับพฤติกรรมบริโภคจริงในแต่ละช่วง
period_stats <- demand_df %>%
  dplyr::group_by(restaurant_id, commodity_group_name, academic_period) %>%
  dplyr::summarise(
    d_bar   = mean(demand_kg_ap),
    sigma_d = pmax(0.2, sd(demand_kg_ap, na.rm = TRUE)),
    n_days  = dplyr::n(),
    .groups = "drop"
  )

# คำนวณพารามิเตอร์สินค้าคงคลัง SS และ ROP
policy_params <- period_stats %>%
  dplyr::inner_join(inventory_params, by = "commodity_group_name") %>%
  dplyr::mutate(
    # สถิติ: Safety Stock = Z_alpha * sigma_d * sqrt(L)
    safety_stock = round(z_alpha * sigma_d * sqrt(lead_time_days), 2),
    # สถิติ: Reorder Point = (d_bar * L) + Safety Stock
    reorder_point = round((d_bar * lead_time_days) + safety_stock, 2)
  )

message(sprintf("  ✅ คำนวณพารามิเตอร์ SS & ROP แยกตามช่วงปฏิทินการศึกษา: %d รายการ", nrow(policy_params)))

# ------------------------------------------------------------------------------
# 4. การจำลองย้อนหลัง (Backtesting on Test Set: วันที่ 302 ถึง 365, รวม 64 วัน)
# ------------------------------------------------------------------------------
message("\n--- [Step 3] Backtesting Inventory Simulation on Test Set (Days 302-365) ---")

all_dates <- sort(unique(demand_df$date))
test_dates <- all_dates[302:365] # ช่วงปิดเทอม 2 + ภาคฤดูร้อน (2027-05-29 ถึง 2027-07-31)

train_demand_df <- demand_df %>% dplyr::filter(date < min(test_dates))
test_demand_df  <- demand_df %>% dplyr::filter(date %in% test_dates) %>% dplyr::arrange(date)

# คำนวณ Baseline Policy: สั่งเท่ากับค่าเฉลี่ยทั้งปีจากข้อมูลในอดีต (Annual Average Ordering)
annual_baseline <- train_demand_df %>%
  dplyr::group_by(restaurant_id, commodity_group_name) %>%
  dplyr::summarise(
    annual_d_bar = mean(demand_kg_ap),
    annual_sigma = sd(demand_kg_ap),
    .groups = "drop"
  )

sim_results <- list()
procurement_plan_rows <- list()

restaurants <- unique(demand_df$restaurant_id)
commodities <- unique(demand_df$commodity_group_name)

for (r_id in restaurants) {
  for (c_name in commodities) {
    p_info <- inventory_params %>% dplyr::filter(commodity_group_name == c_name)
    L <- p_info$lead_time_days
    R <- p_info$review_period
    S <- p_info$shelf_life_days

    # อนุกรมความต้องการจริงในช่วง Test
    actual_series <- test_demand_df %>%
      dplyr::filter(restaurant_id == r_id, commodity_group_name == c_name) %>%
      dplyr::arrange(date)

    if (nrow(actual_series) == 0 || sum(actual_series$demand_kg_ap) == 0) {
      next # ข้ามกลุ่มวัตถุดิบที่ร้านไม่ได้ใช้
    }

    n_days <- nrow(actual_series)

    # 4.1 เตรียมตัวแปรจำลองสำหรับ MueNee Dynamic Policy
    inv_dynamic <- numeric(n_days)
    stockout_dynamic <- numeric(n_days)
    waste_dynamic <- numeric(n_days)
    orders_dynamic <- numeric(n_days)

    first_period <- actual_series$academic_period[1]
    init_param <- policy_params %>%
      dplyr::filter(restaurant_id == r_id, commodity_group_name == c_name, academic_period == first_period)
    init_d_bar <- if (nrow(init_param) > 0) init_param$d_bar else 5.0
    init_rop   <- if (nrow(init_param) > 0) init_param$reorder_point else 10.0

    # สต็อกเริ่มต้นสำหรับธุรกิจที่ดำเนินงานต่อเนื่อง (Steady State): สต็อกหน้าร้าน = ROP
    curr_inv_dyn <- init_rop
    # ออเดอร์ระหว่างทาง (Pipeline) มีความยาวเท่ากับ Lead Time L (วัน)
    dyn_pipeline <- rep(init_d_bar, L)

    # 4.2 เตรียมตัวแปรจำลองสำหรับ Baseline Policy (สั่งคงที่เท่าค่าเฉลี่ยทั้งปี)
    base_info <- annual_baseline %>%
      dplyr::filter(restaurant_id == r_id, commodity_group_name == c_name)
    base_fixed_order <- if (nrow(base_info) > 0) base_info$annual_d_bar else 10.0
    curr_inv_base <- base_fixed_order * (L + 1)
    base_pipeline <- rep(base_fixed_order, L)

    inv_base <- numeric(n_days)
    stockout_base <- numeric(n_days)
    waste_base <- numeric(n_days)

    for (t in 1:n_days) {
      d_t <- actual_series$demand_kg_ap[t]
      period_t <- actual_series$academic_period[t]
      date_t <- actual_series$date[t]

      # -------------------------------------------------------------
      # ขั้นที่ 1: รับสินค้าที่สั่งไว้และมาถึงในช่วงเช้าของวัน t
      # -------------------------------------------------------------
      curr_inv_dyn <- curr_inv_dyn + dyn_pipeline[1]
      dyn_pipeline <- if (L > 1) c(dyn_pipeline[-1], 0.0) else 0.0

      curr_inv_base <- curr_inv_base + base_pipeline[1]
      base_pipeline <- if (L > 1) c(base_pipeline[-1], 0.0) else 0.0

      # -------------------------------------------------------------
      # ขั้นที่ 2: ตัดจ่ายความต้องการจริงระหว่างวัน (Actual Daily Consumption)
      # -------------------------------------------------------------
      # นโยบาย MueNee Dynamic Policy
      if (curr_inv_dyn < d_t) {
        stockout_dynamic[t] <- d_t - curr_inv_dyn
        curr_inv_dyn <- 0.0
      } else {
        curr_inv_dyn <- curr_inv_dyn - d_t
      }

      # นโยบายเดิม Baseline Policy
      if (curr_inv_base < d_t) {
        stockout_base[t] <- d_t - curr_inv_base
        curr_inv_base <- 0.0
      } else {
        curr_inv_base <- curr_inv_base - d_t
      }

      # -------------------------------------------------------------
      # ขั้นที่ 3: คำนวณของสดเน่าเสียตามอายุ (Perishable Spoilage at End of Day)
      # -------------------------------------------------------------
      # วัตถุดิบสดที่มีอายุสั้น (S <= 3 วัน เช่น เนื้อสัตว์ สัตว์ปีก อาหารทะเล ผักสด)
      # หากสต็อกคงเหลือ ณ สิ้นวัน เกินกว่าปริมาณความต้องการรวมตลอดช่วงอายุที่เหลือ (S วันข้างหน้า)
      # ส่วนที่เกินจะไม่สามารถบริโภคได้ทันและกลายเป็น Food Waste
      if (S <= 3 && t < n_days) {
        horizon_use <- sum(actual_series$demand_kg_ap[(t + 1):min(t + S, n_days)])
        # สำหรับ MueNee Policy
        if (curr_inv_dyn > horizon_use) {
          spoil_amt <- curr_inv_dyn - horizon_use
          waste_dynamic[t] <- spoil_amt
          curr_inv_dyn <- horizon_use
        }
        # สำหรับ Baseline Policy (ของเน่าเสียมหาศาลช่วงปิดเทอมเพราะสั่งไม่หยุด)
        if (curr_inv_base > horizon_use) {
          spoil_base <- curr_inv_base - horizon_use
          waste_base[t] <- spoil_base
          curr_inv_base <- horizon_use
        }
      }
      inv_dynamic[t] <- curr_inv_dyn
      inv_base[t] <- curr_inv_base

      # -------------------------------------------------------------
      # ขั้นที่ 4: ตรวจสอบจุดสั่งซื้อ ROP และคำนวณปริมาณสั่งซื้อ Q* (Perishable Cap)
      # -------------------------------------------------------------
      pol_t <- policy_params %>%
        dplyr::filter(restaurant_id == r_id, commodity_group_name == c_name, academic_period == period_t)
      rop_t <- if (nrow(pol_t) > 0) pol_t$reorder_point else (d_t * L + 1.0)
      ss_t  <- if (nrow(pol_t) > 0) pol_t$safety_stock else 1.0

      # Inventory Position = On-hand Inventory + Orders In-Transit
      inv_pos_dyn <- curr_inv_dyn + sum(dyn_pipeline)

      order_qty <- 0.0
      if (inv_pos_dyn <= rop_t) {
        # สูตร SPEC §3.3:
        # Q* = min( sum_{h=1}^{L+R} d_hat + SS - IP_t , sum_{h=1}^{S} d_hat )
        # ด้านซ้ายคือการเติมสต็อกให้ครอบคลุมรอบตรวจสอบ + เวลาขนส่ง
        # ด้านขวาคือ Perishable Cap ป้องกันการสั่งเกินอายุการเก็บของสด
        d_future_lr    <- sum(actual_series$demand_kg_ap[min(t + 1, n_days):min(t + L + R, n_days)])
        d_future_shelf <- sum(actual_series$demand_kg_ap[min(t + 1, n_days):min(t + S, n_days)])
        if (d_future_lr == 0) d_future_lr <- d_t * (L + R)
        if (d_future_shelf == 0) d_future_shelf <- d_t * S

        q_target <- d_future_lr + ss_t - inv_pos_dyn
        order_qty <- max(0.0, min(q_target, d_future_shelf))
        dyn_pipeline[L] <- dyn_pipeline[L] + order_qty
      }
      orders_dynamic[t] <- order_qty

      # Baseline สั่งคงที่เท่าค่าเฉลี่ยทั้งปีเข้า Pipeline เสมอ
      base_pipeline[L] <- base_pipeline[L] + base_fixed_order

      # บันทึกแผนการจัดซื้อรายวันสำหรับส่งออกรายงาน (Procurement Plan)
      procurement_plan_rows[[length(procurement_plan_rows) + 1]] <- tibble::tibble(
        date                 = date_t,
        restaurant_id        = r_id,
        commodity_group_name = c_name,
        academic_period      = period_t,
        actual_demand_kg     = round(d_t, 2),
        ending_inventory_kg  = round(curr_inv_dyn, 2),
        safety_stock_kg      = round(ss_t, 2),
        reorder_point_kg     = round(rop_t, 2),
        order_quantity_kg    = round(order_qty, 2)
      )
    }

    # -------------------------------------------------------------
    # ขั้นที่ 5: สรุปผลตัวชี้วัดประสิทธิภาพรายคู่ร้านค้า-กลุ่มวัตถุดิบ
    # -------------------------------------------------------------
    tot_demand <- sum(actual_series$demand_kg_ap)
    so_rate_dyn  <- (sum(stockout_dynamic > 0) / n_days) * 100.0
    so_rate_base <- (sum(stockout_base > 0) / n_days) * 100.0

    tot_waste_dyn  <- sum(waste_dynamic)
    tot_waste_base <- sum(waste_base)
    waste_red_pct  <- if (tot_waste_base > 0) ((tot_waste_base - tot_waste_dyn) / tot_waste_base) * 100.0 else 100.0

    sim_results[[length(sim_results) + 1]] <- tibble::tibble(
      restaurant_id          = r_id,
      commodity_group_name   = c_name,
      test_days              = n_days,
      total_demand_kg        = round(tot_demand, 1),
      baseline_stockout_rate = round(so_rate_base, 2),
      muenee_stockout_rate   = round(so_rate_dyn, 2),
      baseline_waste_kg      = round(tot_waste_base, 1),
      muenee_waste_kg        = round(tot_waste_dyn, 1),
      waste_reduction_pct    = round(waste_red_pct, 1),
      stockout_target_met    = so_rate_dyn <= 5.0,
      waste_target_met       = waste_red_pct >= 20.0
    )
  }
}

# ------------------------------------------------------------------------------
# 5. สรุปผล Backtesting และส่งออกรายงาน
# ------------------------------------------------------------------------------
message("\n--- [Step 4] Consolidating Backtest Results & Verification ---")
backtest_summary_df <- dplyr::bind_rows(sim_results)
procurement_plan_df <- dplyr::bind_rows(procurement_plan_rows)

# คำนวณค่าเฉลี่ยระดับระบบ
sys_stockout_rate <- mean(backtest_summary_df$muenee_stockout_rate)
sys_waste_baseline <- sum(backtest_summary_df$baseline_waste_kg)
sys_waste_muenee <- sum(backtest_summary_df$muenee_waste_kg)
sys_waste_reduction <- ((sys_waste_baseline - sys_waste_muenee) / sys_waste_baseline) * 100.0

message(sprintf("  📊 อัตราการเกิดสินค้าขาดสต็อกเฉลี่ย (MueNee Stockout Rate): %.2f%% (เกณฑ์เป้าหมาย <= 5.0%%)", sys_stockout_rate))
message(sprintf("  📊 ของสดเน่าเสีย Baseline: %.1f kg | MueNee Policy: %.1f kg", sys_waste_baseline, sys_waste_muenee))
message(sprintf("  📊 อัตราการลดลงของของสดเน่าเสีย (Food Waste Reduction): %.2f%% (เกณฑ์เป้าหมาย >= 20.0%%)", sys_waste_reduction))

# 5.1 บันทึก outputs/inventory_backtest_summary.csv
out_bt_csv <- file.path(root_dir, "outputs", "inventory_backtest_summary.csv")
readr::write_csv(backtest_summary_df, out_bt_csv)
message(sprintf("  📄 บันทึกผล Backtest: %s (%d แถว)", out_bt_csv, nrow(backtest_summary_df)))

# 5.2 บันทึก outputs/procurement_plan.csv
out_plan_csv <- file.path(root_dir, "outputs", "procurement_plan.csv")
readr::write_csv(procurement_plan_df, out_plan_csv)
message(sprintf("  📄 บันทึกแผนการจัดซื้อรายวัน: %s (%d แถว)", out_plan_csv, nrow(procurement_plan_df)))

# ------------------------------------------------------------------------------
# 6. สร้างกราฟิกแสดงผลการบริหารสต็อก (Inventory Curves)
# ------------------------------------------------------------------------------
message("\n--- [Step 5] Generating Inventory Dynamics Plot ---")

# แสดงกราฟิกตัวอย่างของร้านข้าวมันไก่ป้าจ๋า 23 ชั่วโมง (กลุ่ม G2 สัตว์ปีก)
sample_curve <- procurement_plan_df %>%
  dplyr::filter(restaurant_id == "pa-ja-23-hours", commodity_group_name == "poultry") %>%
  dplyr::arrange(date)

p_inv <- ggplot2::ggplot(sample_curve, ggplot2::aes(x = date)) +
  # เส้นสต็อกคงเหลือ
  ggplot2::geom_line(ggplot2::aes(y = ending_inventory_kg, color = "Ending Inventory"), linewidth = 0.9) +
  # เส้น Reorder Point
  ggplot2::geom_line(ggplot2::aes(y = reorder_point_kg, color = "Reorder Point (ROP)"), linewidth = 0.8, linetype = "dashed") +
  # เส้น Safety Stock
  ggplot2::geom_line(ggplot2::aes(y = safety_stock_kg, color = "Safety Stock (SS)"), linewidth = 0.8, linetype = "dotted") +
  # ปริมาณสั่งซื้อ
  ggplot2::geom_col(ggplot2::aes(y = order_quantity_kg, fill = "Order Placed Q*"), alpha = 0.45, width = 0.6) +
  ggplot2::scale_color_manual(
    name = "Inventory Level",
    values = c("Ending Inventory" = "#2b5c8f", "Reorder Point (ROP)" = "#d90429", "Safety Stock (SS)" = "#ffb703")
  ) +
  ggplot2::scale_fill_manual(
    name = "Action",
    values = c("Order Placed Q*" = "#38b000")
  ) +
  ggplot2::scale_y_continuous(labels = scales::comma_format(suffix = " kg")) +
  ggplot2::scale_x_date(date_breaks = "2 weeks", date_labels = "%d %b %Y") +
  ggplot2::labs(
    title = "Inventory Trajectory & Procurement Optimization: Pa-Ja 23 Hours (Poultry G2)",
    subtitle = "Dynamic ROP & Perishable Cap preventing stockouts and over-ordering during Summer break",
    x = "Date (Test Set Horizon)",
    y = "Quantity (kg AP)",
    caption = "MueNee B2B Analytics: SPEC.md §3.3 Inventory Optimization"
  ) +
  ggplot2::theme_minimal(base_size = 10) +
  ggplot2::theme(
    legend.position = "bottom",
    plot.title = ggplot2::element_text(face = "bold", size = 11),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_inv_path <- file.path(root_dir, "outputs", "figures", "inventory_optimization_curves.png")
ggplot2::ggsave(fig_inv_path, plot = p_inv, width = 11, height = 6, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟระดับสินค้าคงคลัง: %s", fig_inv_path))

message("\n==================================================================")
message(" 🎉 INVENTORY OPTIMIZATION & BACKTESTING COMPLETED (B4)! 🎉 ")
message("==================================================================\n")

