# MueNee B2B Analytics: Domain Context & Data Schema Specification

เอกสารฉบับนี้จัดทำขึ้นโดย Data Architect เพื่อสกัดแก่นข้อมูลทางธุรกิจ (Business Core), พฤติกรรมผู้บริโภค (Consumer Constraints), แคตตาล็อกข้อมูลจริง (Seed Catalog), และโครงสร้างฐานข้อมูล (Firestore Schema) จากระบบ MueNee เพื่อใช้เป็น Context ตั้งต้นสำหรับการออกแบบและพัฒนาระบบ **MueNee-b2b-analytics** (ระบบพยากรณ์สต็อกและราคาวัตถุดิบสำหรับร้านอาหาร)

---

## 1. Target Context & Location (บริบทพื้นที่และกลุ่มเป้าหมาย)

### 1.1 พิกัดและขอบเขตพื้นที่ให้บริการ (Geographical Scope)
* **พื้นที่เป้าหมายหลัก (MVP Area):** มหาวิทยาลัยศิลปากร วิทยาเขตพระราชวังสนามจันทร์ และชุมชนโดยรอบ ตำบลสนามจันทร์, ตำบลลำพยา, ตำบลพระปฐมเจดีย์ อำเภอเมือง จังหวัดนครปฐม
* **จุดศูนย์กลาง (Center Coordinates):** 
  * ละติจูด (Latitude): `13.8199`
  * ลองจิจูด (Longitude): `100.0443`
* **รัศมีบริการสูงสุด (Maximum Radius Boundary):** ไม่เกิน `3.0 กิโลเมตร` จากจุดศูนย์กลาง
* **ถนนและย่านร้านอาหารสำคัญรอบมหาวิทยาลัย:**
  * **ถนนทรงพล (หน้ามหาวิทยาลัยศิลปากร):** แหล่งรวมร้านอาหารจานด่วน, ชาบู/เฝอหม้อไฟ, แบรนด์แฟรนไชส์
  * **ถนนยิงเป้า:** แหล่งรวมร้านอาหารเพื่อสุขภาพ, คาเฟ่, อาหารจานเดียว
  * **ถนนจันทรคามพิทักษ์:** แหล่งอาหารญี่ปุ่น, ร้านอาหารตามสั่ง, ร้านขวัญใจนักศึกษา
  * **ถนนราชมรรคาใน (หน้าโรงเรียนสาธิต ม.ศิลปากร):** แหล่งอาหารเช้าและกลางวันยอดนิยม (ข้าวหมูแดง, ก๋วยเตี๋ยวเรือ)
  * **ถนนเพชรเกษม / ตลาด Meeting Point:** แหล่งร้านอาหารขนาดใหญ่สำหรับครอบครัวและกลุ่มสังสรรค์

### 1.2 กลุ่มผู้ใช้หลัก (Consumer Demographics)
* **นักศึกษามหาวิทยาลัยศิลปากร (Undergraduate & Graduate Students):** ผู้บริโภคกลุ่มใหญ่ที่สุด มีความถี่ในการบริโภคอาหารนอกบ้านสูงทั้ง 3 มื้อ
* **คณาจารย์และบุคลากรมหาวิทยาลัย (Faculty & Staff):** ผู้บริโภคมื้อกลางวันสม่ำเสมอในวันทำการ
* **ผู้อยู่อาศัยในหอพักและชุมชนโดยรอบ:** สั่งอาหารเดลิเวอรีและรับประทานมื้อค่ำ

### 1.3 เงื่อนไขและปัจจัยขับเคลื่อนอุปสงค์ (Demand Drivers & University Context)
1. **ความอ่อนไหวต่อราคา (High Price Sensitivity):** กำลังซื้อของนักศึกษาส่วนใหญ่อยู่ในระดับจำกัด เมนูประจำวันต้องควบคุมงบประมาณอย่างเข้มงวด การขึ้นราคาวัตถุดิบจะกระทบต่ออัตราการสั่งซื้อโดยตรง
2. **วงจรเวลาการบริโภค (Temporal Patterns):**
   * *Peak Hours:* กลางวัน (11:30 - 13:30 น.) เน้นอาหารจานด่วน และค่ำ (17:30 - 20:30 น.) เริ่มมีมื้อสังสรรค์/หม้อไฟ
   * *วงจรการศึกษา (Academic Calendar):* ช่วงเปิดเทอมปกติ (High Demand), สัปดาห์สอบกลางภาค/ปลายภาค (Peak Demand & ดึก), ช่วงปิดภาคเรียน (Low Demand สำหรับร้านรอบ ม.)
