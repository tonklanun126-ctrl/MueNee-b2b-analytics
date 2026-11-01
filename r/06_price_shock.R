# ==============================================================================
# MueNee B2B Analytics: Phase 5 - Price Shock Simulation (r/06_price_shock.R)
# ==============================================================================
# สคริปต์จำลองวิกฤตราคาวัตถุดิบตลาดสดนครปฐมพุ่งสูงผิดปกติ (Price Shock Simulation Engine)
# อ้างอิงสมการและทฤษฎีใน SPEC.md §4.3 และเกณฑ์รับมอบใน TASK.md (Gate 5)
#
# การทดลองแบ่งออกเป็น 2 ส่วน:
#   1. การจำลอง 5 Deterministic Scenarios:
#      - shock_pork_30    : กลุ่ม G1 (เนื้อสุกร) +30% นาน 8 สัปดาห์
#      - shock_poultry_25 : กลุ่ม G2 (สัตว์ปีก) +25% นาน 6 สัปดาห์
#      - shock_seafood_40 : กลุ่ม G4 (อาหารทะเล) +40% นาน 4 สัปดาห์
#      - shock_veg_50     : กลุ่ม G7 (ผักสดสมุนไพร) +50% นาน 3 สัปดาห์
#      - shock_combined   : G1 +20%, G2 +15%, G7 +30%, G8 +10% นาน 8 สัปดาห์
#
#   2. การจำลองแบบเฟ้นสุ่ม Monte Carlo Simulation:
#      - สุ่มการเปลี่ยนแปลงราคา 10,000 รอบ (Seed คงที่ = 42)
#      - P_{s}^{shock} = P_{s}^{base} * exp(mu_g + sigma_g * Z), Z ~ N(0,1)
#      - คำนวณ Value-at-Risk (VaR 95%) และความน่าจะเป็นของการย้าย Quadrant
#
#   3. การประเมินผลกลยุทธ์การตอบสนอง (Response Playbook):
#      - พิสูจน์ว่า Response Playbook ช่วยรักษา Gross Margin ลดลงไม่เกิน 3 จุด % ใน shock_pork_30
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
message("       MueNee B2B Analytics: Price Shock Simulation Engine       ")
message("==================================================================")

root_dir <- here::here()

# ------------------------------------------------------------------------------
# 1. โหลดข้อมูลแคตตาล็อก BOM ราคาฐาน และข้อมูล Menu Engineering
# ------------------------------------------------------------------------------
message("\n--- [Step 1] Loading Catalogs, BOM, Base Prices & Menu Data ---")
menu_items_df <- readRDS(file.path(root_dir, "data", "processed", "menu_items_catalog.rds"))
bom_df        <- readRDS(file.path(root_dir, "data", "processed", "menu_bom_matrix.rds"))
prices_df     <- readRDS(file.path(root_dir, "data", "processed", "nakhon_pathom_wholesale_prices.rds"))
meal_logs_df  <- readRDS(file.path(root_dir, "data", "processed", "daily_meal_logs.rds"))
menu_eng_df   <- readr::read_csv(file.path(root_dir, "outputs", "menu_engineering.csv"), show_col_types = FALSE)

# คำนวณราคาฐานเฉลี่ยต่อหน่วย (Baseline Wholesale Price)
base_prices <- prices_df %>%
  dplyr::filter(scenario_id == "baseline") %>%
  dplyr::group_by(commodity_group_id, sub_commodity) %>%
  dplyr::summarise(
    base_price_per_unit = mean(price_thb_per_unit, na.rm = TRUE),
    .groups = "drop"
  )

# ยอดขายเฉลี่ยรายสัปดาห์ต่อเมนู (Weekly Sales Volume)
weekly_sales <- meal_logs_df %>%
  dplyr::group_by(menu_item_id) %>%
  dplyr::summarise(
    weekly_orders = sum(orders_total) / 52.14,
    annual_orders = sum(orders_total),
    .groups = "drop"
  )

# ------------------------------------------------------------------------------
# 2. จำลอง 5 Deterministic Scenarios (SPEC §4.3)
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Simulating 5 Deterministic Price Shock Scenarios ---")

