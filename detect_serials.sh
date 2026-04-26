#!/bin/bash
# 自动检测 STM32 和 IMU 串口
# 原理：在 460800 波特率下读取各端口数据量
#   - 数据量多的 -> IMU
#   - 数据量少的 -> STM32

DETECT_OUTPUT=$(python3 -c "
import glob, serial, time, sys

ports = sorted(glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*'))
if not ports:
    print('  [检测] 未找到串口设备')
    print('IMU_PORT=')
    print('STM32_PORT=')
    sys.exit(0)

print('  [检测] 找到串口: ' + ', '.join(ports))

port_data = {}
for port in ports:
    try:
        s = serial.Serial(port, 460800, timeout=1.0)
        s.reset_input_buffer()
        time.sleep(0.5)
        data = s.read(5000)
        s.close()
        port_data[port] = len(data)
        print('  [检测] ' + port + ' -> ' + str(len(data)) + ' 字节')
    except Exception as e:
        port_data[port] = 0
        print('  [检测] ' + port + ' -> 错误: ' + str(e))

if len(port_data) < 2:
    print('  [检测] 串口数量不足，无法区分')
    print('IMU_PORT=' + ports[0])
    print('STM32_PORT=')
    sys.exit(0)

sorted_ports = sorted(port_data.items(), key=lambda x: x[1], reverse=True)
imu_port = sorted_ports[0][0]
stm32_port = sorted_ports[-1][0]

print('  [检测] ' + stm32_port + ' -> STM32 (' + str(port_data[stm32_port]) + ' 字节, 最少)')
print('  [检测] ' + imu_port + ' -> IMU (' + str(port_data[imu_port]) + ' 字节, 最多)')
print('IMU_PORT=' + imu_port)
print('STM32_PORT=' + stm32_port)
")

echo "$DETECT_OUTPUT" | grep -v "^IMU_PORT=" | grep -v "^STM32_PORT="
eval "$(echo "$DETECT_OUTPUT" | grep -E "^(IMU_PORT|STM32_PORT)=")"
