#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import serial
import struct
from sensor_msgs.msg import Imu
import time

class H30ImuDriver(Node):
    def __init__(self):
        super().__init__('h30_imu_driver')
        
        # 获取参数
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 460800)
        self.declare_parameter('frame_id', 'imu_link')
        
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.frame_id = self.get_parameter('frame_id').value
        
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
        self.imu_pub = self.create_publisher(Imu, '/imu/data', 10)
        
        # 串口初始化
        self.ser = None
        self.buffer = b''
        self.connect_serial()
        
        self.get_logger().info(f"H30 IMU Driver started on {self.serial_port} @ {self.baud_rate}")
        
        # 创建定时器，100Hz 发布频率
        self.timer = self.create_timer(0.01, self.timer_callback)
        self.last_publish_time = self.get_clock().now()
        
    def connect_serial(self):
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=0.1
            )
            self.get_logger().info(f"Successfully connected to {self.serial_port}")
        except serial.SerialException as e:
            self.get_logger().error(f"Failed to connect to {self.serial_port}: {e}")
            self.get_logger().warning("Running in simulation mode - publishing dummy IMU data")
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
        self.last_acceleration = self.acceleration.copy()
        self.got_accel = True
        self.get_logger().debug(f"Accel: {self.acceleration}")
    
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
        self.last_angular_velocity = self.angular_velocity.copy()
        self.got_gyro = True
        self.get_logger().debug(f"Gyro: {self.angular_velocity}")
    
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
        self.last_orientation = self.orientation.copy()
        self.got_quat = True
        self.get_logger().debug(f"Quat: {self.orientation}")
    
    def publish_imu_msg(self):
        imu_msg = Imu()
        imu_msg.header.stamp = self.get_clock().now().to_msg()
        imu_msg.header.frame_id = self.frame_id
        
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
        while len(self.buffer) >= 11:
            idx = self.buffer.find(b'\x55')
            if idx == -1:
                self.buffer = b''
                return
            
            if idx > 0:
                self.buffer = self.buffer[idx:]
            
            if len(self.buffer) < 2:
                return
            
            packet_type = self.buffer[1]
            
            self.get_logger().debug(f"Found packet type: 0x{packet_type:02x}")
            
            required_len = 11
            if packet_type == 0x59:
                required_len = 13
            
            if len(self.buffer) < required_len:
                return
            
            if packet_type == 0x51:
                if self.checksum(self.buffer[0:10]) == self.buffer[10]:
                    self.parse_accel(self.buffer[2:10])
                    self.buffer = self.buffer[11:]
                else:
                    self.get_logger().debug("Checksum failed for 0x51")
                    self.buffer = self.buffer[1:]
            elif packet_type == 0x52:
                if self.checksum(self.buffer[0:10]) == self.buffer[10]:
                    self.parse_gyro(self.buffer[2:10])
                    self.buffer = self.buffer[11:]
                else:
                    self.get_logger().debug("Checksum failed for 0x52")
                    self.buffer = self.buffer[1:]
            elif packet_type == 0x59:
                if self.checksum(self.buffer[0:12]) == self.buffer[12]:
                    self.parse_quat(self.buffer[2:12])
                    self.buffer = self.buffer[13:]
                else:
                    self.get_logger().debug("Checksum failed for 0x59")
                    self.buffer = self.buffer[1:]
            else:
                self.buffer = self.buffer[1:]
    
    def publish_dummy_data(self):
        imu_msg = Imu()
        imu_msg.header.stamp = self.get_clock().now().to_msg()
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
    
    def timer_callback(self):
        current_time = self.get_clock().now()
        
        if self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    self.get_logger().debug(f"Received: {data.hex()}")
                    self.buffer += data
                
                self.process_buffer()
                
                if self.got_accel and self.got_gyro:
                    self.publish_imu_msg()
                    self.got_accel = False
                    self.got_gyro = False
                    self.last_publish_time = current_time
                elif (current_time - self.last_publish_time).nanoseconds >= 10_000_000:
                    self.publish_imu_msg()
                    self.last_publish_time = current_time
                
            except Exception as e:
                self.get_logger().error(f"Serial read error: {e}")
                self.publish_dummy_data()
                self.last_publish_time = current_time
        else:
            self.publish_dummy_data()
            self.last_publish_time = current_time

def main(args=None):
    rclpy.init(args=args)
    driver = H30ImuDriver()
    rclpy.spin(driver)
    driver.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
