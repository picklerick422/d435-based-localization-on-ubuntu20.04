#!/usr/bin/env python
# -*- coding: utf-8 -*-
import serial
import time
import sys
import glob

def main():
    # 参数配置
    port = '/dev/ttyACM1'
    baudrate = 115200
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    if len(sys.argv) > 2:
        baudrate = int(sys.argv[2])
    
    print("=" * 60)
    print(f"串口监听工具")
    print(f"端口: {port}")
    print(f"波特率: {baudrate}")
    print("=" * 60)
    print("按 Ctrl+C 退出")
    print("")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=1.0
        )
        print(f"已打开串口: {port}")
        print("")
        
        buffer = ""
        
        while True:
            if ser.in_waiting > 0:
                try:
                    data = ser.read(ser.in_waiting)
                    text = data.decode('utf-8', errors='ignore')
                    
                    buffer += text
                    
                    # 按行处理
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] {line}")
                            
                except Exception as e:
                    pass
                    
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {str(e)}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("串口已关闭")

if __name__ == '__main__':
    main()
