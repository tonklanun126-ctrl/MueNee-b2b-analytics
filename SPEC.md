# SPEC — Technical, Data & Statistical Specification
## MueNee-b2b-analytics

| รายการ | รายละเอียด |
| :--- | :--- |
| เวอร์ชันเอกสาร | 1.0 |
| อ้างอิง | [RPD.md](RPD.md) · [SDD.md](SDD.md) · [`muenee-b2b-analytics-context.md`](muenee-context.md/muenee-b2b-analytics-context.md) |
| ขอบเขต | 10 ร้าน · 30 เมนู (`menuItemId` จริง) · 8 กลุ่มวัตถุดิบ · 365 วัน |
| สถานะ | Specification เท่านั้น — ไม่มีโค้ด Python/R |

---

## 1. Recipe Bill of Materials (BOM) Mapping Table

### 1.1 หลักการวิศวกรรม BOM

> [!IMPORTANT]
> Seed Data ทุกเมนูมี `ingredientsKnown: false` ดังนั้น BOM ด้านล่างเป็น **ค่าประมาณทางวิศวกรรม (Engineered Estimate)** ที่สอบเทียบย้อนกลับกับ `proteinGrams` / `carbsGrams` จริงของแต่ละเมนู และต้องเปิดให้เจ้าของร้านปรับแก้ได้ (คอลัมน์ `assumption_flag` ใน `menu_bom_matrix.csv`)

| หลักการ | รายละเอียด |
| :--- | :--- |
| หน่วย | กรัม **ส่วนที่กินได้ (Edible Portion, EP)** ต่อ 1 หน่วยบริโภค (1 จาน/ชุด/ชาม ตามที่ขายจริง) |
| การแปลงเป็นปริมาณจัดซื้อ | ปริมาณซื้อ (As-Purchased, AP) = EP ÷ Yield Factor (ตาราง §1.4) |
| กลุ่ม 6 คาร์โบไฮเดรต | คิดเป็น **น้ำหนักแห้งก่อนหุง/ต้ม** (ข้าวสาร, เส้นแห้ง, แป้ง) ยกเว้นขนมปังคิดน้ำหนักตามจริง |
| กลุ่ม 8 ซอสและเครื่องปรุง | รวมน้ำมันปรุงอาหาร, น้ำซุปปรุงรส, มายองเนส, พริกแกง, นม/เนย/น้ำตาลในเบเกอรี่ |
| เกณฑ์สอบเทียบ (Macro Anchor) | โปรตีนและคาร์โบไฮเดรตที่คำนวณจาก BOM × ความหนาแน่นสารอาหาร (§1.3) ต้องอยู่ในช่วง **±20%** ของค่าใน `menu_items.nutrition` |
| ไขมัน (`fatGrams`) | ใช้เป็นตัวตรวจเชิงคุณภาพ: เมนูไขมันสูง (เช่น หมูกรอบ, ไก่ทอด, ชุดหม้อไฟ) ต้องมีกลุ่ม 8 (น้ำมัน/ซอส) หรือชิ้นส่วนติดมันสูงสอดคล้องกัน |

**รหัสกลุ่มวัตถุดิบ:** G1 หมูและชิ้นส่วน · G2 สัตว์ปีก · G3 เนื้อโค · G4 สัตว์น้ำและอาหารทะเล · G5 ไข่และเต้าหู้ · G6 คาร์โบไฮเดรตหลัก · G7 ผักสดและสมุนไพร · G8 ซอสและเครื่องปรุง

### 1.2 ตาราง BOM ทั้ง 30 เมนู (กรัม EP ต่อหน่วยบริโภค)

| # | `menuItemId` | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | Pro / Carb / Fat จริง (g) | Pro / Carb ประเมินจาก BOM (g) |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 1 | `madam-ho-pork-crunch-set` | 220 | 0 | 0 | 0 | 40 | 70 | 150 | 60 | 55 / 75 / 50 | 57.7 / 78.6 |
| 2 | `madam-ho-paper-pot-pho` | 140 | 0 | 0 | 0 | 50 | 110 | 150 | 60 | 48 / 105 / 34 | 45.5 / 109.8 |
| 3 | `madam-ho-soft-pork-heart-set` | 280 | 0 | 0 | 0 | 50 | 75 | 180 | 60 | 68 / 82 / 58 | 71.7 / 84.3 |
| 4 | `volcano-baked-prawn` | 0 | 0 | 0 | 420 | 0 | 20 | 80 | 30 | 88 / 30 / 32 | 87.9 / 27.9 |
| 5 | `volcano-three-armies-salad` | 0 | 0 | 0 | 180 | 0 | 20 | 150 | 30 | 38 / 28 / 18 | 41.3 / 32.1 |
| 6 | `volcano-sour-curry-prawn-omelette` | 0 | 0 | 0 | 90 | 100 | 0 | 220 | 70 | 34 / 32 / 27 | 37.0 / 30.7 |
| 7 | `bonchon-wings-6` | 0 | 200 | 0 | 0 | 0 | 45 | 20 | 35 | 42 / 44 / 33 | 44.6 / 45.1 |
| 8 | `bonchon-chicken-rice-soy-garlic` | 0 | 160 | 0 | 0 | 0 | 115 | 40 | 35 | 40 / 98 / 28 | 41.9 / 100.9 |
| 9 | `bonchon-fish-rice-hot` | 0 | 0 | 0 | 130 | 0 | 125 | 40 | 30 | 34 / 105 / 23 | 36.5 / 107.4 |
| 10 | `pa-ja-boiled-chicken-rice` | 0 | 125 | 0 | 0 | 0 | 95 | 30 | 25 | 32 / 78 / 18 | 33.0 / 82.2 |
| 11 | `pa-ja-fried-chicken-rice` | 0 | 130 | 0 | 0 | 0 | 105 | 30 | 25 | 34 / 88 / 29 | 34.7 / 90.0 |
| 12 | `pa-ja-spicy-chicken-rice` | 0 | 135 | 0 | 0 | 0 | 105 | 60 | 30 | 35 / 91 / 21 | 36.5 / 93.0 |
| 13 | `good-food-custom-sandwich` | 0 | 35 | 0 | 0 | 60 | 80 | 60 | 25 | 22 / 48 / 17 | 23.2 / 44.6 |
| 14 | `good-food-banana-oat-loaf` | 0 | 0 | 0 | 0 | 15 | 40 | 50 | 15 | 6 / 44 / 8 | 6.7 / 44.5 |
| 15 | `good-food-salmon-salad-rice` | 0 | 0 | 0 | 120 | 0 | 70 | 100 | 20 | 29 / 61 / 18 | 31.5 / 65.6 |
| 16 | `tama-kani-miso-set` | 0 | 0 | 0 | 90 | 30 | 85 | 20 | 25 | 25 / 72 / 22 | 26.2 / 73.8 |
| 17 | `tama-salmon-ebiko-sauce-rice` | 0 | 0 | 0 | 125 | 0 | 95 | 15 | 30 | 31 / 80 / 23 | 32.9 / 82.5 |
| 18 | `tama-torched-salmon-mayo-rice` | 0 | 0 | 0 | 120 | 10 | 95 | 15 | 35 | 31 / 82 / 29 | 32.6 / 76.4 |
| 19 | `loong-loy-tofu-pork-soup` | 70 | 0 | 0 | 0 | 120 | 0 | 100 | 20 | 23 / 16 / 17 | 25.0 / 13.4 |
| 20 | `loong-loy-large-crab-fried-rice` | 0 | 0 | 0 | 90 | 100 | 140 | 50 | 30 | 35 / 122 / 27 | 40.4 / 119.7 |
| 21 | `loong-loy-jungle-catfish-curry` | 0 | 0 | 0 | 150 | 0 | 0 | 180 | 40 | 31 / 19 / 14 | 31.8 / 18.8 |
| 22 | `kinkane-salmon-sashimi` | 0 | 0 | 0 | 150 | 0 | 0 | 15 | 10 | 30 / 2 / 14 | 30.6 / 1.9 |
| 23 | `kinkane-hamachi-sashimi` | 0 | 0 | 0 | 130 | 0 | 0 | 15 | 10 | 29 / 1 / 17 | 29.2 / 1.9 |
| 24 | `kinkane-scallop-sashimi` | 0 | 0 | 0 | 160 | 0 | 0 | 15 | 10 | 27 / 8 / 3 | 27.8 / 6.7 |
| 25 | `hinn-red-pork-rice` | 80 | 0 | 0 | 0 | 50 | 95 | 20 | 45 | 29 / 86 / 21 | 30.7 / 86.6 |
| 26 | `hinn-crispy-pork-rice` | 110 | 0 | 0 | 0 | 50 | 95 | 20 | 45 | 30 / 84 / 36 | 30.1 / 86.6 |
| 27 | `hinn-roast-duck-rice` | 0 | 110 | 0 | 0 | 50 | 95 | 20 | 40 | 32 / 83 / 28 | 35.4 / 85.3 |
| 28 | `thasanam-boat-noodle-soup` | 40 | 0 | 35 | 0 | 0 | 60 | 50 | 35 | 23 / 57 / 10 | 21.4 / 56.3 |
| 29 | `thasanam-spicy-pork` | 150 | 0 | 0 | 0 | 0 | 10 | 120 | 40 | 34 / 25 / 25 | 34.3 / 25.0 |
| 30 | `thasanam-spicy-liver` | 140 | 0 | 0 | 0 | 0 | 10 | 110 | 35 | 31 / 22 / 20 | 32.0 / 23.2 |