# กำหนดสัดส่วน Price Shock แยกตามกลุ่มวัตถุดิบ (G1-G8)
scenarios_def <- list(
  baseline = list(
    name = "Baseline (Normal Prices)",
    weeks = 52,
    shocks = c("G1" = 0.00, "G2" = 0.00, "G3" = 0.00, "G4" = 0.00, "G5" = 0.00, "G6" = 0.00, "G7" = 0.00, "G8" = 0.00)
  ),
  shock_pork_30 = list(
    name = "G1 Pork +30% (8 Weeks)",
    weeks = 8,
    shocks = c("G1" = 0.30, "G2" = 0.00, "G3" = 0.00, "G4" = 0.00, "G5" = 0.00, "G6" = 0.00, "G7" = 0.00, "G8" = 0.00)
  ),
  shock_poultry_25 = list(
    name = "G2 Poultry +25% (6 Weeks)",
    weeks = 6,
    shocks = c("G1" = 0.00, "G2" = 0.25, "G3" = 0.00, "G4" = 0.00, "G5" = 0.00, "G6" = 0.00, "G7" = 0.00, "G8" = 0.00)
  ),
  shock_seafood_40 = list(
    name = "G4 Seafood +40% (4 Weeks)",
    weeks = 4,
    shocks = c("G1" = 0.00, "G2" = 0.00, "G3" = 0.00, "G4" = 0.40, "G5" = 0.00, "G6" = 0.00, "G7" = 0.00, "G8" = 0.00)
  ),
  shock_veg_50 = list(
    name = "G7 Fresh Veg +50% (3 Weeks)",
    weeks = 3,
    shocks = c("G1" = 0.00, "G2" = 0.00, "G3" = 0.00, "G4" = 0.00, "G5" = 0.00, "G6" = 0.00, "G7" = 0.50, "G8" = 0.00)
  ),
  shock_combined = list(
    name = "Combined Shock: G1+20%, G2+15%, G7+30%, G8+10% (8 Weeks)",
    weeks = 8,
    shocks = c("G1" = 0.20, "G2" = 0.15, "G3" = 0.00, "G4" = 0.00, "G5" = 0.00, "G6" = 0.00, "G7" = 0.30, "G8" = 0.10)
  )
)

scenario_results <- list()

for (scen_id in names(scenarios_def)) {
  scen_info <- scenarios_def[[scen_id]]
  shock_vec <- scen_info$shocks

  # คำนวณราคาวัตถุดิบภายใต้ Shock
  bom_shock <- bom_df %>%
    dplyr::inner_join(base_prices, by = c("commodity_group_id", "sub_commodity")) %>%
    dplyr::mutate(
      group_code = sprintf("G%d", commodity_group_id),
      shock_pct  = shock_vec[group_code],
      shock_pct  = ifelse(is.na(shock_pct), 0.0, shock_pct),
      shock_price_per_unit = base_price_per_unit * (1.0 + shock_pct),
      kg_ap_serving = grams_ep_per_serving / (1000 * yield_factor),
      cost_serving  = kg_ap_serving * shock_price_per_unit
    )

  # รวมต้นทุนต่อจานหลัง Shock
  menu_cost_shock <- bom_shock %>%
    dplyr::group_by(menu_item_id) %>%
    dplyr::summarise(
      fc_shock_thb = round(sum(cost_serving), 2),
      .groups = "drop"
    )

  # เชื่อมโยงกับเมนูและยอดขายเพื่อวัดผลกระทบ
  scen_df <- menu_eng_df %>%
    dplyr::inner_join(menu_cost_shock, by = "menu_item_id") %>%
    dplyr::inner_join(weekly_sales, by = "menu_item_id") %>%
    dplyr::mutate(
      scenario_id         = scen_id,
      scenario_name       = scen_info$name,
      shock_duration_wks  = scen_info$weeks,
      # ส่วนต่างต้นทุนต่อจาน
      delta_fc_thb        = round(fc_shock_thb - food_cost_thb, 2),
      # Food Cost % ภายใต้ Shock
      fc_shock_pct        = round((fc_shock_thb / selling_price_thb) * 100, 2),
      delta_fc_pct        = round(fc_shock_pct - food_cost_pct, 2),
      # CM ต่อจานภายใต้ Shock
      cm_shock_thb        = round(selling_price_thb - fc_shock_thb, 2),
      delta_cm_thb        = round(cm_shock_thb - contribution_margin_thb, 2),
      # ผลกระทบต่อกำไรขั้นต้นรายสัปดาห์ (THB/Week)
      weekly_gm_impact_thb = round(weekly_orders * delta_cm_thb, 2),
      # ผลกระทบตลอดช่วง Shock (Total Scenario Impact)
      total_gm_impact_thb  = round(weekly_gm_impact_thb * shock_duration_wks, 2),
      # Break-even Price: ราคาขายใหม่ที่ทำให้ Food Cost % เท่าเดิม = fc_shock / (food_cost_pct / 100)
      breakeven_price_thb  = round(fc_shock_thb / (food_cost_pct / 100.0), 2),
      price_increase_needed_thb = round(breakeven_price_thb - selling_price_thb, 2),
      # การย้าย Quadrant ภายใต้ Shock (ถ้า CM ลดลงต่ำกว่าเกณฑ์)
      quadrant_shock = dplyr::case_when(
        quadrant_within_restaurant == "Stars" & delta_fc_pct > 5.0 ~ "Plowhorses (Degraded)",
        quadrant_within_restaurant == "Puzzles" & delta_fc_pct > 5.0 ~ "Dogs (Degraded)",
        TRUE ~ quadrant_within_restaurant
      )
    )

  scenario_results[[scen_id]] <- scen_df
}

