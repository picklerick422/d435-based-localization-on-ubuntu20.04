#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import serial
import glob
import sys
import time
import threading
from std_msgs.msg import String
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion


def is_printable_text(data):
    """检查数据是否主要是可打印的 ASCII 文本"""
    if not data:
        return False
    # 计算可打印字符比例（包括常见控制字符：\n \r \t）
    printable_count = sum(1 for b in data if (32 <= b <= 126) or b in (10, 13, 9))
    return printable_count > len(data) * 0.85


def detect_stm32_port(baudrate=115200):
    """
    自动检测 STM32 串口
    
    IMU 特征: 持续输出大量二进制数据
    STM32 特征: 安静等待，收到 "coor:" 指令后才回应可识别文本
    """
    all_ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    all_ports.sort()

    if not all_ports:
        rospy.logwarn("未找到任何串口设备")
        return None

    rospy.loginfo("开始检测 STM32 串口，候选端口: %s", ", ".join(all_ports))

    # 第一步：找出所有 IMU 端口
    imu_ports = set()
    for port in all_ports:
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
            ser.reset_input_buffer()
            time.sleep(0.3)
            data = ser.read(2000)
            ser.close()

            if len(data) > 50:
                if is_printable_text(data):
                    rospy.loginfo("  - %s: 收到 %d 字节文本 '%s'", port, len(data), data[:40].decode('utf-8', errors='ignore'))
                else:
                    rospy.loginfo("  ✗ %s: 疑似 IMU（%d 字节二进制数据）", port, len(data))
                    imu_ports.add(port)
            else:
                rospy.loginfo("  - %s: 安静（可能是 STM32）", port)
        except Exception as e:
            rospy.logwarn("  - %s: 错误 (%s)", port, str(e))
            imu_ports.add(port)

    # 第二步：向非 IMU 端口发送测试指令
    candidate_ports = [p for p in all_ports if p not in imu_ports]
    if not candidate_ports:
        rospy.logwarn("所有端口都被识别为 IMU!")
        return None

    rospy.loginfo("候选 STM32 端口: %s", ", ".join(candidate_ports))

    for port in candidate_ports:
        try:
            ser = serial.Serial(port=port, baudrate=baudrate, timeout=1.0)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            time.sleep(0.2)

            # 发送测试指令
            test_cmd = b"coor:0,0,0\n"
            ser.write(test_cmd)
            ser.flush()

            # 等待回应
            time.sleep(1.0)
            response = ser.read(2000)
            ser.close()

            if response and is_printable_text(response):
                text = response.decode('utf-8', errors='ignore').strip()
                rospy.loginfo("  ✓ %s: 是 STM32！收到 '%s'", port, text[:60])
                return port
            else:
                rospy.loginfo("  - %s: 无有效文本回应", port)
        except Exception as e:
            rospy.logwarn("  - %s: 错误 (%s)", port, str(e))

    return None


