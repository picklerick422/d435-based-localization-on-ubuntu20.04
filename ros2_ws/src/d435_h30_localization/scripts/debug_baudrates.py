#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUDRATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

for baud in BAUDRATES:
    print(f"\n{'='*50}")
    print(f"尝试波特率: {baud}")
    print('='*50)
    
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=baud,
            timeout=1.0
        )
        print(f"成功连接 @ {baud}")
        
        time.sleep(0.5)
        
        # 读取一些数据
        start_time = time.time()
        data_received = b''
        
        while time.time() - start_time < 2:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                data_received += data
                print(f"收到数据: {data.hex()}")
                if b'\x55' in data:
                    print("  ✓ 找到了 0x55 帧头!")
                    
            time.sleep(0.1)
        
        ser.close()
        
    except Exception as e:
        print(f"错误: {e}")
        continue

print("\n测试完成!")
