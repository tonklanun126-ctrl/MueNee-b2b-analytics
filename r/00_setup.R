# ==============================================================================
# MueNee B2B Analytics: Phase 3 - Environment Setup (r/00_setup.R)
# ==============================================================================
# สคริปต์ตั้งค่าสภาพแวดล้อมภาษา R (Module B: Statistical Engine)
# สำหรับโปรเจกต์ MueNee-b2b-analytics รอบ ม.ศิลปากร วิทยาเขตพระราชวังสนามจันทร์
# ==============================================================================

# ปรับการตั้งค่า Encoding และภาษาให้รองรับภาษาไทยและ UTF-8 บน Windows
Sys.setlocale("LC_CTYPE", "Thai")
options(encoding = "UTF-8")
options(warn = 1)
options(scipen = 999) # ป้องกัน Scientific notation (เช่น 1e+05) เพื่อความแม่นยำในการรายงานตัวเลข

message("==================================================================")
message("   MueNee B2B Analytics: Module B R Environment Initialization   ")
message("==================================================================")

# 1. รายชื่อแพ็กเกจที่จำเป็นสำหรับกระบวนการวิเคราะห์ข้อมูลและอนุกรมเวลา
required_packages <- c(
  "here",         # จัดการ Root Directory แบบยืดหยุ่นข้ามแพลตฟอร์ม
  "readr",        # อ่านและเขียนไฟล์ CSV ได้อย่างรวดเร็ว
  "dplyr",        # จัดการและแปลงรูปตารางข้อมูล (Data Manipulation)
  "tidyr",        # จัดระเบียบข้อมูล Long/Wide formats
  "purrr",        # Functional programming สำหรับการประมวลผลวนซ้ำ
  "lubridate",    # จัดการข้อมูลวันที่และเวลาท้องถิ่น Asia/Bangkok
  "janitor",      # ทำความสะอาดชื่อคอลัมน์และสร้างตารางความถี่
  "scales",       # จัดรูปแบบตัวเลข เงินบาท และร้อยละ
  "ggplot2",      # การสร้างกราฟิกสถิติระดับ Publication-Quality
  "patchwork"     # รวมภาพกราฟิกหลายมิติเข้าด้วยกัน
)

# 2. ตรวจสอบและโหลดแพ็กเกจ
message("\n--- [Step 1] Verifying & Loading R Core Libraries ---")
missing_packages <- required_packages[!required_packages %in% rownames(installed.packages())]

if (length(missing_packages) > 0) {
  message(sprintf("⚠️ ตรวจพบแพ็กเกจที่ยังไม่ได้ติดตั้ง: %s", paste(missing_packages, collapse = ", ")))
  message("กำลังติดตั้งแพ็กเกจผ่าน CRAN Mirror...")
  install.packages(missing_packages, repos = "https://cloud.r-project.org")
}

# โหลดไลบรารีทั้งหมด
loaded_status <- sapply(required_packages, function(pkg) {
  suppressPackageStartupMessages(library(pkg, character.only = TRUE, quietly = TRUE))
  return(TRUE)
})

message(sprintf("✅ โหลดแพ็กเกจหลักสำเร็จครบถ้วน %d/%d แพ็กเกจ", sum(loaded_status), length(required_packages)))

# 3. กำหนดและตรวจสอบโครงสร้างไดเรกทอรี
message("\n--- [Step 2] Project Workspace & Directory Structure ---")
project_root <- here::here()
message(sprintf("📁 Project Root: %s", project_root))

dirs_to_ensure <- c(
  file.path(project_root, "data", "reference"),
  file.path(project_root, "data", "raw"),
  file.path(project_root, "data", "processed"),
  file.path(project_root, "outputs"),
  file.path(project_root, "outputs", "figures"),
  file.path(project_root, "reports")
)

for (d in dirs_to_ensure) {
  if (!dir.exists(d)) {
    dir.create(d, recursive = TRUE, showWarnings = FALSE)
    message(sprintf("  + สร้างไดเรกทอรี: %s", d))
  }
}
message("✅ ไดเรกทอรี data/processed/ และ outputs/figures/ พร้อมใช้งาน")

# 4. บันทึกข้อมูลระบบ
message("\n--- [Step 3] System Metadata ---")
message(sprintf("🖥️ Platform: %s (%s)", R.version$platform, R.version$version.string))
message(sprintf("⏰ Timestamp: %s (ICT)", format(Sys.time(), "%Y-%m-%d %H:%M:%S")))
message("==================================================================")
message(" 🎉 R ENVIRONMENT SETUP READY FOR INGESTION & BOM TRANSFORMATION 🎉")
message("==================================================================\n")