3. **รูปแบบมื้ออาหาร:**
   * *มื้อเดี่ยวประจำวัน (Individual Daily Meals):* อาหารจานเดียว เช่น ข้าวมันไก่, ข้าวหมูแดง, ก๋วยเตี๋ยวเรือ
   * *มื้อสังสรรค์กลุ่ม (Shared / Social Meals):* เฝอหม้อไฟ, กุ้งอบภูเขาไฟ, ข้าวผัดจานใหญ่

---

## 2. Menu & Nutrition Schema (ข้อมูลร้านค้า เมนู โภชนาการ และวัตถุดิบ)

ข้อมูลทั้งหมดถูกตรวจสอบและบันทึกอยู่ในระดับ Seed Data จริงของระบบ MueNee มีจำนวน 10 ร้านค้า และ 30 เมนู (3 เมนูต่อร้าน)

### 2.1 รายชื่อร้านค้าตัวอย่าง (10 Restaurants Catalog)

1. **มาดามโฮ เฝอหม้อไฟ หน้า ม.ศิลปากร นครปฐม**
   * Document ID: `madam-ho-sanamchan`
   * Google Place ID: `ChIJOzc6os3l4jARB84YKHWyoj8`
   * พิกัด: Lat `13.8140352`, Lng `100.0391741`
   * ที่อยู่: 119/7 ถนนทรงพล ตำบลลำพยา อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.6` | สถานะ: `verified`, `isActive: true`
2. **กุ้งอบภูเขาไฟ**
   * Document ID: `volcano-prawn`
   * Google Place ID: `ChIJQRxWKtTl4jAR4dIrcJVbBSU`
   * พิกัด: Lat `13.8042573`, Lng `100.0413817`
   * ที่อยู่: ตำบลสนามจันทร์ อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.5` | สถานะ: `verified`, `isActive: true`
3. **Bonchon Sanamchan Nakornpathom**
   * Document ID: `bonchon-sanamchan`
   * Google Place ID: `ChIJARhVkYHl4jARhYnz8mp33KM`
   * พิกัด: Lat `13.8141035`, Lng `100.0392829`
   * ที่อยู่: 119/2-4 ถนนทรงพล ตำบลลำพยา อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.5` | สถานะ: `verified`, `isActive: true`
4. **ข้าวมันไก่ป้าจ๋า 23 ชั่วโมง**
   * Document ID: `pa-ja-23-hours`
   * Google Place ID: `ChIJTbm7PNDl4jARKfIvSUP5ixs`
   * พิกัด: Lat `13.8114221`, Lng `100.0454665`
   * ที่อยู่: ตำบลพระปฐมเจดีย์ อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.9` | สถานะ: `verified`, `isActive: true`
5. **Good Food**
   * Document ID: `good-food-nakhon-pathom`
   * Google Place ID: `ChIJl6DyJeXl4jARDcSJ6SNjmho`
   * พิกัด: Lat `13.8147462`, Lng `100.0453114`
   * ที่อยู่: ถนนยิงเป้า ตำบลพระปฐมเจดีย์ อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.9` | สถานะ: `verified`, `isActive: true`
6. **TAMA Japanese Restaurant นครปฐม**
   * Document ID: `tama-nakhon-pathom`
   * Google Place ID: `ChIJMXeGyofl4jARtF1x3H7FTiE`
   * พิกัด: Lat `13.8142539`, Lng `100.040768`
   * ที่อยู่: 135/2 ห้อง 4 ตลาด Meeting Point ถนนสนามจันทร์ อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.8` | สถานะ: `verified`, `isActive: true`
7. **ลุงลอยป่าลั่น**
   * Document ID: `loong-loy-pa-lan`
   * Google Place ID: `ChIJ0cCqC93l4jARxhtbq33DscA`
   * พิกัด: Lat `13.8092718`, Lng `100.0569076`
   * ที่อยู่: 1010 ถนนเพชรเกษม ตำบลสนามจันทร์ อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.2` | สถานะ: `verified`, `isActive: true`
8. **KinKane 89**
   * Document ID: `kinkane-89`
   * Google Place ID: `ChIJv7nnqtHl4jARMx1ojcJc7mU`
   * พิกัด: Lat `13.8109457`, Lng `100.0432165`
   * ที่อยู่: 64 ถนนจันทรคามพิทักษ์ ตำบลสนามจันทร์ อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.4` | สถานะ: `verified`, `isActive: true`
9. **ร้านฮิ้น ข้าวหมูแดง**
   * Document ID: `hinn-red-pork-rice`
   * Google Place ID: `ChIJxSbXEM_l4jARwM4F82AYm_0`
   * พิกัด: Lat `13.8161391`, Lng `100.0452057`
   * ที่อยู่: ถนนราชมรรคาใน ใกล้โรงเรียนสาธิต ม.ศิลปากร อำเภอเมืองนครปฐม นครปฐม 73000
   * เรตติ้ง: `4.3` | สถานะ: `verified`, `isActive: true`