### 1.3 รายละเอียดวัตถุดิบย่อย (Sub-commodity) และสมมติฐานต่อเมนู

| # | `menuItemId` | วัตถุดิบย่อยหลักที่แมป | Assumption Flag |
| :-: | :--- | :--- | :--- |
| 1 | `madam-ho-pork-crunch-set` | G1 หมูสไลซ์/หมูกรุบ · G5 เต้าหู้/ไข่ · G6 เส้นเฝอ · G7 ผักลวก, สมุนไพร · G8 น้ำซุป, ซอสถั่วเหลือง, น้ำมันงา | Standard |
| 2 | `madam-ho-paper-pot-pho` | G1 หมูสไลซ์ · G5 ไข่ไก่ · G6 เส้นเฝอ · G7 ผักสด, ต้นหอม · G8 น้ำซุป, ซีอิ๊ว | ⚠️ `ingredients` ว่าง (`-`) — สมมติโปรตีนเป็นหมูสไลซ์ ต้องยืนยันกับร้าน |
| 3 | `madam-ho-soft-pork-heart-set` | G1 หมูสไลซ์ 220 + หัวใจหมู 60 · G5 เต้าหู้/ไข่ · G6 เส้นเฝอ · G7 ผัก · G8 น้ำซุป, น้ำมันงา | Standard (เครื่องในเสียเร็ว) |
| 4 | `volcano-baked-prawn` | G4 กุ้งก้ามกราม/กุ้งขาว · G6 วุ้นเส้น · G7 กระเทียม, ผักชี, ขึ้นฉ่าย · G8 ซอสอบ | Standard (ราคา `unverified`) |
| 5 | `volcano-three-armies-salad` | G4 กุ้ง + ปลา/อาหารทะเลรวม · G6 วุ้นเส้น · G7 หอมแดง, พริกสด, มะนาว, ผักชี · G8 น้ำปลา, น้ำยำ | Standard |
| 6 | `volcano-sour-curry-prawn-omelette` | G4 กุ้ง · G5 ไข่ไก่ (ไข่เจียวชะอม) · G7 ชะอมสด, ผักแกงส้ม · G8 พริกแกงส้ม, น้ำปลา, กะปิ | Standard (ไม่รวมข้าว) |
| 7 | `bonchon-wings-6` | G2 ปีกไก่บน/ปีกกลาง (EP) · G6 แป้งสาลีชุบทอด · G7 กระเทียม · G8 ซอสซอยการ์ลิค, น้ำมันทอด | Standard |
| 8 | `bonchon-chicken-rice-soy-garlic` | G2 สะโพก/อกไก่ · G6 ข้าวสาร 100 + แป้ง 15 · G7 ผักเคียง · G8 ซอสซอยการ์ลิค, น้ำมัน | Standard |
| 9 | `bonchon-fish-rice-hot` | G4 ปลาเนื้อขาวชุบทอด · G6 ข้าวสาร 105 + แป้ง 20 · G7 ผักเคียง · G8 ซอสฮอท, น้ำมัน | Standard |
| 10 | `pa-ja-boiled-chicken-rice` | G2 น่อง/สะโพก/อกไก่สด · G6 ข้าวสาร (ข้าวมัน) · G7 ขิง, กระเทียม, แตงกวา · G8 น้ำจิ้มเต้าเจี้ยว, ซอสถั่วเหลือง | Standard |
| 11 | `pa-ja-fried-chicken-rice` | G2 สะโพก/อกไก่ · G6 ข้าวสาร 90 + แป้ง 15 · G7 แตงกวา, กระเทียม · G8 น้ำจิ้ม, น้ำมันทอด | Standard |
| 12 | `pa-ja-spicy-chicken-rice` | G2 อกไก่/สะโพก · G6 ข้าวสาร · G7 พริกสด, หอมแดง, มะนาว, ผักชี · G8 น้ำปลา, น้ำยำ | Standard |
| 13 | `good-food-custom-sandwich` | G2 อกไก่ (ไส้มาตรฐาน) · G5 ไข่ไก่ · G6 ขนมปังแซนด์วิช · G7 ผักสลัดไฮโดรโปนิกส์ · G8 มายองเนส, นม/เนย | ⚠️ `ingredients` ว่าง (`-`) และเป็นเมนู "เลือกไส้" — ใช้ไส้มาตรฐานไก่+ไข่ |
| 14 | `good-food-banana-oat-loaf` | G5 ไข่ไก่ · G6 ข้าวโอ๊ต + แป้งสาลี · G7 กล้วยน้ำว้า · G8 นม, เนย, น้ำตาล | Standard |
| 15 | `good-food-salmon-salad-rice` | G4 แซลมอนสด · G6 ข้าวสาร · G7 ผักสลัดไฮโดรโปนิกส์ · G8 น้ำสลัดงา, ซอสถั่วเหลือง | Standard |
| 16 | `tama-kani-miso-set` | G4 เนื้อปู/ปูอัด + มันปูคานิมิโซะ · G5 ไข่ไก่ · G6 ข้าวญี่ปุ่น · G7 ต้นหอม · G8 ซอสโชยุ, มายองเนส | Standard |
| 17 | `tama-salmon-ebiko-sauce-rice` | G4 แซลมอน 110 + ไข่กุ้ง (Ebiko) 15 · G6 ข้าวญี่ปุ่น · G7 ต้นหอม · G8 ซอสไข่กุ้ง, โชยุ | Standard |
| 18 | `tama-torched-salmon-mayo-rice` | G4 แซลมอน · G5 ไข่ (ฐานมายองเนส) · G6 ข้าวญี่ปุ่น · G7 ต้นหอม · G8 มายองเนส, โชยุ | Standard |
| 19 | `loong-loy-tofu-pork-soup` | G1 หมูสับ · G5 เต้าหู้ขาว/เต้าหู้ไข่ · G7 ผักกาด, ต้นหอม, ผักชี · G8 ซีอิ๊วขาว, น้ำซุป | Standard (ขนาดเล็ก) |
| 20 | `loong-loy-large-crab-fried-rice` | G4 เนื้อปูแกะ/ปูม้า · G5 ไข่ไก่ 2 ฟอง · G6 ข้าวสาร · G7 ต้นหอม, มะนาว, แตงกวา · G8 ซีอิ๊ว, น้ำมัน | Standard (ขนาดใหญ่/แชร์) |
| 21 | `loong-loy-jungle-catfish-curry` | G4 ปลาบึก/ปลาน้ำจืด · G7 กระชาย, พริก, ใบมะกรูด, ผักแกงป่า · G8 พริกแกงป่า, น้ำปลา | Standard (ไม่รวมข้าว) |
| 22 | `kinkane-salmon-sashimi` | G4 แซลมอนสดเกรดซาชิมิ · G7 หัวไชเท้า, วาซาบิ · G8 โชยุ | Standard (เสียเร็วมาก) |
| 23 | `kinkane-hamachi-sashimi` | G4 ฮามาจิสด · G7 หัวไชเท้า, วาซาบิ · G8 โชยุ | Standard (เสียเร็วมาก) |
| 24 | `kinkane-scallop-sashimi` | G4 หอยเชลล์โฮตาเตะ · G7 หัวไชเท้า, วาซาบิ · G8 โชยุ | Standard (เสียเร็วมาก) |
| 25 | `hinn-red-pork-rice` | G1 สันคอ/สันนอกหมู (หมูแดง) + กุนเชียง · G5 ไข่ต้ม 1 ฟอง · G6 ข้าวสาร · G7 แตงกวา, ต้นหอม · G8 น้ำราดหมูแดง, ซีอิ๊วดำ | Standard |
| 26 | `hinn-crispy-pork-rice` | G1 หมูสามชั้น (หมูกรอบ) · G5 ไข่ต้ม · G6 ข้าวสาร · G7 แตงกวา · G8 น้ำราด, น้ำมันทอด | Standard (ไขมันสูง) |
| 27 | `hinn-roast-duck-rice` | G2 เป็ดย่าง/พะโล้ · G5 ไข่ต้ม · G6 ข้าวสาร · G7 แตงกวา, ต้นหอม · G8 น้ำราดเป็ด, ซีอิ๊วดำ | ⚠️ `ingredients` ระบุเพียง `egg` แต่ชื่อเมนูมีเป็ด — แมปเป็ดเข้า G2 |
| 28 | `thasanam-boat-noodle-soup` | G1 หมูหมัก + ตับหมู · G3 เนื้อวัวสด/ลูกชิ้นเนื้อ · G6 เส้นก๋วยเตี๋ยวแห้ง · G7 ผักบุ้ง, ถั่วงอก, โหระพา · G8 น้ำซุปน้ำตก, เลือดหมู/วัวสด, ซีอิ๊ว | Standard (เมนูเดียวที่ใช้ G3) |
| 29 | `thasanam-spicy-pork` | G1 หมูสไลซ์ · G6 ข้าวคั่ว · G7 ผักชี, หอมแดง, พริก, มะนาว · G8 น้ำปลา | Standard |
| 30 | `thasanam-spicy-liver` | G1 ตับหมูสด · G6 ข้าวคั่ว · G7 ผักชี, หอมแดง, พริก, มะนาว · G8 น้ำปลา | Standard (เครื่องในเสียเร็ว) |

