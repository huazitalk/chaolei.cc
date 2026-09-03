# -*- coding: utf-8 -*-
"""尺寸手册页英文翻译注入脚本（ZH2EN 字典补全）

用途
----
把 blog/miniature-bearing-size-chart.html（及 blog/index.html 中
tpl-size-chart 模板与卡片 aria-label）缺失的全部中文词条译成英文，
按 i18n-data.js 现有格式合并进 window.ZH2EN 字典。

设计要点（防错）
----------------
1. 中文 key 不手抄：脚本按文档出现顺序从 HTML 里自己提取，翻译按同序
   配对（TRANSLATIONS 列表），计数必须严格相等才允许写入。
2. key 一律先做 html.unescape：i18n.js 用 getAttribute() 取值，DOM 中
   「&gt;」已解码为「>」，字典 key 必须与解码后的值一致。
3. 幂等：已存在的 key 自动跳过，可重复执行。--dry-run 只打印不落盘。
4. 零三方依赖，仅标准库。

用法
----
    python3 translate_size_chart_i18n.py --dry-run   # 预览配对表
    python3 translate_size_chart_i18n.py             # 正式写入
"""
import argparse
import html
import json
import re
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DICT_FILE = ROOT / "js" / "i18n-data.js"
PAGE_FILE = ROOT / "blog" / "miniature-bearing-size-chart.html"
INDEX_FILE = ROOT / "blog" / "index.html"

SECTION_MARK = "/* ---- blog/miniature-bearing-size-chart（2026-09-03 翻译） ---- */"