10. **ก๋วยเตี๋ยวเรือ ท่าสนาม THASANAM**
    * Document ID: `thasanam-boat-noodles`
    * Google Place ID: `ChIJQQMnDs_l4jARYfvOanBx37c`
    * พิกัด: Lat `13.8157152`, Lng `100.045282`
    * ที่อยู่: ถนนราชมรรคาใน หน้าโรงเรียนสาธิต ม.ศิลปากร อำเภอเมืองนครปฐม นครปฐม 73000
    * เรตติ้ง: `4.3` | สถานะ: `verified`, `isActive: true`

---

### 2.2 รายการเมนูและโภชนาการแบบละเอียด (30 Menu Items Seed Data)

| Restaurant ID | Menu Item ID | ชื่อเมนู | หมวดหมู่ (Tags) | ราคา (THB) | สถานะราคา | Cal (kcal) | Pro (g) | Carb (g) | Fat (g) | วัตถุดิบ (Ingredients) | สารก่อภูมิแพ้ (Allergens) |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| `madam-ho-sanamchan` | `madam-ho-pork-crunch-set` | ชุดหมูกรุบกริบ | `hot-pot`, `vietnamese`, `shared` | 359 | verified | 980 | 55 | 75 | 50 | pork | soy, sesame |
| `madam-ho-sanamchan` | `madam-ho-paper-pot-pho` | เฝอหม้อกระดาษ | `hot-pot`, `noodles`, `vietnamese` | 399 | verified | 920 | 48 | 105 | 34 | - | soy, wheat |
| `madam-ho-sanamchan` | `madam-ho-soft-pork-heart-set` | ชุดหมูขนุ้มหัวใจ | `hot-pot`, `vietnamese`, `shared` | 499 | verified | 1120 | 68 | 82 | 58 | pork | soy, sesame |
| `volcano-prawn` | `volcano-baked-prawn` | กุ้งอบภูเขาไฟ | `seafood`, `shared`, `signature` | 800 | unverified | 760 | 88 | 30 | 32 | shellfish | shellfish |
| `volcano-prawn` | `volcano-three-armies-salad` | ยำสามทัพ | `seafood`, `spicy`, `salad` | 250 | unverified | 420 | 38 | 28 | 18 | shellfish, fish | shellfish, fish |
| `volcano-prawn` | `volcano-sour-curry-prawn-omelette` | แกงส้มชะอมกุ้ง | `thai`, `spicy`, `curry` | 180 | unverified | 510 | 34 | 32 | 27 | shellfish, egg | shellfish, egg, fish |
| `bonchon-sanamchan` | `bonchon-wings-6` | ปีกไก่บอนชอน 6 ชิ้น | `korean`, `fried`, `chicken` | 199 | verified | 640 | 42 | 44 | 33 | chicken | soy, wheat, sesame |
| `bonchon-sanamchan` | `bonchon-chicken-rice-soy-garlic` | ชุดข้าวกล่องไก่บอนชอน ซอยการ์ลิค | `korean`, `rice`, `chicken` | 229 | verified | 790 | 40 | 98 | 28 | chicken | soy, wheat, sesame |
| `bonchon-sanamchan` | `bonchon-fish-rice-hot` | ชุดข้าวกล่องปลาทอดบอนชอน ฮอท | `korean`, `rice`, `fish`, `spicy` | 259 | verified | 760 | 34 | 105 | 23 | fish | fish, soy, wheat, sesame |
| `pa-ja-23-hours` | `pa-ja-boiled-chicken-rice` | ข้าวไก่ต้ม | `thai`, `rice`, `chicken` | 59 | verified | 610 | 32 | 78 | 18 | chicken | soy |
| `pa-ja-23-hours` | `pa-ja-fried-chicken-rice` | ข้าวไก่ทอด | `thai`, `rice`, `fried`, `chicken` | 59 | verified | 760 | 34 | 88 | 29 | chicken | soy, wheat |
| `pa-ja-23-hours` | `pa-ja-spicy-chicken-rice` | ข้าวยำไก่แซ่บ | `thai`, `rice`, `spicy`, `chicken` | 69 | verified | 690 | 35 | 91 | 21 | chicken | fish, wheat |
| `good-food-nakhon-pathom` | `good-food-custom-sandwich` | แซนด์วิชเลือกไส้ | `healthy`, `sandwich` | 109 | unverified | 430 | 22 | 48 | 17 | - | wheat, egg, milk |
| `good-food-nakhon-pathom` | `good-food-banana-oat-loaf` | โลฟโอ๊ตกล้วยน้ำว้า | `healthy`, `bakery`, `snack` | 59 | unverified | 260 | 6 | 44 | 8 | - | wheat, egg, milk |
| `good-food-nakhon-pathom` | `good-food-salmon-salad-rice` | Salad Rice Salmon | `healthy`, `rice`, `salmon` | 159 | unverified | 520 | 29 | 61 | 18 | fish | fish, soy, sesame |
| `tama-nakhon-pathom` | `tama-kani-miso-set` | คานิมิโซะ | `japanese`, `rice`, `crab` | 169 | verified | 590 | 25 | 72 | 22 | shellfish | shellfish, soy, egg |
| `tama-nakhon-pathom` | `tama-salmon-ebiko-sauce-rice` | ข้าวแซลมอนซอสไข่กุ้ง | `japanese`, `rice`, `salmon` | 159 | verified | 650 | 31 | 80 | 23 | fish, shellfish | fish, shellfish, soy, egg |
| `tama-nakhon-pathom` | `tama-torched-salmon-mayo-rice` | ข้าวแซลมอนเบิร์นมาโย | `japanese`, `rice`, `salmon` | 159 | verified | 720 | 31 | 82 | 29 | fish, egg | fish, egg, soy |
| `loong-loy-pa-lan` | `loong-loy-tofu-pork-soup` | แกงจืดเต้าหู้หมูสับ เล็ก | `thai`, `soup` | 80 | verified | 310 | 23 | 16 | 17 | pork | soy |
| `loong-loy-pa-lan` | `loong-loy-large-crab-fried-rice` | ข้าวผัดปู ใหญ่ | `thai`, `rice`, `shared` | 150 | verified | 880 | 35 | 122 | 27 | shellfish, egg | shellfish, egg, soy |
| `loong-loy-pa-lan` | `loong-loy-jungle-catfish-curry` | แกงป่าปลาบึก ชาม | `thai`, `curry`, `spicy`, `fish` | 80 | verified | 330 | 31 | 19 | 14 | fish | fish |
| `kinkane-89` | `kinkane-salmon-sashimi` | แซลมอนซาชิมิ | `japanese`, `sashimi`, `salmon` | 220 | unverified | 250 | 30 | 2 | 14 | fish | fish, soy |
| `kinkane-89` | `kinkane-hamachi-sashimi` | ฮามาจิซาชิมิ | `japanese`, `sashimi` | 280 | unverified | 270 | 29 | 1 | 17 | fish | fish, soy |
| `kinkane-89` | `kinkane-scallop-sashimi` | โฮตาเตะซาชิมิ | `japanese`, `sashimi`, `shellfish` | 250 | unverified | 170 | 27 | 8 | 3 | shellfish | shellfish, soy |
| `hinn-red-pork-rice` | `hinn-red-pork-rice` | ข้าวหมูแดง | `thai`, `rice`, `pork` | 60 | unverified | 650 | 29 | 86 | 21 | pork, egg | egg, soy, wheat |
| `hinn-red-pork-rice` | `hinn-crispy-pork-rice` | ข้าวหมูกรอบ | `thai`, `rice`, `pork` | 60 | unverified | 780 | 30 | 84 | 36 | pork, egg | egg, soy, wheat |
| `hinn-red-pork-rice` | `hinn-roast-duck-rice` | ข้าวหน้าเป็ด | `thai`, `rice`, `duck` | 60 | unverified | 720 | 32 | 83 | 28 | egg | egg, soy, wheat |
| `thasanam-boat-noodles` | `thasanam-boat-noodle-soup` | ก๋วยเตี๋ยวเรือน้ำ | `thai`, `noodles`, `soup` | 40 | unverified | 410 | 23 | 57 | 10 | pork, beef | soy, wheat |
| `thasanam-boat-noodles` | `thasanam-spicy-pork` | หมูแซ่บนัว | `thai`, `spicy`, `pork` | 60 | unverified | 460 | 34 | 25 | 25 | pork, coriander | fish |
| `thasanam-boat-noodles` | `thasanam-spicy-liver` | ตับแซ่บนัว | `thai`, `spicy`, `offal` | 60 | unverified | 390 | 31 | 22 | 20 | offal, coriander | fish |

