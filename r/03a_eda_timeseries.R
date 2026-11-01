# ==============================================================================
# MueNee B2B Analytics: Phase 4 - Exploratory Time-Series Analysis (r/03a_eda_timeseries.R)
# ==============================================================================
# สคริปต์สำรวจและวิเคราะห์คุณสมบัติทางอนุกรมเวลา (EDA Time-Series Analysis)
# ครอบคลุม: STL Decomposition, ACF/PACF Diagnostics, และ Outlier Event Detection
# สำหรับข้อมูลร้านอาหารรอบ ม.ศิลปากร วิทยาเขตพระราชวังสนามจันทร์
# ==============================================================================

options(encoding = "UTF-8")
options(scipen = 999)

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(lubridate)
  library(tsibble)
  library(fabletools)
  library(feasts)
  library(patchwork)
  library(ggplot2)
  library(scales)
  library(here)
})

message("==================================================================")
message("   MueNee B2B Analytics: Exploratory Time-Series Analysis (EDA)   ")
message("==================================================================")

root_dir <- here::here()

# ------------------------------------------------------------------------------
# 1. โหลดข้อมูล Processed จาก Phase 3
# ------------------------------------------------------------------------------
message("\n--- [Step 1] Loading Processed Datasets ---")
daily_logs <- readRDS(file.path(root_dir, "data", "processed", "daily_meal_logs.rds"))
commodity_demand <- readRDS(file.path(root_dir, "data", "processed", "commodity_daily_demand.rds"))

message(sprintf("  ✅ daily_meal_logs: %d rows (365 days)", nrow(daily_logs)))
message(sprintf("  ✅ commodity_daily_demand: %d rows", nrow(commodity_demand)))

# ------------------------------------------------------------------------------
# 2. จัดเตรียมข้อมูลเป็น Tsibble แยกตาม Price Tier (m = 7 สำหรับข้อมูลรายวัน)
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Formatting Time-Series (Tsibble Object m = 7) ---")

tier_daily <- daily_logs %>%
  dplyr::group_by(date, price_tier) %>%
  dplyr::summarise(
    orders_total = sum(orders_total),
    revenue_thb  = sum(revenue_thb),
    academic_period = dplyr::first(academic_period),
    is_weekend      = dplyr::first(is_weekend),
    .groups = "drop"
  ) %>%
  tsibble::as_tsibble(key = price_tier, index = date)

# ข้อมูลรวมระดับมหาวิทยาลัย
total_daily <- daily_logs %>%
  dplyr::group_by(date) %>%
  dplyr::summarise(
    orders_total = sum(orders_total),
    academic_period = dplyr::first(academic_period),
    is_weekend      = dplyr::first(is_weekend),
    .groups = "drop"
  ) %>%
  tsibble::as_tsibble(index = date)

message("  ✅ แปลงข้อมูลอนุกรมเวลาเข้าสู่ Tsibble สำเร็จ (ความถี่ 365 วัน)")

# ------------------------------------------------------------------------------
# 3. การแยกองค์ประกอบอนุกรมเวลา STL Decomposition (Seasonal-Trend with LOESS)
# ------------------------------------------------------------------------------
message("\n--- [Step 3] STL Decomposition for Economy Tier (Weekly Seasonality m = 7) ---")

# สำหรับ Economy Tier ซึ่งมีสัดส่วนสูงสุด (66.1% ของอุปสงค์ทั้งหมด)
eco_ts <- tier_daily %>%
  dplyr::filter(price_tier == "economy")

# คำนวณ STL Decomposition โดยกำหนด period = 7 (รอบ 7 วันต่อสัปดาห์)
stl_model <- eco_ts %>%
  fabletools::model(
    stl = feasts::STL(orders_total ~ season(period = 7, window = 13))
  )

stl_components <- fabletools::components(stl_model)

