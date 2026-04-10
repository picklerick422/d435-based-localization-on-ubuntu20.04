#!/usr/bin/env python3
import serial
import time

# 配置
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

print(f"正在连接 {SERIAL_PORT} @ {BAUD_RATE}...")

try:
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=0.5
    )
    print(f"成功连接到 {SERIAL_PORT}")
    
    print("\n开始读取数据... (按 Ctrl+C 停止)")
    
    while True:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"收到 {len(data)} 字节: {data.hex()}")
            # 同时打印ASCII表示
            print(f"ASCII: {data}")
            
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n停止读取")
except serial.SerialException as e:
    print(f"串口错误: {e}")
except Exception as e:
    print(f"错误: {e}")