*หมายเหตุ:* ข้อมูลใน Seed Data ชุดนี้ ทุกเมนูมี `ingredientsKnown: false`, `allergensKnown: false`, `vegetarianConfirmed: false`, `halalConfirmed: false`, และ `isActive: true` ตามนโยบาย Conservative Data Safety

---

### 2.3 วัตถุดิบหลักจำแนกตามกลุ่มสินค้าเพื่อการพยากรณ์ (Commodity Mapping for Stock & Cost Modeling)

เพื่อเชื่อมโยงความต้องการของผู้บริโภค (Consumer Demand) ไปสู่อุปสงค์วัตถุดิบ (Raw Material Inventory Requirements) สามารถจัดกลุ่มวัตถุดิบหลักได้ดังนี้:

1. **กลุ่มเนื้อสุกรและชิ้นส่วน (Pork & Cuts):**
   * *ชิ้นส่วน:* หมูสไลซ์ (สำหรับชาบู/เฝอ), สันคอ/สันนอกหมู (หมูแดง), หมูสามชั้น (หมูกรอบ), หมูสับ (แกงจืด), หมูหมัก (ก๋วยเตี๋ยวเรือ)
   * *เครื่องในหมู:* ตับหมูสด (ตับแซ่บนัว, ก๋วยเตี๋ยวเรือ), หัวใจหมู (ชุดเฝอ)
