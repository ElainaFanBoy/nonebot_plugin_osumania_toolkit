from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""
    
    # =========== 常规配置 ===========

    # 缓存文件最大保留时间（小时），默认 24 小时
    omtk_cache_max_age: int = 24
    
    # 允许的最大谱面文件大小（MB），默认 50 MB
    max_file_size_mb: int = 50
    
    # .mc 转 .osu 的默认 OverallDifficulty 和 HPDrainRate
    default_convert_od: int = 8
    default_convert_hp: int = 8
    
    # =========== 分析常数 ===========
    
    # 按压分析基础阈值
    # 统计按压时长分布时，最大统计窗口（毫秒）
    bin_max_time: int = 500
    # 直方图桶宽（毫秒），越小越敏感但也更容易噪声抖动
    bin_width: int = 1
    # 轨道分布相似度过高时判作弊阈值
    sim_right_cheat_threshold: float = 0.99
    # 轨道分布相似度过高时判可疑阈值
    sim_right_sus_threshold: float = 0.985
    # 轨道分布相似度过低时判作弊阈值（过低可能是非自然映射/生成）
    sim_left_cheat_threshold: float = 0.4
    # 轨道分布相似度过低时判可疑阈值
    sim_left_sus_threshold: float = 0.55
    # 单个时间点尖峰占所在区间总量的比例阈值
    abnormal_peak_threshold: float = 0.33
    # 低于该采样率时，弱化部分时域尖峰检测，减少误判
    low_sample_rate_threshold: float = 165

    # 高级 delta_t 分析阈值（用于识别人类化脚本）
    # 多押强判：最小样本数
    delta_chord_hard_min_count: int = 16
    # 多押强判：近同步比例阈值（span <= 1.2ms 的占比）
    delta_chord_hard_ratio: float = 0.82
    # 多押强判：P95 跨度上限（毫秒）
    delta_chord_hard_p95: float = 1.8
    # 多押软判：最小样本数
    delta_chord_soft_min_count: int = 8
    # 多押软判：近同步比例阈值
    delta_chord_soft_ratio: float = 0.60
    # 多押软判：P90 跨度上限（毫秒）
    delta_chord_soft_p90: float = 2.2
    # 局部密度统计半径（毫秒），用于区分高密/低密段
    delta_dense_radius_ms: int = 180
    # 高密段强判：MAD 上限
    delta_dense_hard_mad: float = 1.8
    # 高密段强判：高密MAD/低密MAD 比值上限
    delta_dense_hard_ratio: float = 0.60
    # 高密段软判：MAD 上限
    delta_dense_soft_mad: float = 2.5
    # 高密段软判：高密MAD/低密MAD 比值上限
    delta_dense_soft_ratio: float = 0.70
    # 长空段画像：未匹配按键比例阈值
    delta_gap_unmatched_ratio: float = 0.35
    # 长空段画像：空段按键占比阈值
    delta_gap_press_ratio: float = 0.12
    # 多特征风险分融合：达到该分值直接判作弊
    delta_risk_cheat_score: int = 3
    # 多特征风险分融合：达到该分值判可疑
    delta_risk_sus_score: int = 1

    # 列内自相关与周期漂移检测（wander+tremor 叠加）
    # 列内自相关硬阈值（最大滞后相关系数）
    delta_col_autocorr_hard: float = 0.65
    # 列内自相关软阈值
    delta_col_autocorr_soft: float = 0.50
    # 列内低频能量占比硬阈值
    delta_col_lowfreq_hard: float = 0.48
    # 列内低频能量占比软阈值
    delta_col_lowfreq_soft: float = 0.38

    # 多押同步模板检测（针对同组同偏移模板复用）
    # 参与检测的最小多押组数量
    delta_chord_template_min_groups: int = 6
    # 模板量化步长（毫秒）
    delta_chord_template_quant_ms: float = 0.5
    # 组内近同偏移判定跨度（毫秒）
    delta_chord_template_span_ms: float = 1.4
    # 强判：主模板占比阈值
    delta_chord_template_hard_ratio: float = 0.52
    # 强判：组内近同偏移占比阈值
    delta_chord_template_hard_zero_ratio: float = 0.60
    # 软判：主模板占比阈值
    delta_chord_template_soft_ratio: float = 0.38
    # 软判：组内近同偏移占比阈值
    delta_chord_template_soft_zero_ratio: float = 0.50

    # 空敲上下文检测 v2（长空段时序评分）
    # 长空段最小长度（毫秒）
    delta_gap_v2_min_gap_ms: int = 1000
    # 长空段边缘内缩（毫秒）
    delta_gap_v2_inner_margin_ms: int = 100
    # IOI 量化步长（毫秒）
    delta_gap_v2_ioi_quant_ms: float = 8.0
    # 评分项权重：未匹配率
    delta_gap_v2_weight_unmatched: float = 0.30
    # 评分项权重：长空段空敲占比
    delta_gap_v2_weight_gap: float = 0.30
    # 评分项权重：时序规律度
    delta_gap_v2_weight_regular: float = 0.30
    # 评分项权重：列熵惩罚
    delta_gap_v2_weight_entropy: float = 0.10
    # v2 软判分数阈值
    delta_gap_v2_soft_score: float = 0.45
    # v2 强判分数阈值
    delta_gap_v2_hard_score: float = 0.60
    # 评分项权重：空闲段内位置均匀性
    delta_gap_v2_weight_uniform: float = 0.10

    # 按压时长分布形态检测（KDE + 理论分布贴合）
    # 平滑度软阈值
    time_shape_smoothness_soft: float = 0.98
    # 平滑度硬阈值
    time_shape_smoothness_hard: float = 0.99
    # 平滑度过低阈值
    time_shape_smoothness_low: float = 0.86
    # 理论分布拟合MSE软阈值（越小越贴合）
    time_shape_fit_mse_soft: float = 0.030
    # 理论分布拟合MSE硬阈值（越小越贴合）
    time_shape_fit_mse_hard: float = 0.022

    # 按压时长序列隐频检测
    # 共同主峰占比阈值
    time_duration_freq_common_ratio: float = 0.9
    # 共同主峰频谱强度阈值
    time_duration_freq_strength: float = 3.4

    # AR(1) 记忆模式拟合检测
    # 软判 R2 阈值
    delta_ar1_fit_soft_r2: float = 0.95
    # 强判 R2 阈值
    delta_ar1_fit_hard_r2: float = 0.98

    # 非线性记忆检测（用于补充 AR(1) 规则性识别）
    # 最小样本数
    delta_nonlinear_min_count: int = 260
    # BDS 显著性阈值
    delta_nonlinear_bds_p: float = 0.01
    # BDS epsilon 系数（epsilon = std * 系数）
    delta_nonlinear_bds_eps_scale: float = 0.7
    # PACF(滞后2~5) 显著阈值
    delta_nonlinear_pacf_threshold: float = 0.14
    # ARCH 检验显著性阈值
    delta_nonlinear_arch_p: float = 0.01
    # BDS 不可用时，残差平方一阶相关阈值
    delta_nonlinear_sqacf_threshold: float = 0.25

    # 轨道间相关性检测（剔除多押点后）
    # 最小对齐样本总数
    delta_cross_corr_min_pairs: int = 100
    # 零滞后相关系数绝对值中位阈值
    delta_cross_corr_threshold: float = 0.05
    # 滞后互相关最大绝对值中位阈值
    delta_cross_corr_lag_threshold: float = 0.05
    # 多押识别时间容差（毫秒）
    delta_cross_corr_chord_tol_ms: float = 1.0

    # 多押超近同步聚集检测
    # 最小样本数
    delta_chord_near_zero_min_count: int = 20
    # 近零跨度阈值（毫秒）
    delta_chord_near_zero_ms: float = 0.25
    # 软判近零占比阈值
    delta_chord_near_zero_soft_ratio: float = 0.72
    # 强判近零占比阈值
    delta_chord_near_zero_hard_ratio: float = 0.82
    # 宽差值判定阈值（毫秒）
    delta_chord_wide_ms: float = 2.0
    # 软判宽差值占比上限
    delta_chord_wide_soft_ratio: float = 0.10
    # 强判宽差值占比上限
    delta_chord_wide_hard_ratio: float = 0.06

    # 疲劳趋势与密度形态检测
    # 单调增长软阈值
    delta_fatigue_mono_soft: float = 0.83
    # 单调增长硬阈值
    delta_fatigue_mono_hard: float = 0.9
    # 高低密度分布形状差软阈值
    delta_fatigue_shape_diff_soft: float = 0.83
    # 高低密度分布形状差硬阈值
    delta_fatigue_shape_diff_hard: float = 0.9