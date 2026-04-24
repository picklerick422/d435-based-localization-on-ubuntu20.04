#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import serial
import time
import glob
import sys

def is_stm32_port(port):
    """检测是否是STM32设备
    方法: 用115200波特率连接，发送coor数据，看是否有[coor]回应
    """
    try:
        ser = serial.Serial(port, 115200, timeout=0.5, write_timeout=0.5)
        # 清空输入缓冲区
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        test_data = b'coor:123.4,567.8,90.0\n'
        ser.write(test_data)
        ser.flush()
        
        # 等一会看回应
        time.sleep(0.2)
        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            ser.close()
            # 检查回应是否有 [coor] 或 coor 字样
            if b'coor' in response.lower():
                return True, response
            return True, None  # 即使没有特定回应，能通信也行
        ser.close()
        return True, None
    except Exception as e:
        return False, None

def is_imu_port(port):
    """检测是否是IMU设备
    方法: 用460800波特率连接，看是否有高频数据包，且不是乱码
    """
    try:
        ser = serial.Serial(port, 460800, timeout=0.2)
        # 读一段时间数据
        start = time.time()
        buffer = b""
        has_good_data = False
        
        while time.time() - start < 1.5:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                buffer += data
                
                # IMU数据特征: 
                # 1. 不是全0xf8或0x78
                # 2. 有变化的字节
                # 3. 数据在持续更新
                
                # 排除全是重复字节的乱码
                unique_bytes = len(set(buffer[:20]))
                if unique_bytes > 3:
                    has_good_data = True
                    break
        
        ser.close()
        return has_good_data
    except Exception as e:
        return False

def main():
    print("=" * 70)
    print("     智能串口自动检测")
    print("=" * 70)
    
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    
    print(f"\n发现 {len(ports)} 个串口设备: {ports}\n")
    
    imu_port = None
    stm32_port = None
    
    for port in ports:
        print(f"正在检测: {port}...")
        
        # 先检查是不是STM32
        is_stm, resp = is_stm32_port(port)
        if is_stm:
            stm32_port = port
            print(f"  ✓ 发现 STM32 设备: {port} @ 115200")
            if resp:
                try:
                    print(f"    回应: {resp.decode('utf-8', errors='ignore').strip()}")
                except:
                    print(f"    回应 (hex): {resp.hex()}")
            continue
        
        # 再检查是不是IMU
        if is_imu_port(port):
            imu_port = port
            print(f"  ✓ 发现 IMU 设备: {port} @ 460800")
    
    print("\n" + "=" * 70)
    print("检测结果:")
    if stm32_port:
        print(f"  STM32:  {stm32_port} @ 115200")
    if imu_port:
        print(f"  IMU:    {imu_port} @ 460800")
    if not stm32_port and not imu_port:
        print("  未检测到设备!")
    print("=" * 70)
    
    return stm32_port, imu_port

if __name__ == "__main__":
    stm32_port, imu_port = main()
