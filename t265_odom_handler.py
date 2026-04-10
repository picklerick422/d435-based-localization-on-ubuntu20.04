#!/usr/bin/env python
import rospy
import serial
import glob
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

class T265ToSTM32:
    def __init__(self):
        # 串口初始化（自动检测可用端口）
        self.ser = self._init_serial()
        # ROS订阅初始化
        rospy.Subscriber('/camera/odom/sample', Odometry, self.odom_callback)
        self.last_send_time = rospy.Time.now()
        
    def _init_serial(self):
        """自动检测并连接可用的串口设备（ttyACM/ttyUSB）"""
        candidate_ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')  # 搜索两种常见设备
        for port in candidate_ports:
            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=115200,
                    timeout=0.1,
                    write_timeout=0.1
                )
                rospy.loginfo(f"成功连接到串口设备: {port}")
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
    
    def odom_callback(self, msg):
        """里程计数据回调函数（保留原数据格式，新增角度处理注释）"""
        # 提取四元数
        q = msg.pose.pose.orientation
        quaternion = [q.x, q.y, q.z, q.w]
        roll, pitch, yaw = euler_from_quaternion(quaternion)
        # 提取位置数据（x, y, z）
        pos = msg.pose.pose.position
        # 提取四元数（建议转换为欧拉角获取正确角度，当前直接使用z分量可能不准确）
        orientation = msg.pose.pose.orientation
        
        # 数据格式化（示例：x,y,z坐标放大100倍，角度z分量转换为度数+90°偏移）
        data_str = "{:.2f} {:.2f} {:.2f}".format(
            pos.x * 100,   # x坐标（厘米）
            pos.y * 100,   # y坐标（厘米）
            yaw * 180 / 3.14159  # 角度转换（示例逻辑，需根据实际需求调整）
        )
        
        # 发送频率控制（10Hz）
        if (rospy.Time.now() - self.last_send_time).to_sec() > 0.1:
            try:
                self.ser.write(data_str.encode('utf-8'))
                self.last_send_time = rospy.Time.now()
                # rospy.logdebug("发送数据: {}".format(data_str.strip()))  # 调试日志（建议保留）
            except serial.SerialTimeoutException:
                rospy.logwarn("串口发送超时，尝试重新连接...")
                self.ser = self._init_serial()  # 自动重连
    
    def run(self):
        rospy.loginfo("T265数据处理节点已启动，等待接收里程计数据...")
        rospy.spin()

if __name__ == '__main__':
    rospy.init_node('t265_odom_to_stm32')
    try:
        handler = T265ToSTM32()
        handler.run()
    except rospy.ROSInterruptException:
        pass
    except serial.SerialException as e:
        rospy.logfatal(f"串口通信失败: {str(e)}")
    finally:
        if hasattr(handler, 'ser') and handler.ser.is_open:
            handler.ser.close()
            rospy.loginfo("串口已安全关闭")