### 1.4 ตารางความหนาแน่นสารอาหารที่ใช้สอบเทียบ (ต่อ 1 กรัม EP)

| กลุ่ม / วัตถุดิบย่อย | Protein | Carb | หมายเหตุ |
| :--- | :-: | :-: | :--- |
| G1 หมูเนื้อแดง / เครื่องใน | 0.20 | 0.00 | หมูสามชั้น 0.14 |
| G2 ไก่ (EP) | 0.20 | 0.00 | เป็ด 0.19 |
| G3 เนื้อวัว / ลูกชิ้นเนื้อ | 0.20 | 0.00 | |
| G4 กุ้ง / แซลมอน / ปลาเนื้อขาว | 0.20 | 0.00 | ฮามาจิ 0.22 · ปลาบึก/ปู 0.18 · เนื้อปูคานิ 0.17 · หอยเชลล์ 0.17 (Carb 0.03) |
| G5 ไข่ไก่ | 0.125 | 0.00 | เต้าหู้ 0.07 (Carb 0.02) |
| G6 ข้าวสาร / เส้นแห้ง / แป้ง (แห้ง) | 0.07 | 0.78 | เส้นก๋วยเตี๋ยว 0.06/0.80 · ขนมปัง 0.09/0.50 · โอ๊ต+แป้ง 0.10/0.70 |
| G7 ผักสดและสมุนไพร | 0.02 | 0.06 | กล้วยน้ำว้า 0.01/0.23 |
| G8 ซอสและเครื่องปรุง (ค่าเริ่มต้น) | 0.03 | 0.25 | มายองเนส 0.01/0.04 · โชยุจิ้ม 0.03/0.10 · พริกแกง 0.03/0.20 · น้ำซุปน้ำตก 0.05/0.15 · ส่วนผสมเบเกอรี่ 0.02/0.33 |

