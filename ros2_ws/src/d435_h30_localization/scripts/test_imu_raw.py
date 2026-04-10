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
    
    print("\n开始读取数据... (按 Ctrl+C 停止)")
    print("=" * 80)
    
    start_time = time.time()
    
    while True:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            buffer += data
            
            # 查找所有 0x55 的位置
            idx = 0
            while idx < len(buffer):
                pos = buffer.find(b'\x55', idx)
                if pos == -1:
                    break
                
                print(f"\n找到 0x55 在位置 {pos}")
                
                # 显示从 0x55 开始的15个字节
                end_pos = min(pos + 15, len(buffer))
                packet_data = buffer[pos:end_pos]
                print(f"数据包: {packet_data.hex()}")
                
                # 如果有足够的字节，尝试解析
                if len(buffer) >= pos + 11:
                    packet_type = buffer[pos + 1]
                    print(f"类型: 0x{packet_type:02x}")
                    
                    if packet_type in [0x51, 0x52, 0x53, 0x54, 0x55, 0x59]:
                        print("  ✓ 这是有效的维特智能数据包类型!")
                        packet_count += 1
                        
                        # 验证校验和
                        if packet_type == 0x59 and len(buffer) >= pos + 13:
                            checksum_calc = sum(buffer[pos:pos+12]) & 0xFF
                            checksum_packet = buffer[pos+12]
                            print(f"  校验和: 计算={checksum_calc:02x}, 数据包={checksum_packet:02x}")
                            if checksum_calc == checksum_packet:
                                print("  ✓ 校验和正确!")
                        elif len(buffer) >= pos + 11:
                            checksum_calc = sum(buffer[pos:pos+10]) & 0xFF
                            checksum_packet = buffer[pos+10]
                            print(f"  校验和: 计算={checksum_calc:02x}, 数据包={checksum_packet:02x}")
                            if checksum_calc == checksum_packet:
                                print("  ✓ 校验和正确!")
                
                idx = pos + 1
        
        # 定期打印统计
        elapsed = time.time() - start_time
        if elapsed > 1:
            print(f"\n--- {elapsed:.1f}秒, 找到 {packet_count} 个有效数据包 ---")
            start_time = time.time()
            packet_count = 0
        
        time.sleep(0.05)
        
except KeyboardInterrupt:
    print("\n停止")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
