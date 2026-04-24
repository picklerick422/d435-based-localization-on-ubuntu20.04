# STM32 串口通信问题排查报告

## 问题描述
用户反映串口发送给 STM32 的数据没有被接收到。

---

## 问题总结
1. **设备分配错误**：`d435_imu.launch` 中默认设备搞反了
   - 正确配置：
     - **STM32**: `/dev/ttyACM0` @ 115200 (波特率)
     - **IMU**: `/dev/ttyACM1` @ 460800 (波特率)
2. **代码缺少 flush() 调用**：`rtabmap_odom_handler.py` 发送数据后没有立即刷新缓冲区
3. **缺少错误处理和重连机制**

---

## 修复内容

### 1. 修复 `/home/picklerick/d435/catkin_ws/src/d435_h30_localization/launch/d435_imu.launch`
- ✅ 修正设备分配：
  - `imu_port`: `/dev/ttyACM1` (之前错误设为 ttyACM0)
  - `stm32_port`: `/dev/ttyACM0` (之前错误设为 ttyACM1)

### 2. 修复 `/home/picklerick/d435/catkin_ws/src/d435_h30_localization/scripts/rtabmap_odom_handler.py`
- ✅ 添加 `ser.flush()` 和 `ser.flushOutput()` 调用，确保数据立即发送
- ✅ 添加发送字节数日志，便于调试
- ✅ 添加异常捕获后自动重连串口的逻辑

---

## 提供的调试工具

### `/home/picklerick/d435/debug_serial_tool.py`
全面的串口调试工具，支持：
- 模式 1：监控 STM32 (/dev/ttyACM0 @ 115200)
- 模式 2：监控 IMU (/dev/ttyACM1 @ 460800)
- 模式 3：同时监控两个串口
- 模式 4：发送测试数据到 STM32
- 模式 5：发送测试数据到 IMU

### `/home/picklerick/d435/test_serial.py`
简单的串口测试脚本

---

## 设备分配（已修正）
- `/dev/ttyACM0`：**STM32 通信** (波特率 115200)
- `/dev/ttyACM1`：**IMU 通信** (波特率 460800)

---

## 测试步骤
1. **验证串口权限**
```bash
sudo chmod 666 /dev/ttyACM0 /dev/ttyACM1
```

2. **使用调试工具发送测试数据到 STM32**
```bash
python3 /home/picklerick/d435/debug_serial_tool.py
# 选择选项 4 发送测试数据到 ttyACM0 (STM32)
```

3. **运行完整系统**
```bash
/home/picklerick/d435/00.sh
```

---

## 常见问题
1. **找不到设备节点**：确保 USB 设备已连接，检查 `lsusb` 输出
2. **权限错误**：使用 `sudo chmod 666 /dev/ttyACM*` 临时修复，或把用户加入 `dialout` 组
3. **IMU 数据错误**：确保 IMU 连接到了 `/dev/ttyACM1`
