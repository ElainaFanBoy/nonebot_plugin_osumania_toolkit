import json
import os
import datetime

from collections import Counter
from typing import Optional
from nonebot.log import logger
from nonebot import get_plugin_config

from ..algorithm.utils import malody_mods_to_osu_mods

from ..file.osr_file_parser import osr_file, ReplayEvent
from ..file.mr_file_parser import mr_file
from ..config import Config

config = get_plugin_config(Config)

# 辅助函数
def ms(beats, bpm, offset):
    return 1000 * (60 / bpm) * beats + offset

def beat(beat_arr):
    return beat_arr[0] + beat_arr[1] / beat_arr[2]

def col(column, keys):
    return int(512 * (2 * column + 1) / (2 * keys))

def convert_mc_to_osu(mc_file_path: str, output_dir: Optional[str] = None) -> str:
    """
    Summary:
        将 .mc 文件转换为 .osu 文件。
        本函数修改自 https://github.com/Jakads/malody2osu/blob/master/convert.py
    Args:
        mc_file_path: .mc 文件路径
        output_dir: 输出目录，如果为 None 则输出到原文件所在目录
    Returns:
        转换后的 .osu 文件路径
    Raises:
        ValueError: 如果文件不是有效的 .mc 文件
        Exception: 转换过程中的其他错误
    """
    # 检查文件
    if not os.path.exists(mc_file_path):
        raise FileNotFoundError(f"文件不存在: {mc_file_path}")
    if not mc_file_path.lower().endswith('.mc'):
        raise ValueError(f"文件不是 .mc 格式: {mc_file_path}")

    # 读取 JSON
    try:
        with open(mc_file_path, 'r', encoding='utf-8') as f:
            mc_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"无效的 JSON 格式: {e}")

    # 验证基础字段
    if 'meta' not in mc_data:
        raise ValueError("无效的 .mc 文件: 缺少 'meta' 字段")
    meta = mc_data['meta']
    if meta.get('mode') != 0:
        raise ValueError("只支持 Key 模式 (mode 0) 的 .mc 文件")

    if 'mode_ext' not in meta or 'column' not in meta['mode_ext']:
        raise ValueError("无效的 .mc 文件: 缺少 'mode_ext.column' 字段")
    keys = meta['mode_ext']['column']

    if 'time' not in mc_data or not mc_data['time']:
        raise ValueError("无效的 .mc 文件: 缺少 'time' 字段或为空")
    line = mc_data['time']

    if 'note' not in mc_data:
        raise ValueError("无效的 .mc 文件: 缺少 'note' 字段")
    note = mc_data['note']

    effect = mc_data.get('effect', [])

    # 提取音效 note（type != 0 的第一个）
    soundnote = {}
    for n in note:
        if n.get('type', 0) != 0:
            soundnote = n
            break

    # 计算 BPM 和偏移（完全照搬 ref.py 的累积算法）
    bpm = [line[0]['bpm']]
    bpmoffset = [-soundnote.get('offset', 0)]  # 初始偏移

    if len(line) > 1:
        j = 0
        lastbeat = line[0]['beat']
        for x in line[1:]:
            bpm.append(x['bpm'])
            # 计算绝对时间偏移
            offset = ms(beat(x['beat']) - beat(lastbeat), line[j]['bpm'], bpmoffset[j])
            bpmoffset.append(offset)
            j += 1
            lastbeat = x['beat']

    bpmcount = len(bpm)

    # 元数据
    title = meta["song"]["title"]
    artist = meta["song"]["artist"]
    creator = meta["creator"]
    version = meta["version"]
    background = meta.get("background", "")
    preview = meta.get("preview", -1)
    title_org = meta['song'].get('titleorg', title)
    artist_org = meta['song'].get('artistorg', artist)
    sound_file = soundnote.get('sound', '') if soundnote else ''

    # 输出路径
    if output_dir is None:
        output_dir = os.path.dirname(mc_file_path)
    base_name = os.path.splitext(os.path.basename(mc_file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.osu")

    # 构建 .osu 内容
    lines = [
        'osu file format v14',
        '',
        '[General]',
        f'AudioFilename: {sound_file}',
        'AudioLeadIn: 0',
        f'PreviewTime: {preview}',
        'Countdown: 0',
        'SampleSet: Soft',
        'StackLeniency: 0.7',
        'Mode: 3',
        'LetterboxInBreaks: 0',
        'SpecialStyle: 0',
        'WidescreenStoryboard: 0',
        '',
        '[Editor]',
        'DistanceSpacing: 1.2',
        'BeatDivisor: 4',
        'GridSize: 8',
        'TimelineZoom: 2.4',
        '',
        '[Metadata]',
        f'Title:{title}',
        f'TitleUnicode:{title_org}',
        f'Artist:{artist}',
        f'ArtistUnicode:{artist_org}',
        f'Creator:{creator}',
        f'Version:{version}',
        'Source:Malody',
        'Tags:Malody Convert by Jakads',
        'BeatmapID:0',
        'BeatmapSetID:-1',
        '',
        '[Difficulty]',
        f'HPDrainRate:{config.default_convert_hp}',
        f'CircleSize:{keys}',
        f'OverallDifficulty:{config.default_convert_od}',
        'ApproachRate:5',
        'SliderMultiplier:1.4',
        'SliderTickRate:1',
        '',
        '[Events]',
        '//Background and Video events',
        f'0,0,"{background}",0,0',
        '',
        '[TimingPoints]'
    ]

    # 红色 Timing Points（BPM 点）
    for i in range(bpmcount):
        meter = line[i].get('sign', 4)
        lines.append(f'{int(bpmoffset[i])},{60000 / bpm[i]},{meter},1,0,0,1,0')

    # 绿色 Timing Points（SV 点）
    for sv in effect:
        sv_beat = beat(sv['beat'])
        # 找到所属 BPM 段（最后一个节拍 ≤ sv_beat 的段）
        idx = 0
        for i, b in enumerate(line):
            if beat(b['beat']) > sv_beat:
                break
            idx = i
        delta_beat = sv_beat - beat(line[idx]['beat'])
        sv_time = ms(delta_beat, bpm[idx], bpmoffset[idx])
        scroll = sv.get('scroll', 1.0)
        sv_value = "1E+308" if scroll == 0 else 100 / abs(scroll)
        meter = line[idx].get('sign', 4)
        lines.append(f'{int(sv_time)},-{sv_value},{meter},1,0,0,0,0')

    lines.append('')
    lines.append('[HitObjects]')

    # 先转换为中间结构，便于做兼容性修正（如 LN 尾与同列同毫秒起点冲突）。
    converted_notes = []
    start_time_counter: Counter[tuple[int, int]] = Counter()

    # 音符
    for n in note:
        if n.get('type', 0) != 0:
            continue  # 跳过音效

        column_idx = int(n['column'])

        n_beat = beat(n['beat'])
        # 找到所属 BPM 段
        idx = 0
        for i, b in enumerate(line):
            if beat(b['beat']) > n_beat:
                break
            idx = i
        delta_beat = n_beat - beat(line[idx]['beat'])
        n_time = ms(delta_beat, bpm[idx], bpmoffset[idx])
        n_time_ms = int(n_time)
        x = col(column_idx, keys)
        start_time_counter[(column_idx, n_time_ms)] += 1

        # 长按或普通
        end_time_ms = None
        if 'endbeat' in n:
            end_beat = beat(n['endbeat'])
            idx_end = 0
            for i, b in enumerate(line):
                if beat(b['beat']) > end_beat:
                    break
                idx_end = i
            delta_end = end_beat - beat(line[idx_end]['beat'])
            end_time = ms(delta_end, bpm[idx_end], bpmoffset[idx_end])
            end_time_ms = int(end_time)
            type_str = '128'
        else:
            type_str = '1'

        converted_notes.append(
            {
                'x': x,
                'column_idx': column_idx,
                'start_time_ms': n_time_ms,
                'end_time_ms': end_time_ms,
                'type_str': type_str,
                'vol': n.get('vol', 100),
                'sound': n.get('sound', 0),
            }
        )

    # 兼容性处理：若 LN 结束时刻与同列起点同毫秒，向前微调 LN 结束时间，避免严格解析器冲突。
    adjusted_tail_count = 0
    for item in converted_notes:
        end_time_ms = item['end_time_ms']
        if end_time_ms is None:
            continue

        start_time_ms = item['start_time_ms']
        column_idx = item['column_idx']
        adjusted_end = int(end_time_ms)

        while adjusted_end > start_time_ms and start_time_counter[(column_idx, adjusted_end)] > 0:
            adjusted_end -= 1

        if adjusted_end <= start_time_ms:
            adjusted_end = start_time_ms + 1

        if adjusted_end != end_time_ms:
            item['end_time_ms'] = adjusted_end
            adjusted_tail_count += 1

    if adjusted_tail_count > 0:
        logger.debug(
            f".mc 转换中检测到 {adjusted_tail_count} 个 LN 尾同毫秒冲突，已自动微调结束时间提升兼容性"
        )

    for item in converted_notes:
        x = item['x']
        n_time_ms = item['start_time_ms']
        end_time_ms = item['end_time_ms']
        type_str = item['type_str']
        vol = item['vol']
        sound = item['sound']

        # osu!mania HitObject:
        # 普通键: x,y,time,type,hitSound,hitSample
        # 长按键: x,y,time,type,hitSound,endTime:hitSample
        if end_time_ms is not None:
            line_str = f'{x},192,{n_time_ms},{type_str},{sound},{end_time_ms}:0:0:0:{vol}:'
        else:
            line_str = f'{x},192,{n_time_ms},{type_str},{sound},0:0:0:{vol}:'
        lines.append(line_str)

    # 写入文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    except Exception as e:
        raise Exception(f"写入 .osu 文件失败: {e}")

    return output_path

def convert_mr_to_osr(mr_obj: mr_file) -> osr_file:
    """
    summary:
        将 mr_file 对象转换为 osr_file 实例，并保持旧字段兼容。
        .mr 时间通常已是 1.0x chart 时间，因此本转换默认保持 real/chart 一致，
        但仍显式填充 press_events_real / press_events_chart 双时间线字段。
    Args:
        mr_obj: 解析后的 mr_file 对象。
    Returns:
        可直接用于旧流程的 osr_file 对象。
    """
    osr = osr_file.__new__(osr_file)
    osr._init_derived_attrs()

    # 兼容 __init__ 中的配置字段（__new__ 绕过初始化时需要手动补齐）
    osr.assume_replay_times_scaled = False
    osr.keep_float_times = True
    osr.log_level_override = None
    osr.allow_force_no_scale = True

    # 基础属性
    osr.file_path = mr_obj.file_path
    osr.status = mr_obj.status
    osr.player_name = "ConvertedFromMalody"
    osr.mod, osr.mods = malody_mods_to_osu_mods(mr_obj.mods_flags)

    # .mr 默认不做速度反缩放，real/chart 时间线一致。
    osr.speed_factor = 1.0
    osr.corrector = 1.0
    osr.scale_applied = False

    # 判定映射：best->320, cool->200, good->100, miss->0
    osr.judge = {
        "320": mr_obj.best_count,
        "300": 0,
        "200": mr_obj.cool_count,
        "100": mr_obj.good_count,
        "50": 0,
        "0": mr_obj.miss_count,
    }
    osr.score = 0
    osr.ratio = 0

    # 按 Malody 计分方式计算 acc
    tot_obj = mr_obj.best_count + mr_obj.cool_count + mr_obj.good_count + mr_obj.miss_count
    if tot_obj > 0:
        osr.acc = (mr_obj.best_count * 100 + mr_obj.cool_count * 75 + mr_obj.good_count * 40) / (tot_obj * 100) * 100
    else:
        osr.acc = 0.0

    osr.timestamp = datetime.datetime.fromtimestamp(mr_obj.timestamp) if mr_obj.timestamp else datetime.datetime.min
    osr.life_bar_graph = ""

    # 直接继承 mr parser 已构建的数据（real/chart 在 mr 中一致）。
    osr.pressset_raw = [list(col) for col in mr_obj.pressset_raw]
    osr.pressset = [list(col) for col in mr_obj.pressset]
    osr.intervals_raw = list(mr_obj.intervals_raw)
    osr.intervals = list(mr_obj.intervals)

    osr.press_times_raw = list(mr_obj.press_times_raw)
    osr.press_events_raw = list(mr_obj.press_events_raw)

    osr.press_times_real_float = list(mr_obj.press_times_real_float)
    osr.press_events_real_float = list(mr_obj.press_events_real_float)
    osr.press_times_real = list(mr_obj.press_times_real)
    osr.press_events_real = list(mr_obj.press_events_real)

    osr.press_times_chart_float = list(mr_obj.press_times_chart_float)
    osr.press_events_chart_float = list(mr_obj.press_events_chart_float)
    osr.press_times_chart = list(mr_obj.press_times_chart)
    osr.press_events_chart = list(mr_obj.press_events_chart)

    # 旧字段兼容：保持 chart 时间线
    osr.press_times_float = list(osr.press_times_chart_float)
    osr.press_events_float = list(osr.press_events_chart_float)
    osr.press_times = list(osr.press_times_chart)
    osr.press_events = list(osr.press_events_chart)

    osr.play_data = list(mr_obj.play_data)
    osr.replay_data_real = list(mr_obj.replay_data_real)
    osr.replay_data_chart = list(mr_obj.replay_data_chart)

    if osr.intervals_raw:
        osr.sample_rate = osr._estimate_sample_rate(osr.intervals_raw)
    else:
        osr.sample_rate = float("inf")

    if mr_obj.status != "OK":
        osr.status = mr_obj.status
        return osr

    valid_pressset = [p for p in osr.pressset if len(p) > 5]
    if len(valid_pressset) < 2:
        osr.status = "tooFewKeys"
    else:
        osr.status = "OK"

    logger.debug(f"按下事件总数(len(press_events)): {len(osr.press_events)}")
    logger.debug(f"按下事件总数(len(press_times))：{len(osr.press_times)}")
    logger.debug(f"按下事件时间样本（前10个）：{str(osr.press_times[:10])}")
    logger.debug(f"按下事件时间样本（后10个）：{str(osr.press_times[-10:])}")
    return osr