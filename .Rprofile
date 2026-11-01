# ==============================================================================
# MueNee B2B Analytics: .Rprofile Project Initialization
# ==============================================================================

# กำหนด CRAN repository เริ่มต้น
local({
  r <- getOption("repos")
  r["CRAN"] <- "https://cloud.r-project.org"
  options(repos = r)
  options(encoding = "UTF-8")
  options(scipen = 999)
})

# ข้อความต้อนรับเมื่อเปิด R ใน VS Code
if (interactive()) {
  message(">> MueNee B2B Analytics Project loaded successfully (R-4.6.1)")
  message(">> Working Directory: ", getwd())
}

