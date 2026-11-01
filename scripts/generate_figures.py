#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Module A analytical figures in outputs/figures/
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.makedirs("outputs/figures", exist_ok=True)
daily_df = pd.read_csv("data/raw/daily_meal_logs.csv")

# 1. Time Series ยอดสั่งซื้อรายวันแยกตาม 3 Price Tiers
daily_df["date_dt"] = pd.to_datetime(daily_df["date"])
tier_daily = daily_df.groupby(["date_dt", "price_tier"])["orders_total"].sum().unstack()

plt.figure(figsize=(14, 5))
plt.plot(tier_daily.index, tier_daily["economy"], label="Economy (40-70 THB)", color="#1f77b4", linewidth=1.5)
plt.plot(tier_daily.index, tier_daily["mid"], label="Mid Tier (80-180 THB)", color="#ff7f0e", linewidth=1.5)
plt.plot(tier_daily.index, tier_daily["premium_social"], label="Premium/Social (199-800 THB)", color="#2ca02c", linewidth=1.5)
plt.title("Daily Order Volume by Price Tier (Sanam Chandra Campus Context 2026-2027)", fontsize=13, fontweight="bold")
plt.xlabel("Date", fontsize=11)
plt.ylabel("Daily Orders", fontsize=11)
plt.legend(frameon=True, facecolor="white", edgecolor="none")
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("outputs/figures/01_daily_orders_by_tier.png", dpi=200)
plt.close()
print("Saved outputs/figures/01_daily_orders_by_tier.png")

# 2. Heatmap มื้ออาหาร (Lunch, Dinner, Late Night) x ช่วงปฏิทิน
period_meal = daily_df.groupby("academic_period")[["orders_lunch", "orders_dinner", "orders_late_night"]].mean()
plt.figure(figsize=(9, 4.5))
sns.heatmap(period_meal.T, annot=True, fmt=".1f", cmap="YlOrRd", cbar_kws={'label': 'Avg Orders per Menu Item'})
plt.title("Meal Demand Intensity across Academic Periods (Midterm/Final Late Night Spikes)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig("outputs/figures/02_meal_time_heatmap.png", dpi=200)
plt.close()
print("Saved outputs/figures/02_meal_time_heatmap.png")

# 3. Bar Chart สัดส่วนช่องทางสั่งซื้อ (Recommendation, Scan, Manual)
channel_totals = daily_df[["src_recommendation", "src_food_scan", "src_manual"]].sum()
labels = ["Recommendation\n(Allergen/Diet Filtered)", "Food Scan\n(Nutrition Verified)", "Manual Search\n(Dine-in/Walk-in)"]
colors = ["#2b5c8f", "#e26d5c", "#7209b7"]

plt.figure(figsize=(8, 4.8))
bars = plt.bar(labels, channel_totals.values, color=colors, width=0.55)
plt.title("Annual Order Distribution by Acquisition Channel", fontsize=12, fontweight="bold")
plt.ylabel("Total Orders", fontsize=11)
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2.0, yval + 5000, f"{int(yval):,} ({yval/channel_totals.sum()*100:.1f}%)", ha="center", va="bottom", fontsize=10, fontweight="bold")
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("outputs/figures/03_channel_distribution.png", dpi=200)
plt.close()
print("Saved outputs/figures/03_channel_distribution.png")

print("All figures successfully created.")