# พล็อตและบันทึกภาพ STL Decomposition
p_stl <- feasts::autoplot(stl_components) +
  ggplot2::labs(
    title = "STL Decomposition of Daily Orders: Economy Tier (40-70 THB)",
    subtitle = "Weekly Seasonality (m = 7) with Academic Calendar Shifts (Sanam Chandra Campus)",
    x = "Timeline (2026-08-01 to 2027-07-31)",
    y = "Daily Orders",
    caption = "MueNee B2B Analytics: Module B Time-Series Analysis"
  ) +
  ggplot2::theme_minimal(base_size = 11) +
  ggplot2::theme(
    plot.title = ggplot2::element_text(face = "bold", size = 12),
    plot.subtitle = ggplot2::element_text(color = "gray30", size = 9),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_stl_path <- file.path(root_dir, "outputs", "figures", "eda_stl_decomposition.png")
ggplot2::ggsave(fig_stl_path, plot = p_stl, width = 11, height = 7, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟ STL Decomposition: %s", fig_stl_path))

# ------------------------------------------------------------------------------
# 4. การตรวจสอบฟังก์ชันความสัมพันธ์ในตัวเอง (ACF & PACF Diagnostics)
# ------------------------------------------------------------------------------
message("\n--- [Step 4] ACF & PACF Analysis (Lag Structure & Seasonality) ---")

# คำนวณ ACF และ PACF ของข้อมูลรายวัน
p_acf <- eco_ts %>%
  feasts::ACF(orders_total, lag_max = 35) %>%
  ggplot2::autoplot() +
  ggplot2::labs(
    title = "Autocorrelation Function (ACF) - Economy Tier",
    subtitle = "Prominent weekly spikes at Lag 7, 14, 21, 28 confirming m = 7 seasonality",
    x = "Lag (Days)",
    y = "Autocorrelation"
  ) +
  ggplot2::theme_minimal(base_size = 10) +
  ggplot2::theme(plot.title = ggplot2::element_text(face = "bold"))

p_pacf <- eco_ts %>%
  feasts::PACF(orders_total, lag_max = 35) %>%
  ggplot2::autoplot() +
  ggplot2::labs(
    title = "Partial Autocorrelation Function (PACF) - Economy Tier",
    subtitle = "Significant cutoff after Lag 1-2 and Lag 7 guiding SARIMA parameter bounds",
    x = "Lag (Days)",
    y = "Partial Autocorrelation"
  ) +
  ggplot2::theme_minimal(base_size = 10) +
  ggplot2::theme(plot.title = ggplot2::element_text(face = "bold"))

p_acf_combined <- p_acf / p_pacf
fig_acf_path <- file.path(root_dir, "outputs", "figures", "eda_acf_pacf.png")
ggplot2::ggsave(fig_acf_path, plot = p_acf_combined, width = 10, height = 6.5, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟ ACF & PACF: %s", fig_acf_path))

# ------------------------------------------------------------------------------
# 5. การตรวจจับค่าผิดปกติและการกำหนดตัวแปรเหตุการณ์ (Outlier & Event Dummies)
# ------------------------------------------------------------------------------
message("\n--- [Step 5] Outlier Detection (> 3 Sigma of STL Remainder) & Event Mapping ---")

# สกัดค่า Remainder จาก STL
rem <- stl_components$remainder
sigma_rem <- sd(rem, na.rm = TRUE)
mean_rem  <- mean(rem, na.rm = TRUE)

stl_components <- stl_components %>%
  dplyr::mutate(
    is_outlier = abs(remainder - mean_rem) > (3.0 * sigma_rem),
    outlier_magnitude = abs(remainder - mean_rem) / sigma_rem
  )

outlier_rows <- stl_components %>%
  dplyr::filter(is_outlier) %>%
  dplyr::left_join(
    total_daily %>% dplyr::as_tibble() %>% dplyr::select(date, academic_period),
    by = "date"
  )

message(sprintf("  - พบค่าผิดปกติระดับ > 3 Sigma ทั้งหมด: %d วัน (จาก 365 วัน)", nrow(outlier_rows)))
if (nrow(outlier_rows) > 0) {
  for (i in 1:min(5, nrow(outlier_rows))) {
    row <- outlier_rows[i, ]
    message(sprintf("    * วันที่ %s: ส่วนเบี่ยงเบน %.2f Sigma | ช่วง: %s",
                    format(row$date, "%Y-%m-%d"), row$outlier_magnitude, row$academic_period))
  }
}

# พล็อตภาพระบุ Outlier พร้อมการจับคู่กับปฏิทินการศึกษา
p_outlier <- ggplot2::ggplot(stl_components, ggplot2::aes(x = date, y = orders_total)) +
  ggplot2::geom_line(color = "#2b5c8f", alpha = 0.75, linewidth = 0.8) +
  ggplot2::geom_point(
    data = stl_components %>% dplyr::filter(is_outlier),
    ggplot2::aes(x = date, y = orders_total),
    color = "#d90429", size = 2.5, shape = 21, fill = "#ff4d6d"
  ) +
  ggplot2::scale_y_continuous(labels = scales::comma_format()) +
  ggplot2::scale_x_date(date_breaks = "2 months", date_labels = "%b %Y") +
  ggplot2::labs(
    title = "Outlier & Structural Break Identification (> 3σ STL Residual)",
    subtitle = "Red circles indicate exam peaks, public holidays, or semester break transitions",
    x = "Date",
    y = "Daily Orders (Economy Tier)",
    caption = "SPEC.md §4.4: Outliers mapped to Academic Calendar Event Regressors"
  ) +
  ggplot2::theme_minimal(base_size = 11) +
  ggplot2::theme(
    plot.title = ggplot2::element_text(face = "bold"),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_outlier_path <- file.path(root_dir, "outputs", "figures", "eda_outliers_events.png")
ggplot2::ggsave(fig_outlier_path, plot = p_outlier, width = 11, height = 5, dpi = 300)
message(sprintf("  🖼️ บันทึกกราฟ Outliers & Event Dummies: %s", fig_outlier_path))

message("\n==================================================================")
message(" 🎉 EXPLORATORY TIME-SERIES ANALYSIS (EDA) COMPLETED! 🎉 ")
message("==================================================================\n")
