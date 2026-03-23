# -*- coding: utf-8 -*-
"""
集中配置：用于快速调参。

说明：
1. 本文件仅放“经常需要手动微调”的常量，尽量避免把业务流程代码塞进来。
2. 改完后直接重新运行 main.py 即可生效（无需改其它模块）。
3. 这里的默认值尽量保持现有行为，只在你明确想调时再改。
"""

from __future__ import annotations


# -----------------------------
# 运行入口相关
# -----------------------------

# main.py 写入 output 时使用的默认 rate。
DEFAULT_RATE = 1.0

# 通过 bid 下载 .osu 的超时时间（秒）。
# 网络慢时可适当调大。
BID_DOWNLOAD_TIMEOUT_SECONDS = 20


# -----------------------------
# RatingMultiplier（倍率）
# -----------------------------

# CorePattern 级别倍率。
# 键名必须与 CorePattern.value 一致。
CORE_RATING_MULTIPLIER: dict[str, float] = {
    "Stream": 1.0 / 3.0,
    "Chordstream": 0.65,
    "Jacks": 0.9,
    "Coordination": 0.75,
    "Density": 0.9,
    "Wildcard": 1.0,
}

# 子类倍率覆盖。若子类不在该表中，会回退到对应 CorePattern 的倍率。
SUBTYPE_RATING_MULTIPLIER: dict[str, float] = {
    # Coordination
    "Column Lock": 0.75,
    "Release": 0.8,
    "Shield": 0.7,

    # Density
    "JS Density": 0.95,
    "HS Density": 1.10,
    "DS Density": 0.90,
    "LCS Density": 0.85,
    "DCS Density": 0.95,
    "Inverse": 0.8,

    # Wildcard
    "Jacky WC": 1.1,
    "Speedy WC": 0.65,
    "TimingHell": 0.8,
}


# -----------------------------
# 聚类/分类相关阈值
# -----------------------------

# assign_clusters 时，非 Mixed 模式按 ms/beat 聚类的距离阈值。
# 值越大：不同节奏更容易合并到同一 BPM 簇。
BPM_CLUSTER_THRESHOLD = 5.0

# Mixed 判定阈值：同一段内各点 ms/beat 相对均值的允许偏差。
# 偏差超过该阈值则更容易被判定为 Mixed。
PATTERN_STABILITY_THRESHOLD = 5.0

# “重要簇”筛选阈值：Importance / 第一簇 Importance > 该值。
# 值越低：参与分类判断的重要簇越多。
IMPORTANT_CLUSTER_RATIO = 0.5

# Category 里 Jumpstream/Handstream 混合命名阈值。
# 当第二名占比 / 第一名占比 > 该值时，名称显示为 Jumpstream/Handstream。
CATEGORY_JS_HS_SECONDARY_RATIO = 0.4

# SV 分类阈值（ms）。
SV_AMOUNT_THRESHOLD = 2000.0

# Cluster.Format 显示子类名称的最低占比。
# 设为 0.0 表示只要有子类统计就显示第一名子类名；
# 例如设为 0.4 表示第一名子类至少 40% 才显示，否则显示 CorePattern 名称。
CLUSTER_SPECIFIC_NAME_MIN_RATIO = 0.0


# -----------------------------
# 识别器相关（可用于微调判定松紧）
# -----------------------------

# Column Lock 中 jack 速度下限。
JACKY_MIN_BPM = 90.0

# Shield 的最大时间间隔上限（按 beat 比例）。
SHIELD_MAX_BEAT_RATIO = 0.25

# Inverse 判定：尾到头间隔一致性容忍（毫秒）。
INVERSE_GAP_TOLERANCE_MS = 30.0

# Inverse 判定：窗口内 LN Body 最少覆盖列数。
INVERSE_MIN_FILLED_LANES = 3

# TimingHell 的 grace 间隔窗口（按 beat 比例）。
GRACE_MIN_BEAT_RATIO = 1.0 / 20.0
GRACE_MAX_BEAT_RATIO = 1.0 / 4.0

# TimingHell：LN 上下文检测窗口。
TIMINGHELL_CONTEXT_WINDOW = 8

# TimingHell：最少需要的窗口行数。
TIMINGHELL_MIN_ROWS = 2

# TimingHell：是否要求 grace-like 通过。
# 设为 False 可大幅放宽：只要满足释放密度/抖动条件即可命中。
TIMINGHELL_REQUIRE_GRACE = True

# TimingHell：尾部释放间隔判定阈值（按 beat 比例）。
# 数值越大越宽松，例如 1/2 比 1/3 更宽松。
TIMINGHELL_TAIL_DELTA_BEAT_RATIO = 1.0 / 2.0

# TimingHell：尾部释放样本最少数量。
TIMINGHELL_MIN_TAIL_ROWS = 2

# TimingHell：抖动容忍阈值（ms）。
# 相邻释放间隔差异超过该值时，会被视作 timing 不稳定特征。
TIMINGHELL_JITTER_THRESHOLD_MS = 18.0

# Release：从窗口前多少行里找单尾（len(LNTails)==1）。
RELEASE_SCAN_ROWS = 7

# Release：至少需要多少个单尾点才能继续判定。
RELEASE_MIN_TAIL_ROWS = 2

# Release：用于判定 roll 的最小点数（给 STREAM_4K_ROLL 的长度）。
RELEASE_ROLL_POINTS = 3

# Release：达到该点数时返回更长匹配长度（更稳定的 Release 段）。
RELEASE_FULL_MATCH_ROWS = 4

# Jacky WC：LN 上下文检测窗口。
JACKY_CONTEXT_WINDOW = 2

# Jacky WC 放宽分支：当有连续 jack 且速度足够快时可判定。
JACKY_FALLBACK_MAX_MSPB = 170.0