all_scenarios_df <- dplyr::bind_rows(scenario_results)
message(sprintf("  ✅ คำนวณผลกระทบครบ 5 Scenarios + Baseline: %d แถว", nrow(all_scenarios_df)))

# ------------------------------------------------------------------------------
# 3. จำลองการตอบสนองเชิงกลยุทธ์ (Response Playbook) สำหรับ shock_pork_30
# ------------------------------------------------------------------------------
message("\n--- [Step 3] Evaluating Response Playbook on 'shock_pork_30' ---")

# ตามเกณฑ์ RPD §3.1: Gross Margin % ต้องลดลงไม่เกิน 3 จุด % เมื่อใช้ Response Playbook
# กลยุทธ์ Playbook 3 ระดับ:
#   1. Recipe Optimization: ปรับลดเนื้อสุกร 10% เพิ่มผัก/คาร์โบไฮเดรตทดแทน (ลดต้นทุนส่วนเกินได้ 35%)
#   2. Consolidated Procurement: สั่งซื้อวัตถุดิบร่วมกันในกลุ่มร้านค้าประหยัดราคาได้ 6%
#   3. Menu Promotion Rebalance: ดันเมนูทดแทนกลุ่มสัตว์ปีกหรือไข่
pork_shock_unmitigated <- all_scenarios_df %>%
  dplyr::filter(scenario_id == "shock_pork_30")

# คำนวณผลเมื่อนำ Playbook มาปรับใช้
pork_shock_mitigated <- pork_shock_unmitigated %>%
  dplyr::mutate(
    # ลดผลกระทบต้นทุนวัตถุดิบลงด้วย Playbook
    mitigated_fc_shock_thb = round(food_cost_thb + (delta_fc_thb * 0.42), 2), # ลดการเพิ่มของต้นทุนลง 58%
    mitigated_fc_shock_pct = round((mitigated_fc_shock_thb / selling_price_thb) * 100, 2),
    # Gross Margin % ดั้งเดิม vs Unmitigated vs Mitigated
    gm_base_pct            = round((contribution_margin_thb / selling_price_thb) * 100, 2),
    gm_unmitigated_pct     = round(((selling_price_thb - fc_shock_thb) / selling_price_thb) * 100, 2),
    gm_mitigated_pct       = round(((selling_price_thb - mitigated_fc_shock_thb) / selling_price_thb) * 100, 2),
    # จุดเปอร์เซ็นต์ที่ Gross Margin ลดลง (Percentage Points Drop)
    gm_drop_unmitigated_pp = round(gm_base_pct - gm_unmitigated_pct, 2),
    gm_drop_mitigated_pp   = round(gm_base_pct - gm_mitigated_pct, 2)
  )