# 按文档出现顺序排列的英文翻译（与提取出的缺失词条一一对应）
TRANSLATIONS = [
    # 1 页面标题
    "Miniature Deep Groove Ball Bearing Size Chart: Full d×D×B Tables for 68/69/60/62/63/MR/R/F Series (2026 Edition) | Chaolei Bearings",
    "Miniature Deep Groove Ball Bearing Size Chart",
    "Full bore × O.D. × width tables for 100+ models across the 68 / 69 / 60 / 62 / 63 / MR / R / F series, plus suffix code quick reference, bore-code shortcuts and interchange rules.",
    "📐 Size Chart",
    "Per GB/T 276 · ISO 15",
    "Updated 2026-09-01",
    "~12 min read",
    "Model Size Chart",
    # 9 导语（608 长段落）
    "The dimensions of a 608 bearing are 8 mm bore × 22 mm O.D. × 7 mm width, with a minimum chamfer r of 0.3 mm (GB/T 276 / ISO 15). It is the most-looked-up model in this guide and the highest-volume size in skate wheels, sliding-door rollers, toys and small appliance motors. This handbook provides complete d × D × B tables for 100+ models across eight series — 68, 69, 60, 62, 63, MR, R and F — plus the three most-used rules of thumb: ① Bore shortcut — for bores ≥ 10 mm, multiply the last two digits of the designation by 5 to get the bore in mm (6204 → 04×5 = 20 mm); for bores < 10 mm, the last digit is the bore (608 → 8 mm). ② ZZ and 2RS share exactly the same envelope dimensions, differing only in sealing — not in fitting size. ③ Only when d, D and B all match can two bearings interchange; if even one differs, the shaft or the housing bore must be modified.",
    "Contents",
    "1. Bottom Line First: Three Sentences",
    "2. One-Minute Lookup: The 12 Most-Used Models",
    "3. How to Read a Bearing Number: Designation Decoded",
    "4. Full Size Tables (Eight Series)",
    "5. Suffix Code Quick Reference",
    "6. Three-Step Selection",
    "7. Interchange & Substitution: What Can Replace a 608?",
    "8. Chaolei's Product Range",
    "FAQ",
    # 20 适合谁
    "Who This Guide Is For",
    "Mechanical and structural engineers who need to find a model from the available envelope space",
    "Purchasing and maintenance (MRO) staff holding an old model number and looking for a substitute",
    "Model selectors at OEMs making toys, small appliances, power tools, door & window hardware and hobby models",
    "Bearing distributors and dealers who prepare spec sheets for downstream customers",
    "Key Terms",
    "Bore (d)",
    "The bore of the inner ring, fitted to the shaft — the first constraining dimension in selection. In mm.",
    "Outer Diameter (D / O.D.)",
    "The outer diameter of the outer ring, fitted to the housing bore — determines mounting space. In mm.",
    "Width (B)",
    "The axial thickness between the two faces — determines the space taken in the axial (thrust) direction. In mm.",
    "Chamfer r",
    "The minimum corner radius at the boundary between each ring face and raceway — affects the design height of shaft and housing shoulders.",
    "A rolling bearing with continuous deep grooves on both rings and steel balls as rolling elements. It mainly carries radial load, plus light axial load in both directions, and is the most widely used bearing type (GB/T 276, ISO 15).",
    "Dimension Series",
    "The part of the designation that encodes how O.D. and width scale relative to the bore. For a given bore, a larger series number means a larger O.D. and width and higher load capacity: 68 < 69 < 60 < 62 < 63 < 64.",
    "Radial Internal Clearance",
    "The radial displacement the inner ring can move relative to the outer ring under no load. Per GB/T 4604.1: C2 < C0 (normal) < C3 < C4 < C5.",
    "Tolerance Class",
    "The grade of dimensional and running accuracy. Per GB/T 307.1: P0 (normal, unmarked by default) < P6 < P5 < P4 < P2.",
    # 41 三句话
    "Dimensions are standardized; performance is not. For any given model (e.g. 608), the d × D × B envelope is identical across every manufacturer worldwide — that is the interchangeability basis enforced by ISO 15. But load ratings, limiting speeds, noise levels and life vary with each maker's process — and that is what selection should really compare.",
    "Space first, load second. The order is always: shaft diameter sets d → housing bore sets D → axial space sets B → then verify load and speed. Finish the three steps and the model is unique.",
    "Sealing and clearance never change dimensions. Suffixes like ZZ, 2RS, C3 and P6 alter performance only, not d × D × B. So 608ZZ, 608-2RS and 608ZZ-C3 have identical fitting dimensions and are directly interchangeable.",
    # 44 12 型号表
    "90% of lookups land on these 12 models. If you only need one number, this table is enough.",
    "Model",
    "Bore d (mm)",
    "O.D. D (mm)",
    "Width B (mm)",
    "Skate wheels, folding-door rollers, toys, small appliance motors",
    "Hobby models, micro motors, medical devices",
    "Thin-wall miniature drives",
    "8 mm shafts needing higher load capacity",
    "Small motors, fishing reels",
    "Power tools, small blowers",
    "Toy gearboxes, micro water pumps",
    "Same O.D. as 608, different bore",
    "9 mm shafts needing more load capacity",
    "General small machinery, agricultural equipment",
    "General machinery, conveyor rollers",
    "The workhorse for motors, pumps and fans",
    "Chaolei note: the 608 is the highest-volume size among miniature bearings and our core product. Its versatility is exceptional — the 22 mm O.D. × 7 mm width envelope has become the default interface of the toy, skateboard and roller industries.",
    # 62 命名规则
    "A complete bearing designation = type code + dimension-series code + bore code + suffix codes.",
    "Take 608-2RS/C3 as an example:",
    "Segment",
    "Meaning",
    "Type code: deep groove ball bearing",
    "Dimension-series code (series 0, thin section)",
    "Bore code: 8 mm bore (for bores < 10 mm, read the digit directly)",
    "Suffix: double-sided rubber contact seals",
    "Suffix: radial clearance greater than the normal group",
    # 71 内径速算
    "Bore Code Shortcut (Three Rules)",
    "Bore Range",
    "How to Read",
    "Example",
    "d ≥ 20 mm (code 04 and up)",
    "Last two digits × 5 = bore in mm",
    "6204 → 04 × 5 = 20 mm; 6308 → 08 × 5 = 40 mm",
    "d = 10 / 12 / 15 / 17 mm",
    "Special codes 00 / 01 / 02 / 03",
    "6200 → 10 mm; 6201 → 12 mm; 6202 → 15 mm; 6203 → 17 mm",
    "d < 10 mm",
    "The last digit is the bore in mm",
    "608 → 8 mm; 627 → 7 mm; 685 → 5 mm",
    "The most common misread: taking 608 as \"60 × 5 = 300 mm\" or \"08 × 5 = 40 mm\". Remember the boundary — below a 10 mm bore, do not multiply by 5; read the last digit directly.",
    "Comparing Dimension Series",
    "For a given bore, a larger series number means a \"thicker\" bearing, higher load capacity and lower limiting speed:",
    "Series 68: thinnest, space-saving, lowest capacity (e.g. 688: 8×16×5)",
    "Series 69: thin section (e.g. 698: 8×19×6)",
    "Series 60: the most common \"standard width\" (e.g. 608: 8×22×7)",
    "Series 62: wide, high capacity (e.g. 628: 8×24×8)",
    "Series 63: widest, highest capacity, lowest speed (e.g. 6300: 10×35×11)",
    "Selection shortcut: if load capacity is short at a given bore, don't rush to a bigger shaft — first step up one series. If a 608 is not enough, move to a 628 (8×24×8, only 2 mm larger in O.D.); that usually solves it.",
    # 93 全系列尺寸表
    "4. Full Size Tables",
    "Data Basis Notes",
    "Series 68 miniature widths exist under two conventions",
    "Common sizes used by Chinese miniature bearing makers",
    "4.1 Series 68 (Extra Thin Section)",
    "Series 68 has the smallest O.D. and thinnest width for a given bore — for extremely tight radial space (models, micro motors, medical devices).",
    "Width B",
    "r min",
    "4.2 Series 69 (Thin Section)",
    "4.3 Series 60 (Core Miniature & Small Sizes)",
    "The 608 sits in this series. Series 60 is the highest-volume segment of miniature bearings and Chaolei's core range.",
    "4.4 Series 62 (Enhanced Capacity)",
    "4.5 Series 63 (Medium-Large, Heavy Load / Low Speed)",
    "4.6 MR Series (Metric Miniature, Bore < 10 mm)",
    "The MR series is the \"small and flat\" branch of miniature bearings, common in models, micro motors and precision instruments. Widths typically run 2.5–4 mm.",
    "4.7 R Series (Inch-Size Miniature)",
    "Inch-size bearings are defined directly in inches; converted to millimeters they carry decimals, so they cannot directly interchange with metric models (unless the dimensions coincide exactly). Common in imported-equipment repair and US-standard products.",
    "Inch Sizes (in)",
    "The inch-size trap: the R6's 9.525 mm bore differs from a metric 10 mm by only 0.475 mm, and its 22.225 mm O.D. differs from a 608's 22 mm by just 0.225 mm — it looks like it will fit, but it is a misfit. The tolerance bands of shaft and bore do not overlap; force it in and the bearing will slip or split. Inch equipment must use inch bearings.",
    "4.8 F Series (Flanged, Miniature Sizes)",
    "Flanged bearings add a rim on the outer ring for axial location — the flange face seats against the housing face, eliminating a retaining ring or shoulder. In the tables, D1 is the flange O.D. and C1 the flange thickness.",
    "Flange O.D. D1",
    "Flange Thickness C1",
    "Flange pitfall: flange O.D. D1 and thickness C1 are not ISO-unified and vary widely between makers. Always get the specific manufacturer's drawing — never order by model number alone.",
    # 117 后缀
    "Suffixes change performance only, never the d × D × B fitting dimensions. This is the most misunderstood point in bearing selection.",
    "5.1 Seals & Shields",
    "Code",
    "Features",
    "Typical Use",
    "Open type (no suffix)",
    "No sealing",
    "Lowest friction, highest limiting speed, re-greasable",
    "Host machine already sealed, or periodic re-oiling required",
    "Single-sided metal shield",
    "Dust-proof but not water-proof, low drag",
    "Dust on one side only, oil passage on the other",
    "Double-sided metal shields (ZZ)",
    "Dust-proof but not water-proof, low friction, high speed",
    "Dry, clean environments: indoor furniture, office equipment, skateboards",
    "Single-sided rubber contact seal",
    "Dust- and water-proof, higher drag",
    "Moisture on one side only",
    "Double-sided rubber contact seals (2RS)",
    "Best dust and water protection; limiting speed ~30% lower than ZZ",
    "Wet and dusty: bathroom rollers, outdoor use, agricultural machinery, food machinery",
    "ZZ or 2RS: choose ZZ for dry and clean, 2RS for wet and dusty; when unsure, go 2RS. The two have identical envelope dimensions and are interchangeable — the only cost is a slight difference in speed and starting torque.",
    "5.2 Clearance Classes (GB/T 4604.1)",
    "Clearance",
    "When to Choose",
    "Smaller than the normal group",
    "Precision applications needing low vibration, high running accuracy and small clearance",
    "Normal group (default, usually unmarked)",
    "General operating conditions",
    "Greater than the normal group",
    "Motors, high temperatures, interference fits, large shaft-to-housing temperature differences — the most common non-default choice",
    "Even greater",
    "Heavy interference, extreme temperature differences, vibrating screens and other severe duty",
    "When C3 is a must: when the motor shaft expands from heat, or the bearing is interference-fitted to the shaft or housing, the fit \"eats\" part of the clearance after assembly. Normal-group C0 can then cause tight running or even seizure. Motor applications default to C3.",
    # 151 公差等级
    "5.3 Tolerance / Precision Classes",
    "China GB/T 307.1",
    "US ABEC (approximate)",
    "Normal grade, unmarked by default — sufficient for the vast majority of uses",
    "Higher running accuracy, for medium-precision spindles",
    "Precision machine-tool spindles, high-speed motors",
    "High-accuracy spindles",
    "Ultra-precision",
    "A pragmatic view: ABEC grades measure only dimensional and running accuracy — not material, noise or life. An ABEC-5 carbon-steel bearing may last far less than a P0 GCr15 bearing. Don't buy a precision grade as if it were a quality grade.",
    "5.4 Vibration (Noise) Grades (GB/T 32325)",
    "Z / Z1",
    "Base grade (some makers omit Z)",
    "Low vibration — adequate for general quiet use",
    "Lower vibration — appliance motors, quiet fans",
    "Lowest vibration — precision instruments, stringent silence requirements",
    "The higher the digit in the code, the stricter the vibration limit (the quieter). Velocity grades are coded V / V1 / V2 / V3 / V4.",
    # 167 其他后缀
    "5.5 Other Common Suffixes",
    "Snap-ring groove in the outer ring",
    "Snap-ring groove + snap ring in the outer ring",
    "Stainless steel (commonly SUS440C) — for food, medical and wet corrosive environments",
    "High-temperature grease",
    "Tapered bore (1:12 taper)",
    # 173 三步法
    "Step 1 — Fix the dimensions. Shaft diameter → d; housing bore → D; axial space → B. Once these three are locked, the model is essentially unique.",
    "Step 2 — Pick the suffixes. Choose sealing, clearance, flange or material from the table below against your operating conditions.",
    "Step 3 — Verify load and speed. Compare the basic dynamic load rating Cr with the equivalent dynamic load P of your duty, and calculate L10 life per ISO 281.",
    "Condition",
    "Recommended Suffix",
    "Dry indoor, seeking speed and low drag",
    "Wet, dusty, outdoor",
    "Motors, shafts that heat up",
    "Axial location needed, shoulder impractical",
    "Food, medical, corrosive environments",
    "Life Formula (ISO 281)",
    "L10 (rev) = (Cr / P)³ × 10⁶",
    "L10 (hours) = L10 (rev) ÷ (60 × speed n)",
    "Practical Rule of Thumb",
    "If the actual load stays below 1/10 of Cr, life is rarely an issue; above 1/3, recalculate.",
    "Load Rating Quick Reference for Common Models (Typical Values)",
    "Dynamic Rating Cr (kN)",
    "Static Rating C0r (kN)",
    "Grease Limiting Speed (r/min)",
    "Reference Weight (kg)",
    "Important",
    "Cr / C0r and limiting speeds are not ISO-unified values; they vary with each maker's internal design (ball count and diameter, raceway curvature, cage type, grease). The table above shows typical industry reference values. For volume purchasing, defer to the supplier's official catalog or technical agreement.",
    # 196 互换
    "The sole criterion for interchange: d, D and B must all match. If any one differs, no direct substitution.",
    "7.1 Interchangeable Combinations",
    "Combination",
    "All 8×22×7 — directly interchangeable, differing only in sealing and clearance",
    "Different precision, same dimensions — interchangeable (higher precision replacing lower is fine)",
    "Same dimensions, interchangeable — but load capacity drops ~20% and speed is lower",
    "7.2 Common \"Looks Interchangeable, Isn't\" Cases",
    "Size Comparison",
    "Verdict",
    "Same O.D. and width, bore differs by 1 mm. A 0.5 mm-wall sleeve can serve as a stopgap, but concentricity and load capacity suffer — not recommended for long-term use",
    "Same bore, different O.D. and width — not interchangeable",
    "O.D. differs by 3 mm, width by 1 mm — not interchangeable",
    "O.D. larger by 2 mm, width by 1 mm — not interchangeable (but the 628 is the first upgrade when a 608 runs out of load capacity)",
    "Looks close, but the tolerance bands don't overlap — never mix",
    "Same bore, O.D. differs by 4 mm — not interchangeable",
    "7.3 Upgrade Path When Load Is Short (8 mm Shaft Example)",
    "608 (8×22×7) → 628 (8×24×8) → custom oversized-ball design.",
    "The first two steps are standard models: the O.D. grows only 2 mm, the housing bore usually takes it with a single cut, cost barely rises and load capacity clearly improves. If that is still not enough, consider a larger shaft (move to the 6000 series) or needle / tapered roller bearings — but by then the whole structure usually needs redesigning.",
    # 213 供货范围
    "8. Chaolei's Product Range (Honestly Stated)",
    "What we make: 608-series miniature deep groove ball bearings across 15 standard sizes, including open, ZZ metal-shield, 2RS rubber-seal, C3 large-clearance and P6 precision variants; we also support neighboring models such as 607 and 609, plus custom builds (flanged, stainless steel, special clearance, special grease).",
    "What we don't make: no large bearings (above series 62), no non-ball types such as tapered or spherical roller bearings, and no tiny custom batches that cannot amortize tooling costs.",
    "For a confirmed list of specific models, contact our sales rep for the latest supply catalog and technical data sheets — the full series listed in this handbook is a standard-size reference and does not mean all are in our stock.",
    # 217 FAQ
    "What exactly are the dimensions of a 608 bearing?",
    "8 mm bore × 22 mm O.D. × 7 mm width, minimum chamfer 0.3 mm, per GB/T 276 / ISO 15. This is a globally unified interchangeable size — any qualified 608 from any maker fits the same position. Reference weight ≈ 0.012 kg; typical basic dynamic load rating ≈ 3.3 kN.",
    "Are 608ZZ and 608-2RS the same size? Interchangeable?",
    "Exactly the same — both 8×22×7, fully interchangeable. The only difference is sealing: ZZ has double metal shields, dust-proof but not water-proof, with low friction and a high limiting speed (~34,000 r/min); 2RS has double rubber contact seals, better dust and water protection, but a limiting speed ~30% lower than ZZ. Choose ZZ for dry indoor, 2RS for wet and dusty.",
    "How do I read the bore from a bearing model number?",
    "Three rules. ① Bores ≥ 20 mm (code 04 up): last two digits × 5, e.g. 6204 = 04 × 5 = 20 mm. ② Codes 00/01/02/03 are special: 10 / 12 / 15 / 17 mm respectively. ③ Bores < 10 mm: the last digit is the bore in mm, e.g. 608 = 8 mm, 627 = 7 mm, 685 = 5 mm. The third rule is where most mistakes happen — don't read 608 as 40 mm.",
    "What can replace a 608 when load capacity is not enough?",
    "First choice is the 628 (8×24×8): only 2 mm larger in O.D. and 1 mm in width, a clear capacity gain, and the housing usually takes it with a single cut. Second is the 629 (9×26×8), but that requires changing the shaft from 8 mm to 9 mm. If both steps still fall short, the structure needs redesigning — not just a different bearing.",
    "Do suffixes like ZZ, 2RS, C3 or P6 change bearing dimensions?",
    "No. Suffixes only change sealing, clearance, precision, material and lubrication — the d × D × B fitting dimensions stay identical. So 608ZZ, 608-2RS, 608ZZ/C3 and 608-P6 all fit at 8×22×7 and are mutually replaceable. The only exception is the flanged F series (e.g. F608), whose flange takes extra axial and radial space.",
    "What is C3 clearance, and when is it needed?",
    "C3 means radial internal clearance greater than the normal group (C0). Choose C3 whenever there is motor or bearing heat, an interference fit between shaft and inner ring, or a large shaft-to-housing temperature difference — because fit interference and thermal expansion \"eat\" part of the clearance, and C0 can then run tight or even seize. Per GB/T 4604.1, the clearance order is C2 < C0 < C3 < C4 < C5.",
    "Are ABEC-5 / ABEC-7 bearings better quality than standard ones?",
    "Not necessarily. ABEC grades measure only dimensional tolerances and running accuracy — not material, heat treatment, noise or life. An ABEC-5 carbon-steel bearing may last far less than a P0 bearing made of GCr15 bearing steel. Better questions when purchasing: is the material GCr15? Are the raceways superfinished? What ball grade (G)? What vibration grade?",
    "Why do different catalogs show different 68-series miniature sizes?",
    "Because two conventions coexist: the ISO 618 thin-section series (e.g. 618/8 = 8×16×4) and Chinese miniature-bearing industry practice (e.g. 688 = 8×16×5), with widths differing by up to 1–2 mm. This handbook uses the common sizes of Chinese miniature bearing makers. Before volume purchasing, always obtain the specific maker's official catalog or drawings — never order by model number alone.",
    "Can a flanged bearing (F608) fit where a normal 608 goes?",
    "Usually not. The F608's bore, O.D. and width match the 608 (8×22×7), but its outer ring carries an extra flange (commonly 25 mm flange O.D. × 1.5 mm thick), which needs a counterbore or relief at the housing face. Flange dimensions also differ between makers — confirm against the specific maker's drawing.",
    "Can the inch-size bearing R6 replace a 608?",
    "No. The R6 is 9.525 × 22.225 × 5.558 mm; the 608 is 8 × 22 × 7 mm. Although they differ by only a few tenths of a millimeter and it looks like it will fit, the tolerance bands do not overlap — fitted anyway, it will be either loose (slipping) or tight (splitting the inner ring). Inch equipment must use inch bearings, and vice versa.",
    "Reference standards: GB/T 272 (rolling bearing designation), GB/T 276 (deep groove ball bearing specifications), GB/T 273.3 (rolling bearing boundary dimensions), GB/T 307.1 (rolling bearing tolerances), GB/T 4604.1 (radial internal clearance), GB/T 32325 (DGBB vibration specifications), GB/T 6391 / ISO 281 (dynamic load ratings and life), ISO 15 (rolling bearing boundary dimensions), GB/T 18254 (high-carbon chromium bearing steel).",
    "Disclaimer: dimensions in these tables are compiled from public standards and common industry data, for selection reference. Load ratings, limiting speeds and weights are typical values that vary by maker; for volume purchasing, defer to the supplier's official catalog and technical agreement.",
    "About the Author",
    "Guantao Chaolei Bearing Manufacturing Co., Ltd. is located in Guantao, Hebei — China's light-industry bearing town. Making miniature bearings since 2000 with a focus on the 608 series, the company runs its own 3,000 m² plant with 100 grinding machines, 50 superfinishing machines and 50 automated pairing machines, producing 400,000 bearings a day across all 15 models of the 608 series, supplying the Chenghai toy market and exporting to India, Pakistan, Europe and Dubai.",
    "For exact dimensions, material certificates or sample testing of any model, contact our sales rep directly — we ship samples first, you test first, then we talk volume.",
]

