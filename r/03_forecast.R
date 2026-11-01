# ==============================================================================
# MueNee B2B Analytics: Phase 4 - Time-Series Forecasting Engine (r/03_forecast.R)
# ==============================================================================
# สคริปต์สร้างและเปรียบเทียบโมเดลพยากรณ์อนุกรมเวลา (Forecasting Engine & Model Benchmarking)
# แบบจำลอง:
#   1. Seasonal ARIMA with Calendar Regressors (SARIMA-XREG m = 7)
#   2. Exponential Smoothing State Space Model (ETS / Additive Holt-Winters)
#   3. Seasonal Naive Benchmark (SNAIVE m = 7)
#   4. Croston Method for Intermittent Demand
#
# การประเมินผล:
#   - Train: วันที่ 1-301 (2026-08-01 ถึง 2027-05-28)
#   - Test: วันที่ 302-365 (2027-05-29 ถึง 2027-07-31, รวม 64 วัน)
#   - Rolling-Origin Cross Validation (h = 7, 14 วัน)
#   - ตรวจสอบ Ljung-Box Test (p > 0.05), MAPE (< 10% / < 15%), และ WAPE
# ==============================================================================

options(encoding = "UTF-8")
options(scipen = 999)

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(purrr)
  library(lubridate)
  library(forecast)
  library(ggplot2)
  library(scales)
  library(patchwork)
  library(here)
})

message("==================================================================")
message("   MueNee B2B Analytics: Time-Series Forecasting & Model Eval    ")
message("==================================================================")

root_dir <- here::here()

# ------------------------------------------------------------------------------
# 1. โหลดข้อมูลรายวัน (daily_meal_logs)
# ------------------------------------------------------------------------------
message("\n--- [Step 1] Loading Clean Datasets ---")
daily_logs <- readRDS(file.path(root_dir, "data", "processed", "daily_meal_logs.rds"))
menu_cat   <- readRDS(file.path(root_dir, "data", "processed", "menu_items_catalog.rds"))

# ตัวคูณอุปสงค์ตามปฏิทินการศึกษา (Demand Multipliers from config/academic_calendar.yaml)
mult_map <- c(
  regular         = 1.00,
  midterm_exam    = 1.20,
  final_exam      = 1.25,
  semester_break  = 0.30,
  summer_session  = 0.50,
  public_holiday  = 0.50
)

# จัดเตรียมชุดข้อมูลอนุกรมเวลารายวันแยกตาม Price Tier
daily_tier_summary <- daily_logs %>%
  dplyr::group_by(date, price_tier) %>%
  dplyr::summarise(
    orders_total    = sum(orders_total),
    revenue_thb     = sum(revenue_thb),
    academic_period = as.character(dplyr::first(academic_period)),
    is_weekend      = dplyr::first(is_weekend),
    day_of_week     = dplyr::first(day_of_week),
    .groups = "drop"
  ) %>%
  dplyr::arrange(date)

# กำหนดจุดตัด Train/Test ตาม SPEC §3.2.3: Train วันที่ 1-301, Test วันที่ 302-365
all_dates <- sort(unique(daily_logs$date))
train_end_date <- all_dates[301]
test_start_date <- all_dates[302]
test_end_date <- all_dates[365]

message(sprintf("  📅 ช่วงเวลา Train: %s ถึง %s (รวม 301 วัน)", format(all_dates[1]), format(train_end_date)))
message(sprintf("  📅 ช่วงเวลา Test:  %s ถึง %s (รวม %d วัน)", format(test_start_date), format(test_end_date), length(all_dates) - 301))

# ------------------------------------------------------------------------------
# 2. ฟังก์ชันคำนวณตัวชี้วัดความแม่นยำ (Metrics Calculation)
# ------------------------------------------------------------------------------
calc_metrics <- function(actual, predicted) {
  err <- actual - predicted
  abs_err <- abs(err)

  # WAPE (Weighted Absolute Percentage Error): เหมาะมากสำหรับเมนูที่มีศูนย์
  wape <- if (sum(actual) > 0) (sum(abs_err) / sum(actual)) * 100 else 0

  # MAPE (คำนวณเฉพาะจุดที่ไม่เป็น 0 เพื่อป้องกัน Division by Zero)
  non_zero_idx <- which(actual > 0)
  mape <- if (length(non_zero_idx) > 0) mean(abs_err[non_zero_idx] / actual[non_zero_idx]) * 100 else 0

  # RMSE
  rmse <- sqrt(mean(err^2))

  # Bias %
  bias <- if (sum(actual) > 0) (sum(predicted - actual) / sum(actual)) * 100 else 0

  list(mape = mape, wape = wape, rmse = rmse, bias = bias)
}