### 1.5 Yield Factor, อายุการเก็บ และ Lead Time ต่อกลุ่ม (พารามิเตอร์ Inventory)

| กลุ่ม | Yield Factor (EP/AP) | อายุการเก็บ (วัน, แช่เย็น) | Lead Time $L$ (วัน) | Service Level เป้าหมาย | $Z_\alpha$ |
| :--- | :-: | :-: | :-: | :-: | :-: |
| G1 หมูและชิ้นส่วน | 0.90 (เครื่องใน 0.95) | 2–3 (เครื่องใน 1) | 1 | 95% | 1.645 |
| G2 สัตว์ปีก | 0.85 (ปีก 0.75, เป็ด 0.55) | 2 | 1 | 95% | 1.645 |
| G3 เนื้อโค | 0.85 | 3 | 1 | 95% | 1.645 |
| G4 สัตว์น้ำและอาหารทะเล | 0.55 (กุ้งทั้งตัว) – 0.95 (หอยเชลล์) | 1–2 | 2 | 90% | 1.282 |
| G5 ไข่และเต้าหู้ | 0.88 (ไข่) / 1.00 (เต้าหู้) | ไข่ 14 / เต้าหู้ 3 | 2 | 97.5% | 1.960 |
| G6 คาร์โบไฮเดรตหลัก | 1.00 | 90+ (ขนมปัง 3) | 7 | 97.5% | 1.960 |
| G7 ผักสดและสมุนไพร | 0.80 | 2–4 | 1 | 90% | 1.282 |
| G8 ซอสและเครื่องปรุง | 1.00 | 180+ (เลือดสด 1) | 14 | 97.5% | 1.960 |

> [!NOTE]
> กลุ่มที่เสียเร็ว (G4, G7) ตั้ง Service Level ต่ำกว่าเพื่อแลกกับความเสี่ยงของเสีย ส่วนกลุ่มเก็บได้นาน (G5, G6, G8) ตั้งสูงเพราะต้นทุนการถือครองต่ำแต่การขาดสต็อกทำให้ขายไม่ได้ทั้งเมนู

---

## 2. CSV Data Dictionary

### 2.1 `daily_meal_logs.csv` (Module A → Module B)

Grain: **1 แถว = 1 วัน × 1 เมนู** (365 × 30 = 10,950 แถว) — Aggregate จากเหตุการณ์ `meal_logs` ระดับรายการ

| คอลัมน์ | ชนิดข้อมูล | ตัวอย่าง | ที่มา / กฎ |
| :--- | :--- | :--- | :--- |
| `date` | Date (ISO 8601, `YYYY-MM-DD`, เวลาท้องถิ่น Asia/Bangkok) | `2026-08-17` | จาก `meal_logs.createdAt` (UTC → ICT) |
| `restaurant_id` | String (FK) | `pa-ja-23-hours` | ต้องอยู่ใน 10 `restaurantId` |
| `menu_item_id` | String (FK) | `pa-ja-fried-chicken-rice` | ต้องอยู่ใน 30 `menuItemId` และตรงกับร้าน |
| `price_tier` | Factor {`economy`,`mid`,`premium_social`} | `economy` | จาก `price.amount` ตาม RPD §1.3 |
| `academic_period` | Factor {`regular`,`midterm_exam`,`final_exam`,`semester_break`,`summer_session`,`public_holiday`} | `final_exam` | จาก `config/academic_calendar.yaml` |
| `day_of_week` | Integer 1–7 (1 = จันทร์) | `3` | ISO weekday |
| `is_weekend` | Boolean | `FALSE` | |
| `orders_total` | Integer ≥ 0 | `142` | ผลรวมทุกช่วงเวลา |
| `orders_lunch` | Integer ≥ 0 | `61` | 11:30–13:30 |
| `orders_dinner` | Integer ≥ 0 | `44` | 17:30–20:30 |
| `orders_late_night` | Integer ≥ 0 | `19` | 22:00–02:00 (สำคัญช่วงสอบ) |
| `orders_other` | Integer ≥ 0 | `18` | ช่วงเวลาอื่น |
| `src_recommendation` | Integer ≥ 0 | `55` | `meal_logs.source = "recommendation"` |
| `src_food_scan` | Integer ≥ 0 | `30` | `source = "food_scan"` |
| `src_manual` | Integer ≥ 0 | `57` | `source = "manual"` |
| `unit_price_thb` | Integer | `59` | `price.amount` (Integer THB) |
| `price_confidence` | Factor {`verified`,`estimated`,`unverified`} | `verified` | `price.confidence` |
| `revenue_thb` | Integer | `8378` | `orders_total × unit_price_thb` |
| `kcal_total` | Integer | `107920` | `orders_total × nutrition.calories` |
| `run_id` | String | `A-20260101-v1` | Traceability |

**Integrity Rules:** `orders_total = orders_lunch + orders_dinner + orders_late_night + orders_other = src_recommendation + src_food_scan + src_manual`; ไม่มีแถวซ้ำบนคีย์ (`date`, `menu_item_id`)

### 2.2 `menu_bom_matrix.csv` (Reference — Long Format)

Grain: **1 แถว = 1 เมนู × 1 วัตถุดิบย่อย** (ค่ารวมรายกลุ่มต้องเท่ากับตาราง §1.2)

| คอลัมน์ | ชนิดข้อมูล | ตัวอย่าง | กฎ |
| :--- | :--- | :--- | :--- |
| `menu_item_id` | String (FK) | `hinn-red-pork-rice` | 30 รหัสจริง |
| `restaurant_id` | String (FK) | `hinn-red-pork-rice` | |
| `commodity_group_id` | Integer 1–8 | `1` | G1–G8 |
| `commodity_group_name` | String | `pork_and_cuts` | `pork_and_cuts`, `poultry`, `beef`, `seafood`, `egg_and_tofu`, `carb_base`, `fresh_veg_herbs`, `sauce_seasoning` |
| `sub_commodity` | String | `pork_collar` | รหัสวัตถุดิบย่อย (snake_case) |
| `grams_ep_per_serving` | Numeric (≥ 0, 1 ทศนิยม) | `80.0` | น้ำหนัก EP |
| `yield_factor` | Numeric (0, 1] | `0.90` | §1.5 |
| `grams_ap_per_serving` | Numeric | `88.9` | `grams_ep_per_serving ÷ yield_factor` |
| `perishability_class` | Factor {`ultra`,`high`,`medium`,`low`} | `high` | ultra = อายุ ≤ 1 วัน |
| `assumption_flag` | Factor {`standard`,`ingredients_unknown`,`name_inferred`,`owner_verified`} | `standard` | §1.3 |
| `bom_version` | String | `bom-v1.0` | |