2. **กลุ่มสัตว์ปีก (Poultry):**
   * *ไก่สด:* ปีกไก่บน/ปีกกลาง (ไก่ทอดบอนชอน), น่อง/สะโพก/อกไก่สด (ข้าวมันไก่ต้ม, ข้าวมันไก่ทอด, ข้าวยำไก่แซ่บ)
   * *เป็ด:* เป็ดสดสำหรับย่าง/พะโล้ (ข้าวหน้าเป็ด)
3. **กลุ่มเนื้อโค (Beef):**
   * เนื้อวัวสด, เนื้อเปื่อย, ลูกชิ้นเนื้อ (ก๋วยเตี๋ยวเรือ)
4. **กลุ่มสัตว์น้ำและอาหารทะเลสด (Seafood & Marine Commodities):**
   * กุ้งก้ามกรามสด / กุ้งขาว (กุ้งอบภูเขาไฟ, แกงส้มชะอมกุ้ง)
   * ปลาแซลมอนสด (Salad Rice, ข้าวหน้าแซลมอน, ซาชิมิ)
   * ปลาฮามาจิสด (ซาชิมิ)
   * หอยเชลล์โฮตาเตะ (ซาชิมิ)
   * ปูม้า/เนื้อปูแกะ, มันปูคานิมิโซะ
   * ปลาบึก / ปลาน้ำจืด (แกงป่าปลาบึก)
   * ไข่กุ้ง (Ebiko)
5. **กลุ่มไข่และผลิตภัณฑ์ถั่วเหลือง (Eggs & Soy/Tofu):**
   * ไข่ไก่สด (เบอร์ 2/3): ไข่ต้ม (ข้าวมันไก่, ข้าวหมูแดง), ไข่เจียวชะอม, ข้าวผัด, ส่วนผสมเบเกอรี่/แป้งชุบทอด
   * เต้าหู้ขาว/เต้าหู้ไข่ (แกงจืด)
6. **กลุ่มคาร์โบไฮเดรตหลัก (Carbohydrate Base Stocks):**
   * ข้าวสาร (ข้าวหอมมะลิ, ข้าวขาวสำหรับข้าวมันและข้าวผัด)
   * เส้นก๋วยเตี๋ยวแป้งข้าวเจ้า/แป้งมัน (เส้นเล็ก, เส้นหมี่, เส้นใหญ่)
   * เส้นบะหมี่ไข่
   * เส้นเฝอเวียดนาม
   * ขนมปังแซนด์วิช, ข้าวโอ๊ต (Oatmeal), แป้งสาลีชุบทอด
7. **กลุ่มผักสดและสมุนไพรพื้นฐาน (Fresh Vegetables & Herbs):**
   * ชะอมสด, ผักชี, ต้นหอม, กล้วยน้ำว้า, ผักสลัดไฮโดรโปนิกส์
   * สมุนไพรแกง: พริกสด, พริกแห้ง, ข่า, ตะไคร้, ใบมะกรูด, กระเทียม, หอมแดง, มะนาว
8. **กลุ่มซอสปรุงรสและของเหลวปรุงแต่ง (Sauces & Seasonings):**
   * ซอสถั่วเหลือง/ซีอิ๊วขาว, ซอสดำหวาน, ซอสซอยการ์ลิค, น้ำมันงา, มายองเนส
   * น้ำปลาแท้, เลือดหมู/เลือดวัวสด (สำหรับน้ำซุปก๋วยเตี๋ยวเรือตก), กะปิ, พริกแกงส้ม, พริกแกงป่า

---

## 3. Consumer Behavior Constraints (ข้อจำกัดและพฤติกรรมผู้บริโภค)

### 3.1 โครงสร้างงบประมาณอาหาร (Budget Tiers)

* **กฎเกณฑ์ระดับ Core Model (`MealBudget` Invariants):**
  * เป็นจำนวนเต็มบวกในสกุลเงินบาท (Integer THB) เท่านั้น
  * ขอบเขตที่ระบบยอมรับ: ตั้งแต่ `1` ถึง `10,000` บาทต่อมื้อ
  * ระบบรองรับการป้อนตัวเลขไทย (เช่น `๘๐`), ตัวเลขอารบิก (เช่น `80`), และคอมม่าคั่นหลักพัน (เช่น `1,000`)
  * ปฏิเสธค่าทศนิยม, ค่าติดลบ, ข้อความ หรือตัวคั่นที่ไม่ถูกต้อง
