# ─────────────────────────────────────────────────────────────
#  COUNTRIES
# ─────────────────────────────────────────────────────────────
COUNTRIES = {
    # Allies
    "gb":  {"flag": "🇬🇧", "name_fa": "United Kingdom (بریتانیا)",        "faction": "allies",   "vip": True},
    "su":  {"flag": "🇷🇺", "name_fa": "Soviet Union (شوروی)",              "faction": "allies",   "vip": True},
    "us":  {"flag": "🇺🇸", "name_fa": "United States (آمریکا)",            "faction": "allies",   "vip": True},
    "fr":  {"flag": "🇫🇷", "name_fa": "France (فرانسه)",                   "faction": "allies",   "vip": True},
    "cn":  {"flag": "🇨🇳", "name_fa": "China (چین)",                       "faction": "allies",   "vip": True},
    "pl":  {"flag": "🇵🇱", "name_fa": "Poland (لهستان)",                   "faction": "allies",   "vip": False},
    "ca":  {"flag": "🇨🇦", "name_fa": "Canada (کانادا)",                   "faction": "allies",   "vip": False},
    "au":  {"flag": "🇦🇺", "name_fa": "Australia (استرالیا)",              "faction": "allies",   "vip": False},
    "nz":  {"flag": "🇳🇿", "name_fa": "New Zealand (نیوزیلند)",            "faction": "allies",   "vip": False},
    "za":  {"flag": "🇿🇦", "name_fa": "South Africa (آفریقای جنوبی)",     "faction": "allies",   "vip": False},
    "nl":  {"flag": "🇳🇱", "name_fa": "Netherlands (هلند)",                "faction": "allies",   "vip": False},
    "be":  {"flag": "🇧🇪", "name_fa": "Belgium (بلژیک)",                   "faction": "allies",   "vip": False},
    "gr":  {"flag": "🇬🇷", "name_fa": "Greece (یونان)",                    "faction": "allies",   "vip": False},
    "no":  {"flag": "🇳🇴", "name_fa": "Norway (نروژ)",                     "faction": "allies",   "vip": False},
    "yu":  {"flag": "🇾🇪", "name_fa": "Yugoslavia (یوگسلاوی)",             "faction": "allies",   "vip": False},
    "br":  {"flag": "🇧🇷", "name_fa": "Brazil (برزیل)",                    "faction": "allies",   "vip": False},
    "mx":  {"flag": "🇲🇽", "name_fa": "Mexico (مکزیک)",                    "faction": "allies",   "vip": False},
    "lu":  {"flag": "🇱🇺", "name_fa": "Luxembourg (لوکزامبورگ)",           "faction": "allies",   "vip": False},
    "et":  {"flag": "🇪🇹", "name_fa": "Ethiopia (اتیوپی)",                 "faction": "allies",   "vip": False},
    "ph":  {"flag": "🇵🇭", "name_fa": "Philippines (فیلیپین)",             "faction": "allies",   "vip": False},
    "in":  {"flag": "🇮🇳", "name_fa": "India (هند بریتانیایی)",            "faction": "allies",   "vip": False},
    # Axis
    "de":  {"flag": "🇩🇪", "name_fa": "Germany Nazi (آلمان نازی)",         "faction": "axis",     "vip": True},
    "jp":  {"flag": "🇯🇵", "name_fa": "Japan (ژاپن)",                      "faction": "axis",     "vip": True},
    "it":  {"flag": "🇮🇹", "name_fa": "Italy (ایتالیا)",                   "faction": "axis",     "vip": True},
    "hu":  {"flag": "🇭🇺", "name_fa": "Hungary (مجارستان)",                "faction": "axis",     "vip": False},
    "ro":  {"flag": "🇷🇴", "name_fa": "Romania (رومانی)",                  "faction": "axis",     "vip": False},
    "bg":  {"flag": "🇧🇬", "name_fa": "Bulgaria (بلغارستان)",              "faction": "axis",     "vip": False},
    "fi":  {"flag": "🇫🇮", "name_fa": "Finland (فنلاند)",                  "faction": "axis",     "vip": False},
    "sk":  {"flag": "🇸🇰", "name_fa": "Slovakia (اسلواکی)",                "faction": "axis",     "vip": False},
    "hr":  {"flag": "🇭🇷", "name_fa": "Croatia (کرواسی)",                  "faction": "axis",     "vip": False},
    "th":  {"flag": "🇹🇭", "name_fa": "Thailand (تایلند)",                 "faction": "axis",     "vip": False},
    # Neutral
    "ch":  {"flag": "🇨🇭", "name_fa": "Switzerland (سوئیس)",               "faction": "neutral",  "vip": False},
    "se":  {"flag": "🇸🇪", "name_fa": "Sweden (سوئد)",                     "faction": "neutral",  "vip": False},
    "es":  {"flag": "🇪🇸", "name_fa": "Spain (اسپانیا)",                   "faction": "neutral",  "vip": False},
    "pt":  {"flag": "🇵🇹", "name_fa": "Portugal (پرتغال)",                 "faction": "neutral",  "vip": False},
    "ie":  {"flag": "🇮🇪", "name_fa": "Ireland (ایرلند)",                   "faction": "neutral",  "vip": False},
    "va":  {"flag": "🇻🇦", "name_fa": "Vatican City (واتیکان)",            "faction": "neutral",  "vip": False},
    "tr":  {"flag": "🇹🇷", "name_fa": "Turkey (ترکیه)",                    "faction": "neutral",  "vip": False},
    "ar":  {"flag": "🇦🇷", "name_fa": "Argentina (آرژانتین)",              "faction": "neutral",  "vip": False},
    "cl":  {"flag": "🇨🇱", "name_fa": "Chile (شیلی)",                      "faction": "neutral",  "vip": False},
    "af":  {"flag": "🇦🇫", "name_fa": "Afghanistan (افغانستان)",           "faction": "neutral",  "vip": False},
    "sa":  {"flag": "🇸🇦", "name_fa": "Saudi Arabia (عربستان سعودی)",     "faction": "neutral",  "vip": False},
    # Occupied
    "ir":  {"flag": "🇮🇷", "name_fa": "Iran (ایران)",                      "faction": "occupied", "vip": False},
    "dk":  {"flag": "🇩🇰", "name_fa": "Denmark (دانمارک)",                 "faction": "occupied", "vip": False},
    "cz":  {"flag": "🇨🇿", "name_fa": "Czechoslovakia (چکسلواکی)",         "faction": "occupied", "vip": False},
}

