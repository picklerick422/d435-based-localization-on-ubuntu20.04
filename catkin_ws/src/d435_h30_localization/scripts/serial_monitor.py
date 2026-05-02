#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口监控工具 - 用于调试 STM32 通信
功能：
1. 监控发送到 STM32 的数据（TX）- 通过 ROS 话题 /rtabmap/serial_send
2. 监控从 STM32 接收的数据（RX）- 通过 ROS 话题 /rtabmap/serial_recv

使用方法:
  rosrun d435_h30_localization serial_monitor.py --mode tx
  rosrun d435_h30_localization serial_monitor.py --mode rx
"""

import sys
import time
import argparse


def run_tx_monitor():
    """TX模式：通过ROS话题监控发送到STM32的数据"""
    import rospy
    from std_msgs.msg import String

    rospy.init_node('serial_monitor_tx', anonymous=True)

    print("\n" + "=" * 70)
    print("  📤 TX 监控 - 显示发送到 STM32 的原始数据")
    print("=" * 70)
    print("  等待数据中...\n")

    def callback(msg):
        ts = time.strftime("%H:%M:%S")
        data = msg.data.strip()

        # 显示原始格式 coor:x,y,r
        if 'coor:' in data:
            try:
                # 从 "[123.456] coor:1.23,4.56,7.89" 中提取
                raw = data[data.find('coor:'):]
                print(f"[{ts}] 📤 TX | {raw}")
                return
            except:
                pass

        print(f"[{ts}] 📤 TX | {data}")

    rospy.Subscriber('/rtabmap/serial_send', String, callback)

    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("\n停止 TX 监控")


def run_rx_monitor():
    """RX模式：通过ROS话题监控从STM32接收的数据"""
    import rospy
    from std_msgs.msg import String

    rospy.init_node('serial_monitor_rx', anonymous=True)

    print("\n" + "=" * 70)
    print("  📥 RX 监控 - 显示从 STM32 接收的数据")
    print("=" * 70)
    print("  等待数据中...\n")

    def callback(msg):
        ts = time.strftime("%H:%M:%S")
        data = msg.data.strip()

        # 显示原始格式 coor:x,y,r
        if data.startswith('coor:'):
            print(f"[{ts}] 📥 RX | {data}")
        else:
            print(f"[{ts}] 📥 RX | {data[:80]}")

    rospy.Subscriber('/rtabmap/serial_recv', String, callback)

    try:
        rospy.spin()
    except KeyboardInterrupt:
        print("\n停止 RX 监控")


def main():
    parser = argparse.ArgumentParser(description='串口监控工具')
    parser.add_argument('--mode', '-m', choices=['tx', 'rx'], required=True,
                        help='监控模式: tx=发送监控, rx=接收监控')

    args = parser.parse_args()

    if args.mode == 'tx':
        run_tx_monitor()
    else:
        run_rx_monitor()


if __name__ == '__main__':
    main()