* **ปุ่มลัดเลือกงบประมาณด่วนใน UI (Preset Quick Shortcuts):**
  * `60 บาท` (มื้อประหยัดขั้นต่ำ)
  * `80 บาท` (มื้อมาตรฐานยอดนิยมของนักศึกษา)
  * `100 บาท` (มื้อคุณภาพ/สั่งเพิ่มพิเศษ)
  * `150 บาท` (มื้อพรีเมียมส่วนบุคคล)
* **การแบ่งกลุ่มระดับการใช้จ่ายในตลาดจริงรอบ ม.ศิลปากร (Market Spending Tiers):**
  * **Economy Tier (40 – 70 บาท):**
    * *เมนู:* ก๋วยเตี๋ยวเรือน้ำ (40 บ.), ข้าวมันไก่ต้ม/ทอด (59 บ.), ข้าวหมูแดง/หมูกรอบ/หน้าเป็ด (60 บ.), ข้าวยำไก่แซ่บ (69 บ.)
    * *พฤติกรรม:* สั่งบ่อยที่สุด (High Volume), ความต้องการวัตถุดิบ (ไก่, หมู, ข้าว, เส้น) เสถียรและสม่ำเสมอในวันเรียน
  * **Mid Tier (80 – 180 บาท):**
    * *เมนู:* แกงจืดเต้าหู้หมูสับ/แกงป่าปลาบึก (80 บ.), แซนด์วิช (109 บ.), ข้าวผัดปู (150 บ.), ข้าวหน้าแซลมอน (159 บ.), คานิมิโซะ (169 บ.)
    * *พฤติกรรม:* สั่งเป็นมื้อสุขภาพหรือมื้อที่ต้องการโปรตีนสูง/อาหารญี่ปุ่น
  * **Premium / Social Tier (199 – 800 บาท):**
    * *เมนู:* ไก่ทอดบอนชอนชุด (199–259 บ.), ซาชิมิรวม (220–280 บ.), เฝอหม้อไฟชุด (359–499 บ.), กุ้งอบภูเขาไฟ (800 บ.)
    * *พฤติกรรม:* รวมกลุ่มสั่งในมื้อเย็น/วันหยุดสุดสัปดาห์

### 3.2 กฎข้อจำกัดและการคัดกรองอาหาร (Food Restrictions & Preferences)

| หมวดหมู่ | ตัวเลือก / รหัส Enum | พฤติกรรมการคัดกรองในระบบ (Filtering Logic) | ผลกระทบต่อ Stock Prediction |
| :--- | :--- | :--- | :--- |
| **Hard Exclusions (ข้อห้ามเด็ดขาด)** | `no_pork`<br>`no_beef`<br>`vegetarian`<br>`halal_only` | เชื่อมเงื่อนไขด้วยตัวดำเนินการ `AND`<br>- `vegetarian`: กรองเนื้อสัตว์/ปลา/อาหารทะเลออก แต่ยอมรับไข่และนม<br>- `halal_only`: ต้องมี `halalConfirmed == true` เท่านั้น (การไม่มีหมูไม่เพียงพอ) | ผู้ใช้กลุ่มนี้จะตัด Demand วัตถุดิบเนื้อสัตว์เป้าหมายออกจากระบบอย่างสมบูรณ์ |
| **Allergens (สารก่อภูมิแพ้ 9 กลุ่ม)** | `peanut`, `tree_nuts`, `milk`, `egg`, `soy`, `wheat`, `fish`, `shellfish`, `sesame` | กรองเมนูที่มีส่วนผสมดังกล่าวออกทั้งหมด รวมถึง**คัดทิ้งเมนูที่ข้อมูลสารก่อภูมิแพ้ไม่สมบูรณ์ (`allergensKnown: false`)** โดยไม่มีการผ่อนปรน | ความต้องการเมนูที่มีถั่วเหลือง ข้าวสาลี หรืออาหารทะเลจะลดลงตามสัดส่วนผู้แพ้ |
| **Dislikes (วัตถุดิบที่ไม่ชอบ 10 ชนิด)** | `pork`, `beef`, `chicken`, `fish`, `shellfish`, `egg`, `milk`, `mushroom`, `coriander`, `offal` | **Soft Constraint:**<br>- ค่าเริ่มต้น: เมนูที่มีวัตถุดิบนี้จะถูกจัดอันดับไว้รั้งท้ายสุด (หลังเมนูอื่นที่ผ่านเกณฑ์ทั้งหมด)<br>- เปิด `hideDisliked`: เมนูจะถูกคัดทิ้งทันที | มีผลต่อการกระจายตัวของอันดับคำแนะนำและการเลือกมื้ออาหาร |
| **Price Confidence (สถานะราคา)** | `verified`<br>`estimated`<br>`unverified` | - `verified`: มี URL แหล่งที่มา และวันที่ตรวจสอบย้อนหลังไม่เกิน 30 วัน<br>- `estimated`: ราคาโดยประมาณ<br>- `unverified`: ไม่มีหลักฐาน หรือหลักฐานเกิน 30 วัน | ความเชื่อมั่นของราคาอาหารส่งผลต่อการตัดสินใจซื้อของผู้ใช้ที่คุมงบ |

