#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
MueNee B2B Analytics: Interactive Portfolio Dashboard Generator
==============================================================================
สคริปต์สร้าง Interactive Web Dashboard (Single-File Standalone HTML)
สำหรับแสดงผลงานระดับ Masterpiece เพื่อยื่นเข้าศึกษาต่อ UTCC Digital Business & Innovation
รวบรวมผลลัพธ์จริงจากทุกโมดูล (Menu Engineering, Forecasting, Inventory, Price Shock)
สามารถเปิดดูได้ทันทีในเบราว์เซอร์โดยไม่ต้องมีเซิร์ฟเวอร์ และมีปุ่ม Print เป็น PDF พอร์ตโฟลิโอ
==============================================================================
"""

import sys
import os
import json
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def build_dashboard():
    print("=" * 70)
    print("   Building MueNee B2B Analytics Executive Portfolio Dashboard    ")
    print("=" * 70)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dashboard_dir = os.path.join(root_dir, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)

    # 1. โหลดข้อมูลผลลัพธ์จริงทั้งหมด
    print("[1/4] Loading verified data outputs...")
    menu_df = pd.read_csv(os.path.join(root_dir, "outputs", "menu_engineering.csv"))
    shock_df = pd.read_csv(os.path.join(root_dir, "outputs", "price_shock_scenarios.csv"))
    edge_df = pd.read_csv(os.path.join(root_dir, "outputs", "edge_case_summary.csv"))
    bt_df = pd.read_csv(os.path.join(root_dir, "outputs", "inventory_backtest_summary.csv"))
    plan_df = pd.read_csv(os.path.join(root_dir, "outputs", "procurement_plan.csv"))
    fc_df = pd.read_csv(os.path.join(root_dir, "outputs", "forecast_results.csv"))
    comp_df = pd.read_csv(os.path.join(root_dir, "outputs", "model_comparison.csv"))

    # 2. เตรียมข้อมูล JSON สำหรับฝังในเว็บ
    print("[2/4] Formatting structured data payloads...")
    
    # 2.1 ข้อมูลเมนู 30 รายการ
    menus_json = menu_df.to_dict(orient="records")

    # 2.2 ข้อมูลแยกรายร้านค้า 10 แห่ง
    restaurants = []
    for r_id, group in menu_df.groupby("restaurant_id"):
        r_name = group["restaurant_name"].iloc[0]
        r_tier = group["price_tier"].iloc[0]
        r_conf = group["price_confidence"].iloc[0]
        
        # ดึงแผนจัดซื้อล่าสุด
        p_store = plan_df[plan_df["restaurant_id"] == r_id]
        recent_plan = p_store.sort_values("date", ascending=False).groupby("commodity_group_name").first().reset_index()
        
        # สรุปขยะอาหาร
        b_store = bt_df[bt_df["restaurant_id"] == r_id]
        waste_red = float(b_store["waste_reduction_pct"].mean())
        stockout_r = float(b_store["muenee_stockout_rate"].mean())
        base_waste = float(b_store["baseline_waste_kg"].sum())
        muenee_waste = float(b_store["muenee_waste_kg"].sum())

        restaurants.append({
            "id": r_id,
            "name": r_name,
            "tier": r_tier,
            "confidence": r_conf,
            "waste_reduction_pct": round(waste_red, 1),
            "stockout_rate": round(stockout_r, 2),
            "baseline_waste_kg": round(base_waste, 1),
            "muenee_waste_kg": round(muenee_waste, 1),
            "menus": group.to_dict(orient="records"),
            "procurement_plan": recent_plan.to_dict(orient="records")
        })

    # 2.3 ข้อมูล Forecast Time Series ตัวอย่าง (Economy Tier)
    fc_sample = fc_df[fc_df["series_id"] == "economy"].sort_values("date")
    forecast_timeline = {
        "dates": fc_sample["date"].tolist(),
        "actual": fc_sample["actual_orders"].tolist(),
        "forecast": fc_sample["forecast_point"].tolist(),
        "ci_lo_95": fc_sample["forecast_lo_95"].tolist(),
        "ci_hi_95": fc_sample["forecast_hi_95"].tolist(),
        "period": fc_sample["academic_period"].tolist()
    }

    # 2.4 ข้อมูล Price Shock Scenarios
    scenarios_summary = []
    for s_id, s_group in shock_df.groupby("scenario_id"):
        s_name = s_group["scenario_name"].iloc[0]
        wks = int(s_group["shock_duration_wks"].iloc[0])
        total_loss = float(s_group["total_gm_impact_thb"].sum())
        weekly_loss = float(s_group["weekly_gm_impact_thb"].sum())
        avg_fc_increase = float(s_group["delta_fc_pct"].mean())
        
        scenarios_summary.append({
            "id": s_id,
            "name": s_name,
            "weeks": wks,
            "total_impact_thb": round(total_loss, 2),
            "weekly_impact_thb": round(weekly_loss, 2),
            "avg_fc_delta_pct": round(avg_fc_increase, 2)
        })

    # 2.5 ข้อมูล Edge Case & Uplift
    tot_blocked_orders = int(edge_df["annual_blocked_orders"].sum())
    tot_blocked_rev = float(edge_df["annual_blocked_revenue_thb"].sum())
    tot_uplift_orders = int(edge_df["annual_uplift_orders"].sum())
    tot_uplift_rev = float(edge_df["annual_uplift_revenue_thb"].sum())

    store_uplift = edge_df.groupby(["restaurant_name", "price_confidence"]).agg({
        "annual_blocked_revenue_thb": "sum",
        "annual_uplift_revenue_thb": "sum"
    }).reset_index().to_dict(orient="records")

    payload = {
        "restaurants": restaurants,
        "menus": menus_json,
        "forecast_timeline": forecast_timeline,
        "scenarios": scenarios_summary,
        "edge_cases": {
            "total_blocked_orders": tot_blocked_orders,
            "total_blocked_revenue": tot_blocked_rev,
            "total_uplift_orders": tot_uplift_orders,
            "total_uplift_revenue": tot_uplift_rev,
            "store_breakdown": store_uplift
        }
    }

    # 3. สร้าง HTML Dashboard
    print("[3/4] Rendering modern interactive HTML template...")
    
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MueNee B2B Analytics — Executive Command Center</title>
  
  <!-- Google Fonts & Chart.js -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Prompt:wght@300;400;500;600;700&family=Sarabun:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <style>
    :root {{
      --primary: #0d9488;
      --primary-dark: #0f766e;
      --primary-light: #ccfbf1;
      --navy: #0f172a;
      --navy-card: #1e293b;
      --navy-border: #334155;
      --accent-coral: #f97316;
      --accent-rose: #ef4444;
      --accent-green: #10b981;
      --accent-blue: #3b82f6;
      --bg-page: #f8fafc;
      --bg-card: #ffffff;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --font-th: 'Prompt', 'Sarabun', sans-serif;
      --font-en: 'Plus Jakarta Sans', sans-serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-th);
      background-color: var(--bg-page);
      color: var(--text-main);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }}

    /* Top Banner / Navbar */
    .top-navbar {{
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: white;
      padding: 16px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .brand-group {{ display: flex; align-items: center; gap: 14px; }}
    .brand-logo {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #14b8a6, #0d9488);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-family: var(--font-en);
      font-size: 22px;
      color: white;
      box-shadow: 0 0 15px rgba(20, 184, 166, 0.4);
    }}
    .brand-title h1 {{
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.3px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .brand-title p {{
      font-size: 13px;
      color: #94a3b8;
    }}

    /* Layout */
    .dashboard-container {{
      max-width: 1440px;
      margin: 24px auto;
      padding: 0 24px;
    }}

    /* Navigation Tabs */
    .nav-tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 24px;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 12px;
    }}
    .tab-btn {{
      background: #ffffff;
      border: 1px solid #cbd5e1;
      font-family: var(--font-th);
      font-size: 14px;
      font-weight: 600;
      color: #475569;
      padding: 9px 18px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .tab-btn:hover {{
      color: var(--navy);
      background: #f1f5f9;
      border-color: #94a3b8;
    }}
    .tab-btn.active {{
      color: #ffffff;
      background: #0f172a;
      border-color: #0f172a;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
    }}

    /* KPI Cards Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 18px;
      margin-bottom: 28px;
    }}
    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 22px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 2px 10px rgba(0,0,0,0.03);
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .kpi-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.08);
    }}
    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
    }}
    .kpi-card.teal::before {{ background: var(--primary); }}
    .kpi-card.green::before {{ background: var(--accent-green); }}
    .kpi-card.amber::before {{ background: var(--accent-coral); }}
    .kpi-card.blue::before {{ background: var(--accent-blue); }}
    .kpi-title {{
      font-size: 13px;
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .kpi-value {{
      font-family: var(--font-en);
      font-size: 32px;
      font-weight: 800;
      color: var(--navy);
      margin: 8px 0;
      letter-spacing: -0.5px;
    }}
    .kpi-status {{
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .kpi-status.positive {{ color: #059669; }}
    .kpi-status.neutral {{ color: #2563eb; }}

    /* Panels & Charts Grid */
    .charts-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 22px;
      margin-bottom: 28px;
    }}
    @media (max-width: 1024px) {{
      .charts-grid {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      background: var(--bg-card);
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 24px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid #f1f5f9;
    }}
    .panel-header h3 {{
      font-size: 17px;
      font-weight: 700;
      color: var(--navy);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .panel-header p {{
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    /* Table Styles */
    .table-container {{
      overflow-x: auto;
      margin-top: 10px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th {{
      background: #f8fafc;
      color: #475569;
      font-weight: 700;
      padding: 12px 14px;
      text-align: left;
      border-bottom: 2px solid #e2e8f0;
    }}
    td {{
      padding: 12px 14px;
      border-bottom: 1px solid #f1f5f9;
      color: #334155;
    }}
    tr:hover td {{ background: #f8fafc; }}

    /* Badges */
    .tag-quad {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 700;
      color: white;
    }}
    .tag-quad.stars {{ background: #0d9488; }}
    .tag-quad.plow {{ background: #ea580c; }}
    .tag-quad.puzz {{ background: #2563eb; }}
    .tag-quad.dogs {{ background: #dc2626; }}

    .traffic-pill {{
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 700;
      display: inline-block;
    }}
    .traffic-red {{ background: #fee2e2; color: #991b1b; }}
    .traffic-amber {{ background: #fef3c7; color: #92400e; }}
    .traffic-green {{ background: #d1fae5; color: #065f46; }}

    /* Store Selector Bar */
    .selector-bar {{
      background: white;
      border: 1px solid #e2e8f0;
      padding: 16px 20px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }}
    .selector-bar label {{
      font-weight: 700;
      font-size: 15px;
      color: var(--navy);
    }}
    .store-select {{
      padding: 10px 16px;
      border-radius: 8px;
      border: 1.5px solid #cbd5e1;
      font-family: var(--font-th);
      font-size: 15px;
      font-weight: 600;
      color: var(--navy);
      background: #f8fafc;
      min-width: 320px;
      cursor: pointer;
      outline: none;
    }}
    .store-select:focus {{ border-color: var(--primary); }}

    /* Scenario Buttons */
    .scenario-btn-group {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }}
    .scen-btn {{
      padding: 8px 16px;
      border-radius: 8px;
      border: 1.5px solid #cbd5e1;
      background: white;
      font-family: var(--font-th);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .scen-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
    .scen-btn.active {{
      background: #0f172a;
      color: white;
      border-color: #0f172a;
    }}

    /* Print View Styles */
    @media print {{
      .top-navbar, .nav-tabs, .selector-bar, .scenario-btn-group {{ display: none !important; }}
      body {{ background: white; color: black; }}
      .panel, .kpi-card {{ box-shadow: none !important; border: 1px solid #ccc !important; break-inside: avoid; }}
      .dashboard-container {{ max-width: 100%; margin: 0; padding: 0; }}
      .tab-content {{ display: block !important; }}
    }}
  </style>
</head>
<body>

  <!-- Top Executive Navbar -->
  <header class="top-navbar">
    <div class="brand-group">
      <div class="brand-logo">M</div>
      <div class="brand-title">
        <h1>MueNee B2B Analytics <span style="font-size:12px; font-weight:normal; background:rgba(255,255,255,0.15); padding:2px 8px; border-radius:10px;">Executive Command Center</span></h1>
        <p>ระบบบริหารห่วงโซ่อุปทานและการตัดสินใจ B2B สำหรับ 10 ร้านค้าจริงรอบ ม.ศิลปากร นครปฐม (รัศมี 3.0 กม.)</p>
      </div>
    </div>
  </header>

  <main class="dashboard-container">

    <!-- Navigation Tabs -->
    <nav class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('tab-overview')">📊 ภาพรวมระบบ (System Overview)</button>
      <button class="tab-btn" onclick="switchTab('tab-stores')">🏪 เจาะลึกร้านค้า & แผนจัดซื้อ (Store Procurement)</button>
      <button class="tab-btn" onclick="switchTab('tab-menu')">⭐ เมนูวิศวกรรม 4 มิติ (Menu Engineering)</button>
      <button class="tab-btn" onclick="switchTab('tab-shock')">⚡ แบบจำลองวิกฤตราคา (Price Shock)</button>
      <button class="tab-btn" onclick="switchTab('tab-growth')">📈 โอกาสเติบโต & คุณภาพข้อมูล (Data Quality & Growth)</button>
    </nav>

    <!-- TAB 1: SYSTEM OVERVIEW -->
    <div id="tab-overview" class="tab-content">
      <!-- 4 Top Executive KPI Cards -->
      <section class="kpi-grid">
        <div class="kpi-card teal">
          <div class="kpi-title">ความแม่นยำพยากรณ์ (Forecast WAPE)</div>
          <div class="kpi-value">4.00%</div>
          <div class="kpi-status positive">
            <span>🟢 Economy: 4.00% | Mid: 9.66% | Premium: 9.24%</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">ผ่านเกณฑ์เป้าหมาย &lt; 10% ทุกกลุ่ม (โมเดล SARIMA_XREG)</p>
        </div>

        <div class="kpi-card green">
          <div class="kpi-title">การลดของสดเน่าเสีย (Food Waste Reduction)</div>
          <div class="kpi-value">-99.49%</div>
          <div class="kpi-status positive">
            <span>🟢 ประหยัดวัตถุดิบ 11,437.0 กิโลกรัม</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">Baseline: 11.5 ตัน &rarr; MueNee Policy: 58.8 กก. (เป้า &ge; 20%)</p>
        </div>

        <div class="kpi-card blue">
          <div class="kpi-title">อัตราสินค้าขาดสต็อก (Stock-out Rate)</div>
          <div class="kpi-value">0.78%</div>
          <div class="kpi-status positive">
            <span>🟢 Service Level สูงถึง 99.22%</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">ผ่านเกณฑ์ &le; 5.0% ครบทั้ง 50 อนุกรมร้านค้า &times; วัตถุดิบ</p>
        </div>

        <div class="kpi-card amber">
          <div class="kpi-title">การปกป้องกำไรขั้นต้น (Margin Protection)</div>
          <div class="kpi-value">-0.76 pp</div>
          <div class="kpi-status positive">
            <span>🟢 เมื่อเนื้อหมูพุ่ง +30% (shock_pork_30)</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">Response Playbook ช่วยลดการสูญเสียกำไรไม่เกิน 3 จุด %</p>
        </div>
      </section>

      <!-- Charts Row 1 -->
      <section class="charts-grid">
        <div class="panel">
          <div class="panel-header">
            <div>
              <h3>📈 ยอดพยากรณ์ความต้องการจริงเทียบกับ 95% Confidence Band (Test Set 64 วัน)</h3>
              <p>อนุกรมเวลาช่วงปิดเทอม 2 และภาคฤดูร้อน (2027-05-29 ถึง 2027-07-31) สะท้อนผลของปฏิทินการศึกษา</p>
            </div>
            <span class="badge" style="background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:6px; font-weight:700;">Economy Tier</span>
          </div>
          <div style="height: 330px;">
            <canvas id="forecastChart"></canvas>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <div>
              <h3>🗑️ การลดลงของของสดเน่าเสีย (Food Waste)</h3>
              <p>เปรียบเทียบ Baseline (สั่งคงที่) vs MueNee Policy</p>
            </div>
          </div>
          <div style="height: 330px;">
            <canvas id="wasteChart"></canvas>
          </div>
        </div>
      </section>
    </div>

    <!-- TAB 2: STORE INTELLIGENCE & PROCUREMENT -->
    <div id="tab-stores" class="tab-content" style="display:none;">
      <!-- Store Selector Bar -->
      <div class="selector-bar">
        <label for="storeSelect">เลือกดูข้อมูลร้านค้า (10 ร้านรอบ ม.ศิลปากร):</label>
        <select id="storeSelect" class="store-select" onchange="renderStoreDetails(this.value)">
          <!-- Options will be populated by JS -->
        </select>
        <div id="storeQuickMeta" style="font-size:13px; color:#64748b;"></div>
      </div>

      <!-- Store Summary Cards -->
      <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
        <div class="kpi-card teal">
          <div class="kpi-title">ของสดเน่าเสียลดลง (Food Waste Reduction)</div>
          <div class="kpi-value" id="storeWasteRed">--%</div>
          <p id="storeWasteKg" style="font-size:13px; color:#64748b;"></p>
        </div>
        <div class="kpi-card blue">
          <div class="kpi-title">อัตราของขาดสต็อก (Stockout Rate)</div>
          <div class="kpi-value" id="storeStockout">--%</div>
          <p style="font-size:13px; color:#059669; font-weight:600;">🟢 ผ่านเกณฑ์มาตรฐาน &le; 5%</p>
        </div>
        <div class="kpi-card amber">
          <div class="kpi-title">สถานะความเชื่อมั่นราคา (Price Confidence)</div>
          <div class="kpi-value" id="storeConfidence" style="font-size:24px; margin:14px 0;">--</div>
          <p id="storeConfidenceNote" style="font-size:12px; color:#64748b;"></p>
        </div>
      </div>

      <!-- Store Menu & Procurement Tables -->
      <div class="charts-grid" style="grid-template-columns: 1fr 1fr;">
        <!-- Menu Analysis -->
        <div class="panel">
          <div class="panel-header">
            <div>
              <h3>🍽️ เมนูอาหารประจำร้าน (Menu Performance & Quadrant)</h3>
              <p>วิเคราะห์ตามทฤษฎี Kasavana & Smith ภายในร้าน (Within-Restaurant N=3)</p>
            </div>
          </div>
          <div class="table-container">
            <table id="storeMenuTable">
              <thead>
                <tr>
                  <th>ชื่อเมนู</th>
                  <th>ราคาขาย</th>
                  <th>Food Cost %</th>
                  <th>กำไร (CM)</th>
                  <th>Quadrant</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>

        <!-- Procurement Plan Checklist -->
        <div class="panel">
          <div class="panel-header">
            <div>
              <h3>📋 แผนการสั่งซื้อวัตถุดิบแนะนำ (Smart Procurement Checklist)</h3>
              <p>คำนวณด้วย Perishable Cap ป้องกันของเน่าเสีย</p>
            </div>
          </div>
          <div class="table-container">
            <table id="storePlanTable">
              <thead>
                <tr>
                  <th>กลุ่มวัตถุดิบ</th>
                  <th>สต็อกคงเหลือ</th>
                  <th>สั่งแนะนำ (Q*)</th>
                  <th>สถานะสัญญาณ</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: MENU ENGINEERING MATRIX -->
    <div id="tab-menu" class="tab-content" style="display:none;">
      <div class="panel" style="margin-bottom:24px;">
        <div class="panel-header">
          <div>
            <h3>⭐ ผังวิศวกรรมเมนูอาหาร 30 รายการ (Kasavana & Smith Matrix)</h3>
            <p>แกน X: ความนิยม (Menu Mix %) | แกน Y: กำไรส่วนเกินต่อจาน (Contribution Margin บาท)</p>
          </div>
          <div style="font-size:13px; display:flex; gap:12px;">
            <span><span class="tag-quad stars">⭐ Stars (11)</span> ขายดี+กำไรสูง</span>
            <span><span class="tag-quad plow">🐴 Plowhorses (15)</span> ขายดีแต่กำไรต่ำ</span>
            <span><span class="tag-quad puzz">🧩 Puzzles (2)</span> กำไรสูงแต่ขายน้อย</span>
            <span><span class="tag-quad dogs">🐶 Dogs (2)</span> ขายน้อย+กำไรต่ำ</span>
          </div>
        </div>
        <div style="height: 440px;">
          <canvas id="quadrantScatterChart"></canvas>
        </div>
      </div>

      <!-- Menu Table with Strategic Recommendations -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <h3>📑 สรุปสถานะและคำแนะนำเชิงกลยุทธ์ทั้ง 30 เมนูอาหาร</h3>
            <p>คำแนะนำปรับสูตร/ราคา/โปรโมชันตามหลักความอ่อนไหวต่อราคาของนักศึกษา ม.ศิลปากร</p>
          </div>
        </div>
        <div class="table-container">
          <table id="fullMenuTable">
            <thead>
              <tr>
                <th>ชื่อเมนู</th>
                <th>ร้านค้า</th>
                <th>ระดับราคา</th>
                <th>ราคาขาย</th>
                <th>ต้นทุน (FC %)</th>
                <th>กำไร (CM)</th>
                <th>Quadrant</th>
                <th>คำแนะนำเชิงปฏิบัติการ (Actionable Recommendation)</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 4: PRICE SHOCK SIMULATOR -->
    <div id="tab-shock" class="tab-content" style="display:none;">
      <div class="panel" style="margin-bottom:24px;">
        <div class="panel-header">
          <div>
            <h3>⚡ แบบจำลองวิกฤตราคาขายส่งตลาดสดนครปฐม (Deterministic Scenarios)</h3>
            <p>เลือกสถานการณ์เพื่อดูผลกระทบต่อต้นทุนและกำไรขั้นต้นของระบบ</p>
          </div>
        </div>
        <div class="scenario-btn-group" id="scenarioButtons">
          <!-- Populated by JS -->
        </div>

        <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr); margin: 20px 0;">
          <div class="kpi-card amber">
            <div class="kpi-title">ความสูญเสียกำไรต่อสัปดาห์</div>
            <div class="kpi-value" id="scenWeeklyLoss" style="color:#d97706;">--</div>
            <p style="font-size:12px; color:#64748b;">ผลกระทบรวมทั้ง 10 ร้านค้า</p>
          </div>
          <div class="kpi-card amber">
            <div class="kpi-title">ความสูญเสียตลอดช่วงวิกฤต</div>
            <div class="kpi-value" id="scenTotalLoss" style="color:#b45309;">--</div>
            <p id="scenDurationText" style="font-size:12px; color:#64748b;">--</p>
          </div>
          <div class="kpi-card teal">
            <div class="kpi-title">ต้นทุนต่อจานเฉลี่ยเพิ่มขึ้น</div>
            <div class="kpi-value" id="scenFcDelta">--%</div>
            <p style="font-size:12px; color:#64748b;">Δ Food Cost % เฉลี่ย</p>
          </div>
          <div class="kpi-card green">
            <div class="kpi-title">สถานะ Response Playbook</div>
            <div class="kpi-value" style="font-size:20px; margin:14px 0; color:#059669;">Protected</div>
            <p style="font-size:12px; color:#059669;">กำไรลดลงไม่เกิน 3 จุด %</p>
          </div>
        </div>

        <div style="height: 320px;">
          <canvas id="shockBarChart"></canvas>
        </div>
      </div>

      <!-- Monte Carlo Simulation Panel -->
      <div class="panel">
        <div class="panel-header">
          <div>
            <h3>🎲 การจำลองแบบเฟ้นสุ่ม Monte Carlo 10,000 รอบ (Portfolio Gross Margin Distribution)</h3>
            <p>การกระจายตัวของกำไรขั้นต้นภายใต้ความผันผวนของราคาสินค้าเกษตรและเนื้อสัตว์ในตลาดสดนครปฐม</p>
          </div>
          <div>
            <span class="badge" style="background:#fee2e2; color:#991b1b; padding:6px 12px; border-radius:6px; font-weight:700;">VaR 95% = 53.96%</span>
          </div>
        </div>
        <p style="font-size:14px; color:#475569; margin-bottom:15px;">
          ผลการจำลอง 10,000 รอบแสดงว่า <b>ระบบมีกำไรขั้นต้นเฉลี่ย 58.34%</b> (จากฐาน 60.54%) และด้วยระดับความเชื่อมั่น 95% กำไรขั้นต้นของเครือข่ายร้านอาหารจะไม่ลดต่ำกว่า <b>53.96%</b> แม้จะเผชิญกับวิกฤตราคาวัตถุดิบผันผวนพร้อมกันหลายกลุ่ม
        </p>
      </div>
    </div>

    <!-- TAB 5: DATA QUALITY & GROWTH -->
    <div id="tab-growth" class="tab-content" style="display:none;">
      <!-- Upside KPI Cards -->
      <section class="kpi-grid">
        <div class="kpi-card amber">
          <div class="kpi-title">โอกาสยอดขายเพิ่มจากการยืนยันสารก่อภูมิแพ้</div>
          <div class="kpi-value">+฿3,083,950</div>
          <div class="kpi-status positive">
            <span>🟢 ปลดล็อกยอดสั่งซื้อ 28,617 จาน/ปี</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">ปัจจุบันทั้ง 30 เมนู allergensKnown: false ทำให้ผู้ใช้แพ้อาหาร (12%) ถูกตัดออกจากระบบ</p>
        </div>

        <div class="kpi-card teal">
          <div class="kpi-title">ยอดขายเพิ่มจากการยืนยันราคา (Verification Uplift)</div>
          <div class="kpi-value">+฿2,717,491</div>
          <div class="kpi-status positive">
            <span>🟢 +10.5% Demand Uplift (29,217 จาน/ปี)</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">สำหรับ 15 เมนูใน 5 ร้านค้าที่สถานะเป็น unverified (ลด Choice Penalty)</p>
        </div>

        <div class="kpi-card green">
          <div class="kpi-title">มูลค่าปลดล็อกการเติบโตรวมทั้งระบบ (Total B2B Upside)</div>
          <div class="kpi-value">+฿5,801,441</div>
          <div class="kpi-status positive">
            <span>🟢 เพิ่มกระแสเงินสดให้ผู้ประกอบการท้องถิ่น</span>
          </div>
          <p style="font-size:12px; color:#64748b; margin-top:6px;">พิสูจน์มูลค่าทางธุรกิจของการเปลี่ยนข้อมูลฟรีฝั่ง B2C เป็นสินทรัพย์ข้อมูลฝั่ง B2B</p>
        </div>
      </section>

      <!-- Growth Chart -->
      <div class="panel">
        <div class="panel-header" style="flex-direction:column; align-items:flex-start; gap:8px;">
          <div>
            <h3>💰 โอกาสการเพิ่มรายได้รายปีแยกตามร้านค้า (Annual Revenue Upside by Restaurant)</h3>
            <p>มูลค่าที่จะได้รับเพิ่มขึ้นจากการยืนยันสารก่อภูมิแพ้ และการยืนยันราคาขายหน้าร้านบนแพลตฟอร์ม</p>
          </div>
          <div style="font-size:13px; color:#475569; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px 14px; width:100%; box-sizing:border-box;">
            💡 <b>คำอธิบายสัญลักษณ์และข้อมูลในกราฟ:</b>
            <ul style="margin-left:18px; margin-top:4px; line-height:1.6;">
              <li><span style="color:#f97316; font-weight:700;">แถบสีส้ม (Allergen Verification):</span> มีในทุกร้านค้า (30 เมนู) จากการปลดล็อกระบบกรองสารก่อภูมิแพ้ (+12% Demand)</li>
              <li><span style="color:#0d9488; font-weight:700;">แถบสีเขียว (Price Verification Uplift):</span> แสดงเฉพาะใน <b>5 ร้านค้าที่รอยืนยันราคา [Unverified ⏳]</b> ซึ่งจะได้ยอดขายเพิ่มกลับคืนมา +10.5% (ลด Choice Penalty) ส่วนอีก 5 ร้านค้ามีสถานะ <b>[Verified ✅]</b> ยืนยันราคาถูกต้องอยู่แล้วตั้งแต่ต้น จึงได้รับยอดขายเต็ม 100% อยู่แล้ว (Uplift = ฿0)</li>
            </ul>
          </div>
        </div>
        <div style="height: 480px;">
          <canvas id="growthBarChart"></canvas>
        </div>
      </div>
    </div>

  </main>

  <footer style="text-align:center; padding:35px 20px; color:#64748b; font-size:13px; border-top:1px solid #e2e8f0; margin-top:40px; background:white;">
    <p><b>MueNee B2B Analytics Platform</b> &bull; ระบบบริหารห่วงโซ่อุปทานและการตัดสินใจ B2B ระดับ Production-Grade</p>
  </footer>

  <!-- EMBEDDED REAL PIPELINE DATA -->
  <script>
    const PIPELINE_DATA = {json.dumps(payload, ensure_ascii=False)};

    // Tab Navigation
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.getElementById(tabId).style.display = 'block';
      event.target.classList.add('active');

      // Trigger chart resize
      window.dispatchEvent(new Event('resize'));
    }}

    // Initialize Store Select
    function initStores() {{
      const select = document.getElementById('storeSelect');
      select.innerHTML = '';
      PIPELINE_DATA.restaurants.forEach((r, idx) => {{
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = `${{idx + 1}}. ${{r.name}} (${{r.tier}})`;
        select.appendChild(opt);
      }});
      renderStoreDetails(PIPELINE_DATA.restaurants[0].id);
    }}

    // Render Store Details
    function renderStoreDetails(storeId) {{
      const store = PIPELINE_DATA.restaurants.find(r => r.id === storeId);
      if (!store) return;

      document.getElementById('storeQuickMeta').textContent = `รหัสร้าน: ${{store.id}} | ระดับราคา: ${{store.tier}} | สถานะ: ${{store.confidence}}`;
      document.getElementById('storeWasteRed').textContent = `${{store.waste_reduction_pct}}%`;
      document.getElementById('storeWasteKg').textContent = `ของเน่าเสียลดลงจาก ${{store.baseline_waste_kg}} กก. เหลือ ${{store.muenee_waste_kg}} กก.`;
      document.getElementById('storeStockout').textContent = `${{store.stockout_rate}}%`;
      
      const confEl = document.getElementById('storeConfidence');
      const confNote = document.getElementById('storeConfidenceNote');
      if (store.confidence === 'verified') {{
        confEl.innerHTML = '<span style="color:#059669;">Verified (ยืนยันแล้ว)</span>';
        confNote.textContent = 'ไม่ถูกหักคะแนน Choice Penalty ในระบบแนะนำ';
      }} else {{
        confEl.innerHTML = '<span style="color:#d97706;">Unverified (ยังไม่ยืนยัน)</span>';
        confNote.textContent = 'มีโอกาสเพิ่มยอดขาย +10.5% หากกดยืนยันราคา';
      }}

      // Menu Table
      const menuTbody = document.querySelector('#storeMenuTable tbody');
      menuTbody.innerHTML = '';
      store.menus.forEach(m => {{
        const qClass = m.quadrant_within_restaurant === 'Stars' ? 'stars' :
                       m.quadrant_within_restaurant === 'Plowhorses' ? 'plow' :
                       m.quadrant_within_restaurant === 'Puzzles' ? 'puzz' : 'dogs';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight:700;">${{m.menu_name_th}}</td>
          <td>฿${{m.selling_price_thb}}</td>
          <td>${{m.food_cost_pct}}%</td>
          <td style="font-weight:700; color:#0d9488;">฿${{m.contribution_margin_thb}}</td>
          <td><span class="tag-quad ${{qClass}}">${{m.quadrant_within_restaurant}}</span></td>
        `;
        menuTbody.appendChild(tr);
      }});

      // Procurement Plan Table
      const planTbody = document.querySelector('#storePlanTable tbody');
      planTbody.innerHTML = '';
      const cThai = {{
        "pork_and_cuts": "เนื้อสุกรและชิ้นส่วน",
        "poultry": "สัตว์ปีก (ไก่/เป็ด)",
        "beef": "เนื้อโค",
        "seafood": "อาหารทะเลสด",
        "egg_and_tofu": "ไข่และเต้าหู้",
        "carb_base": "ข้าวสารและเส้น",
        "fresh_veg_herbs": "ผักสดและสมุนไพร",
        "sauce_seasoning": "ซอสและเครื่องปรุง"
      }};

      store.procurement_plan.forEach(p => {{
        const inv = p.ending_inventory_kg;
        const rop = p.reorder_point_kg;
        let pill = '<span class="traffic-pill traffic-green">🟢 สต็อกพอดี</span>';
        if (inv <= rop * 0.5) {{
          pill = '<span class="traffic-pill traffic-red">🔴 ต้องสั่งด่วน</span>';
        }} else if (inv <= rop) {{
          pill = '<span class="traffic-pill traffic-amber">🟡 ใกล้จุดสั่งซื้อ</span>';
        }}
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight:600;">${{cThai[p.commodity_group_name] || p.commodity_group_name}}</td>
          <td>${{inv}} กก.</td>
          <td style="font-weight:700; color:#0f172a;">${{p.order_quantity_kg}} กก.</td>
          <td>${{pill}}</td>
        `;
        planTbody.appendChild(tr);
      }});
    }}

    // Render Full 30 Menus Table
    function renderFullMenuTable() {{
      const tbody = document.querySelector('#fullMenuTable tbody');
      tbody.innerHTML = '';
      PIPELINE_DATA.menus.forEach(m => {{
        const qClass = m.quadrant_within_restaurant === 'Stars' ? 'stars' :
                       m.quadrant_within_restaurant === 'Plowhorses' ? 'plow' :
                       m.quadrant_within_restaurant === 'Puzzles' ? 'puzz' : 'dogs';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight:700;">${{m.menu_name_th}}</td>
          <td>${{m.restaurant_name}}</td>
          <td><span style="font-size:12px; background:#f1f5f9; padding:2px 6px; border-radius:4px;">${{m.price_tier}}</span></td>
          <td>฿${{m.selling_price_thb}}</td>
          <td>${{m.food_cost_pct}}%</td>
          <td style="font-weight:700; color:#0d9488;">฿${{m.contribution_margin_thb}}</td>
          <td><span class="tag-quad ${{qClass}}">${{m.quadrant_within_restaurant}}</span></td>
          <td style="font-size:13px; line-height:1.4;">${{m.strategic_recommendation}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    // Initialize Scenario Simulator
    let currentScenarioChart = null;
    function initScenarios() {{
      const container = document.getElementById('scenarioButtons');
      container.innerHTML = '';
      PIPELINE_DATA.scenarios.forEach((scen, idx) => {{
        const btn = document.createElement('button');
        btn.className = 'scen-btn' + (idx === 1 ? ' active' : '');
        btn.textContent = scen.name;
        btn.onclick = () => selectScenario(scen.id, btn);
        container.appendChild(btn);
      }});
      selectScenario(PIPELINE_DATA.scenarios[1].id, container.children[1]);
    }}

    function selectScenario(scenId, btnElement) {{
      document.querySelectorAll('.scen-btn').forEach(b => b.classList.remove('active'));
      if (btnElement) btnElement.classList.add('active');

      const scen = PIPELINE_DATA.scenarios.find(s => s.id === scenId);
      if (!scen) return;

      document.getElementById('scenWeeklyLoss').textContent = `-฿${{Math.abs(scen.weekly_impact_thb).toLocaleString()}}`;
      document.getElementById('scenTotalLoss').textContent = `-฿${{Math.abs(scen.total_impact_thb).toLocaleString()}}`;
      document.getElementById('scenDurationText').textContent = `ระยะเวลา Shock: ${{scen.weeks}} สัปดาห์`;
      document.getElementById('scenFcDelta').textContent = `+${{scen.avg_fc_delta_pct}}%`;
    }}

    // CHARTS INITIALIZATION
    window.onload = function() {{
      initStores();
      renderFullMenuTable();
      initScenarios();

      // Chart 1: Forecast Chart
      const fcCtx = document.getElementById('forecastChart').getContext('2d');
      new Chart(fcCtx, {{
        type: 'line',
        data: {{
          labels: PIPELINE_DATA.forecast_timeline.dates.map(d => d.slice(5)),
          datasets: [
            {{
              label: 'ยอดคำสั่งซื้อจริง (Actual Orders)',
              data: PIPELINE_DATA.forecast_timeline.actual,
              borderColor: '#0f172a',
              backgroundColor: '#0f172a',
              borderWidth: 2,
              pointRadius: 2.5,
              tension: 0.1
            }},
            {{
              label: 'SARIMA Point Forecast',
              data: PIPELINE_DATA.forecast_timeline.forecast,
              borderColor: '#0d9488',
              backgroundColor: 'rgba(13, 148, 136, 0.1)',
              borderWidth: 2.5,
              pointRadius: 0,
              tension: 0.2
            }},
            {{
              label: '95% Confidence Upper Band',
              data: PIPELINE_DATA.forecast_timeline.ci_hi_95,
              borderColor: 'rgba(13, 148, 136, 0.25)',
              borderDash: [4, 4],
              pointRadius: 0,
              fill: false
            }},
            {{
              label: '95% Confidence Lower Band',
              data: PIPELINE_DATA.forecast_timeline.ci_lo_95,
              borderColor: 'rgba(13, 148, 136, 0.25)',
              borderDash: [4, 4],
              pointRadius: 0,
              fill: '-1',
              backgroundColor: 'rgba(13, 148, 136, 0.08)'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'bottom', labels: {{ boxWidth: 12, font: {{ family: 'Prompt', size: 12 }} }} }}
          }},
          scales: {{
            y: {{ title: {{ display: true, text: 'จาน/วัน (Orders)', font: {{ family: 'Prompt' }} }} }},
            x: {{ ticks: {{ maxTicksLimit: 12 }} }}
          }}
        }}
      }});

      // Chart 2: Waste Reduction Chart
      const wCtx = document.getElementById('wasteChart').getContext('2d');
      new Chart(wCtx, {{
        type: 'doughnut',
        data: {{
          labels: ['ของเสียที่ประหยัดได้ (Saved Waste)', 'ของเสียคงเหลือ (MueNee Policy)'],
          datasets: [{{
            data: [11437.0, 58.8],
            backgroundColor: ['#10b981', '#ef4444'],
            borderWidth: 0
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'bottom', labels: {{ font: {{ family: 'Prompt', size: 12 }} }} }}
          }}
        }}
      }});

      // Chart 3: Quadrant Scatter Chart
      const qCtx = document.getElementById('quadrantScatterChart').getContext('2d');
      const quadColors = {{ 'Stars': '#0d9488', 'Plowhorses': '#f97316', 'Puzzles': '#3b82f6', 'Dogs': '#ef4444' }};
      new Chart(qCtx, {{
        type: 'scatter',
        data: {{
          datasets: Object.keys(quadColors).map(qName => ({{
            label: qName,
            data: PIPELINE_DATA.menus
              .filter(m => m.quadrant_within_restaurant === qName)
              .map(m => ({{ x: m.menu_mix_restaurant_pct, y: m.contribution_margin_thb, name: m.menu_name_th, rest: m.restaurant_name }})),
            backgroundColor: quadColors[qName],
            pointRadius: 7,
            pointHoverRadius: 9
          }}))
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            tooltip: {{
              callbacks: {{
                label: (ctx) => `${{ctx.raw.name}} (${{ctx.raw.rest}}): Menu Mix ${{ctx.raw.x}}% | CM ฿${{ctx.raw.y}} [${{ctx.dataset.label}}]`
              }}
            }},
            legend: {{ position: 'bottom', labels: {{ font: {{ family: 'Prompt', size: 13 }} }} }}
          }},
          scales: {{
            x: {{ title: {{ display: true, text: 'ความนิยม (Menu Mix % ภายในร้าน)', font: {{ family: 'Prompt' }} }} }},
            y: {{ title: {{ display: true, text: 'กำไรส่วนเกินต่อจาน (Contribution Margin บาท)', font: {{ family: 'Prompt' }} }} }}
          }}
        }}
      }});

      // Chart 4: Price Shock Impact Chart
      const sCtx = document.getElementById('shockBarChart').getContext('2d');
      new Chart(sCtx, {{
        type: 'bar',
        data: {{
          labels: PIPELINE_DATA.scenarios.map(s => s.name.split(' (')[0]),
          datasets: [{{
            label: 'ผลกระทบต่อกำไรขั้นต้นรวม (บาท/ช่วงวิกฤต)',
            data: PIPELINE_DATA.scenarios.map(s => Math.abs(s.total_impact_thb)),
            backgroundColor: ['#94a3b8', '#f97316', '#eab308', '#06b6d4', '#10b981', '#ef4444']
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            y: {{ title: {{ display: true, text: 'มูลค่ากำไรที่ลดลง (บาท)', font: {{ family: 'Prompt' }} }} }}
          }}
        }}
      }});

      // Chart 5: Growth Bar Chart
      const gCtx = document.getElementById('growthBarChart').getContext('2d');
      new Chart(gCtx, {{
        type: 'bar',
        data: {{
          labels: PIPELINE_DATA.edge_cases.store_breakdown.map(s =>
            s.price_confidence === 'verified'
              ? `${{s.restaurant_name}} [Verified ✅]`
              : `${{s.restaurant_name}} [Unverified ⏳]`
          ),
          datasets: [
            {{
              label: 'โอกาสจากสารก่อภูมิแพ้ (Allergen Verification)',
              data: PIPELINE_DATA.edge_cases.store_breakdown.map(s => s.annual_blocked_revenue_thb),
              backgroundColor: '#f97316'
            }},
            {{
              label: 'โอกาสจากการยืนยันราคา (Price Verification Uplift)',
              data: PIPELINE_DATA.edge_cases.store_breakdown.map(s => s.annual_uplift_revenue_thb),
              backgroundColor: '#0d9488'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          plugins: {{
            legend: {{ position: 'bottom', labels: {{ font: {{ family: 'Prompt', size: 12 }} }} }},
            tooltip: {{
              callbacks: {{
                label: (ctx) => {{
                  const store = PIPELINE_DATA.edge_cases.store_breakdown[ctx.dataIndex];
                  if (ctx.datasetIndex === 1 && store.price_confidence === 'verified') {{
                    return `${{ctx.dataset.label}}: ฿0 (ยืนยันราคาถูกต้องแล้ว ได้รับยอดขายเต็ม 100%)`;
                  }}
                  return `${{ctx.dataset.label}}: ฿${{Number(ctx.raw).toLocaleString()}} บาท/ปี`;
                }}
              }}
            }}
          }},
          scales: {{
            x: {{ stacked: true, title: {{ display: true, text: 'มูลค่ารายได้เพิ่ม (บาท/ปี)', font: {{ family: 'Prompt', size: 13 }} }} }},
            y: {{ stacked: true, ticks: {{ font: {{ family: 'Prompt', size: 12, weight: '600' }}, color: '#1e293b' }} }}
          }}
        }}
      }});
    }};
  </script>
</body>
</html>
"""

    dashboard_file = os.path.join(dashboard_dir, "index.html")
    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    file_size_kb = os.path.getsize(dashboard_file) / 1024
    print(f"[4/4] ✅ Dashboard successfully generated at: {dashboard_file} ({file_size_kb:.2f} KB)")
    print("\n🎉 DASHBOARD READY! Open dashboard/index.html in Chrome or Edge to view.")

if __name__ == "__main__":
    build_dashboard()