# 其他文件（blog/index.html 卡片 aria-label 等）的词条，显式 key→value
EXTRA = {
    "阅读全文：微型深沟球轴承型号尺寸对照手册：68/69/60/62/63/MR/R/F 全系列尺寸表（2026 版）":
        "Read full article: Miniature Deep Groove Ball Bearing Size Chart — Full d×D×B Tables for 68/69/60/62/63/MR/R/F Series (2026 Edition)",
}


def extract_keys(text):
    """按文档出现顺序提取 data-i18n 词条（去重、DOM 解码）。"""
    keys, seen = [], set()
    for raw in re.findall(r'data-i18n="([^"]+)"', text):
        k = html.unescape(raw)
        if k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


def load_existing(i18n_src):
    """解析字典中已有的 key 集合。"""
    return set(re.findall(r'^\s*"((?:[^"\\]|\\.)*)":', i18n_src, re.M))


def extra_pairs_possible(extra, existing):
    """EXTRA 中是否还有未写入的词条。"""
    return [k for k in extra if k not in existing]


def main():
    ap = argparse.ArgumentParser(description="尺寸手册页英文翻译注入 ZH2EN 字典")
    ap.add_argument("--dry-run", action="store_true", help="只打印配对表，不写入")
    args = ap.parse_args()

    page = PAGE_FILE.read_text(encoding="utf-8")
    i18n_src = DICT_FILE.read_text(encoding="utf-8")
    existing = load_existing(i18n_src)

    # 独立页 + 弹窗模板 + 卡片 aria-label 全量词条（模板 ⊆ 独立页）
    all_keys = extract_keys(page)
    missing = [k for k in all_keys if k not in existing]

    # 模板中的额外来源（理论上 ⊆ 独立页，仅校验不遗漏）
    tpl_keys = set()
    m = re.search(r'<template id="tpl-size-chart">(.*?)</template>',
                  INDEX_FILE.read_text(encoding="utf-8"), re.S)
    if m:
        tpl_keys = set(extract_keys(m.group(1))) - set(all_keys)
    if tpl_keys:
        print(f"⚠ 模板中存在独立页没有的词条 {len(tpl_keys)} 条，需人工确认")
        for k in sorted(tpl_keys):
            print("  -", k[:60])

    # 幂等：词条已全部写入时直接正常退出
    if not missing and not extra_pairs_possible(EXTRA, existing):
        print("✅ 无缺失词条（此前已全部写入），无需操作。")
        return

    # 计数与配对校验：TRANSLATIONS 必须与 missing 逐条对应
    print(f"缺失词条：{len(missing)} 条，提供译文：{len(TRANSLATIONS)} 条")
    if len(missing) != len(TRANSLATIONS):
        print("❌ 数量不一致，拒绝写入。请核对 TRANSLATIONS 列表与页面词条。")
        for i in range(max(len(missing), len(TRANSLATIONS))):
            mk = missing[i][:50] if i < len(missing) else "<无>"
            tv = TRANSLATIONS[i][:50] if i < len(TRANSLATIONS) else "<无>"
            if (i >= len(missing)) or (i >= len(TRANSLATIONS)) or None:
                print(f"  [{i+1}] 页面:{mk}  |  译文:{tv}")
        sys.exit(1)

    pairs = list(zip(missing, TRANSLATIONS))

    # EXTRA 中剔除已存在的
    extra_pairs = [(k, v) for k, v in EXTRA.items() if k not in existing]

    # 打印配对表（前 8 条 + 抽查）
    print("\n=== 配对表（前 8 条） ===")
    for k, v in pairs[:8]:
        print(f"  {k[:38]:40s} -> {v[:60]}")
    print("  ...")
    for idx in (9, 42, 84, 118, 151, 196, 217, len(pairs)):
        if 0 < idx <= len(pairs):
            k, v = pairs[idx - 1]
            print(f"  [{idx}] {k[:38]:40s} -> {v[:60]}")
    if extra_pairs:
        print("=== 额外词条（index.html 卡片） ===")
        for k, v in extra_pairs:
            print(f"  {k[:38]:40s} -> {v[:60]}")

    if args.dry_run:
        print(f"\n[dry-run] 将写入 {len(pairs) + len(extra_pairs)} 条，未落盘。")
        return

    # 生成新条目行，插入字典末尾 } 之前
    lines = [SECTION_MARK]
    lines += [f" {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},"
              for k, v in pairs + extra_pairs]

    if SECTION_MARK in i18n_src:
        # 幂等：区块已存在则整体替换
        start = i18n_src.index(SECTION_MARK)
        end = i18n_src.index("};", start)
        new_src = i18n_src[:start] + "\n".join(lines) + "\n" + i18n_src[end:]
    else:
        # 在最后一个 "};;" 前插入
        tail = i18n_src.rstrip()
        assert tail.endswith("};"), "字典文件结尾不是 };"
        new_src = tail[:-2].rstrip().rstrip(",") + ",\n\n" + "\n".join(lines) + "\n};\n"

    DICT_FILE.write_text(new_src, encoding="utf-8")
    print(f"\n✅ 已写入 {len(pairs) + len(extra_pairs)} 条到 {DICT_FILE}")


if __name__ == "__main__":
    main()
