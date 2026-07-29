import select
import sys
import termios
import tty

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


HELP = """OrphBot teleop
W/S forward/back  A/D turn  X stop  +/- speed  Q quit
"""


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        self.declare_parameter('linear_speed', 0.16)
        self.declare_parameter('angular_speed', 0.65)
        self.declare_parameter('speed_step', 0.04)
        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)
        self.speed_step = float(self.get_parameter('speed_step').value)

    def publish_motion(self, linear, angular):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)

    def stop(self):
        self.publish_motion(0.0, 0.0)

    def adjust_speed(self, direction):
        self.linear_speed = max(0.04, min(0.4, self.linear_speed + direction * self.speed_step))
        angular_delta = direction * self.speed_step * 3.0
        self.angular_speed = max(0.15, min(1.5, self.angular_speed + angular_delta))
        print(f'linear={self.linear_speed:.2f} m/s angular={self.angular_speed:.2f} rad/s')

    def handle_key(self, key):
        key = key.lower()
        if key == 'w':
            self.publish_motion(self.linear_speed, 0.0)
        elif key == 's':
            self.publish_motion(-self.linear_speed, 0.0)
        elif key == 'a':
            self.publish_motion(0.0, self.angular_speed)
        elif key == 'd':
            self.publish_motion(0.0, -self.angular_speed)
        elif key == 'x':
            self.stop()
        elif key in ('+', '='):
            self.adjust_speed(1)
        elif key in ('-', '_'):
            self.adjust_speed(-1)
        elif key == 'q':
            self.stop()
            return False
        return True


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
            ready, _, _ = select.select([sys.stdin], [], [], 0.02)
            if ready:
                running = node.handle_key(sys.stdin.read(1))
    except KeyboardInterrupt:
        node.stop()
    finally:
        node.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