# ─────────────────────────────────────────────────────────────
#  INFRASTRUCTURE
# ─────────────────────────────────────────────────────────────
INFRASTRUCTURE = {
    "rail":       {"name": "🚂 خطوط آهن سراسری",          "cost": 25_000_000,  "income": 15_000_000, "satisfaction": 2,  "limit": 10},
    "port":       {"name": "🚢 بندر تجاری",                "cost": 25_000_000,  "income": 15_000_000, "satisfaction": 2,  "limit": 10},
    "road":       {"name": "🚛 ناوگان حمل‌ونقل جاده‌ای",   "cost": 12_000_000,  "income": 7_000_000,  "satisfaction": 1,  "limit": 20},
    "bank":       {"name": "🏦 بانک مرکزی",                "cost": 35_000_000,  "income": 20_000_000, "satisfaction": 4,  "limit": 5},
    "post":       {"name": "📮 اداره پست و تلگراف",        "cost": 6_000_000,   "income": 3_500_000,  "satisfaction": 1,  "limit": 5},
    "insurance":  {"name": "🛡️ صندوق بیمه ملی",           "cost": 18_000_000,  "income": 10_000_000, "satisfaction": 2,  "limit": 10},
    "coal":       {"name": "⛏️ استخراج زغال‌سنگ",          "cost": 120_000_000, "income": 70_000_000, "satisfaction": 8,  "limit": 10},
    "iron":       {"name": "🔩 استخراج سنگ‌آهن",           "cost": 90_000_000,  "income": 55_000_000, "satisfaction": 5,  "limit": 5},
    "copper":     {"name": "🪙 معدن مس و برنز",            "cost": 100_000_000, "income": 60_000_000, "satisfaction": 3,  "limit": 5},
    "wood":       {"name": "🌲 معدن چوب",                  "cost": 35_000_000,  "income": 20_000_000, "satisfaction": 2,  "limit": 15},
    "wheat":      {"name": "🌾 مزرعه گندم و غلات",         "cost": 18_000_000,  "income": 10_000_000, "satisfaction": 5,  "limit": 15},
    "rice":       {"name": "🍚 مزرعه برنج و حبوبات",       "cost": 15_000_000,  "income": 8_000_000,  "satisfaction": 5,  "limit": 15},
    "flower":     {"name": "🌸 کشت گل و گیاه",             "cost": 5_000_000,   "income": 3_000_000,  "satisfaction": 4,  "limit": 20},
    "canning":    {"name": "🥫 کنسروسازی و بسته‌بندی",     "cost": 22_000_000,  "income": 12_000_000, "satisfaction": 3,  "limit": 20},
    "textile":    {"name": "🧵 کارخانه نساجی",             "cost": 45_000_000,  "income": 25_000_000, "satisfaction": 5,  "limit": 20},
    "household":  {"name": "🏠 تولید لوازم خانگی",         "cost": 30_000_000,  "income": 17_000_000, "satisfaction": 10, "limit": 10},
    "chemical":   {"name": "🧪 صنایع شیمیایی",             "cost": 40_000_000,  "income": 22_000_000, "satisfaction": 2,  "limit": 10},
    "paper":      {"name": "📄 کارخانه کاغذسازی",          "cost": 50_000_000,  "income": 30_000_000, "satisfaction": 5,  "limit": 8},
    "hotel":      {"name": "🏨 هتل و پانسیون",             "cost": 60_000_000,  "income": 35_000_000, "satisfaction": 8,  "limit": 20},
    "restaurant": {"name": "🍽️ رستوران و آشپزخانه عمومی",  "cost": 18_000_000,  "income": 10_000_000, "satisfaction": 5,  "limit": 25},
    "hospital":   {"name": "🏥 بیمارستان عمومی",           "cost": 90_000_000,  "income": 50_000_000, "satisfaction": 15, "limit": 10},
    "school":     {"name": "🏫 مدرسه و آموزشگاه",          "cost": 25_000_000,  "income": 14_000_000, "satisfaction": 10, "limit": 15},
}