### 2.3 `nakhon_pathom_wholesale_prices.csv` (Reference — Time Series)

Grain: **1 แถว = 1 วัน × 1 วัตถุดิบย่อย**

| คอลัมน์ | ชนิดข้อมูล | ตัวอย่าง | กฎ |
| :--- | :--- | :--- | :--- |
| `date` | Date | `2026-08-17` | ครบ 365 วัน |
| `commodity_group_id` | Integer 1–8 | `4` | |
| `sub_commodity` | String | `salmon_fillet` | ต้องตรงกับ `menu_bom_matrix.sub_commodity` |
| `unit` | Factor {`kg`,`egg`,`litre`} | `kg` | ไข่ไก่ใช้ `egg` แล้วแปลงด้วยน้ำหนักเฉลี่ยต่อฟอง |
| `price_thb_per_unit` | Numeric (2 ทศนิยม) | `640.00` | ราคาขายส่ง (AP) |
| `price_source_type` | Factor {`synthetic`,`observed`} | `synthetic` | MVP = `synthetic` ทั้งหมด |
| `market_ref` | String | `nakhon_pathom_fresh_market` | ระบุตลาดจริงเมื่อเป็น `observed` |
| `scenario_id` | String | `baseline` | `baseline`, `shock_pork_30`, … (§4.3) |

**ช่วงราคาจำลองตั้งต้น (Synthetic Baseline Range, บาท/กก. AP):**

| กลุ่ม | วัตถุดิบย่อย (ช่วงราคาจำลอง) |
| :--- | :--- |
| G1 | หมูสไลซ์/สันคอ 140–170 · หมูสามชั้น 160–190 · หมูสับ 130–150 · ตับหมู 80–110 · หัวใจหมู 90–120 |
| G2 | อก/สะโพกไก่ 70–90 · ปีกไก่ 90–120 · เป็ดทั้งตัว 110–150 |
| G3 | เนื้อวัวสด/ลูกชิ้นเนื้อ 250–320 |
| G4 | กุ้งขาว/กุ้งก้ามกราม 180–380 · แซลมอน 550–750 · ฮามาจิ 900–1,200 · หอยเชลล์โฮตาเตะ 900–1,300 · เนื้อปู 600–900 · ปลาบึก/ปลาน้ำจืด 100–160 · ปลาเนื้อขาว 120–180 · ไข่กุ้ง 800–1,100 |
| G5 | ไข่ไก่ 3.5–5.0 บาท/ฟอง · เต้าหู้ 40–60 |
| G6 | ข้าวสาร 25–40 · ข้าวญี่ปุ่น 60–90 · เส้นก๋วยเตี๋ยว/เฝอ 40–60 · แป้งสาลี 30–45 · ขนมปัง 60–90 · ข้าวโอ๊ต 80–120 |
| G7 | ผักใบ/สมุนไพร 30–80 · ชะอม 60–120 · ผักสลัดไฮโดรโปนิกส์ 120–180 · กล้วยน้ำว้า 25–40 |
| G8 | ซอสถั่วเหลือง/น้ำปลา 40–80 · ซอสซอยการ์ลิค/มายองเนส 90–150 · พริกแกง 80–140 · น้ำมันพืช 45–60 |

> [!WARNING]
> ช่วงราคาข้างต้นเป็น **ค่าจำลองสำหรับทดสอบโมเดลเท่านั้น** ยังไม่ใช่ราคาตลาดจริง ก่อนนำเสนอผลเชิงตัวเลขต่อร้านค้าต้องแทนด้วยข้อมูล `observed` พร้อมระบุแหล่งที่มาและวันที่

### 2.4 `tag_trend_scores.csv` (Module A → Module B, เสริม)

| คอลัมน์ | ชนิดข้อมูล | ความหมาย |
| :--- | :--- | :--- |
| `date` | Date | |
| `menu_item_id` | String (FK) | |
| `eligible_user_share` | Numeric [0,1] | สัดส่วนผู้ใช้ที่เมนูนี้ผ่านตัวกรอง Hard Restriction + Allergen |
| `dislike_penalty_share` | Numeric [0,1] | สัดส่วนผู้ใช้ที่เมนูถูกลดอันดับจาก Dislikes |
| `tag_demand_score` | Numeric [0,100] | คะแนนแนวโน้มความต้องการตาม Tags (คำนวณบน GPU) |
| `restriction_exposure_index` | Numeric [0,1] | ระดับความเสี่ยงที่ Demand ถูกตัดจากข้อจำกัดอาหาร |

---

## 3. R Statistical Models & Formulas

### 3.1 BOM Transformation (จาน → กิโลกรัมจัดซื้อ)

ความต้องการวัตถุดิบกลุ่ม $g$ ของร้าน $r$ ในวัน $t$:

$$
D_{r,g,t} = \frac{1}{1000}\sum_{i \in \mathcal{M}_r} q_{i,t} \times \frac{b^{EP}_{i,g}}{y_g}
$$

- $q_{i,t}$ = `orders_total` ของเมนู $i$ ในวัน $t$
- $b^{EP}_{i,g}$ = กรัม EP ของกลุ่ม $g$ ต่อจาน (§1.2)
- $y_g$ = Yield Factor (§1.5)
- $\mathcal{M}_r$ = เซตเมนู 3 รายการของร้าน $r$

### 3.2 Time-Series Forecasting

**ระดับการพยากรณ์ (Forecast Hierarchy):** (ก) ยอดจานรายเมนูรายวัน → แปลงด้วย BOM และ (ข) พยากรณ์ตรงที่ระดับกลุ่มวัตถุดิบรายร้าน — เลือกระดับที่ MAPE ดีกว่าต่อกลุ่ม

#### 3.2.1 Seasonal ARIMA $(p,d,q)(P,D,Q)_m$

$$
\Phi_P(B^m)\,\phi_p(B)\,(1-B)^d\,(1-B^m)^D\, y_t = c + \Theta_Q(B^m)\,\theta_q(B)\,\varepsilon_t,\qquad \varepsilon_t \sim \mathcal{N}(0,\sigma^2)
$$

โดย $\phi_p(B)=1-\phi_1B-\dots-\phi_pB^p$, $\theta_q(B)=1+\theta_1B+\dots+\theta_qB^q$, $\Phi_P(B^m)=1-\Phi_1B^m-\dots$, $\Theta_Q(B^m)=1+\Theta_1B^m+\dots$ และ $B$ คือ Backshift Operator

