"""兼容层：保留旧导入路径，实际实现位于 algorithm.analyze。"""

from .analyze import (
    analyze_cheating,
    analyze_delta_t,
    analyze_pulse_spectrum,
    analyze_time_domain,
    run_analyze_cheating,
)

__all__ = [
    "run_analyze_cheating",
    "analyze_cheating",
    "analyze_time_domain",
    "analyze_delta_t",
    "analyze_pulse_spectrum",
]
