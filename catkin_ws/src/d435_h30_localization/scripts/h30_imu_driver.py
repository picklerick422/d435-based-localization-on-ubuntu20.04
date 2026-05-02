#!/usr/bin/env python3
import rospy
import serial
import struct
from sensor_msgs.msg import Imu
from std_msgs.msg import Header

class H30ImuDriver:
    def __init__(self):
        rospy.init_node('h30_imu_driver', anonymous=True)
        
        # 获取参数
        self.serial_port = rospy.get_param('~serial_port', '/dev/ttyUSB0')
        self.baud_rate = rospy.get_param('~baud_rate', 460800)  # 修改为 460800
        self.frame_id = rospy.get_param('~frame_id', 'imu_link')
        
        # IMU 数据存储 - 保持上一次的有效数据
        self.acceleration = [0.0, 0.0, 0.0]
        self.angular_velocity = [0.0, 0.0, 0.0]
        self.orientation = [0.0, 0.0, 0.0, 1.0]
        
        # 数据标志
        self.got_accel = False
        self.got_gyro = False
        self.got_quat = False
        
        # 初始化默认数据（防止数据为空）
        self.last_acceleration = [0.0, 0.0, 9.81]
        self.last_angular_velocity = [0.0, 0.0, 0.0]
        self.last_orientation = [0.0, 0.0, 0.0, 1.0]
        
        # IMU 发布者
        self.imu_pub = rospy.Publisher('/imu/data', Imu, queue_size=10)
        
        # 串口初始化
        self.ser = None
        self.buffer = b''
        self.connect_serial()
        
        rospy.loginfo(f"H30 IMU Driver started on {self.serial_port} @ {self.baud_rate}")
        
    def connect_serial(self):
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=0.1
            )
            rospy.loginfo(f"Successfully connected to {self.serial_port}")
        except serial.SerialException as e:
            rospy.logerr(f"Failed to connect to {self.serial_port}: {e}")
            rospy.logwarn("Running in simulation mode - publishing dummy IMU data")
            self.ser = None
    
    def checksum(self, data):
        sum = 0
        for i in range(len(data)):
            sum += data[i]
        return sum & 0xFF
    
    def parse_accel(self, data):
        axl, axh, ayl, ayh, azl, azh, _, _ = struct.unpack('<8B', data)
        ax = (axh << 8) | axl
        ay = (ayh << 8) | ayl
        az = (azh << 8) | azl
        
        if ax > 32767: ax -= 65536
        if ay > 32767: ay -= 65536
        if az > 32767: az -= 65536
        
        self.acceleration = [ax / 16384.0 * 9.81, ay / 16384.0 * 9.81, az / 16384.0 * 9.81]
        self.last_acceleration = self.acceleration.copy()  # 保存最后一次有效数据
        self.got_accel = True
        rospy.logdebug(f"Accel: {self.acceleration}")
    
    def parse_gyro(self, data):
        wxl, wxh, wyl, wyh, wzl, wzh, _, _ = struct.unpack('<8B', data)
        wx = (wxh << 8) | wxl
        wy = (wyh << 8) | wyl
        wz = (wzh << 8) | wzl
        
        if wx > 32767: wx -= 65536
        if wy > 32767: wy -= 65536
        if wz > 32767: wz -= 65536
        
        self.angular_velocity = [wx / 32768.0 * 2000.0 * 3.14159 / 180.0, 
                                  wy / 32768.0 * 2000.0 * 3.14159 / 180.0, 
                                  wz / 32768.0 * 2000.0 * 3.14159 / 180.0]
        self.last_angular_velocity = self.angular_velocity.copy()  # 保存最后一次有效数据
        self.got_gyro = True
        rospy.logdebug(f"Gyro: {self.angular_velocity}")
    
    def parse_quat(self, data):
        q0l, q0h, q1l, q1h, q2l, q2h, q3l, q3h, _, _ = struct.unpack('<10B', data)
        q0 = (q0h << 8) | q0l
        q1 = (q1h << 8) | q1l
        q2 = (q2h << 8) | q2l
        q3 = (q3h << 8) | q3l
        
        if q0 > 32767: q0 -= 65536
        if q1 > 32767: q1 -= 65536
        if q2 > 32767: q2 -= 65536
        if q3 > 32767: q3 -= 65536
        
        self.orientation = [q1 / 32768.0, q2 / 32768.0, q3 / 32768.0, q0 / 32768.0]
        self.last_orientation = self.orientation.copy()  # 保存最后一次有效数据
        self.got_quat = True
        rospy.logdebug(f"Quat: {self.orientation}")
    
    def publish_imu_msg(self):
        imu_msg = Imu()
        imu_msg.header = Header()
        imu_msg.header.stamp = rospy.Time.now()
        imu_msg.header.frame_id = self.frame_id
        
        # 使用最后一次的有效数据，确保数据连续性
        imu_msg.linear_acceleration.x = self.last_acceleration[0]
        imu_msg.linear_acceleration.y = self.last_acceleration[1]
        imu_msg.linear_acceleration.z = self.last_acceleration[2]
        
        imu_msg.angular_velocity.x = self.last_angular_velocity[0]
        imu_msg.angular_velocity.y = self.last_angular_velocity[1]
        imu_msg.angular_velocity.z = self.last_angular_velocity[2]
        
        imu_msg.orientation.x = self.last_orientation[0]
        imu_msg.orientation.y = self.last_orientation[1]
        imu_msg.orientation.z = self.last_orientation[2]
        imu_msg.orientation.w = self.last_orientation[3]
        
        imu_msg.orientation_covariance = [0.0] * 9
        imu_msg.angular_velocity_covariance = [0.0] * 9
        imu_msg.linear_acceleration_covariance = [0.0] * 9
        
        self.imu_pub.publish(imu_msg)
    
    def process_buffer(self):
        while len(self.buffer) >= 11:  # 最小包长度
            idx = self.buffer.find(b'\x55')
            if idx == -1:
                self.buffer = b''
                return
            
            if idx > 0:
                self.buffer = self.buffer[idx:]
            
            if len(self.buffer) < 2:
                return
            
            packet_type = self.buffer[1]
            
            rospy.logdebug(f"Found packet type: 0x{packet_type:02x}")
            
            # 根据包类型确定需要的长度
            required_len = 11  # 0x51, 0x52 需要11字节
            if packet_type == 0x59:
                required_len = 13  # 0x59 需要13字节
            
            if len(self.buffer) < required_len:
                return
            
            # 根据包类型处理
            if packet_type == 0x51:
                if self.checksum(self.buffer[0:10]) == self.buffer[10]:
                    self.parse_accel(self.buffer[2:10])
                    self.buffer = self.buffer[11:]
                else:
                    rospy.logdebug("Checksum failed for 0x51")
                    self.buffer = self.buffer[1:]
            elif packet_type == 0x52:
                if self.checksum(self.buffer[0:10]) == self.buffer[10]:
                    self.parse_gyro(self.buffer[2:10])
                    self.buffer = self.buffer[11:]
                else:
                    rospy.logdebug("Checksum failed for 0x52")
                    self.buffer = self.buffer[1:]
            elif packet_type == 0x59:
                if self.checksum(self.buffer[0:12]) == self.buffer[12]:
                    self.parse_quat(self.buffer[2:12])
                    self.buffer = self.buffer[13:]
                else:
                    rospy.logdebug("Checksum failed for 0x59")
                    self.buffer = self.buffer[1:]
            else:
                self.buffer = self.buffer[1:]
    
    def publish_dummy_data(self):
        imu_msg = Imu()
        imu_msg.header = Header()
        imu_msg.header.stamp = rospy.Time.now()
        imu_msg.header.frame_id = self.frame_id
        
        imu_msg.linear_acceleration.x = 0.0
        imu_msg.linear_acceleration.y = 0.0
        imu_msg.linear_acceleration.z = 9.81
        
        imu_msg.angular_velocity.x = 0.0
        imu_msg.angular_velocity.y = 0.0
        imu_msg.angular_velocity.z = 0.0
        
        imu_msg.orientation.x = 0.0
        imu_msg.orientation.y = 0.0
        imu_msg.orientation.z = 0.0
        imu_msg.orientation.w = 1.0
        
        imu_msg.orientation_covariance = [0.0] * 9
        imu_msg.angular_velocity_covariance = [0.0] * 9
        imu_msg.linear_acceleration_covariance = [0.0] * 9
        
        self.imu_pub.publish(imu_msg)
    
    def run(self):
        rate = rospy.Rate(100)  # 稳定100Hz发布频率
        last_publish_time = rospy.Time.now()
        
        while not rospy.is_shutdown():
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        data = self.ser.read(self.ser.in_waiting)
                        rospy.logdebug(f"Received: {data.hex()}")
                        self.buffer += data
                    
                    self.process_buffer()
                    
                    current_time = rospy.Time.now()
                    
                    # 只要至少有加速度计和陀螺仪数据就发布
                    if self.got_accel and self.got_gyro:
                        self.publish_imu_msg()
                        self.got_accel = False
                        self.got_gyro = False
                        last_publish_time = current_time
                    # 确保稳定的发布频率 - 即使没有新数据也发布最后一次有效数据
                    elif (current_time - last_publish_time).to_sec() >= 0.01:  # 100Hz
                        self.publish_imu_msg()
                        last_publish_time = current_time
                    
                except Exception as e:
                    rospy.logerr(f"Serial read error: {e}")
                    self.publish_dummy_data()
                    last_publish_time = rospy.Time.now()
            else:
                # 串口未连接时也持续发布数据
                self.publish_dummy_data()
                last_publish_time = rospy.Time.now()
            
            rate.sleep()

if __name__ == '__main__':
    try:
        driver = H30ImuDriver()
        driver.run()
    except rospy.ROSInterruptException:
        pass
