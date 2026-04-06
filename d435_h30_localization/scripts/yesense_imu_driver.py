#!/usr/bin/env python3
import rospy
import serial
import struct
import time
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion
from std_msgs.msg import Header

class YesenseImuDriver:
    def __init__(self):
        rospy.init_node('yesense_imu_driver', anonymous=True)
        
        self.serial_port = rospy.get_param('~serial_port', '/dev/ttyACM0')
        self.baud_rate = rospy.get_param('~baud_rate', 460800)
        self.frame_id = rospy.get_param('~frame_id', 'imu_link')
        
        self.imu_pub = rospy.Publisher('/imu/data', Imu, queue_size=10)
        
        self.buffer = b''
        self.ser = None
        self.connect_serial()
        
        rospy.loginfo(f"Yesense IMU Driver started on {self.serial_port} @ {self.baud_rate}")
    
    def connect_serial(self):
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=0.1
            )
            rospy.loginfo(f"Successfully connected to {self.serial_port}")
        except Exception as e:
            rospy.logerr(f"Failed to connect: {e}")
            self.ser = None
    
    def parse_yesense_packet(self, data):
        """解析 Yesense 协议数据包"""
        # 查找帧头 0x59 0x53
        idx = data.find(b'\x59\x53')
        if idx == -1:
            return None, data
        
        if idx > 0:
            data = data[idx:]
        
        # 至少需要 10 字节：帧头(2) + 长度(1) + 命令(1) + 数据(至少1) + 校验(2)
        if len(data) < 10:
            return None, data
        
        # 读取长度字节
        length = data[2]
        
        # 完整数据包长度: 2(帧头) + 1(长度) + 1(命令) + length(数据) + 2(校验)
        packet_len = 2 + 1 + 1 + length + 2
        
        if len(data) < packet_len:
            return None, data
        
        cmd = data[3]
        payload = data[4:4+length]
        
        # 计算校验和 (从帧头开始到数据结束)
        checksum_calc = 0
        for i in range(2 + 1 + 1 + length):
            checksum_calc += data[i]
        checksum_calc = checksum_calc & 0xFFFF
        
        # 读取数据包中的校验和 (小端)
        checksum_packet = (data[4+length+1] << 8) | data[4+length]
        
        rospy.logdebug(f"Found packet: cmd=0x{cmd:02x}, len={length}, checksum=calc={checksum_calc:04x}, packet={checksum_packet:04x}")
        
        if checksum_calc == checksum_packet:
            return (cmd, payload), data[packet_len:]
        else:
            rospy.logdebug(f"Checksum mismatch")
            return None, data[1:]
    
    def parse_imu_data(self, cmd, payload):
        """根据命令类型解析 IMU 数据"""
        imu_msg = Imu()
        imu_msg.header = Header()
        imu_msg.header.stamp = rospy.Time.now()
        imu_msg.header.frame_id = self.frame_id
        
        # 默认零值
        accel = [0.0, 0.0, 9.81]
        gyro = [0.0, 0.0, 0.0]
        quat = [0.0, 0.0, 0.0, 1.0]
        
        # 这只是一个框架，需要根据具体的 Yesense 协议完善
        # 不同的 cmd 对应不同的数据输出
        
        rospy.logdebug(f"Parsing cmd=0x{cmd:02x}, payload={payload.hex()}")
        
        imu_msg.linear_acceleration.x = accel[0]
        imu_msg.linear_acceleration.y = accel[1]
        imu_msg.linear_acceleration.z = accel[2]
        
        imu_msg.angular_velocity.x = gyro[0]
        imu_msg.angular_velocity.y = gyro[1]
        imu_msg.angular_velocity.z = gyro[2]
        
        imu_msg.orientation.x = quat[0]
        imu_msg.orientation.y = quat[1]
        imu_msg.orientation.z = quat[2]
        imu_msg.orientation.w = quat[3]
        
        # 设置协方差
        imu_msg.orientation_covariance = [0.0] * 9
        imu_msg.angular_velocity_covariance = [0.0] * 9
        imu_msg.linear_acceleration_covariance = [0.0] * 9
        
        return imu_msg
    
    def run(self):
        rate = rospy.Rate(200)
        
        while not rospy.is_shutdown():
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        data = self.ser.read(self.ser.in_waiting)
                        self.buffer += data
                        
                        # 持续解析缓冲区
                        while True:
                            packet, self.buffer = self.parse_yesense_packet(self.buffer)
                            if packet is None:
                                break
                            
                            cmd, payload = packet
                            imu_msg = self.parse_imu_data(cmd, payload)
                            self.imu_pub.publish(imu_msg)
                
                except Exception as e:
                    rospy.logerr(f"Serial error: {e}")
            
            rate.sleep()

if __name__ == '__main__':
    try:
        driver = YesenseImuDriver()
        driver.run()
    except rospy.ROSInterruptException:
        pass