| ข้อกำหนด | ค่า |
| :--- | :--- |
| ความถี่ฤดูกาล $m$ | `7` (รอบสัปดาห์ของข้อมูลรายวัน) |
| ผลของปฏิทินการศึกษา | ใช้ **Regression with SARIMA Errors**: $y_t = \beta_0 + \sum_k \beta_k x_{k,t} + \eta_t$ โดย $\eta_t$ เป็น SARIMA และ $x_{k,t}$ = Dummy ของ `academic_period`, `public_holiday` |
| เหตุผล | ข้อมูล 365 วันมีรอบปีเพียง 1 รอบ จึงไม่สามารถประมาณฤดูกาลรายปีได้ — ต้องใช้ตัวแปรปฏิทินแทน |
| การเลือกอันดับ | Auto-selection ตาม AICc (เช่น `forecast::auto.arima` หรือ `fable::ARIMA`), ตรวจ Stationarity ด้วย KPSS |
| การแปลงข้อมูล | Box-Cox / `log1p` สำหรับยอดที่แปรปรวนตามระดับ |

#### 3.2.2 Exponential Smoothing (ETS — Additive Holt-Winters, ฤดูกาล $m=7$)

$$
\begin{aligned}
\text{Forecast:}\quad & \hat{y}_{t+h|t} = \ell_t + h\,b_t + s_{t+h-m(k+1)} \\
\text{Level:}\quad & \ell_t = \alpha\,(y_t - s_{t-m}) + (1-\alpha)(\ell_{t-1} + b_{t-1}) \\
\text{Trend:}\quad & b_t = \beta^{*}(\ell_t - \ell_{t-1}) + (1-\beta^{*})\,b_{t-1} \\
\text{Season:}\quad & s_t = \gamma\,(y_t - \ell_{t-1} - b_{t-1}) + (1-\gamma)\,s_{t-m}
\end{aligned}
$$

โดย $k=\lfloor (h-1)/m \rfloor$ — ให้ระบบเลือกรูปแบบ ETS(Error, Trend, Season) ที่เหมาะสม (A/M, N/A/Ad, N/A/M) ตาม AICc; สำหรับเมนู Premium/Social ที่มีวันยอดศูนย์บ่อย พิจารณา **Croston / TSB** เป็นโมเดลเทียบ

#### 3.2.3 การประเมินโมเดล (Model Evaluation)

$$
\text{MAPE} = \frac{100\%}{n}\sum_{t=1}^{n}\left|\frac{y_t-\hat{y}_t}{y_t}\right| \qquad
\text{Bias} = \frac{\sum_t (\hat{y}_t - y_t)}{\sum_t y_t}
$$

| ข้อกำหนด | ค่า |
| :--- | :--- |
| การแบ่งข้อมูล | Train วันที่ 1–301 · Test วันที่ 302–365 (≈ 9 สัปดาห์) |
| Cross-Validation | Rolling Origin (Time-Series CV), Horizon $h = 7, 14$ วัน |
| เกณฑ์ผ่าน | Economy/Mid MAPE < 10% · Premium/Social < 15% · ช่วงปิดภาค < 20% |
| ข้อควรระวัง | MAPE ไม่นิยามเมื่อ $y_t = 0$ → ใช้ **WAPE** $= \sum|y_t-\hat{y}_t| / \sum y_t$ แทนสำหรับเมนูยอดต่ำ |
| Residual Diagnostics | Ljung-Box Test ($p > 0.05$), ACF ของ Residual ไม่มี Lag ใดเกินขอบ |

### 3.3 Inventory Optimization

**Safety Stock:**

$$
SS_{r,g} = Z_{\alpha} \times \sigma_{d} \times \sqrt{L}
$$

**Reorder Point:**

$$
ROP_{r,g} = (\bar{d} \times L) + SS_{r,g}
$$

| สัญลักษณ์ | ความหมาย | แหล่งค่า |
| :--- | :--- | :--- |
| $\bar{d}$ | ความต้องการเฉลี่ยต่อวัน (กก./วัน) ในช่วง Lead Time | ค่าพยากรณ์ Point Forecast ของ **ช่วงการศึกษาที่จะมาถึง** (ไม่ใช่ค่าเฉลี่ยทั้งปี) |
| $\sigma_d$ | ส่วนเบี่ยงเบนมาตรฐานของความต้องการรายวัน | ส่วนเบี่ยงเบนมาตรฐานของ Forecast Residual ใน Test Set |
| $L$ | Lead Time (วัน) | §1.5 |
| $Z_\alpha$ | ค่ามาตรฐานตาม Service Level | §1.5 |

**ส่วนขยาย (กรณี Lead Time ผันผวน):** $SS = Z_\alpha\sqrt{L\,\sigma_d^2 + \bar{d}^2\,\sigma_L^2}$

**ปริมาณสั่งแนะนำ (Perishable Cap):**

$$
Q^{*}_{r,g} = \min\Big(\; \textstyle\sum_{h=1}^{L+R}\hat{d}_{t+h} + SS - I_t,\;\; \textstyle\sum_{h=1}^{S_g}\hat{d}_{t+h} \Big)
$$

โดย $R$ = รอบการทบทวนสต็อก (วัน), $I_t$ = สต็อกคงเหลือ, $S_g$ = อายุการเก็บของกลุ่ม $g$ — เพดานด้านขวาป้องกันการสั่งเกินกว่าที่จะใช้ทันก่อนเสีย

### 3.4 Menu Engineering Matrix (Kasavana & Smith)

**ต้นทุนวัตถุดิบต่อจาน:**

$$
FC_i = \sum_{g}\sum_{s \in g} \frac{b^{EP}_{i,s}}{1000\,y_s} \times P_{s,t}
\qquad
\text{Food Cost \%}_i = \frac{FC_i}{\text{price}_i} \times 100
$$

**Contribution Margin:** $CM_i = \text{price}_i - FC_i$

**Popularity (Menu Mix %):** $MM_i = q_i \,/\, \sum_{j \in \mathcal{M}} q_j$

| เกณฑ์ | สูตร |
| :--- | :--- |
| ความนิยมสูง | $MM_i \ge 0.70 \times \dfrac{1}{N}$ ($N$ = จำนวนเมนูในชุดวิเคราะห์) |
| กำไรสูง | $CM_i \ge \overline{CM}_w = \dfrac{\sum_i CM_i\,q_i}{\sum_i q_i}$ (ค่าเฉลี่ยถ่วงน้ำหนักยอดขาย) |

| Quadrant | ความนิยม | กำไร (CM) | กลยุทธ์ที่แนะนำ |
| :--- | :-: | :-: | :--- |
| ⭐ **Stars** | สูง | สูง | รักษาคุณภาพและตำแหน่ง ไม่ขึ้นราคาในช่วงวิกฤตหากเลี่ยงได้ |
| 🐴 **Plowhorses** | สูง | ต่ำ | ปรับสูตร/สัดส่วนวัตถุดิบแพง, ขึ้นราคาเล็กน้อยแบบค่อยเป็นค่อยไป, จับคู่ขายกับเมนูกำไรสูง |
| 🧩 **Puzzles** | ต่ำ | สูง | เพิ่มการมองเห็น (ยืนยันราคาเป็น `verified`, ยืนยันสารก่อภูมิแพ้), โปรโมชันช่วงเย็น/สุดสัปดาห์ |
| 🐶 **Dogs** | ต่ำ | ต่ำ | พิจารณาถอดออก ปรับใหม่ หรือขายเฉพาะช่วง Demand สูง |

