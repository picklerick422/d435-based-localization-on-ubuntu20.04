#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STM32 串口全面诊断工具
检查所有可能导致乱码的原因
"""

import serial
import serial.tools.list_ports
import time
import sys


def list_ports_detail():
    """列出所有串口详细信息"""
    print("\n" + "=" * 60)
    print("1. 检测到的串口设备")
    print("=" * 60)
    
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("未找到任何串口设备！")
        return []
    
    for p in ports:
        print(f"  设备: {p.device}")
        print(f"    描述: {p.description}")
        print(f"    硬件ID: {p.hwid}")
        print()
    
    return [p.device for p in ports]


def test_port_baudrate(port, baudrate, timeout=1.0):
    """测试指定端口的波特率"""
    print(f"\n测试 {port} @ {baudrate}...")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # 发送测试指令
        test_cmd = b"coor:0,0,0\n"
        print(f"  发送: {test_cmd}")
        ser.write(test_cmd)
        ser.flush()
        
        # 等待回应
        print(f"  等待 {timeout} 秒...")
        time.sleep(timeout)
        
        # 读取所有数据
        raw_data = ser.read(1024)
        
        if raw_data:
            print(f"  收到 {len(raw_data)} 字节")
            print(f"  Hex: {raw_data.hex()}")
            
            # 尝试解码
            try:
                text = raw_data.decode('utf-8').strip()
                print(f"  Text (UTF-8): {text}")
            except:
                print(f"  Text (UTF-8): [无法解码]")
            
            # 尝试 ASCII
            ascii_text = raw_data.decode('ascii', errors='ignore').strip()
            print(f"  Text (ASCII): {ascii_text}")
            
            ser.close()
            return True, raw_data
        else:
            print(f"  无回应")
            ser.close()
            return False, None
            
    except Exception as e:
        print(f"  错误: {e}")
        return False, None


def test_all_ports():
    """测试所有端口的所有常见波特率"""
    ports = list_ports_detail()
    if not ports:
        return
    
    baudrates = [9600, 115200, 460800, 15200, 57600, 38400, 19200]
    
    print("\n" + "=" * 60)
    print("2. 波特率测试")
    print("=" * 60)
    
    for port in ports:
        print(f"\n--- 测试 {port} ---")
        for br in baudrates:
            success, data = test_port_baudrate(port, br, timeout=0.5)
            if success and data:
                # 判断是否是可识别的数据
                try:
                    text = data.decode('utf-8', errors='ignore').strip()
                    if 'coor:' in text or len(text) > 5:
                        print(f"  ✓ {port} @ {br}: 收到可识别数据")
                    else:
                        print(f"  ? {port} @ {br}: 收到数据但不可识别")
                except:
                    pass


def test_with_monitor(port, baudrate, duration=5):
    """持续监控指定端口"""
    print(f"\n" + "=" * 60)
    print(f"3. 持续监控 {port} @ {baudrate} ({duration}秒)")
    print("=" * 60)
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        ser.reset_input_buffer()
        print(f"已连接，等待 {duration} 秒...")
        
        start = time.time()
        buf = b''
        line_count = 0
        
        while time.time() - start < duration:
            if ser.in_waiting > 0:
                buf += ser.read(ser.in_waiting)
                
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    line_count += 1
                    text = line.decode('utf-8', errors='ignore').strip()
                    
                    if line_count <= 10:
                        if text.startswith('coor:'):
                            print(f"  [{line_count}] {text}")
                        else:
                            print(f"  [{line_count}] [乱码] {text[:60]}...")
        
        print(f"\n总计收到 {line_count} 行数据")
        
        ser.close()
        
    except Exception as e:
        print(f"错误: {e}")


def main():
    print("\n" + "#" * 60)
    print("# STM32 串口全面诊断工具")
    print("#" * 60)
    
    # 1. 列出所有端口
    ports = list_ports_detail()
    
    # 2. 测试所有端口
    test_all_ports()
    
    # 3. 如果找到疑似端口，持续监控
    print("\n" + "=" * 60)
    user_input = input("是否要持续监控某个端口？(输入端口号或跳过): ")
    
    if user_input and user_input != 'skip':
        port = user_input if user_input.startswith('/dev/') else f"/dev/{user_input}"
        baudrate = int(input("波特率 [115200]: ") or "115200")
        duration = int(input("监控时长(秒) [10]: ") or "10")
        
        test_with_monitor(port, baudrate, duration)


if __name__ == '__main__':
    main()
