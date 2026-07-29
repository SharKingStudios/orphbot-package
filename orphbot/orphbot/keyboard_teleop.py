import select
import sys
import termios
import time
import tty

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


HELP = """OrphBot teleop
Hold W/S forward/back  Hold A/D turn  X or Space stop  +/- speed  Q quit
"""


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        self.declare_parameter('linear_speed', 0.16)
        self.declare_parameter('angular_speed', 0.65)
        self.declare_parameter('speed_step', 0.04)
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('key_timeout', 0.45)
        self.declare_parameter('stop_burst', 3)

        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)
        self.speed_step = float(self.get_parameter('speed_step').value)
        publish_rate = max(1.0, float(self.get_parameter('publish_rate').value))
        self.publish_period = 1.0 / publish_rate
        self.key_timeout = max(0.05, float(self.get_parameter('key_timeout').value))
        self.stop_burst = max(1, int(self.get_parameter('stop_burst').value))

        self.active_linear = 0.0
        self.active_angular = 0.0
        self.command_active = False
        self.last_motion_key_time = 0.0
        self.last_publish_time = 0.0
        self.stop_publishes_remaining = 0

    def publish_motion(self, linear, angular):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)
        self.last_publish_time = time.monotonic()

    def set_motion(self, linear, angular):
        self.active_linear = linear
        self.active_angular = angular
        self.command_active = True
        self.stop_publishes_remaining = 0
        self.last_motion_key_time = time.monotonic()
        self.publish_motion(linear, angular)

    def stop(self):
        self.active_linear = 0.0
        self.active_angular = 0.0
        self.command_active = False
        self.stop_publishes_remaining = self.stop_burst
        self.publish_motion(0.0, 0.0)
        self.stop_publishes_remaining -= 1

    def adjust_speed(self, direction):
        self.linear_speed = max(0.04, min(0.4, self.linear_speed + direction * self.speed_step))
        angular_delta = direction * self.speed_step * 3.0
        self.angular_speed = max(0.15, min(1.5, self.angular_speed + angular_delta))
        print(f'linear={self.linear_speed:.2f} m/s angular={self.angular_speed:.2f} rad/s')

    def handle_key(self, key):
        key = key.lower()
        if key == 'w':
            self.set_motion(self.linear_speed, 0.0)
        elif key == 's':
            self.set_motion(-self.linear_speed, 0.0)
        elif key == 'a':
            self.set_motion(0.0, self.angular_speed)
        elif key == 'd':
            self.set_motion(0.0, -self.angular_speed)
        elif key in ('x', ' '):
            self.stop()
        elif key in ('+', '='):
            self.adjust_speed(1)
        elif key in ('-', '_'):
            self.adjust_speed(-1)
        elif key == 'q':
            self.stop()
            return False
        return True

    def tick(self):
        now = time.monotonic()
        if self.command_active and now - self.last_motion_key_time > self.key_timeout:
            self.stop()
            return

        if self.command_active and now - self.last_publish_time >= self.publish_period:
            self.publish_motion(self.active_linear, self.active_angular)
            return

        should_publish_stop = (
            self.stop_publishes_remaining > 0
            and now - self.last_publish_time >= self.publish_period
        )
        if should_publish_stop:
            self.publish_motion(0.0, 0.0)
            self.stop_publishes_remaining -= 1


def read_available_keys():
    keys = []
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 0.0)
        if not ready:
            return keys
        keys.append(sys.stdin.read(1))


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTeleop()
    old_settings = termios.tcgetattr(sys.stdin)
    print(HELP)
    try:
        tty.setcbreak(sys.stdin.fileno())
        running = True
        while rclpy.ok() and running:
            rclpy.spin_once(node, timeout_sec=0.02)
            for key in read_available_keys():
                running = node.handle_key(key)
                if not running:
                    break
            node.tick()
    except KeyboardInterrupt:
        node.stop()
    finally:
        node.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
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
