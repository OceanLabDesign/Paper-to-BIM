"""core/classes.py —— 15 類偵測類別

★ 契約三件套之一。規格 §4（v0.4.1 起）：內容可代擬，**但未經負責人確認前
  不得產生任何正式資料** —— 本檔正是那條規定最要緊的地方。

  ┌────────────────────────────────────────────────────────────┐
  │ 鐵則：**順序即 id，永不重排。**                              │
  │ 新類別只能 append 到最後（id 15 起），不能插隊、不能刪、       │
  │ 不能改名 —— name 直接是 03_detections / 03_elements 的       │
  │ class_name 欄值，也是 plan judgments[].type 的合法值，        │
  │ 改名的破壞力等同重排。                                       │
  │ **本清單目前是草案，尚未有任何資料引用它 —— 現在改是免費的。** │
  └────────────────────────────────────────────────────────────┘

產生方式：四個視角（結構／製圖慣例／偵測器可行性／下游消費者）各提一版，
三位評審（規格符合度／永久性／1979 年圖面現實）評分，再綜合。
四版分數 78/78/77/76 —— 非常接近，代表沒有哪個視角壓倒性正確，
所以下面每一類都附了「為什麼值得佔一個永久 id」讓你能逐條否決。

排序理由（下游依賴深度）：
  0–1   §3 唯二有落地產出的類（07_walls / 07_columns）
  2–3   §6.2 規則 3 之下全系統唯一合法的座標來源
  4–6   牆的二階幾何
  7–9   供給 z 座標（level_* 是脫離 ASSUMED 與 _draft 的唯一路徑）
  10–12 證據級
  13–14 v1 無下游消費者，最可能被拆細
"""

# (name, 中文, tier) —— 索引即 id
CLASSES = (
    ('wall', '牆', 'structure'),
    ('column', '柱', 'structure'),
    ('dim_line', '尺寸線', 'annotation'),
    ('dim_text', '尺寸數字', 'annotation'),
    ('opening', '開口（洞）', 'opening'),
    ('door', '門', 'opening'),
    ('window', '窗', 'opening'),
    ('stair', '樓梯', 'structure'),
    ('level_line', '標高線（樓層線）', 'annotation'),
    ('level_text', '標高數字', 'annotation'),
    ('room_label', '室名', 'annotation'),
    ('hatch', '剖面填充（塗黑／材質剖線）', 'reference'),
    ('material_note', '材料／構造註記', 'annotation'),
    ('element_tag', '元件編號', 'annotation'),
    ('fixture', '衛浴廚具（固定設備）', 'reference'),
)

NAMES = tuple(c[0] for c in CLASSES)
ZH = {c[0]: c[1] for c in CLASSES}
TIER = {c[0]: c[2] for c in CLASSES}
TIERS = ("structure", "opening", "annotation", "reference")


def class_id(name: str) -> int:
    """name → id。id 就是在 CLASSES 裡的位置，永不重排。"""
    return NAMES.index(name)


def is_valid(name: str) -> bool:
    """§6.2 規則 1：plan 的 judgments[].type 不在本清單即退件。"""
    return name in NAMES