---

## 4. Core Data Dictionary (Firestore Schema)

โครงสร้างฐานข้อมูล Firestore ในโปรเจกต์ MueNee ถูกออกแบบไว้ในเวอร์ชัน `schemaVersion: 1` มี Collections สำคัญที่เชื่อมโยงถึงข้อมูลร้านค้า เมนู และพฤติกรรมการบริโภคดังนี้:

### 4.1 Collection: `restaurants/{restaurantId}`
บันทึกข้อมูลร้านอาหารในระบบ MueNee

```typescript
interface RestaurantDocument {
  schemaVersion: 1;
  name: string;                   // ชื่อทางการของร้านอาหาร
  googlePlaceId: string;          // อ้างอิง Place ID ของ Google Maps
  location: GeoPoint;             // พิกัดทางภูมิศาสตร์ (latitude, longitude)
  address: string;                // ที่อยู่ร้านจริง
  rating?: number;                // คะแนนเฉลี่ย (float เช่น 4.5, ช่วง 0.0 - 5.0)
  imageUrl?: string;              // URL รูปภาพร้านอาหาร
  verificationStatus: "verified" | "pending" | "unverified"; // สถานะยืนยันตัวตนร้าน
  isActive: boolean;              // สถานะเปิดใช้งานในระบบแคตตาล็อก
  createdAt: Timestamp;           // วันเวลาที่สร้างเอกสาร (UTC)
  updatedAt: Timestamp;           // วันเวลาที่ปรับปรุงข้อมูลล่าสุด (UTC)
}
```

*ดัชนี (Composite Indexes) ในระบบ:*
* `isActive` (Ascending) + `name` (Ascending) สำหรับการคิวรีรายชื่อร้านที่เปิดบริการเรียงตามชื่อ

---

### 4.2 Collection: `menu_items/{menuItemId}`
บันทึกรายละเอียดเมนูอาหาร คุณค่าทางโภชนาการ และการแมปวัตถุดิบ

```typescript
interface MenuItemDocument {
  schemaVersion: 1;
  restaurantId: string;           // Foreign Key ชี้ไปยัง restaurants/{restaurantId}
  name: string;                   // ชื่อรายการอาหาร
  price: {
    amount: number;               // ราคาขายเป็นจำนวนเต็มหน่วยบาท (Integer THB)
    confidence: "verified" | "estimated" | "unverified"; // ความน่าเชื่อถือของราคา
    source?: string;              // HTTPS URL แหล่งที่มาของราคา
    verifiedAt?: Timestamp;       // วันเวลาที่ตรวจสอบราคาล่าสุด
  };
  nutrition: {
    calories: number;             // พลังงานรวม (kcal ต่อหนึ่งหน่วยบริโภค)
    proteinGrams: number;         // โปรตีน (กรัม)
    carbsGrams: number;           // คาร์โบไฮเดรต (กรัม)
    fatGrams: number;             // ไขมัน (กรัม)
  };
  tags: string[];                 // หมวดหมู่/ลักษณะอาหาร (เช่น ["thai", "rice", "spicy"])
  ingredients: string[];          // รหัสวัตถุดิบหลัก (เช่น ["pork", "chicken", "shellfish", "egg"])
  allergens: string[];            // รหัสสารก่อภูมิแพ้ (เช่น ["soy", "wheat", "sesame", "fish"])
  ingredientsKnown: boolean;      // แฟล็กยืนยันว่าทราบสูตร/วัตถุดิบทั้งหมดครบถ้วน
  allergensKnown: boolean;        // แฟล็กยืนยันว่าทราบสารก่อภูมิแพ้ทั้งหมดครบถ้วน
  vegetarianConfirmed: boolean;   // แฟล็กยืนยันมังสวิรัติ (True เมื่อยืนยันว่าไม่มีเนื้อสัตว์)
  halalConfirmed: boolean;        // แฟล็กยืนยันฮาลาล (True เมื่อผ่านการรับรองฮาลาล)
  imageUrl?: string;              // URL รูปถ่ายเมนูอาหาร
  isActive: boolean;              // สถานะเปิดขายเมนูนี้
  createdAt: Timestamp;           // วันเวลาที่บันทึก
  updatedAt: Timestamp;           // วันเวลาที่ปรับปรุงล่าสุด
}
```