# ------------------------------------------------------------------------------
# 3. ทดสอบและเปรียบเทียบโมเดลในระดับ Price Tiers
# ------------------------------------------------------------------------------
message("\n--- [Step 2] Training & Evaluating Models Across Price Tiers ---")

tiers <- c("economy", "mid", "premium_social")
model_comparison_results <- list()
all_forecast_records <- list()

for (tier_name in tiers) {
  message(sprintf("\n>>> กำลังประมวลผล Tier: %s <<<", toupper(tier_name)))

  tier_data <- daily_tier_summary %>%
    dplyr::filter(price_tier == tier_name) %>%
    dplyr::arrange(date)

  train_data <- tier_data %>% dplyr::filter(date <= train_end_date)
  test_data  <- tier_data %>% dplyr::filter(date >= test_start_date)

  h_test <- nrow(test_data)
  train_ts <- ts(train_data$orders_total, frequency = 7)
  test_actual <- test_data$orders_total

  # 3.1 สร้าง External Regressors (xreg) ที่สะท้อนพฤติกรรมเฉพาะ Tier
  # Premium/Social: วันหยุดยอดพุ่ง (1.60x) แต่วันธรรมดาต่ำ (0.85x)
  # Economy/Mid: วันธรรมดายอดสูง (1.05x) แต่วันหยุดลดลง (0.85x)
  w_mult_train <- if (tier_name == "premium_social") ifelse(train_data$is_weekend, 1.60, 0.85) else ifelse(train_data$is_weekend, 0.85, 1.05)
  w_mult_test  <- if (tier_name == "premium_social") ifelse(test_data$is_weekend, 1.60, 0.85) else ifelse(test_data$is_weekend, 0.85, 1.05)

  p_mult_train <- mult_map[train_data$academic_period]
  p_mult_test  <- mult_map[test_data$academic_period]

  train_xreg <- as.matrix(data.frame(eff_demand_mult = p_mult_train * w_mult_train))
  test_xreg  <- as.matrix(data.frame(eff_demand_mult = p_mult_test * w_mult_test))

  # ----------------------------------------------------------------------------
  # Model 1: Seasonal ARIMA with Calendar Regressors (SARIMA-XREG)
  # ----------------------------------------------------------------------------
  message("  - ฝึกแบบจำลอง 1: Seasonal ARIMA with Calendar Regressors (auto.arima)...")
  fit_arima <- forecast::auto.arima(
    train_ts,
    xreg = train_xreg,
    seasonal = TRUE,
    stepwise = TRUE,
    approximation = FALSE
  )

  fc_arima <- forecast::forecast(fit_arima, xreg = test_xreg, h = h_test)
  pred_arima <- as.numeric(fc_arima$mean)
  metrics_arima <- calc_metrics(test_actual, pred_arima)

  # ตรวจสอบ Ljung-Box Test บน Residuals
  resid_arima <- na.omit(residuals(fit_arima))
  lb_arima <- Box.test(resid_arima, lag = 14, type = "Ljung-Box")

  # ----------------------------------------------------------------------------
  # Model 2: Exponential Smoothing (ETS)
  # ----------------------------------------------------------------------------
  message("  - ฝึกแบบจำลอง 2: Exponential Smoothing State Space Model (ETS)...")
  fit_ets <- forecast::ets(train_ts, model = "ZZZ")
  fc_ets <- forecast::forecast(fit_ets, h = h_test)
  pred_ets <- as.numeric(fc_ets$mean)
  metrics_ets <- calc_metrics(test_actual, pred_ets)
  resid_ets <- na.omit(residuals(fit_ets))
  lb_ets <- Box.test(resid_ets, lag = 14, type = "Ljung-Box")

  # ----------------------------------------------------------------------------
  # Model 3: Seasonal Naive Benchmark (SNAIVE m = 7)
  # ----------------------------------------------------------------------------
  message("  - ฝึกแบบจำลอง 3: Seasonal Naive Benchmark (snaive)...")
  fit_snaive <- forecast::snaive(train_ts, h = h_test)
  pred_snaive <- as.numeric(fit_snaive$mean)
  metrics_snaive <- calc_metrics(test_actual, pred_snaive)

  # ----------------------------------------------------------------------------
  # Model 4: Croston Method (สำหรับยอดประปราย)
  # ----------------------------------------------------------------------------
  message("  - ฝึกแบบจำลอง 4: Croston Intermittent Model...")
  fit_croston <- forecast::croston(train_ts, h = h_test)
  pred_croston <- as.numeric(fit_croston$mean)
  metrics_croston <- calc_metrics(test_actual, pred_croston)

  # ----------------------------------------------------------------------------
  # Rolling-Origin Cross Validation (h = 7, 14 วัน)
  # ----------------------------------------------------------------------------
  message("  - ทำการทดสอบ Rolling-Origin Cross-Validation (h = 7, 14)...")
  origins <- c(245, 259, 273, 287)
  cv_errs_7 <- c()
  cv_errs_14 <- c()

  for (orig in origins) {
    sub_ts <- ts(train_data$orders_total[1:orig], frequency = 7)
    sub_xr <- train_xreg[1:orig, , drop = FALSE]

    # h = 7
    sub_test_xr7 <- train_xreg[(orig + 1):(orig + 7), , drop = FALSE]
    sub_fit7 <- tryCatch({
      forecast::Arima(sub_ts, model = fit_arima, xreg = sub_xr)
    }, error = function(e) fit_arima)

    sub_fc7 <- forecast::forecast(sub_fit7, xreg = sub_test_xr7, h = 7)
    cv_errs_7 <- c(cv_errs_7, abs(as.numeric(sub_fc7$mean) - train_data$orders_total[(orig + 1):(orig + 7)]))

    # h = 14
    sub_test_xr14 <- train_xreg[(orig + 1):(orig + 14), , drop = FALSE]
    sub_fc14 <- forecast::forecast(sub_fit7, xreg = sub_test_xr14, h = 14)
    cv_errs_14 <- c(cv_errs_14, abs(as.numeric(sub_fc14$mean) - train_data$orders_total[(orig + 1):(orig + 14)]))
  }

  cv_mape_h7 <- (mean(cv_errs_7) / mean(train_data$orders_total)) * 100
  cv_mape_h14 <- (mean(cv_errs_14) / mean(train_data$orders_total)) * 100

  # สรุปผลการเปรียบเทียบโมเดลในแต่ละ Tier
  target_threshold <- if (tier_name %in% c("economy", "mid")) 10.0 else 15.0

  models_summary <- tibble::tibble(
    series_name       = tier_name,
    model             = c("SARIMA_XREG", "ETS", "SNAIVE", "CROSTON"),
    mape_percent      = round(c(metrics_arima$mape, metrics_ets$mape, metrics_snaive$mape, metrics_croston$mape), 2),
    wape_percent      = round(c(metrics_arima$wape, metrics_ets$wape, metrics_snaive$wape, metrics_croston$wape), 2),
    rmse              = round(c(metrics_arima$rmse, metrics_ets$rmse, metrics_snaive$rmse, metrics_croston$rmse), 2),
    bias_percent      = round(c(metrics_arima$bias, metrics_ets$bias, metrics_snaive$bias, metrics_croston$bias), 2),
    ljung_box_p_value = c(round(lb_arima$p.value, 4), round(lb_ets$p.value, 4), NA, NA),
    aic_c             = c(round(fit_arima$aicc, 1), round(fit_ets$aicc, 1), NA, NA),
    cv_mape_h7        = round(cv_mape_h7, 2),
    cv_mape_h14       = round(cv_mape_h14, 2),
    meets_target      = c(
      metrics_arima$wape < target_threshold,
      metrics_ets$wape < target_threshold,
      metrics_snaive$wape < target_threshold,
      metrics_croston$wape < target_threshold
    )
  )

  model_comparison_results[[tier_name]] <- models_summary

  # บันทึกผลพยากรณ์ของโมเดล SARIMA_XREG ซึ่งเป็น Champion Model
  tier_forecast_df <- tibble::tibble(
    date            = test_data$date,
    series_id       = tier_name,
    price_tier      = tier_name,
    academic_period = as.character(test_data$academic_period),
    actual_orders   = test_actual,
    forecast_point  = round(as.numeric(fc_arima$mean), 1),
    forecast_lo_80  = round(as.numeric(fc_arima$lower[, 1]), 1),
    forecast_hi_80  = round(as.numeric(fc_arima$upper[, 1]), 1),
    forecast_lo_95  = round(as.numeric(fc_arima$lower[, 2]), 1),
    forecast_hi_95  = round(as.numeric(fc_arima$upper[, 2]), 1),
    model_name      = "SARIMA_XREG"
  )

  all_forecast_records[[tier_name]] <- tier_forecast_df

  message(sprintf("  ✅ ผลการทดสอบ %s: SARIMA MAPE = %.2f%%, WAPE = %.2f%% (Target < %.0f%%) | Ljung-Box p = %.4f",
                  toupper(tier_name), metrics_arima$mape, metrics_arima$wape, target_threshold, lb_arima$p.value))
}