# ─────────────────────────────────────────────────────────────
#  MILITARY EQUIPMENT
# ─────────────────────────────────────────────────────────────
EQUIPMENT = {
    # Ground
    "panzer4":    {"name": "🇩🇪 Panzer IV",           "cost": 500_000,    "category": "ground"},
    "panther":    {"name": "🇩🇪 Panther",              "cost": 800_000,    "category": "ground"},
    "tiger1":     {"name": "🇩🇪 Tiger I",              "cost": 1_200_000,  "category": "ground"},
    "tiger2":     {"name": "🇩🇪 Tiger II",             "cost": 1_500_000,  "category": "ground"},
    "stug3":      {"name": "🇩🇪 StuG III",             "cost": 300_000,    "category": "ground"},
    "jagdpanther":{"name": "🇩🇪 Jagdpanther",          "cost": 900_000,    "category": "ground"},
    "m4sherman":  {"name": "🇺🇸 M4 Sherman",           "cost": 400_000,    "category": "ground"},
    "m26":        {"name": "🇺🇸 M26 Pershing",         "cost": 700_000,    "category": "ground"},
    "m18":        {"name": "🇺🇸 M18 Hellcat",          "cost": 350_000,    "category": "ground"},
    "t34":        {"name": "🇷🇺 T-34",                 "cost": 350_000,    "category": "ground"},
    "kv1":        {"name": "🇷🇺 KV-1",                 "cost": 600_000,    "category": "ground"},
    "is2":        {"name": "🇷🇺 IS-2",                 "cost": 900_000,    "category": "ground"},
    "churchill":  {"name": "🇬🇧 Churchill",            "cost": 700_000,    "category": "ground"},
    "cromwell":   {"name": "🇬🇧 Cromwell",             "cost": 450_000,    "category": "ground"},
    "matilda2":   {"name": "🇬🇧 Matilda II",           "cost": 300_000,    "category": "ground"},
    "sdkfz251":   {"name": "🇩🇪 Sd.Kfz. 251",         "cost": 80_000,     "category": "ground"},
    "katyusha":   {"name": "🇷🇺 Katyusha",             "cost": 120_000,    "category": "ground"},
    "nebelwerfer":{"name": "🇩🇪 Nebelwerfer",          "cost": 100_000,    "category": "ground"},
    # Air
    "bf109":      {"name": "🇩🇪 Bf 109",               "cost": 350_000,    "category": "air"},
    "fw190":      {"name": "🇩🇪 Fw 190",               "cost": 450_000,    "category": "air"},
    "ju87":       {"name": "🇩🇪 Ju 87 Stuka",          "cost": 400_000,    "category": "air"},
    "he111":      {"name": "🇩🇪 He 111",               "cost": 800_000,    "category": "air"},
    "me262":      {"name": "🇩🇪 Me 262",               "cost": 2_500_000,  "category": "air"},
    "me163":      {"name": "🇩🇪 Me 163 Komet",         "cost": 3_000_000,  "category": "air"},
    "spitfire":   {"name": "🇬🇧 Spitfire",             "cost": 400_000,    "category": "air"},
    "hurricane":  {"name": "🇬🇧 Hurricane",            "cost": 300_000,    "category": "air"},
    "lancaster":  {"name": "🇬🇧 Lancaster",            "cost": 1_400_000,  "category": "air"},
    "mosquito":   {"name": "🇬🇧 Mosquito",             "cost": 900_000,    "category": "air"},
    "p51":        {"name": "🇺🇸 P-51 Mustang",         "cost": 450_000,    "category": "air"},
    "p47":        {"name": "🇺🇸 P-47 Thunderbolt",     "cost": 550_000,    "category": "air"},
    "p38":        {"name": "🇺🇸 P-38 Lightning",       "cost": 800_000,    "category": "air"},
    "b17":        {"name": "🇺🇸 B-17 Flying Fortress", "cost": 1_500_000,  "category": "air"},
    "b24":        {"name": "🇺🇸 B-24 Liberator",       "cost": 1_400_000,  "category": "air"},
    "b29":        {"name": "🇺🇸 B-29 Superfortress",   "cost": 3_000_000,  "category": "air"},
    "il2":        {"name": "🇷🇺 IL-2 Shturmovik",      "cost": 300_000,    "category": "air"},
    "yak3":       {"name": "🇷🇺 Yak-3",                "cost": 250_000,    "category": "air"},
    # Naval
    "bismarck":   {"name": "🇩🇪 Bismarck",             "cost": 45_000_000, "category": "naval"},
    "tirpitz":    {"name": "🇩🇪 Tirpitz",              "cost": 45_000_000, "category": "naval"},
    "uboat7":     {"name": "🇩🇪 Type VII U-boat",      "cost": 1_000_000,  "category": "naval"},
    "uboat21":    {"name": "🇩🇪 Type XXI U-boat",      "cost": 2_000_000,  "category": "naval"},
    "yamato":     {"name": "🇯🇵 Yamato",               "cost": 60_000_000, "category": "naval"},
    "musashi":    {"name": "🇯🇵 Musashi",              "cost": 60_000_000, "category": "naval"},
    "akagi":      {"name": "🇯🇵 Akagi",                "cost": 40_000_000, "category": "naval"},
    "shokaku":    {"name": "🇯🇵 Shokaku",              "cost": 45_000_000, "category": "naval"},
    "enterprise": {"name": "🇺🇸 USS Enterprise",       "cost": 55_000_000, "category": "naval"},
    "iowa":       {"name": "🇺🇸 USS Iowa",             "cost": 50_000_000, "category": "naval"},
    "missouri":   {"name": "🇺🇸 USS Missouri",         "cost": 50_000_000, "category": "naval"},
    "hmshood":    {"name": "🇬🇧 HMS Hood",             "cost": 35_000_000, "category": "naval"},
    "hmskg5":     {"name": "🇬🇧 HMS King George V",    "cost": 40_000_000, "category": "naval"},
    "hmsark":     {"name": "🇬🇧 HMS Ark Royal",        "cost": 35_000_000, "category": "naval"},
}