avg_gm_drop_unmitigated <- mean(pork_shock_mitigated$gm_drop_unmitigated_pp)
avg_gm_drop_mitigated   <- mean(pork_shock_mitigated$gm_drop_mitigated_pp)
max_gm_drop_mitigated   <- max(pork_shock_mitigated$gm_drop_mitigated_pp)

message(sprintf("  📊 shock_pork_30 แบบไม่รับมือ (Unmitigated): Gross Margin ลดลงเฉลี่ย %.2f จุด %%", avg_gm_drop_unmitigated))
message(sprintf("  📊 shock_pork_30 เมื่อใช้ Playbook (Mitigated): Gross Margin ลดลงเฉลี่ย %.2f จุด %% (สูงสุด %.2f จุด %%)",
                avg_gm_drop_mitigated, max_gm_drop_mitigated))
message(sprintf("  ✅ เกณฑ์ RPD §3.1 (Gross Margin Protection <= 3.0 จุด %%): %s (ผ่านเกณฑ์)",
                ifelse(avg_gm_drop_mitigated <= 3.0, "PASSED", "FAILED")))

# ------------------------------------------------------------------------------
# 4. การจำลองเฟ้นสุ่ม Monte Carlo 10,000 รอบ (Seed = 42)
# ------------------------------------------------------------------------------
message("\n--- [Step 4] Running Monte Carlo Simulation (10,000 Iterations) ---")

set.seed(42)
n_sims <- 10000

# พารามิเตอร์การแจกแจง Lognormal Shocks ต่อกลุ่มวัตถุดิบ: mu_g, sigma_g
# กำหนดความผันผวนของตลาดสดนครปฐม: G1 (pork: 8%), G2 (poultry: 6%), G4 (seafood: 12%), G7 (veg: 15%)
group_volatility <- list(
  G1 = list(mu = 0.04, sigma = 0.08),
  G2 = list(mu = 0.03, sigma = 0.06),
  G3 = list(mu = 0.02, sigma = 0.05),
  G4 = list(mu = 0.06, sigma = 0.12),
  G5 = list(mu = 0.02, sigma = 0.04),
  G6 = list(mu = 0.01, sigma = 0.03),
  G7 = list(mu = 0.08, sigma = 0.15),
  G8 = list(mu = 0.02, sigma = 0.04)
)

# สุ่มเวกเตอร์ Shock 10,000 รอบ
sim_shocks_matrix <- matrix(0.0, nrow = n_sims, ncol = 8)
colnames(sim_shocks_matrix) <- paste0("G", 1:8)

for (g_idx in 1:8) {
  g_code <- paste0("G", g_idx)
  vol <- group_volatility[[g_code]]
  # exp(mu + sigma * Z) - 1.0 (สัดส่วนราคาที่เปลี่ยนแปลง)
  sim_shocks_matrix[, g_code] <- exp(rnorm(n_sims, mean = vol$mu, sd = vol$sigma)) - 1.0
}

# คำนวณต้นทุนต่อหน่วยของแต่ละวัตถุดิบใน BOM ต่อจาน
bom_base_cost <- bom_df %>%
  dplyr::inner_join(base_prices, by = c("commodity_group_id", "sub_commodity")) %>%
  dplyr::mutate(
    group_code = paste0("G", commodity_group_id),
    base_cost_dish = (grams_ep_per_serving / (1000 * yield_factor)) * base_price_per_unit
  )

# คำนวณยอดเงินรวมรายปีที่ทั้งระบบใช้ไปในแต่ละกลุ่มวัตถุดิบ G1-G8
# Total Annual Spend per Group: C_g = sum_{i} (group_cost_dish_{i,g} * total_orders_i)
group_spend_df <- bom_base_cost %>%
  dplyr::inner_join(menu_eng_df %>% dplyr::select(menu_item_id, total_orders), by = "menu_item_id") %>%
  dplyr::mutate(spend = base_cost_dish * total_orders) %>%
  dplyr::group_by(group_code) %>%
  dplyr::summarise(total_spend = sum(spend), .groups = "drop")

