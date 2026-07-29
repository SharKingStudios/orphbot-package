import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu


ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43
PWR_MGMT_1 = 0x6B
WHO_AM_I = 0x75
G_TO_MS2 = 9.80665


class MPU6050Node(Node):
    def __init__(self):
        super().__init__('mpu6050_node')
        self.declare_parameter('bus', 1)
        self.declare_parameter('address', 0x68)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('publish_rate', 50.0)

        self.bus_number = int(self.get_parameter('bus').value)
        self.address = int(self.get_parameter('address').value)
        self.frame_id = self.get_parameter('frame_id').value
        rate = float(self.get_parameter('publish_rate').value)

        self.bus = self._open_bus()
        self._initialize_sensor()

        self.publisher = self.create_publisher(Imu, 'imu/data_raw', 10)
        self.create_timer(1.0 / rate, self.publish_sample)
        self.get_logger().info(
            f'MPU6050 publishing from bus {self.bus_number}, '
            f'address 0x{self.address:02x}'
        )

    def _open_bus(self):
        try:
            from smbus2 import SMBus
        except ImportError:
            try:
                from smbus import SMBus
            except ImportError as exc:
                raise RuntimeError(
                    'No SMBus module found. Install python3-smbus or python3-smbus2 on the Pi.'
                ) from exc

        try:
            return SMBus(self.bus_number)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f'/dev/i2c-{self.bus_number} was not found. Enable I2C with '
                'dtparam=i2c_arm=on and reboot.'
            ) from exc

    def _initialize_sensor(self):
        try:
            whoami = self.bus.read_byte_data(self.address, WHO_AM_I)
        except OSError as exc:
            raise RuntimeError(
                f'MPU6050 did not respond at 0x{self.address:02x} on I2C bus {self.bus_number}. '
                'Run i2cdetect, then check VCC, GND, SDA, SCL, AD0, and solder joints.'
            ) from exc

        if whoami not in (0x68, 0x70, 0x71):
            raise RuntimeError(
                f'I2C device at 0x{self.address:02x} has unexpected '
                f'WHO_AM_I=0x{whoami:02x}'
            )

        self.bus.write_byte_data(self.address, PWR_MGMT_1, 0x00)

    def read_word_signed(self, register):
        high = self.bus.read_byte_data(self.address, register)
        low = self.bus.read_byte_data(self.address, register + 1)
        value = (high << 8) | low
        if value >= 0x8000:
            value -= 0x10000
        return value

    def publish_sample(self):
        try:
            ax = self.read_word_signed(ACCEL_XOUT_H) / 16384.0 * G_TO_MS2
            ay = self.read_word_signed(ACCEL_XOUT_H + 2) / 16384.0 * G_TO_MS2
            az = self.read_word_signed(ACCEL_XOUT_H + 4) / 16384.0 * G_TO_MS2
            gx = math.radians(self.read_word_signed(GYRO_XOUT_H) / 131.0)
            gy = math.radians(self.read_word_signed(GYRO_XOUT_H + 2) / 131.0)
            gz = math.radians(self.read_word_signed(GYRO_XOUT_H + 4) / 131.0)
        except OSError as exc:
            self.get_logger().error(f'I2C read failed: {exc}')
            return

        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.orientation_covariance[0] = -1.0
        msg.linear_acceleration.x = ax
        msg.linear_acceleration.y = ay
        msg.linear_acceleration.z = az
        msg.angular_velocity.x = gx
        msg.angular_velocity.y = gy
        msg.angular_velocity.z = gz
        msg.linear_acceleration_covariance[0] = 0.04
        msg.linear_acceleration_covariance[4] = 0.04
        msg.linear_acceleration_covariance[8] = 0.04
        msg.angular_velocity_covariance[0] = 0.02
        msg.angular_velocity_covariance[4] = 0.02
        msg.angular_velocity_covariance[8] = 0.02
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MPU6050Node()
        rclpy.spin(node)
    except RuntimeError as exc:
        temp_node = node
        if temp_node is None:
            temp_node = rclpy.create_node('mpu6050_startup_error')
        temp_node.get_logger().error(str(exc))
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            try:
                node.destroy_node()
            except KeyboardInterrupt:
                pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