# ─────────────────────────────────────────────────────────────
# 每一類的立論與偵測線索（給人審核，不是給程式讀）
# ─────────────────────────────────────────────────────────────
NOTES = {
    'wall': {
        "why": "§8 規則式偵測器第一條逐字指名，且是 §3 07_walls.csv 的產出本體與 §10 牆厚（外24／內12）的承載者——刪掉它整個專案沒有產物。",
        "detect": "兩條近平行長線（夾角<3°、投影重疊>0.6）法向間距落在 core.config.WALL_GAP_PX (12–42px≈10–36cm)，中線寫 axis_wkt、間距換算 thickness_cm；★必須加一條退路：1:100 下 12cm 內牆線對只隔 14px 而 1979 針筆 0.4–0.6mm≈5–7px，曬圖擴散後常糊成單一粗帶，thickness_px 落在 WALL_GAP_PX 內的單一粗筆畫也要收成低信心 wall，否則會系統性漏掉全部內牆。",
    },
    'column': {
        "why": "§8 規則式偵測器第二條逐字指名，且是 §3 07_columns.csv 的產出本體與垂直載重路徑的起點，是跨樓層對位最可靠的錨。",
        "detect": "塗黑／填實的封閉小矩形（30–50cm 邊長＝35–59px、長寬比≤2），多落在 wall 線對交點；★30–50cm 的邊長全部低於 MIN_LINE_LENGTH=60px，03_lines.csv 裡根本沒有柱的邊，必須改用二值圖的連通元件／輪廓抓實心塊——這偏離了 §8 寫的「03_lines.csv → 實心矩形→column」的 I/O，依 §0 規則 4 應先停下來問，不要自行取捨。",
    },
    'dim_line': {
        "why": "§8 規則式偵測器第三條逐字指名（名字一字不可改），且 §7.3 戒律一與 §6.2 規則 3 使它成為全系統唯一合法的座標來源——它沒被偵測到，牆柱就只有拓樸沒有幾何。",
        "detect": "落在建物輪廓外圍、不參與任何 wall 線對、彼此共線且首尾相接成串的孤立長線，同向多條即一條 05_chains 的尺寸鏈；★§8 說的「兩端斜線」紙面約 3mm≈30px 低於 MIN_LINE_LENGTH=60，能不能當主判準要看是否補跑小尺度 pass——降級成加分證據是對 §8 的偏離，須負責人裁決。",
    },
    'dim_text': {
        "why": "鏈要的是「值」不是「線」（§11 第 4 步的 403+403=806 比的是值），而且只有數字要走 §1.2 三源投票寫進 04_readings，與線混成一類就無法各自帶 conf／status（§9）。",
        "detect": "03_texts 中 region=body 的純數字字串（1–5 位、無單位），垂直距離某條 dim_line 一個字高（≈40px）以內且書寫方向與該線平行；因需 03_texts，本類在 s03_elements 才定案，s03_detect 只看線段。",
    },
    'opening': {
        "why": "rule_v1 在曬圖上常只認得出牆對的缺口、認不出弧或窗框細線，沒有這個低信心父類整筆不是漏掉就是被硬猜成門，直接違反 §1「不確定往上傳不往下傳」（註：任務書所謂「§2 s09 比對柱位/牆線/開口」在規格與裁決全文皆不存在，只出現在 review/s09_crosscheck.py 的代擬 docstring，不可當法源——已 grep 確認）。",
        "detect": "同一對 wall 平行線在同一段落同時中斷 70–200cm（83–236px），缺口兩端各有一小段垂直於牆、連接內外兩線的封口線；缺口幾何本身就足以定位，不需要任何符號，缺口內找不到弧或貫通細線時就停在本類。",
    },
    'door': {
        "why": "IfcDoor；洞口自樓板起算（0→約210cm）這件事無法從平面幾何事後推得，只能由類別本身攜帶。",
        "detect": "opening 缺口 ＋ 一條長度≈缺口寬（90cm≈106px，過得了 60px 門檻）、以缺口一端為樞紐斜出的門扇線；★開啟弧在 Hough 下碎成約 21px 的段，絕不可當主判準，只能當加分證據。",
    },
    'window': {
        "why": "IfcWindow；窗台高（sill）讓 z 起點不是 0，是它與門在 BIM 裡唯一但決定性的差別，而且它是唯一在平面與立面都以幾何形式出現的開口類——「同一份 classes 同時服務 plan 與立面」的實際承載者。",
        "detect": "平面：opening 缺口內有 2–4 條與牆平行、貫穿整個缺口（150cm≈177px）的細線且無圓弧；立面（kind≠plan）：牆面內的封閉長方形，成列等高排列、常帶等距豎向分格線。",
    },
    'stair': {
        "why": "平面圖上唯一自帶 z 的構件（踏步數×級高＝層高），可交叉驗證 §10 的 ASSUMED 層高，也是跨樓層垂直對位與樓板開孔的錨點。",
        "detect": "≥3（宜≥5）條等長平行線（踏步寬≈100cm≈118px）且法向間距近乎定值（踏面 26–30cm≈31–35px），兩端落在同兩條界線上——判準是間距的週期性不是單線長度，所以掉兩三條線仍成立，是全圖最耐曬圖退化與摺痕的圖樣；「上／下」「UP/DN」文字在 s03_elements 補。",
    },
    'level_line': {
        "why": "§10 是規格裡唯一提到立面的地方（「A-2 頁本身就有四個立面圖和側面圖，上面有標高」），這一類是把 ASSUMED 層高換成真值、讓輸出脫掉 DRAFT_SUFFIX='_draft' 與 ASSUMED_MAX_CONF=0.4 的唯一路徑——沒有它 A-2 有一半版面對系統零產出。",
        "detect": "kind≠plan 的子圖內橫貫整個量體寬度的超長水平線（數百 px），多條近似等距堆疊（GL／各層 FL／屋頂，320cm 層高≈378px、1F 400cm≈472px）——長度本身就是判準，是全張圖最好抓的東西；★絕不可釘在約 35px 的標高三角符號上。",
    },
    'level_text': {
        "why": "與 dim_line／dim_text 同構：線只給拓樸、數字才給值，而只有數字要走 §1.2 三源投票進 04_readings 並各自帶 conf／status——把 ±0.00／+3.20 混進 level_line 就無法追溯「真實層高量過了沒有」，ASSUMED 也就永遠換不掉。",
        "detect": "03_texts 中帶 ± 號、小數點或 GL／FL／1FL 字樣的短字串（與 dim_text 的判別點就在這個符號前綴），bbox 落在某條 level_line 端點一個字高以內；讀值走 §1.2 三源寫進 04_readings。",
    },
    'room_label': {
        "why": "空間用途的唯一來源，決定 IfcSpace，也回頭改幾何參數（§10 的『層高cm_1F: 400 # 店鋪常挑高』要有「這層是店鋪」的證據才不是 assumed），並且是判定封閉牆圍區域是室內而非天井的正向證據。",
        "detect": "03_texts 中 region=body、不含數字的 2–4 字中文短詞（比對室名詞庫：店鋪／客廳／臥室／廚房／浴廁／樓梯間／車庫／陽台／騎樓），質心落在 wall 線段圍出的封閉區內且不在任何 dim_line 的平行帶內；文字比細線耐曬圖退化，這一類保證有貨。",
    },
    'hatch': {
        "why": "§8 的「實心矩形→column」本來就要判「實心」，這是判實心的依據；同時是圖面上唯一能分辨 RC 與加強磚造的幾何證據，也是 fields.THICKNESS_SRC 從 assumed 升級成實據的唯一非文字路徑（比手寫註記更難造假），並且是 §9 evidence 欄最好用的引用對象。",
        "detect": "主判準是大面積連通黑塊／框內黑像素密度遠高於周圍（1:100 下 12cm 牆只有 14px 寬，手繪畫不下斜線，實務上就是塗黑）；等距同角度（多為45°）的短平行線群只在剖面圖與大比例詳圖成立，當第二分支，★不可只寫斜線群否則是永遠 conf=0 的死類別。",
    },
    'material_note': {
        "why": "「1B 磚牆」「R.C.15」「洗石子」這類手寫註記是 §10 ASSUMED 牆厚以外的第二條實據來源，也是 hatch 之外唯一能把 thickness_src 換掉的證據，而文字在曬圖退化下比任何細線都耐命；★刻意採正面詞庫定義而非「body 區其餘文字」的補集定義，補集會在每次 append 新 id 時無聲改變語意。",
        "detect": "03_texts 中 region=body 且命中構造詞庫的字串（RC／R.C.／磚／1B／1/2B／加強磚造／洗石子／二丁掛／粉刷／cm），常一端接一條細引線指向某個 wall 線對或 hatch 區——引線併入本筆當 evidence，不另立類；未命中詞庫的 body 文字不進本類，它們完整留在 03_texts.csv 裡不會消失。",
    },
    'element_tag': {
        "why": "「字母＋數字」的編號是把平面開口接上門窗表的 join key（fields.TEXT_REGIONS 已有 schedule 值，代表表格文字已被收錄），一個 W1 換來門窗真實尺寸——那是機制上獨立於像素量測的第三源，正是 §1.2 要的那種獨立性；編號慣例是百年尺度的製圖事實，v1 沒有查表流程不代表它十年後會被廢。",
        "detect": "region=body 的極短英數字串（W1／D2／C1／窗1／門2），bbox 緊鄰或落在某個 opening／door／window／column 上；再拿該字串去 region=schedule 的文字裡對表取真實尺寸。",
    },
    'fixture': {
        "why": "1979 住宅平面把馬桶／浴缸／洗面盆／流理台畫得很完整，它們是「封閉小矩形→column」與「缺口→opening」最大的假陽性來源——給它一個正面且可窮舉的類別，等於讓偵測器有一個可競爭的假設，而不是把錯誤塞進 column；它也是換 YOLO 後最容易得分的非結構類（§12 要求清單撐得住換 YOLO）。★排最後是誠實的：v1 沒有下游消費者，日後最可能被拆細。",
        "detect": "落在 room_label 為浴廁／廚房的封閉區內、由 2–5 條線構成的孤立小輪廓（浴缸≈150×70cm≈177×83px、流理台長≈200cm≈236px），不與任何 wall 線對共線、內部無 hatch；限定為固定衛生設備與廚具這個可窮舉的集合，認不出具體器具就不收——它不是 catch-all。",
    },
}


