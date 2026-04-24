#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import time
from std_msgs.msg import String

class SerialAssistant:
    def __init__(self):
        rospy.init_node('serial_assistant', anonymous=True)
        self.data_count = 0
        self.start_time = time.time()
        self.last_time = time.time()
        
        # 订阅数据话题
        rospy.Subscriber('/rtabmap/serial_data', String, self.data_callback)
        
        print("=" * 60)
        print("          串口助手 - 定位数据监控")
        print("=" * 60)
        print("订阅话题: /rtabmap/serial_data")
        print("按 Ctrl+C 退出")
        print("=" * 60)
        print("")
        
    def data_callback(self, msg):
        self.data_count += 1
        current_time = time.time()
        
        # 计算频率
        elapsed = current_time - self.start_time
        freq = 0
        if elapsed > 0:
            freq = self.data_count / elapsed
        
        # 计算数据间隔
        interval = current_time - self.last_time
        self.last_time = current_time
        
        # 获取时间戳
        timestamp = time.strftime("%H:%M:%S")
        
        # 打印格式化数据（Python2兼容）
        print("[{}] #{} | {} | 频率: {:.1f}Hz | 间隔: {:.1f}ms".format(
            timestamp,
            self.data_count,
            msg.data,
            freq,
            interval * 1000
        ))

if __name__ == '__main__':
    try:
        assistant = SerialAssistant()
        rospy.spin()
    except rospy.ROSInterruptException:
        print("\n串口助手已退出")
    except Exception as e:
        print("\n错误: {}".format(str(e)))
