#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 460800

print(f"连接 {SERIAL_PORT} @ {BAUD_RATE}...")

try:
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=0.1
    )
    print(f"成功连接!")
    
    buffer = b''
    packet_count = 0
    cmd_stats = {}
    
    print("\n开始读取 Yesense 协议数据... (按 Ctrl+C 停止)")
    print("=" * 80)
    
    start_time = time.time()
    
    while True:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer += data
            
            # 查找 Yesense 帧头 0x59 0x53
            idx = 0
            while idx < len(buffer):
                pos = buffer.find(b'\x59\x53', idx)
                if pos == -1:
                    break
                
                print(f"\n找到 Yesense 帧头在位置 {pos}")
                
                # 显示从帧头开始的数据
                end_pos = min(pos + 50, len(buffer))
                packet_data = buffer[pos:end_pos]
                print(f"原始数据: {packet_data.hex()}")
                
                # 尝试解析
                if len(buffer) >= pos + 4:
                    length = buffer[pos + 2]
                    cmd = buffer[pos + 3]
                    
                    print(f"长度字节: {length}")
                    print(f"命令字节: 0x{cmd:02x}")
                    
                    # 统计命令类型
                    if cmd not in cmd_stats:
                        cmd_stats[cmd] = 0
                    cmd_stats[cmd] += 1
                    packet_count += 1
                    
                    # 计算完整数据包长度
                    full_len = 2 + 1 + 1 + length + 2
                    
                    if len(buffer) >= pos + full_len:
                        payload = buffer[pos+4 : pos+4+length]
                        print(f"有效载荷: {payload.hex()}")
                        
                        # 计算校验和
                        checksum_calc = 0
                        for i in range(2 + 1 + 1 + length):
                            checksum_calc += buffer[pos + i]
                        checksum_calc = checksum_calc & 0xFFFF
                        
                        checksum_packet = (buffer[pos+4+length+1] << 8) | buffer[pos+4+length]
                        
                        print(f"校验和: 计算=0x{checksum_calc:04x}, 数据包=0x{checksum_packet:04x}")
                        
                        if checksum_calc == checksum_packet:
                            print("  ✓ 校验和正确!")
                        else:
                            print("  ✗ 校验和错误!")
                
                idx = pos + 1
        
        # 定期打印统计
        elapsed = time.time() - start_time
        if elapsed > 2:
            print(f"\n--- {elapsed:.1f}秒统计 ---")
            print(f"总共收到 {packet_count} 个数据包")
            print(f"命令类型统计:")
            for cmd, cnt in sorted(cmd_stats.items()):
                print(f"  0x{cmd:02x}: {cnt} 次")
            
            start_time = time.time()
            packet_count = 0
        
        time.sleep(0.05)
        
except KeyboardInterrupt:
    print("\n停止")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
