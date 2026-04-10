#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
import serial
import glob
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

class RTABMapPoseToSTM32:
    def __init__(self):
        # 串口初始化（自动检测可用端口）
        self.ser = self._init_serial()
        # ROS订阅初始化 - 支持两种定位话题
        self.pose_sub = None
        self.odom_sub = None
        self.last_send_time = rospy.Time.now()
        
        # 选择话题优先级：localization_pose > odom
        self._setup_subscribers()
        
    def _setup_subscribers(self):
        """设置订阅话题，优先用localization_pose，如果没有则用odom"""
        # 等待一下让话题发布
        rospy.sleep(1.0)
        
        # 获取当前话题列表
        topics = rospy.get_published_topics()
        topic_names = [t[0] for t in topics]
        
        # 优先用 localization_pose（全局定位）
        if '/rtabmap/localization_pose' in topic_names:
            rospy.loginfo("使用话题: /rtabmap/localization_pose")
            self.pose_sub = rospy.Subscriber('/rtabmap/localization_pose', PoseStamped, self.pose_callback)
        elif '/rtabmap/odom' in topic_names:
            rospy.loginfo("使用话题: /rtabmap/odom")
            self.odom_sub = rospy.Subscriber('/rtabmap/odom', Odometry, self.odom_callback)
        else:
            rospy.logwarn("未找到定位话题，等待话题出现...")
            # 1秒后重试
            rospy.Timer(rospy.Duration(1.0), self._retry_subscribe, oneshot=True)
    
    def _retry_subscribe(self, event):
        """重试订阅话题"""
        self._setup_subscribers()
        
    def _init_serial(self):
        """自动检测并连接可用的串口设备（ttyACM/ttyUSB）"""
        # 获取串口参数（支持launch文件配置）
        port = rospy.get_param('~port', '')
        baudrate = rospy.get_param('~baudrate', 115200)
        
        if port:
            # 如果指定了端口，直接用
            candidate_ports = [port]
        else:
            # 自动搜索
            candidate_ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
        
        for port in candidate_ports:
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.1,
                    write_timeout=0.1
                )
                rospy.loginfo(f"成功连接到串口设备: {port} @ {baudrate}")
                return ser
            except PermissionError:
                rospy.logwarn(f"端口 {port} 权限不足，请检查用户是否属于dialout组")
            except FileNotFoundError:
                rospy.logwarn(f"端口 {port} 不存在（可能设备未连接）")
            except serial.SerialException as e:
                rospy.logwarn(f"端口 {port} 连接失败: {str(e)}")
        
        # 所有端口尝试失败
        rospy.logfatal("未找到任何可用的串口设备，请检查硬件连接！")
        raise serial.SerialException("无可用串口设备")
    
    def _send_data(self, pos_x, pos_y, pos_z, roll, pitch, yaw):
        """发送位姿数据到STM32
        
        数据格式：coor:x,y,t
        - x: x坐标（厘米，保留1位小数）
        - y: y坐标（厘米，保留1位小数）
        - t: z轴欧拉角（yaw，度，保留1位小数）
        """
        # 发送频率控制（10Hz，可配置）
        send_rate = rospy.get_param('~send_rate', 10.0)
        if (rospy.Time.now() - self.last_send_time).to_sec() < (1.0 / send_rate):
            return
        
        # 格式：coor:x,y,t
        yaw_deg = yaw * 180 / 3.14159
        data_str = "coor:{:.1f},{:.1f},{:.1f}\n".format(
            pos_x * 100,   # x坐标（厘米）
            pos_y * 100,   # y坐标（厘米）
            yaw_deg         # yaw角度（度）
        )
        
        try:
            self.ser.write(data_str.encode('utf-8'))
            self.last_send_time = rospy.Time.now()
            # 同时打印到终端（方便调试）
            rospy.loginfo(f"发送数据: {data_str.strip()}")
        except serial.SerialTimeoutException:
            rospy.logwarn("串口发送超时，尝试重新连接...")
            self.ser = self._init_serial()  # 自动重连
        except serial.SerialException as e:
            rospy.logerr(f"串口错误: {str(e)}，尝试重新连接...")
            try:
                self.ser = self._init_serial()
            except:
                pass
    
    def pose_callback(self, msg):
        """PoseStamped 回调（来自 localization_pose）"""
        # 提取位置
        pos = msg.pose.position
        # 提取四元数并转换为欧拉角
        q = msg.pose.orientation
        quaternion = [q.x, q.y, q.z, q.w]
        roll, pitch, yaw = euler_from_quaternion(quaternion)
        
        # 发送数据
        self._send_data(pos.x, pos.y, pos.z, roll, pitch, yaw)
    
    def odom_callback(self, msg):
        """Odometry 回调（来自 odom）"""
        # 提取位置
        pos = msg.pose.pose.position
        # 提取四元数并转换为欧拉角
        q = msg.pose.pose.orientation
        quaternion = [q.x, q.y, q.z, q.w]
        roll, pitch, yaw = euler_from_quaternion(quaternion)
        
        # 发送数据
        self._send_data(pos.x, pos.y, pos.z, roll, pitch, yaw)
    
    def run(self):
        rospy.loginfo("RTAB-Map位姿传输节点已启动，等待接收定位数据...")
        rospy.spin()

if __name__ == '__main__':
    rospy.init_node('rtabmap_pose_to_stm32')
    try:
        handler = RTABMapPoseToSTM32()
        handler.run()
    except rospy.ROSInterruptException:
        pass
    except serial.SerialException as e:
        rospy.logfatal(f"串口通信失败: {str(e)}")
    finally:
        try:
            if 'handler' in locals() and hasattr(handler, 'ser') and handler.ser.is_open:
                handler.ser.close()
                rospy.loginfo("串口已安全关闭")
        except:
            pass