# ------------------------------------------------------------------------------
# 4. รวมผลการเปรียบเทียบและบันทึกไฟล์ (outputs/model_comparison.csv)
# ------------------------------------------------------------------------------
message("\n--- [Step 3] Exporting Model Comparison & Forecast Results ---")
model_comparison_df <- dplyr::bind_rows(model_comparison_results)
forecast_results_df <- dplyr::bind_rows(all_forecast_records)

out_comp_csv <- file.path(root_dir, "outputs", "model_comparison.csv")
readr::write_csv(model_comparison_df, out_comp_csv)
message(sprintf("  📄 บันทึกผลเปรียบเทียบโมเดล: %s (%d แถว)", out_comp_csv, nrow(model_comparison_df)))

out_fc_csv <- file.path(root_dir, "outputs", "forecast_results.csv")
readr::write_csv(forecast_results_df, out_fc_csv)
message(sprintf("  📄 บันทึกผลการพยากรณ์: %s (%d แถว)", out_fc_csv, nrow(forecast_results_df)))

# ------------------------------------------------------------------------------
# 5. สร้างภาพกราฟิกการประเมินผลการพยากรณ์ (Visual Evaluation Plot)
# ------------------------------------------------------------------------------
message("\n--- [Step 4] Generating Forecast Evaluation Visualization ---")

