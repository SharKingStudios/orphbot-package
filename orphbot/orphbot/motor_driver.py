import math
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


class MotorChannel:
    def __init__(self, forward_pin, reverse_pin, pin_factory):
        from gpiozero import PWMOutputDevice

        self.forward = PWMOutputDevice(forward_pin, pin_factory=pin_factory)
        self.reverse = PWMOutputDevice(reverse_pin, pin_factory=pin_factory)

    def set_speed(self, speed):
        speed = max(-1.0, min(1.0, float(speed)))
        if speed > 0:
            self.forward.value = speed
            self.reverse.value = 0.0
        elif speed < 0:
            self.forward.value = 0.0
            self.reverse.value = -speed
        else:
            self.forward.value = 0.0
            self.reverse.value = 0.0

    def stop(self):
        self.set_speed(0.0)

    def close(self):
        self.stop()
        self.forward.close()
        self.reverse.close()


class MotorDriver(Node):
    def __init__(self):
        super().__init__('motor_driver')

        self.declare_parameter('max_pwm', 0.35)
        self.declare_parameter('deadband', 0.04)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('max_linear_speed', 0.4)
        self.declare_parameter('max_angular_speed', 1.5)
        self.declare_parameter('enable_pin', -1)
        self.declare_parameter('left_front_pins', [5, 6])
        self.declare_parameter('left_rear_pins', [13, 19])
        self.declare_parameter('right_front_pins', [20, 21])
        self.declare_parameter('right_rear_pins', [23, 24])
        self.declare_parameter('invert_left', False)
        self.declare_parameter('invert_right', False)

        self.max_pwm = float(self.get_parameter('max_pwm').value)
        self.deadband = float(self.get_parameter('deadband').value)
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.max_linear_speed = float(self.get_parameter('max_linear_speed').value)
        self.max_angular_speed = float(self.get_parameter('max_angular_speed').value)
        self.invert_left = bool(self.get_parameter('invert_left').value)
        self.invert_right = bool(self.get_parameter('invert_right').value)

        self.enable = None
        try:
            from gpiozero import OutputDevice
            from gpiozero.pins.lgpio import LGPIOFactory

            pin_factory = LGPIOFactory()
            enable_pin = int(self.get_parameter('enable_pin').value)
            if enable_pin >= 0:
                self.enable = OutputDevice(
                    enable_pin,
                    active_high=True,
                    initial_value=True,
                    pin_factory=pin_factory,
                )
        except Exception as exc:
            raise RuntimeError(
                'GPIO setup failed. Run this node on the Raspberry Pi after installing '
                'python3-gpiozero and python3-lgpio.'
            ) from exc

        motor_specs = [
            ('left_front_pins'),
            ('left_rear_pins'),
            ('right_front_pins'),
            ('right_rear_pins'),
        ]
        self.motors = [
            MotorChannel(*self._pin_pair(pin_param), pin_factory)
            for pin_param in motor_specs
        ]

        self.last_cmd_time = 0.0
        self.last_left = 0.0
        self.last_right = 0.0
        self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.create_timer(0.05, self.watchdog)
        self.get_logger().info(f'Motor driver ready, max_pwm={self.max_pwm:.2f}')

    def _pin_pair(self, parameter_name):
        pins = list(self.get_parameter(parameter_name).value)
        if len(pins) != 2:
            raise ValueError(f'{parameter_name} must contain exactly two BCM GPIO pins')
        return int(pins[0]), int(pins[1])

    def cmd_vel_callback(self, msg):
        linear = self._normalize(msg.linear.x, self.max_linear_speed)
        angular = self._normalize(msg.angular.z, self.max_angular_speed)

        left = linear - angular
        right = linear + angular
        largest = max(1.0, abs(left), abs(right))
        left /= largest
        right /= largest

        if self.invert_left:
            left = -left
        if self.invert_right:
            right = -right

        left = self._apply_limit(left)
        right = self._apply_limit(right)
        self.set_sides(left, right)
        self.last_cmd_time = time.monotonic()

    def _normalize(self, value, max_value):
        if max_value <= 0:
            return 0.0
        return max(-1.0, min(1.0, float(value) / max_value))

    def _apply_limit(self, value):
        if math.isclose(value, 0.0, abs_tol=self.deadband):
            return 0.0
        return max(-self.max_pwm, min(self.max_pwm, value * self.max_pwm))

    def set_sides(self, left, right):
        for motor in self.motors[:2]:
            motor.set_speed(left)
        for motor in self.motors[2:]:
            motor.set_speed(right)
        self.last_left = left
        self.last_right = right

    def watchdog(self):
        if self.last_cmd_time and (time.monotonic() - self.last_cmd_time) > self.cmd_timeout:
            self.stop()
            self.last_cmd_time = 0.0

    def stop(self):
        self.set_sides(0.0, 0.0)

    def destroy_node(self):
        self.stop()
        for motor in self.motors:
            motor.close()
        if self.enable is not None:
            self.enable.off()
            self.enable.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MotorDriver()
        rclpy.spin(node)
    except RuntimeError as exc:
        temp_node = node
        if temp_node is None:
            temp_node = rclpy.create_node('motor_driver_startup_error')
        temp_node.get_logger().error(str(exc))
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