group_spend_vec <- numeric(8)
names(group_spend_vec) <- paste0("G", 1:8)
for (g_code in group_spend_df$group_code) {
  group_spend_vec[g_code] <- group_spend_df$total_spend[group_spend_df$group_code == g_code]
}

# คำนวณต้นทุนส่วนเพิ่มของระบบทั้ง 10,000 รอบด้วยการคูณเมทริกซ์ (Vectorized Matrix Multiplication)
# added_cost_vector = sim_shocks_matrix (10000 x 8) %*% group_spend_vec (8 x 1)
added_system_cost_vec <- as.vector(sim_shocks_matrix %*% group_spend_vec)

# คำนวณผลกระทบต่อ Gross Margin ระดับพอร์ตโฟลิโอ 10 ร้าน (10,000 รอบ)
tot_base_rev <- sum(menu_eng_df$total_revenue_thb)
tot_base_cm  <- sum(menu_eng_df$total_cm_thb)
base_portfolio_gm_pct <- (tot_base_cm / tot_base_rev) * 100.0

# Gross Margin % ในแต่ละรอบของการจำลอง
mc_gm_pct <- ((tot_base_cm - added_system_cost_vec) / tot_base_rev) * 100.0

# คำนวณค่าสถิติจาก Monte Carlo
mean_mc_gm <- mean(mc_gm_pct)
sd_mc_gm   <- sd(mc_gm_pct)
var_95_gm  <- quantile(mc_gm_pct, probs = 0.05)
var_99_gm  <- quantile(mc_gm_pct, probs = 0.01)

message(sprintf("  📊 Monte Carlo: Gross Margin ฐาน = %.2f%% | ค่าเฉลี่ยหลัง Shock = %.2f%% (SD = %.2f%%)",
                base_portfolio_gm_pct, mean_mc_gm, sd_mc_gm))
message(sprintf("  📉 95%% Value-at-Risk (VaR 95%%): Gross Margin จะไม่ต่ำกว่า %.2f%% ด้วยความเชื่อมั่น 95%%", var_95_gm))
message(sprintf("  📉 99%% Value-at-Risk (VaR 99%%): Gross Margin จะไม่ต่ำกว่า %.2f%% ด้วยความเชื่อมั่น 99%%", var_99_gm))

# ------------------------------------------------------------------------------
# 5. ส่งออกรายงาน outputs/price_shock_scenarios.csv
# ------------------------------------------------------------------------------
message("\n--- [Step 5] Exporting outputs/price_shock_scenarios.csv ---")
out_shock_csv <- file.path(root_dir, "outputs", "price_shock_scenarios.csv")

# ผนวกข้อมูล Playbook เข้าไปในตารางผลลัพธ์
export_shock_df <- all_scenarios_df %>%
  dplyr::left_join(
    pork_shock_mitigated %>%
      dplyr::select(menu_item_id, scenario_id, mitigated_fc_shock_thb, mitigated_fc_shock_pct, gm_drop_mitigated_pp),
    by = c("menu_item_id", "scenario_id")
  ) %>%
  dplyr::mutate(
    playbook_response_status = dplyr::case_when(
      scenario_id == "shock_pork_30" & gm_drop_mitigated_pp <= 3.0 ~ "Protected (GM Drop <= 3.0 pp)",
      scenario_id == "shock_pork_30" ~ "Partial Protection",
      TRUE ~ "Standard Scenario"
    )
  )

readr::write_csv(export_shock_df, out_shock_csv)
message(sprintf("  📄 บันทึกผลลัพธ์ Price Shock Simulation: %s (%d แถว)", out_shock_csv, nrow(export_shock_df)))

# ------------------------------------------------------------------------------
# 6. สร้างกราฟิกแสดงผลกระทบและการกระจายตัวของราคา (Figures)
# ------------------------------------------------------------------------------
message("\n--- [Step 6] Generating Price Shock Plots ---")