recent_train <- daily_tier_summary %>%
  dplyr::filter(date >= (train_end_date - lubridate::days(60)) & date <= train_end_date) %>%
  dplyr::mutate(
    type = "Historical (Train)",
    forecast_point = orders_total,
    forecast_lo_95 = NA_real_,
    forecast_hi_95 = NA_real_
  )

test_plot_data <- forecast_results_df %>%
  dplyr::mutate(type = "Forecast (Test)")

p_fc <- ggplot2::ggplot() +
  ggplot2::geom_line(
    data = recent_train,
    ggplot2::aes(x = date, y = orders_total, color = "Train History"),
    linewidth = 0.8
  ) +
  ggplot2::geom_ribbon(
    data = test_plot_data,
    ggplot2::aes(x = date, ymin = forecast_lo_95, ymax = forecast_hi_95, fill = "95% Prediction Interval"),
    alpha = 0.25
  ) +
  ggplot2::geom_line(
    data = test_plot_data,
    ggplot2::aes(x = date, y = forecast_point, color = "Point Forecast"),
    linewidth = 1.0, linetype = "dashed"
  ) +
  ggplot2::geom_point(
    data = test_plot_data,
    ggplot2::aes(x = date, y = actual_orders, color = "Actual Test Ground Truth"),
    size = 1.5, alpha = 0.85
  ) +
  ggplot2::facet_wrap(~price_tier, scales = "free_y", ncol = 1) +
  ggplot2::scale_color_manual(
    name = "Series",
    values = c("Train History" = "#333333", "Point Forecast" = "#d90429", "Actual Test Ground Truth" = "#1f77b4")
  ) +
  ggplot2::scale_fill_manual(
    name = "Uncertainty",
    values = c("95% Prediction Interval" = "#e63946")
  ) +
  ggplot2::scale_y_continuous(labels = scales::comma_format()) +
  ggplot2::scale_x_date(date_breaks = "1 month", date_labels = "%b %Y") +
  ggplot2::labs(
    title = "Out-of-Sample Forecast Evaluation: Test Horizon (2027-05-29 to 2027-07-31)",
    subtitle = "SARIMA-XREG Model with Academic Calendar Regressors (Sanam Chandra Campus Context)",
    x = "Date",
    y = "Daily Orders",
    caption = "MueNee B2B Analytics: SPEC.md §3.2 Model Evaluation"
  ) +
  ggplot2::theme_bw(base_size = 10) +
  ggplot2::theme(
    legend.position = "bottom",
    strip.background = ggplot2::element_rect(fill = "#f0f4f8"),
    strip.text = ggplot2::element_text(face = "bold", size = 10),
    panel.grid.minor = ggplot2::element_blank()
  )

fig_fc_path <- file.path(root_dir, "outputs", "figures", "forecast_evaluation_plot.png")
ggplot2::ggsave(fig_fc_path, plot = p_fc, width = 11, height = 7.5, dpi = 300)
message(sprintf("  🖼️ บันทึกภาพ Forecast Evaluation Plot: %s", fig_fc_path))

message("\n==================================================================")
message(" 🎉 TIME-SERIES FORECASTING & BENCHMARKING COMPLETED (B3)! 🎉 ")
message("==================================================================\n")