# ─────────────────────────────────────────────────────────────
# 認真考慮過但沒放進 15 類的 —— 這一段跟上面一樣重要
# 之所以留著：日後有人想 append 時，先看這裡有沒有討論過、為什麼當初不收。
# ─────────────────────────────────────────────────────────────
EXCLUDED = {
    "grid_line / grid_axis（軸線、軸號）": "★三位評審唯一互相衝突的一格：longevity 列為 must_include，realism 列為 must_exclude，依「不得包含任何評審的 must_exclude」裁定排除。實質理由站在 realism 這邊：民國 68 年小型街屋／透天的 A 系列圖多半根本沒有軸網；一點鏈線的長短節奏在手繪＋曬圖擴散＋adaptive(31,12) 之後復原不了；軸號圓圈的弧段約 37px 低於 MIN_LINE_LENGTH=60。且規格全文沒有要求軸線（已 grep 確認）。跨樓層基準改用 column 位置＋尺寸鏈。此格需負責人知情裁決，若要留應 append 為 id 15 而非插隊。",
    "drawing_title（子圖圖名）": "realism 列為 must_include（A-2 一頁六張子圖需要綁 sheet_id），但 longevity 列為 must_exclude，依否決規則排除。機制上 longevity 是對的：fields.SHEETS 是一行一張子圖（sheet_id, page, kind, floor, scale…），子圖切分與圖名判讀是 §8 s02_layout 那一次 VLM 呼叫的職責，圖名是它的輸入而不是可裁定的偵測物件；`type: drawing_title` 的 judgment 對 s07 也畫不出任何東西。realism 擔心的「平面牆線與立面樓層線落在同一個 sheet_id 上互相污染」由 02_sheets 一子圖一列解決，不需要永久偵測 id。",
    "text_note / note_text（body 文字補集類）": "spec 與 realism 都要求一個 body 文字類，但 longevity 明令排除「凡以補集定義者」——「region=body 中不屬於其他類的其餘文字」會在每次 append 新 id 時無聲改變語意，讓不同年份的 03_elements.csv 對同一個 id 意思不同。折衷方案：改成正面詞庫定義的 material_note（id 12），保住 spec／realism 真正要的那件事（「1B 磚牆」「RC 15」是 thickness_src 脫離 assumed 的第二條路）。未被任何類認領的 body 文字並不會消失——03_texts.csv 依 §8 收錄每一片全圖的所有文字＋bbox＋region，中樞用 crop_look／脈絡摘要一樣取得到。",
    "slab_edge / slab / roof（樓板、板緣、屋頂）": "realism 列為 must_exclude（單線封閉輪廓與騎樓線、排水溝、地界線、女兒牆投影線、摺痕完全同形，規則式與人眼都分不開），故本版不放。★但 spec 評審點名這是四版中唯一值得提給負責人裁決的一格：§10 ASSUMED 有『板厚cm: 15』，代表規格確實假設了樓板存在卻沒有承載它的類別。建議：若負責人裁定要留，append 為 id 15，名字用 `slab`（十年後承載的是 IfcSlab），不要用製圖視角的 slab_edge——class_name 直接是 CSV 值與 judgments[].type，改名的破壞力等同重排。",
    "beam（梁）": "spec 與 realism 都列為 must_exclude。規格全文沒有出現「梁／樑」一次（已 grep 確認），§3 也沒有 07_beams.csv，v1 完全沒有下游消費者；A 系列建照建築圖本來就不畫梁（在 S 系列結構圖上）。偵測上虛線兩頭卡死門檻：單段約 30px < MIN_LINE_LENGTH=60、段隙約 12px > MAX_LINE_GAP=6，整條線在 03_lines.csv 裡直接消失（structural 版把 MAX_LINE_GAP 讀反了）。等 S 系列進場再 append。",
    "section_mark / detail_ref（剖切符號、詳圖索引）": "realism 列為 must_exclude：粗短線＋直角箭頭＋字母圈，符號與鏈線兩項都在 60px 門檻之下。平面與剖／立面的對應在這批圖上由 02_sheets 的 kind／floor（s02 一次 VLM 呼叫產出）成立，不必另立偵測類。",
    "north_arrow（指北針）": "三位評審一致排除。drafting 版自己的 why 就寫著「將來最可能被搬進 02_sheets 當一個欄位」——在 §4「順序即 id、永不重排、一旦有資料引用就鎖死」的契約裡，明知會遷走還發永久 id 是最直接的違約；且 fields.SHEETS 已有 orientation、01_offsets 已有 rotation。",
    "symbol / unknown / other（萬用桶）": "三位評審一致排除，且 realism 與 longevity 都點名 pipeline 的 symbol 是換皮的 unknown。致命處在 §6.2 規則 1：catch-all 是 classes.py 的合法成員，中樞把認不出的東西標成它，validate 的類別檢查就永遠攔不下來，等於把不確定藏進一個合法類別，正是 §1「不確定往上傳不往下傳」的反面。不確定走 conf 與 status=uncertain（§9）；圖形殘餘已有 fields.RESIDUAL_KINDS.unexplained_stroke 這個既存機制。",
    "outline / elevation_outline（凸包輪廓）": "longevity 列為 must_exclude：「取各 view 內線段的凸包邊界」是對 03_lines 的一次查詢，不是紙上畫出來的東西——與四版一致用來排除 centerline 的是同一個範疇錯誤。realism 另補：對摺過的 A1 曬圖上凸包會把摺痕長線與邊緣顯影暗帶一起圈進去，而騎樓、雨遮本來就伸出牆外。它想解的 §10 外24／內12 判別改用「最外圈封閉 wall 迴圈的 point-in-polygon」，那是 rule.py 的機制，結果寫進 07_walls 的 thickness_cm ＋ thickness_src。",
    "dim_witness（尺寸界線）": "longevity 與 realism 都列為 must_exclude：它是整張手繪圖最細最淡的線，曬圖褪色加 adaptive(31,12) 二值化時第一個消失；活下來的部分又與牆的正交短線、摺痕碎線同形，rule_v1 分不開。而且它是尺寸標註的零件不是獨立主張，該進 §9 的 evidence 欄。尺寸掛回牆面改靠鄰近度＋鏈閉合檢核，需要時再 append。",
    "title_block / drawing_frame / stamp / schedule_table": "三位評審一致排除，且 core/fields.py 已定 EXCLUDE_KINDS=(frame, title_block, stamp, schedule, other) 與 TEXT_REGIONS=(body, title_block, schedule)——§3 的 02_exclude 與 §8 s03_elements「排除帶內的線先剔」已是唯一權威。給它們偵測 id 會讓兩套機制搶同一件事，而且因為剔除發生在 s03_elements 之前，這些 id 在 03_elements 裡永遠是零實例的死格。★這一條要寫進 classes.py 的註解，防止日後有人補回來。",
    "wall_exterior / wall_interior（外牆／內牆拆兩類）": "三位評審一致排除。§10 的差別只是 24 與 12，而 WALL_GAP_PX=(12,42) 一個偵測器同時涵蓋兩者；厚度該由 fields.WALLS 的 thickness_cm ＋ thickness_src 承載。拆成兩個永久 id 會逼 rule_v1 硬猜，而 §6.2 只查類別成員資格、查不出「猜錯類別」，錯誤會一路傳進 DXF 且無法只降 confidence；遇到 15cm RC 牆時兩類還都不對。",
    "centerline / wall_axis（牆心線）": "三位評審一致排除。plan 的 geometry.axis_wkt（§6.1 範例）是從 wall 線對推導出來的產物，不是圖上獨立畫的東西。列成偵測類別等於允許 s03 產出未經量測的座標，直接違反 §7.3 戒律一與 §6.2 規則 3；而且同一道牆會在 03_elements 出現兩筆，s08 算覆蓋率時重複計算。",
    "leader / arrow / break_line / door_swing / window_sill / parallel_pair 等零件與幾何原語": "三位評審一致排除：§1「尺寸是幾何、線段只是拓樸」，原語屬於 03_lines.csv 與 §9 的 evidence 欄（fields.EVIDENCE_NS 已為 pair#／line#／det# 定好命名空間）。類別欄回答的是「這是什麼構件」，不是「這是什麼形狀」；獨立成類會讓同一個記號被偵測兩次、evidence 互相打架。本版已把它們分別併進 dim_line、door、stair、material_note 的判準裡。",
    "level_mark / level_marker（第二種標高寫法）": "三位評審都要求在 level_line／level_mark／level_marker 三種寫法中「現在就定死一個」，因為 class_name 直接是 CSV 值與 judgments[].type，改名的破壞力等同重排。本版的定法不是選同義詞而是定命名規約：`*_line` 一律是幾何／拓樸，`*_text` 一律是要走 §1.2 三源進 04_readings 的值——與 §8 逐字指名的 dim_line／dim_text 完全同構。因此 `level_mark`／`level_marker` 這兩個名字自此作廢，永不使用。",
    "furniture（活動家具）／railing（欄杆）／foundation（基礎）": "furniture：與 id 14 的 fixture 刻意分開——fixture 是可窮舉的固定設備且是 column 規則的主要假陽性源，活動家具兩者皆非。railing：等距平行線的訊號與 stair 完全重疊會互相污染 conf，而 1979 陽台／屋頂多為 RC 實心欄板，用 wall ＋ 高度屬性表達最誠實。foundation：longevity 列為 must_exclude，建照 A 系列沒有基礎平面圖（在 S 系列），為一個這批圖必定不會出現的東西發永久 id，等於清單第一天就有一格是死的。",
}