class RTABMapPoseToSTM32:
    def __init__(self):
        rospy.loginfo("=" * 60)
        rospy.loginfo("RTAB-Map 位姿到 STM32 传输节点")
        rospy.loginfo("=" * 60)

        self.port = rospy.get_param('~port', '')
        self.baudrate = rospy.get_param('~baudrate', 115200)
        self.send_rate = rospy.get_param('~send_rate', 10.0)
        self.fmt = rospy.get_param('~format', 'cm_deg')
        self.pose_topic = rospy.get_param('~pose_topic', '')

        rospy.loginfo("配置:")
        rospy.loginfo("  端口: %s", self.port if self.port else "自动检测")
        rospy.loginfo("  波特率: %d", self.baudrate)
        rospy.loginfo("  发送频率: %.1f Hz", self.send_rate)
        rospy.loginfo("  格式: %s", self.fmt)
        rospy.loginfo("  位姿话题: %s", self.pose_topic if self.pose_topic else "自动 (rtabmap)")

        self.ser = None
        self._init_serial()

        self.send_pub = rospy.Publisher('/rtabmap/serial_send', String, queue_size=10)
        self.recv_pub = rospy.Publisher('/rtabmap/serial_recv', String, queue_size=10)

        self.latest_pos_x = 0.0
        self.latest_pos_y = 0.0
        self.latest_yaw = 0.0
        self.have_data = False

        self.rx_running = True
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()

        self.timer = rospy.Timer(rospy.Duration(1.0 / self.send_rate), self.timer_callback)

        self._setup_subscribers()

        rospy.loginfo("节点初始化成功!")

    def _setup_subscribers(self):
        rospy.sleep(1.0)

        # 优先使用显式配置的 pose_topic (例如 /cad_pose)
        if self.pose_topic:
            topic_type = self._lookup_topic_type(self.pose_topic)
            if topic_type == 'nav_msgs/Odometry':
                rospy.loginfo("订阅话题: %s (Odometry)", self.pose_topic)
                self.odom_sub = rospy.Subscriber(
                    self.pose_topic, Odometry, self.odom_callback)
            else:
                # 尚未发布或类型未知, 默认按 PoseWithCovarianceStamped 订阅
                # (cad_icp_localizer / rtabmap_localization_pose 都是这个类型)
                rospy.loginfo("订阅话题: %s (PoseWithCovarianceStamped)",
                              self.pose_topic)
                self.pose_sub = rospy.Subscriber(
                    self.pose_topic, PoseWithCovarianceStamped,
                    self.pose_callback)
            return

        topics = rospy.get_published_topics()
        topic_names = [t[0] for t in topics]

        if '/rtabmap/odom' in topic_names:
            rospy.loginfo("订阅话题: /rtabmap/odom (Odometry)")
            self.odom_sub = rospy.Subscriber(
                '/rtabmap/odom', Odometry, self.odom_callback)
        elif '/rtabmap/localization_pose' in topic_names:
            rospy.loginfo("订阅话题: /rtabmap/localization_pose (PoseWithCovariance)")
            self.pose_sub = rospy.Subscriber(
                '/rtabmap/localization_pose',
                PoseWithCovarianceStamped, self.pose_callback)
        else:
            rospy.logwarn("未找到RTAB-Map话题，1秒后重试...")
            rospy.Timer(rospy.Duration(1.0), self._retry_subscribe,
                        oneshot=True)

    def _lookup_topic_type(self, name):
        for t, ty in rospy.get_published_topics():
            if t == name:
                return ty
        return None

    def _retry_subscribe(self, event):
        self._setup_subscribers()

    def _init_serial(self):
        """初始化串口"""
        if self.port:
            ports_to_try = [self.port]
        else:
            detected = detect_stm32_port(self.baudrate)
            if detected:
                ports_to_try = [detected]
            else:
                all_ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
                all_ports.sort()
                ports_to_try = [p for p in all_ports if '/dev/ttyACM0' not in p]
                if not ports_to_try:
                    ports_to_try = all_ports

        for p in ports_to_try:
            try:
                self.ser = serial.Serial(
                    port=p,
                    baudrate=self.baudrate,
                    timeout=0.1,
                    write_timeout=0.1,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                rospy.loginfo("✓ 成功连接串口: %s @ %d", p, self.baudrate)
                return
            except Exception as e:
                rospy.logwarn("✗ 连接串口 %s 失败: %s", p, str(e))

        rospy.logfatal("未找到可用串口!")
        raise serial.SerialException("无可用串口")

    def _reconnect_serial(self):
        """重新连接串口"""
        rospy.logwarn("正在尝试重新连接串口...")
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
        self.ser = None
        rospy.sleep(0.5)
        self._init_serial()

    def _is_valid_text(self, text):
        """检查文本是否是有效的 STM32 回应（必须是可打印 ASCII）"""
        if not text or len(text) < 5:
            return False
        # 只接受以 "coor:" 开头的行，或者是纯可打印 ASCII
        if text.startswith('coor:'):
            return True
        # 检查是否全部是可打印字符（包括数字、字母、标点、空格）
        return all(32 <= ord(c) <= 126 for c in text)

    def _rx_loop(self):
        """后台接收线程"""
        buf = b''
        while self.rx_running and not rospy.is_shutdown():
            try:
                if self.ser and self.ser.in_waiting > 0:
                    buf += self.ser.read(self.ser.in_waiting)

                    # 缓冲区过大清空
                    if len(buf) > 10000:
                        rospy.logwarn("接收缓冲区过大，清空")
                        buf = b''
                        continue

                    while b'\n' in buf:
                        line, buf = buf.split(b'\n', 1)
                        try:
                            text = line.decode('utf-8').strip()
                        except UnicodeDecodeError:
                            continue

                        if text and self._is_valid_text(text):
                            self.recv_pub.publish(text)
                            rospy.loginfo("收到: %s", text)

            except Exception as e:
                if self.rx_running:
                    rospy.logwarn("接收错误: %s", str(e))

            rospy.sleep(0.01)

    def timer_callback(self, event):
        """定时回调：发送数据"""
        if not self.have_data or not self.ser:
            return

        if self.fmt == 'cm_deg':
            x_cm = self.latest_pos_x * 100.0
            y_cm = self.latest_pos_y * 100.0
            yaw_deg = self.latest_yaw * (180.0 / 3.1415926535)
            data_str = "coor:{:.1f},{:.1f},{:.1f}\n".format(x_cm, y_cm, yaw_deg)
        else:
            data_str = "coor:{:.3f},{:.3f},{:.3f}\n".format(
                self.latest_pos_x, self.latest_pos_y, self.latest_yaw)

        try:
            bytes_written = self.ser.write(data_str.encode('utf-8'))
            self.ser.flush()

            now = rospy.get_time()
            pub_str = "[{:.3f}] {}".format(now, data_str.strip())
            self.send_pub.publish(pub_str)

            rospy.loginfo("发送: %s (%d bytes)", data_str.strip(), bytes_written)

        except Exception as e:
            rospy.logwarn("发送失败: %s", str(e))
            self._reconnect_serial()

    def pose_callback(self, msg):
        self.latest_pos_x = msg.pose.pose.position.x
        self.latest_pos_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        quat = [q.x, q.y, q.z, q.w]
        _, _, self.latest_yaw = euler_from_quaternion(quat)
        self.have_data = True

    def odom_callback(self, msg):
        self.latest_pos_x = msg.pose.pose.position.x
        self.latest_pos_y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        quat = [q.x, q.y, q.z, q.w]
        _, _, self.latest_yaw = euler_from_quaternion(quat)
        self.have_data = True

    def run(self):
        rospy.loginfo("节点运行中...")
        rospy.spin()
        self.rx_running = False
        if self.ser:
            self.ser.close()


if __name__ == '__main__':
    try:
        rospy.init_node('rtabmap_pose_to_stm32')
        handler = RTABMapPoseToSTM32()
        handler.run()
    except Exception as e:
        rospy.logfatal("节点崩溃: %s", str(e))
        sys.exit(1)