**ระดับการวิเคราะห์ 2 ชั้น:**
1. **Within-Restaurant** ($N = 3$, เกณฑ์ความนิยม $MM \ge 23.3\%$) — ใช้ตัดสินใจภายในร้าน
2. **Within-Tier Benchmark** (เทียบเมนูใน Tier เดียวกันข้ามร้าน) — ใช้เทียบความสามารถแข่งขันด้านราคา ไม่ใช้รวม 30 เมนูในชุดเดียวเพราะราคา 40–800 บาทต่างกันมากเกินไป

---

## 4. Anticipate Edge Cases (การจัดการกรณีสุดขั้วในโมเดล)

### 4.1 วงจรปฏิทินการศึกษา ม.ศิลปากร

> [!IMPORTANT]
> วันที่แต่ละช่วงต้องกำหนดใน `config/academic_calendar.yaml` ตาม **ปฏิทินการศึกษาทางการของมหาวิทยาลัยศิลปากรปีที่ใช้งาน** เอกสารนี้กำหนดเฉพาะโครงสร้างและตัวคูณ Demand

| ช่วง (`academic_period`) | ตัวคูณ Demand เทียบ `regular` | การเปลี่ยนแปลง Pattern | การจัดการในโมเดล |
| :--- | :-: | :--- | :--- |
| `regular` (เปิดเทอมปกติ) | 1.00 | Lunch Peak เด่น, Economy สูงในวันเรียน | Baseline |
| `midterm_exam` / `final_exam` | 1.10–1.30 (รวม) | `orders_late_night` เพิ่ม ×2–3 (ป้าจ๋า 23 ชั่วโมงได้รับผลมากสุด), Social Tier ลดลงระหว่างสอบแล้วพุ่งหลังสอบวันสุดท้าย | Dummy ใน Regression + แยกพยากรณ์ช่วงดึก |
| `semester_break` | **0.20–0.40** (Demand ลดลง 60–80%) | ร้านรอบ ม. (ถ.ทรงพล, ถ.ราชมรรคาใน) ลดมาก; ร้านบน ถ.เพชรเกษม/ลุงลอย ลดน้อยกว่า (ลูกค้าครอบครัว) | Dummy + **Structural Break**: รีเซ็ต SS/ROP ทันทีเมื่อเข้าสู่ช่วง และลด Service Level กลุ่ม G4/G7 |
| `summer_session` | 0.40–0.60 | นักศึกษาบางส่วน | Dummy แยก |
| `public_holiday` / วันหยุดยาว | 0.30–0.70 | ใกล้เคียงปิดภาคระยะสั้น | Dummy วันหยุด |
| สัปดาห์เปลี่ยนผ่าน (ก่อน/หลังเปิดเทอม) | Ramp แบบเส้นตรง 5–7 วัน | Demand ไต่ระดับ | ป้องกันโมเดลตอบสนองช้า: ใช้ Calendar Regressor ล่วงหน้า แทนการรอ Residual |

**กฎความปลอดภัย:** ห้ามคำนวณ $\bar{d}$ และ $\sigma_d$ จากข้อมูลข้ามช่วง (เช่น รวมปิดเทอมกับเปิดเทอม) เพราะจะทำให้ SS สูงเกินจริงในช่วงปิดเทอมและต่ำเกินจริงในช่วงสอบ

### 4.2 พฤติกรรมการคัดกรองของผู้ใช้ (Recommendation Filter Effects)

#### 4.2.1 `allergensKnown: false` — Hard Cut สำหรับผู้มีอาการแพ้

| ข้อเท็จจริงจาก Seed Data | ผลกระทบ |
| :--- | :--- |
| ทั้ง 30 เมนูมี `allergensKnown: false` | ผู้ใช้ที่ระบุ `allergies` อย่างน้อย 1 รายการ จะ **ไม่ได้รับคำแนะนำเมนูใดเลย** ในระบบ MueNee (นโยบายไม่ผ่อนปรน) |
| | Demand ของกลุ่มนี้ **หลุดออกจาก `source = "recommendation"`** ไปปรากฏเป็น `food_scan` / `manual` หรือหายไปจากระบบ |

**การจัดการในโมเดล:**
- Module A จำลองสัดส่วนผู้ใช้ที่มี Allergy (พารามิเตอร์ $\pi_{allergy}$) และส่ง Demand ของกลุ่มนี้ไปยัง `src_manual`/`src_food_scan` ด้วยความน่าจะเป็นที่ลดลง
- รายงานตัวชี้วัด **Allergen-Blocked Demand** = ยอดที่ "น่าจะเกิดได้" หากร้านยืนยันข้อมูลสารก่อภูมิแพ้ → ใช้เป็นเหตุผลเชิงธุรกิจให้ร้านยืนยันข้อมูล (Upside Opportunity)
- พยากรณ์ต้องใช้ `orders_total` (ทุก source) ไม่ใช่เฉพาะ `src_recommendation` เพื่อไม่ประเมิน Demand ต่ำเกินจริง

#### 4.2.2 Hard Restrictions ที่ตัดทั้ง Catalog

| ข้อจำกัด | เมนูที่ผ่านตัวกรอง | เหตุผล |
| :--- | :-: | :--- |
| `halal_only` | 0 / 30 | ทุกเมนู `halalConfirmed: false` |
| `vegetarian` | 0 / 30 | ทุกเมนู `vegetarianConfirmed: false` |
| `no_pork` | 23 / 30 | ตัด 7 เมนูที่มี `pork` ใน `ingredients` (มาดามโฮ 2 ชุด, ลุงลอยแกงจืด, ร้านฮิ้น 2, ท่าสนาม 2) — ⚠️ `thasanam-spicy-liver` ระบุเพียง `offal` จึง **ไม่ถูกตัด** ทั้งที่ BOM แมปเป็นตับหมู (G1) → รายงานเป็น Data Gap ให้ร้านเพิ่ม `pork` ใน `ingredients` |
| `no_beef` | 29 / 30 | ตัด `thasanam-boat-noodle-soup` |

#### 4.2.3 `price.confidence: "unverified"` — Choice Penalty

ความน่าจะเป็นที่ผู้ใช้ $u$ เลือกเมนู $i$ (Multinomial Logit ใน Module A):

$$
P(i \mid u) = \frac{\exp(V_{u,i})}{\sum_{j \in \mathcal{E}_u}\exp(V_{u,j})},\qquad
V_{u,i} = \beta_{tag}\,S_{u,i} - \beta_{price}\,\frac{\text{price}_i}{\text{budget}_u} - \lambda\,\mathbb{1}[\text{unverified}_i] - \delta\,\mathbb{1}[\text{disliked}_{u,i}]
$$

