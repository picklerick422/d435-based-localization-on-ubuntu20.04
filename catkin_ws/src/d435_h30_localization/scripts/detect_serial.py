#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能串口检测脚本
================
扫描所有 /dev/ttyACM* 和 /dev/ttyUSB*，自动识别：
  - STM32: 在 115200 下输出含 'coor:' / '[coor]:' / 'COOR:' 的文本
  - IMU:   在 460800 下输出连续二进制数据流

输出（最后两行，可被 shell `eval` 使用）：
  IMU_PORT=/dev/ttyACMx
  STM32_PORT=/dev/ttyACMy

中间日志全部写到 stderr，不污染上面两行的 stdout。
"""

import glob
import re
import sys
import time

try:
    import serial
except ImportError:
    sys.stderr.write("ERROR: 未安装 pyserial，请先 pip install pyserial\n")
    sys.exit(1)


COOR_PATTERN = re.compile(r'\[?coor\]?\s*:', re.IGNORECASE)


def log(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def is_printable_text(data):
    if not data:
        return False
    pc = sum(1 for b in data if (32 <= b <= 126) or b in (10, 13, 9))
    return pc > len(data) * 0.85


def list_ports():
    return sorted(set(glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')))


def probe_stm32(port, listen=0.5):
    """115200 下被动监听 listen 秒；遇到 coor 标签立即 return，无需等满。"""
    try:
        ser = serial.Serial(port=port, baudrate=115200, timeout=0.05)
        ser.reset_input_buffer()
    except Exception as e:
        log("    {} 115200 打开失败: {}".format(port, e))
        return False, ''

    deadline = time.time() + listen
    buf = b''
    try:
        while time.time() < deadline:
            chunk = ser.read(1024)
            if chunk:
                buf += chunk
                text = buf.decode('utf-8', errors='ignore')
                if COOR_PATTERN.search(text):
                    return True, text[-80:].replace('\r', ' ').replace('\n', '|')
    finally:
        try:
            ser.close()
        except Exception:
            pass

    return False, ''


def probe_imu(port, listen=0.3):
    """460800 下监听 listen 秒；要求大量字节且非可打印文本。"""
    try:
        ser = serial.Serial(port=port, baudrate=460800, timeout=listen)
        ser.reset_input_buffer()
        data = ser.read(8192)
        ser.close()
    except Exception as e:
        log("    {} 460800 打开失败: {}".format(port, e))
        return False, 0

    if len(data) > 200 and not is_printable_text(data):
        return True, len(data)
    return False, len(data)


def detect():
    ports = list_ports()
    if not ports:
        log("未找到任何 /dev/ttyACM* 或 /dev/ttyUSB* 设备")
        print("IMU_PORT=")
        print("STM32_PORT=")
        return

    log("=" * 60)
    log("候选端口: {}".format(", ".join(ports)))
    log("=" * 60)

    stm32_port = None
    imu_port = None

    log("[第 1 轮] 在 115200 下查找 STM32 (coor 标签, listen=0.5s)")
    remaining = []
    for p in ports:
        ok, sample = probe_stm32(p)
        if ok:
            log("  ✓ {} 是 STM32 [{}]".format(p, sample))
            if stm32_port is None:
                stm32_port = p
            else:
                log("  (! 已检测到多个 STM32 候选, 保留第一个 {})".format(stm32_port))
        else:
            remaining.append(p)

    log("[第 2 轮] 在 460800 下查找 IMU (连续二进制流, listen=0.3s)")
    for p in remaining:
        ok, n = probe_imu(p)
        if ok:
            log("  ✓ {} 是 IMU ({} B 二进制)".format(p, n))
            if imu_port is None:
                imu_port = p
        else:
            log("  - {} 不是 IMU ({} B)".format(p, n))

    log("=" * 60)
    log("结果: IMU={}, STM32={}".format(imu_port or '(未检测到)',
                                        stm32_port or '(未检测到)'))
    log("=" * 60)

    print("IMU_PORT={}".format(imu_port or ''))
    print("STM32_PORT={}".format(stm32_port or ''))


if __name__ == '__main__':
    detect()