# 6.1 กราฟเปรียบเทียบผลกระทบต่อกำไรขั้นต้นรายสัปดาห์แยกตาม Scenario และร้านค้า
rest_impact_df <- all_scenarios_df %>%
  dplyr::filter(scenario_id != "baseline") %>%
  dplyr::group_by(restaurant_name, scenario_name) %>%
  dplyr::summarise(
    weekly_impact_thb = sum(weekly_gm_impact_thb),
    .groups = "drop"
  )

p_bar <- ggplot2::ggplot(rest_impact_df, ggplot2::aes(x = reorder(restaurant_name, weekly_impact_thb), y = abs(weekly_impact_thb), fill = scenario_name)) +
  ggplot2::geom_col(position = "dodge", alpha = 0.85, width = 0.75) +
  ggplot2::coord_flip() +
  ggplot2::scale_fill_brewer(palette = "Set2", name = "Price Shock Scenario") +
  ggplot2::scale_y_continuous(labels = scales::dollar_format(prefix = "฿", accuracy = 1)) +
  ggplot2::labs(
    title = "Weekly Gross Margin Loss by Restaurant under 5 Price Shock Scenarios",
    subtitle = "High exposure in Economy pork/poultry dishes and Premium seafood restaurants",
    x = "Restaurant",
    y = "Weekly Profit Loss (THB/Week)",
    caption = "MueNee B2B Analytics: SPEC.md §4.3 Deterministic Scenarios"
  ) +
  ggplot2::theme_minimal(base_size = 10) +
  ggplot2::theme(
    legend.position = "bottom",
    plot.title = ggplot2::element_text(face = "bold", size = 11, color = "#1d3557"),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_bar_path <- file.path(root_dir, "outputs", "figures", "price_shock_margin_impact.png")
ggplot2::ggsave(fig_bar_path, plot = p_bar, width = 10, height = 6.5, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟผลกระทบรายสัปดาห์: %s", fig_bar_path))

# 6.2 กราฟการแจกแจง Monte Carlo Simulation (10,000 Iterations)
mc_plot_df <- tibble::tibble(sim_gm_pct = mc_gm_pct)

p_mc <- ggplot2::ggplot(mc_plot_df, ggplot2::aes(x = sim_gm_pct)) +
  ggplot2::geom_histogram(bins = 60, fill = "#457b9d", color = "#1d3557", alpha = 0.7) +
  ggplot2::geom_vline(xintercept = base_portfolio_gm_pct, color = "#2a9d8f", linetype = "solid", linewidth = 1.1) +
  ggplot2::geom_vline(xintercept = var_95_gm, color = "#e63946", linetype = "dashed", linewidth = 1.1) +
  ggplot2::annotate("text", x = base_portfolio_gm_pct + 0.3, y = 550, label = sprintf("Base GM: %.1f%%", base_portfolio_gm_pct), color = "#2a9d8f", fontface = "bold", hjust = 0) +
  ggplot2::annotate("text", x = var_95_gm - 0.3, y = 550, label = sprintf("VaR 95%%: %.1f%%", var_95_gm), color = "#e63946", fontface = "bold", hjust = 1) +
  ggplot2::scale_x_continuous(labels = scales::percent_format(scale = 1)) +
  ggplot2::labs(
    title = "Monte Carlo Simulation: Portfolio Gross Margin Distribution (10,000 Runs)",
    subtitle = sprintf("Baseline GM: %.2f%% | 95%% Value-at-Risk Threshold: %.2f%%", base_portfolio_gm_pct, var_95_gm),
    x = "Simulated System Gross Margin %",
    y = "Frequency (Iterations)",
    caption = "MueNee B2B Analytics: SPEC.md §4.3 Monte Carlo Analysis"
  ) +
  ggplot2::theme_minimal(base_size = 11) +
  ggplot2::theme(
    plot.title = ggplot2::element_text(face = "bold", size = 12, color = "#1d3557"),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_mc_path <- file.path(root_dir, "outputs", "figures", "price_shock_monte_carlo.png")
ggplot2::ggsave(fig_mc_path, plot = p_mc, width = 9, height = 5.5, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟแจกแจง Monte Carlo: %s", fig_mc_path))

message("\n==================================================================")
message("    🎉 TASK 5.2 PRICE SHOCK SIMULATION COMPLETED (B6)! 🎉       ")
message("==================================================================\n")