- $\mathcal{E}_u$ = เซตเมนูที่ผ่าน Hard Restriction + Allergen + งบ `MealBudget` (1–10,000 บาท)
- $\lambda$ = ค่าปรับความไม่เชื่อมั่นของราคา (ทดสอบ Sensitivity ที่ $\lambda \in \{0, 0.25, 0.5, 1.0\}$)
- $\delta$ = ค่าปรับ Dislike (Soft) — หาก `hideDisliked: true` ให้ตัดออกจาก $\mathcal{E}_u$
- เมนู `unverified` 15 รายการ (กุ้งอบภูเขาไฟ, Good Food, KinKane 89, ร้านฮิ้น, ท่าสนาม) จะถูกวิเคราะห์ **Verification Uplift** = ยอดที่เพิ่มขึ้นหากเปลี่ยนเป็น `verified`

#### 4.2.4 Dislikes ที่สำคัญเชิงสต็อก

| Dislike | เมนูที่ได้รับผลกระทบโดยตรง (จาก `ingredients`) |
| :--- | :--- |
| `offal` | `thasanam-spicy-liver` |
| `coriander` | `thasanam-spicy-pork`, `thasanam-spicy-liver` |
| `shellfish` | `volcano-baked-prawn`, `volcano-three-armies-salad`, `volcano-sour-curry-prawn-omelette`, `tama-kani-miso-set`, `tama-salmon-ebiko-sauce-rice`, `loong-loy-large-crab-fried-rice`, `kinkane-scallop-sashimi` |
| `mushroom`, `milk` | ไม่มีเมนูใดระบุใน `ingredients` (ข้อมูลไม่ครบ — `ingredientsKnown: false`) → ตั้งค่าผลกระทบเป็นศูนย์และบันทึกเป็นข้อจำกัด |

### 4.3 วิกฤตราคาวัตถุดิบตลาดสดนครปฐมพุ่งสูงผิดปกติ (Price Shock Simulation)

**ชุดสถานการณ์กำหนด (Deterministic Scenarios):**

| `scenario_id` | กลุ่มที่ได้รับผลกระทบ | ขนาด Shock | ระยะเวลา | ร้าน/เมนูที่เปราะบางที่สุด (คาดการณ์เพื่อทดสอบ) |
| :--- | :--- | :-: | :-: | :--- |
| `shock_pork_30` | G1 | +30% | 8 สัปดาห์ | ร้านฮิ้น, ท่าสนาม (Economy, ราคาคงที่ 40–60 บาท), มาดามโฮ |
| `shock_poultry_25` | G2 | +25% | 6 สัปดาห์ | ป้าจ๋า (59–69 บาท), Bonchon |
| `shock_seafood_40` | G4 | +40% | 4 สัปดาห์ | KinKane 89, กุ้งอบภูเขาไฟ, TAMA |
| `shock_veg_50` | G7 | +50% | 3 สัปดาห์ | แกงส้มชะอมกุ้ง, ยำสามทัพ, ร้านท่าสนาม (ผักเคียง) |
| `shock_combined` | G1 +20%, G2 +15%, G7 +30%, G8 +10% | ผสม | 8 สัปดาห์ | ทุก Economy Tier |

**การจำลองแบบ Monte Carlo (Stochastic):**

$$
P_{s,t}^{shock} = P_{s,t}^{base}\times\exp(\mu_g + \sigma_g Z_t),\quad Z_t\sim\mathcal{N}(0,1)
$$

จำลอง 10,000 รอบ เพื่อหาการกระจายของ Gross Margin และความน่าจะเป็นที่เมนูจะย้าย Quadrant

**ผลลัพธ์ที่ต้องรายงานต่อสถานการณ์:**

| ตัวชี้วัด | สูตร |
| :--- | :--- |
| Δ Food Cost % ต่อเมนู | $\text{FC\%}^{shock}_i - \text{FC\%}^{base}_i$ |
| Δ Gross Margin ต่อร้าน (บาท/สัปดาห์) | $\sum_i q_i\,(CM^{shock}_i - CM^{base}_i)$ |
| Break-even Price | ราคาขั้นต่ำที่คง Food Cost % เดิม = $FC^{shock}_i / \text{FC\%}^{base}_i$ |
| Price Elasticity Guardrail | ประเมินยอดที่หายไปหากขึ้นราคา โดยใช้ $\beta_{price}$ จาก §4.2.3 — Economy Tier ใช้ค่า Elasticity สูงกว่า |
| Quadrant Migration | เมนูที่ย้ายจาก Stars → Plowhorses หรือ Puzzles → Dogs |

**ลำดับคำแนะนำเชิงธุรกิจ (Response Playbook):** 1) ปรับสัดส่วนสูตร (ลด G ที่แพงขึ้น เพิ่ม G7/G6) → 2) ดันเมนูทดแทนในร้านเดียวกันที่ใช้กลุ่มวัตถุดิบอื่น → 3) จัดซื้อร่วม (Consolidated Procurement) ระหว่างร้านในรัศมี 3 กม. → 4) ขึ้นราคาเฉพาะเมนู Premium/Social ที่ความอ่อนไหวต่ำกว่า → 5) ขึ้นราคา Economy เป็นทางเลือกสุดท้าย

### 4.4 Edge Cases ด้านข้อมูลอื่น ๆ

| กรณี | การจัดการ |
| :--- | :--- |
| วันที่ยอด = 0 (เมนู Social ในวันธรรมดา) | เก็บเป็น 0 ใน CSV, ใช้ WAPE แทน MAPE, ทดสอบ Croston/TSB |
| ร้านปิดชั่วคราว (`isActive: false`) | ทำเครื่องหมาย Missing (NA) ไม่ใช่ 0 เพื่อไม่ให้โมเดลเรียนรู้ว่าไม่มี Demand |
| เขตเวลา | `createdAt` เก็บเป็น UTC ต้องแปลงเป็น Asia/Bangkok ก่อนตัดวัน — มื้อดึก 00:00–02:00 นับเป็นวันใหม่ตามปฏิทิน |
| Outlier (งานรับปริญญา, งานคณะ) | ตรวจจับด้วย STL Residual > 3σ แล้วใช้ Dummy Event แทนการลบทิ้ง |
| เมนูราคาเฉพาะชุดแชร์ (เช่น `volcano-baked-prawn` 800 บาท) | 1 หน่วยบริโภค = 1 ชุด/จาน ไม่แปลงเป็นต่อคน เพื่อให้ BOM สอดคล้อง |
| ราคา `MealBudget` ผิดรูปแบบ | ยึด Invariant ของ MueNee: Integer 1–10,000 บาทเท่านั้น ปฏิเสธทศนิยม/ค่าติดลบ |