*ดัชนี (Composite Indexes) ในระบบ:*
* `restaurantId` (Ascending) + `isActive` (Ascending) + `name` (Ascending) สำหรับดึงเมนูของแต่ละร้าน
* `isActive` (Ascending) สำหรับการดึง Candidate เมนูทั้งหมดมาประมวลผลคำแนะนำ

---

### 4.3 Collection: `meal_logs/{mealLogId}`
บันทึกประวัติการเลือกและบริโภคอาหารจริงของผู้ใช้ (Actual Consumption Event) ข้อมูลชุดนี้คือ **Direct Demand Signal** ที่สำคัญที่สุดสำหรับระบบพยากรณ์สต็อก

```typescript
interface MealLogDocument {
  schemaVersion: 1;
  userId: string;                 // UID ของผู้บริโภค (อ้างอิง users/{uid})
  source: "recommendation" | "food_scan" | "manual"; // ที่มาของการบันทึก
  foodName: string;               // ชื่ออาหารที่ผู้ใช้รับประทาน
  nutrition: {
    calories: number;             // พลังงานที่ได้รับ (kcal)
    proteinGrams: number;         // โปรตีนที่ได้รับ (กรัม)
    carbsGrams: number;           // คาร์โบไฮเดรตที่ได้รับ (กรัม)
    fatGrams: number;             // ไขมันที่ได้รับ (กรัม)
  };
  menuId?: string;                // อ้างอิง menu_items/{menuItemId} (ถ้าเลือกจากระบบ)
  restaurantId?: string;          // อ้างอิง restaurants/{restaurantId} (ถ้าเลือกจากระบบ)
  imageUrl?: string;              // ภาพถ่ายมื้ออาหาร (ถ้ามี)
  createdAt: Timestamp;           // วันเวลาที่เกิดธุรกรรมการกิน (ใช้ทำ Time-series Analysis)
}
```

*ดัชนี (Composite Indexes) ในระบบ:*
* `userId` (Ascending) + `createdAt` (Descending) สำหรับเรียกดูบันทึกย้อนหลังรายบุคคล

---

### 4.4 Collection: `users/{uid}`
บันทึกโปรไฟล์ ข้อจำกัดทางอาหาร และความชอบของผู้บริโภค (Consumer Segmentation Profile)

```typescript
interface UserDocument {
  schemaVersion: 1;
  displayName?: string;
  profile: {
    age: number;                  // อายุ (ปี)
    height: number;               // ส่วนสูง (ซม.)
    weight: number;               // น้ำหนัก (กก.)
    activityLevel: "sedentary" | "lightly_active" | "moderately_active" | "very_active";
  };
  preferences: {
    hardRestrictions: string[];   // ["no_pork", "no_beef", "vegetarian", "halal_only"]
    allergies: string[];          // ลิสต์สารก่อภูมิแพ้ที่ผู้ใช้ระบุ
    dislikes: string[];           // ลิสต์วัตถุดิบที่ไม่ชอบ
    hideDisliked: boolean;        // เลือกว่าจะซ่อนสิ่งที่ไม่ชอบหรือไม่
  };
  targetCalories?: number;        // เป้าหมายพลังงานต่อวัน (kcal)
  createdAt: Timestamp;
  updatedAt: Timestamp;
}
```

---

## 5. การนำไปต่อยอดในโปรเจกต์ MueNee-b2b-analytics

| มิติข้อมูลใน MueNee (Data Dimension) | การประยุกต์ใช้ในโมเดล B2B Analytics & Inventory Forecasting |
| :--- | :--- |
| **`meal_logs.createdAt` + `menuId`** | สร้าง Time-series Demand Curve วิเคราะห์จำนวนจานที่ถูกบริโภคต่อวัน/สัปดาห์/เดือน ตามปฏิทินการศึกษาของ ม.ศิลปากร |
| **`menu_items.ingredients`** | แปลง Recipe BOM (Bill of Materials): แปลงยอดสั่งซื้อเมนูเป็นปริมาณความต้องการวัตถุดิบดิบรายวัน (กก./หน่วย) |
| **`restaurants.location` (3 km boundary)** | วิเคราะห์ Cluster การจัดซื้อร่วม (Consolidated Procurement) ของร้านอาหารรอบ ม. เพื่อลดต้นทุนโลจิสติกส์วัตถุดิบ |
| **`menu_items.price.amount` vs Wholesale Price** | วิเคราะห์ Food Cost Margin และผลกระทบจากความผันผวนของราคาวัตถุดิบในตลาดสดนครปฐม |
| **`users.preferences` + `tags`** | พยากรณ์แนวโน้มพฤติกรรมการบริโภค (Consumer Preference Shifts) เช่น อัตราการเติบโตของอาหารเพื่อสุขภาพ หรือเมนูปลา/ไก่ |