# ─────────────────────────────────────────────────────────────
#  MISSILES
# ─────────────────────────────────────────────────────────────
MISSILES = {
    "v1":         {"name": "🇩🇪 V-1 Flying Bomb",     "cost": 500_000},
    "v2":         {"name": "🇩🇪 V-2 Rocket",          "cost": 5_000_000},
    "wasserfall": {"name": "🇩🇪 Wasserfall",           "cost": 3_000_000},
    "hs293":      {"name": "🇩🇪 Hs 293",              "cost": 650_000},
    "fritzx":     {"name": "🇩🇪 Fritz X",             "cost": 500_000},
    "r4m":        {"name": "🇩🇪 R4M",                 "cost": 300_000},
    "rp3":        {"name": "🇬🇧 RP-3",                "cost": 200_000},
    "hvar":       {"name": "🇺🇸 HVAR",                "cost": 200_000},
    "rs82":       {"name": "🇷🇺 RS-82",               "cost": 100_000},
    "rs132":      {"name": "🇷🇺 RS-132",              "cost": 150_000},
}

# ─────────────────────────────────────────────────────────────
#  AIR DEFENSE
# ─────────────────────────────────────────────────────────────
AIR_DEFENSE = {
    "flak30":     {"name": "🇩🇪 Flak 30 (20mm)",              "cost": 50_000},
    "flak38":     {"name": "🇩🇪 Flak 38 (20mm)",              "cost": 60_000},
    "flakvierling":{"name":"🇩🇪 Flakvierling 38 (4×20mm)",    "cost": 120_000},
    "m1bofors":   {"name": "🇺🇸 M1 40mm Bofors",             "cost": 100_000},
    "qf40mm":     {"name": "🇬🇧 QF 40mm Bofors",             "cost": 100_000},
    "37mm39":     {"name": "🇷🇺 37mm M1939 AA",              "cost": 80_000},
    "flak18":     {"name": "🇩🇪 8.8cm Flak 18",              "cost": 250_000},
    "flak36":     {"name": "🇩🇪 8.8cm Flak 36",              "cost": 300_000},
    "flak41":     {"name": "🇩🇪 8.8cm Flak 41",              "cost": 350_000},
    "flak105":    {"name": "🇩🇪 10.5cm FlaK 38",             "cost": 500_000},
    "flak128":    {"name": "🇩🇪 12.8cm FlaK 40",             "cost": 800_000},
    "m1aa90":     {"name": "🇺🇸 90mm M1 AA Gun",             "cost": 350_000},
    "qf37inch":   {"name": "🇬🇧 QF 3.7-inch AA Gun",         "cost": 350_000},
    "85mm39":     {"name": "🇷🇺 85mm M1939 AA Gun",          "cost": 300_000},
    "mobelwagen": {"name": "🇩🇪 Möbelwagen",                  "cost": 450_000},
    "wirbelwind": {"name": "🇩🇪 Wirbelwind",                  "cost": 600_000},
    "ostwind":    {"name": "🇩🇪 Ostwind",                     "cost": 650_000},
    "kugelblitz": {"name": "🇩🇪 Kugelblitz",                  "cost": 900_000},
    "m16mgmc":    {"name": "🇺🇸 M16 MGMC",                   "cost": 250_000},
    "crusaderaak":{"name": "🇬🇧 Crusader AA Mk II",           "cost": 400_000},
}

# ─────────────────────────────────────────────────────────────
#  INFANTRY  (شامل جوخه جاسوسی)
# ─────────────────────────────────────────────────────────────
INFANTRY = {
    "infantry":   {"name": "🪖 پیاده‌نظام (جوخه 10 نفره)",    "cost": 10_000},
    "motorized":  {"name": "🎖️ موتوری (جوخه 10 نفره)",        "cost": 20_000},
    "mechanized": {"name": "🚚 مکانیزه (جوخه 10 نفره)",       "cost": 35_000},
    "paratrooper":{"name": "🪂 چترباز (جوخه 10 نفره)",        "cost": 40_000},
    "commando":   {"name": "🦅 کماندو (جوخه 10 نفره)",        "cost": 50_000},
    "sas":        {"name": "🇬🇧 SAS (جوخه 10 نفره)",          "cost": 70_000},
    "spy_squad":  {"name": "🕵️ جوخه جاسوسی (10 جاسوس)",      "cost": 80_000},
}


def get_equipment_by_id(item_id: str):
    all_items = {**EQUIPMENT, **MISSILES, **AIR_DEFENSE}
    return all_items.get(item_id)
