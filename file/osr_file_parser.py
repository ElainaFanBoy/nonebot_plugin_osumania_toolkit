import os
import struct
import lzma
import datetime
import numpy as np
from collections import Counter
from nonebot.log import logger

MOD_MAPPING = {
    0: "None",
    1: "NoFail",
    2: "Easy",
    4: "TouchDevice",
    8: "Hidden",
    16: "HardRock",
    32: "SuddenDeath",
    64: "DoubleTime",
    128: "Relax",
    256: "HalfTime",
    512: "Nightcore",
    1024: "Flashlight",
    2048: "Autoplay",
    4096: "SpunOut",
    8192: "Autopilot",
    16384: "Perfect",
    32768: "Key4",
    65536: "Key5",
    131072: "Key6",
    262144: "Key7",
    524288: "Key8",
    1048576: "FadeIn",
    2097152: "Random",
    4194304: "Cinema",
    8388608: "TargetPractice",
    16777216: "Key9",
    33554432: "Coop",
    67108864: "Key1",
    134217728: "Key3",
    268435456: "Key2",
    536870912: "ScoreV2",
    1073741824: "Mirror",
}


# ---------- 辅助函数 ----------
def read_uleb128(data, offset):
    """从字节流中读取ULEB128编码的整数，返回(值, 新偏移)"""
    result = 0
    shift = 0
    while True:
        b = data[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return result, offset

def read_string(data, offset):
    """读取osu!专用变长字符串，返回(字符串, 新偏移)"""
    if offset >= len(data):
        return "", offset
    flag = data[offset]
    offset += 1
    if flag == 0x00:
        return "", offset
    elif flag == 0x0B:
        length, offset = read_uleb128(data, offset)
        if offset + length > len(data):
            return "", offset
        s = data[offset:offset+length].decode('utf-8')
        offset += length
        return s, offset
    else:
        # 无效标志，返回空
        return "", offset

class ReplayEvent:
    """模拟osrparse的事件对象，仅包含time_delta和keys""" 
    def __init__(self, time_delta, keys):
        self.time_delta = time_delta
        self.keys = keys

def findkey(x=0):
    """将按键掩码转换为18位二进制数组"""
    keyset = [0] * 18
    a, keyset[0] = x // 2, x % 2
    j = 1
    while a != 0:
        a, keyset[j] = a // 2, a % 2
        j += 1
    return np.array(keyset)

class osr_file:
    def __init__(self, file_path):
        self.file_path = file_path
        self.status = "init"

        # 读取整个文件
        with open(file_path, 'rb') as f:
            data = f.read()

        offset = 0
        # 游戏模式 (1 byte)
        if offset >= len(data):
            self.status = "ParseError"
            return
        self.game_mode = data[offset]
        offset += 1
        if self.game_mode != 3:
            self.status = "NotMania"
            return

        # 游戏版本 (4 bytes, int)
        if offset + 4 > len(data):
            self.status = "ParseError"
            return
        self.game_version = struct.unpack('<i', data[offset:offset+4])[0]
        offset += 4

        # 谱面hash
        self.beatmap_hash, offset = read_string(data, offset)
        # 玩家名
        self.player_name, offset = read_string(data, offset)
        # 回放hash
        self.replay_hash, offset = read_string(data, offset)

        # 统计信息 (6个short + 1个int + 1个short + 1个byte)
        if offset + 19 > len(data):
            self.status = "ParseError"
            return
        self.number_300s = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.number_100s = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.number_50s = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.gekis = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.katus = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.misses = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.score = struct.unpack('<i', data[offset:offset+4])[0]
        offset += 4
        self.max_combo = struct.unpack('<h', data[offset:offset+2])[0]
        offset += 2
        self.is_perfect_combo = data[offset] != 0
        offset += 1

        # mod组合 (4 bytes)
        if offset + 4 > len(data):
            self.status = "ParseError"
            return
        self.mod = struct.unpack('<i', data[offset:offset+4])[0]
        offset += 4
        
        # mod列表
        self.mods = self._parse_mods(self.mod)

        # HP字符串
        self.life_bar_graph, offset = read_string(data, offset)

        # 时间戳 (8 bytes, ticks)
        if offset + 8 > len(data):
            self.status = "ParseError"
            return
        ticks = struct.unpack('<q', data[offset:offset+8])[0]
        offset += 8
        # Windows ticks: 从0001-01-01开始的100ns间隔
        self.timestamp = datetime.datetime.min + datetime.timedelta(microseconds=ticks/10)

        # 压缩数据长度
        if offset + 4 > len(data):
            self.status = "ParseError"
            return
        replay_data_length = struct.unpack('<i', data[offset:offset+4])[0]
        offset += 4

        # 压缩数据
        if offset + replay_data_length > len(data):
            self.status = "ParseError"
            return
        compressed_data = data[offset:offset+replay_data_length]
        self.compressed_data = compressed_data

        # 在线成绩ID (8 bytes)
        if offset + 8 > len(data):
            # 有些老版本没有？尝试读取，如果不够则忽略
            self.replay_id = 0
        else:
            self.replay_id = struct.unpack('<q', data[offset:offset+8])[0]
            offset += 8

        # 附加模组信息 (Target Practice等) 暂时忽略
        self.extra_mod_data = None

        # 初始化派生数据
        self.play_data = []          # 将在process中填充
        self.pressset = [[] for _ in range(18)]
        self.intervals = []
        self.press_times = []
        self.press_events = []
        self.sample_rate = float('inf')
        self.acc = 0.0
        self.ratio = 0.0
        self.judge = {
            "320": self.gekis,
            "300": self.number_300s,
            "200": self.katus,
            "100": self.number_100s,
            "50": self.number_50s,
            "0": self.misses,
        }
        totObj = self.gekis + self.number_300s + self.number_100s + self.number_50s + self.misses + self.katus
        if totObj > 0:
            self.acc = ((self.gekis + self.number_300s) * 300 + self.katus * 200 +
                        self.number_100s * 100 + self.number_50s * 50) / (totObj * 300) * 100
        self.ratio = self.gekis / self.number_300s if self.number_300s > 0 else 0

        # 如果之前状态正常，则继续，否则标记
        if self.status == "init" and self.game_mode == 3:
            self.status = "OK"
        else:
            self.status = "ParseError" if self.status != "NotMania" else "NotMania"

    def process(self):
        """解压LZMA数据并处理事件"""
        if self.status not in ["OK", "init"]:
            return

        try:
            decompressed = lzma.decompress(self.compressed_data).decode('ascii')
        except Exception as e:
            logger.error(f"LZMA解压失败: {e}")
            self.status = "ParseError"
            return

        frames = decompressed.split(',')
        pressed_start = {}          # 记录每个键的按下起始时间（原始时间）
        current_time_raw = 0         # 累积原始时间
        onset = np.zeros(18)        # 当前帧的按键状态
        timeset = np.zeros(18)      # 当前键已持续的时间（原始时间）

        # 用于存储原始数据
        intervals_raw = []
        press_events_raw = []        # 每个元素为 (col, time_raw)
        press_times_raw = []         # 所有按下时刻的原始时间

        for frame in frames:
            if not frame:
                continue
            parts = frame.split('|')
            if len(parts) < 4:
                continue
            w = int(parts[0])
            x_val = float(parts[1])
            y_val = float(parts[2])   # 坐标 y，用于检测定位帧

            # 跳过种子帧
            if w == -12345:
                continue

            # 检测并跳过定位帧 (256, -500)
            if abs(x_val - 256) < 1e-6 and abs(y_val + 500) < 1e-6:
                continue

            # 累加原始时间
            current_time_raw += w
            intervals_raw.append(w)

            keys_bitmask = int(x_val)
            r_onset = findkey(keys_bitmask)

            # 检测新按下的键（原始时间）
            for k, l in enumerate(r_onset):
                if onset[k] == 0 and l == 1:
                    press_times_raw.append(current_time_raw)
                    press_events_raw.append((k, current_time_raw))

            timeset += onset * w
            for k, l in enumerate(r_onset):
                if onset[k] != 0 and l == 0:
                    # 键释放，记录按压时长（原始时间）
                    # 此处将按压时长存入 pressset_raw，稍后根据速度因子缩放
                    # 为了方便，先暂存在临时字典，最后再统一处理
                    pass  # 我们稍后统一处理按压时长，因为需要释放事件
                    # 实际可在释放时直接存入，但需要知道原始时长
            onset = r_onset

        # 现在需要构建按压时长（原始）列表 pressset_raw
        # 由于我们只有按下和释放事件，需要重建。简单的方法是：
        # 从 press_events_raw 中按列整理按下和释放，计算持续时间。
        # 但您原有代码中，pressset 是在循环中实时计算的，并且依赖于 timeset。
        # 为了最小改动，我们可以保留原计算逻辑，但将 timeset 的累积基于原始时间。
        # 实际上，原代码中 timeset 的累积是正确的，只要 w 是原始时间。
        # 我们只需要在最后将按压时长（存储在 pressset 中）进行缩放即可。
        # 但原代码中 pressset 是在循环内直接 append 的，且使用了 timeset[k]（原始时间）。
        # 所以 pressset 已经存储了原始时长。

        # 由于我们已经修改了循环，删除了原有的 pressset 填充代码，现在需要重新加入。
        # 最好将原循环完整保留，仅修改时间累加和跳过定位帧的部分。

        # 建议：复制原有循环，但将 current_time 改为 current_time_raw，并跳过定位帧。
        # 原代码中 pressset 的填充依赖于 timeset 和 onset 的变化，这部分可以保留。
        # 我们直接修改原有循环，添加定位帧跳过，并确保 timeset 使用原始时间。

        # 重写循环如下：
        pressed_start = {}
        current_time_raw = 0
        onset = np.zeros(18)
        timeset = np.zeros(18)
        intervals_raw = []
        press_events_raw = []
        press_times_raw = []
        pressset_raw = [[] for _ in range(18)]   # 原始按压时长

        for frame in frames:
            if not frame:
                continue
            parts = frame.split('|')
            if len(parts) < 4:
                continue
            w = int(parts[0])
            x_val = float(parts[1])
            y_val = float(parts[2])
            if w == -12345:
                continue
            if abs(x_val - 256) < 1e-6 and abs(y_val + 500) < 1e-6:
                continue
            current_time_raw += w
            intervals_raw.append(w)
            keys_bitmask = int(x_val)
            r_onset = findkey(keys_bitmask)

            for k, l in enumerate(r_onset):
                if onset[k] == 0 and l == 1:
                    press_times_raw.append(current_time_raw)
                    press_events_raw.append((k, current_time_raw))
                    # 可选：记录按下起始时间（用于计算时长），但 timeset 已处理

            timeset += onset * w
            for k, l in enumerate(r_onset):
                if onset[k] != 0 and l == 0:
                    # 释放，记录原始按压时长
                    pressset_raw[k].append(int(timeset[k]))
                    timeset[k] = 0
            onset = r_onset

        # 现在我们有原始数据
        self.intervals_raw = intervals_raw
        self.press_events_raw = press_events_raw
        self.press_times_raw = press_times_raw
        self.pressset_raw = pressset_raw

        # 计算速度因子和实时缩放系数
        speed_factor = 1.0
        try:
            mod_int = int(self.mod)
        except Exception:
            mod_int = 0
        if mod_int != 0:
            mod_bin = bin(mod_int)[2:].zfill(32)
            # DT (位6) 或 Nightcore (位9) 实际 DT 和 NC 都使用 speed_factor=1.5
            if (mod_int & 64) or (mod_int & 512):
                speed_factor = 1.5
            elif mod_int & 256:   # HalfTime
                speed_factor = 0.75
        # corrector = 1/speed_factor，用于将原始时间转换为实时时间
        corrector = 1.0 / speed_factor

        self.corrector = corrector
        self.speed_factor = speed_factor

        # 生成实时时间数据（用于分析和绘图）
        self.press_times = [int(t * corrector) for t in press_times_raw]
        self.press_events = [(col, int(t * corrector)) for col, t in press_events_raw]
        self.intervals = [int(w * corrector) for w in intervals_raw]
        self.pressset = [
            [int(d * corrector) for d in col_data] if col_data else []
            for col_data in pressset_raw
        ]

        # 估算采样率（使用实时间隔）
        if self.intervals:
            interval_counts = Counter(self.intervals)
            most_common_interval, _ = interval_counts.most_common(1)[0]
            self.sample_rate = 1000 / most_common_interval
        else:
            self.sample_rate = float('inf')

        # 过滤无效轨道（使用原始数据判断？用 pressset_raw 或 pressset 均可）
        valid_pressset = [p for p in self.pressset if len(p) > 5]
        if len(valid_pressset) < 2:
            self.status = "tooFewKeys"
        else:
            self.status = "OK"
            
        logger.debug(f"按下事件总数(len(self.press_events)): {len(self.press_events)}")
        logger.debug(f"按下事件总数(len(self.press_times))：{len(self.press_times)}")
        logger.debug(f"按下事件时间样本（前10个）：{str(self.press_times[:10])}")
        logger.debug(f"按下事件时间样本（后10个）：{str(self.press_times[-10:])}")

        # # 如果存在 Mirror 模组，进行水平镜像（轨道翻转）
        # if self.mod & 1073741824:  # Mirror 位 (1 << 30)
        #     # 确定有效轨道数（列数）
        #     # 找出 pressset 中非空轨道的最大索引
        #     max_col = -1
        #     for col_idx, presses in enumerate(self.pressset):
        #         if presses:
        #             max_col = max(max_col, col_idx)
        #     if max_col >= 0:
        #         column_count = max_col + 1
        #         # 镜像 pressset
        #         mirrored_pressset = [[] for _ in range(18)]
        #         for col in range(column_count):
        #             mirrored_col = column_count - 1 - col
        #             mirrored_pressset[mirrored_col] = self.pressset[col]
        #         # 镜像 press_events
        #         mirrored_events = []
        #         for col, t in self.press_events:
        #             if col < column_count:
        #                 mirrored_col = column_count - 1 - col
        #                 mirrored_events.append((mirrored_col, t))
        #             else:
        #                 mirrored_events.append((col, t))
        #         self.pressset = mirrored_pressset
        #         self.press_events = mirrored_events
        #         # 重新生成 press_times（按时间排序）
        #         self.press_times = [t for _, t in sorted(self.press_events, key=lambda x: x[1])]
        #         logger.debug(f"应用 Mirror 模组：轨道 {list(range(column_count))} 镜像为 {list(range(column_count-1, -1, -1))}")

    def get_data(self):
        return {
            "status": self.status,
            "player_name": self.player_name,
            "mod": self.mod,
            "corrector": getattr(self, 'corrector', 1.0),
            "mods": self.mods,
            "score": self.score,
            "accuracy": self.acc,
            "ratio": self.ratio,
            "pressset": self.pressset,
            "press_times": self.press_times,
            "press_events": self.press_events,
            "intervals": self.intervals,
            "life_bar_graph": self.life_bar_graph,
            "sample_rate": self.sample_rate,
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "judge": self.judge
        }
        
    def _parse_mods(self, mod_value: int) -> list:
        """将模组整数值解析为模组名称列表"""
        if mod_value == 0:
            return ["None"]
        
        mods = []
        # 检查每个模组位
        for bit_value, mod_name in MOD_MAPPING.items():
            if bit_value == 0:  # 跳过None
                continue
            if mod_value & bit_value:
                mods.append(mod_name)
        
        # 特殊处理：Nightcore总是和DoubleTime一起出现
        if "Nightcore" in mods and "DoubleTime" in mods:
            mods.remove("DoubleTime")  # 只显示Nightcore
        
        return mods