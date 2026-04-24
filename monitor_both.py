#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import time
import threading
import sys
import glob

print("=" * 60)
print("         双串口同时监控")
print("=" * 60)

monitor_running = True


def monitor_serial(name, port, baudrate):
    print(f"\n[启动 {name}: {port} @ {baudrate}")
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        print(f"[✓ {name} 连接成功")
    except Exception as e:
        print(f"[✗ {name} 连接失败: {e}")
        return
    
    buffer = b""
    while monitor_running:
        try:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                timestamp = time.strftime("%H:%M:%S.%f")[:-3]
                print(f"\n[{timestamp}] [{name}] 收到 {len(data)} 字节: {data.hex()}")
                try:
                    print(f"[{timestamp}] [{name}] ASCII: {data.decode('utf-8', errors='ignore')}")
                except:
                    pass
                buffer += data
        except Exception as e:
            print(f"[{timestamp}] [{name}] 错误: {e}")
            time.sleep(1)
    ser.close()


try:
    t1 = threading.Thread(target=monitor_serial, args=("STM32", "/dev/ttyACM0", 115200))
    t2 = threading.Thread(target=monitor_serial, args=("IMU", "/dev/ttyACM1", 460800))
    t1.start()
    t2.start()
    
    print("\n" + "=" * 60)
    print("正在监控，按 Ctrl+C 停止")
    print("=" * 60)
    print("\n")
    
    t1.join()
    t2.join()
    
except KeyboardInterrupt:
    print("\n\n停止监控中...")
    monitor_running = False
