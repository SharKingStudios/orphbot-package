import time
import tkinter as tk

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node


HELP = 'Focus this window. Hold W/S/A/D to drive. Space stops. Q quits.'
MOTION_KEYS = {'w', 's', 'a', 'd'}


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        self.declare_parameter('linear_speed', 0.16)
        self.declare_parameter('angular_speed', 0.65)
        self.declare_parameter('speed_step', 0.04)
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('release_debounce_ms', 80)
        self.declare_parameter('stop_burst', 3)

        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)
        self.speed_step = float(self.get_parameter('speed_step').value)
        publish_rate = max(1.0, float(self.get_parameter('publish_rate').value))
        self.publish_period = 1.0 / publish_rate
        self.release_debounce_ms = max(
            0,
            int(self.get_parameter('release_debounce_ms').value),
        )
        self.stop_burst = max(1, int(self.get_parameter('stop_burst').value))

        self.active_keys = set()
        self.pending_releases = {}
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.last_publish_time = 0.0
        self.stop_publishes_remaining = 0

    def publish_motion(self, linear, angular):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)
        self.last_publish_time = time.monotonic()

    def desired_motion(self):
        linear = 0.0
        angular = 0.0
        if 'w' in self.active_keys:
            linear += self.linear_speed
        if 's' in self.active_keys:
            linear -= self.linear_speed
        if 'a' in self.active_keys:
            angular += self.angular_speed
        if 'd' in self.active_keys:
            angular -= self.angular_speed
        return linear, angular

    def set_key_down(self, root, key):
        key = key.lower()
        pending = self.pending_releases.pop(key, None)
        if pending is not None:
            root.after_cancel(pending)
        if key in MOTION_KEYS:
            self.active_keys.add(key)
            self.stop_publishes_remaining = 0
        elif key in ('+', '='):
            self.adjust_speed(1)
        elif key in ('-', '_'):
            self.adjust_speed(-1)
        elif key in ('space', 'x'):
            self.stop_now(root)
        elif key == 'q':
            self.stop_now(root)
            root.destroy()

    def set_key_up(self, root, key):
        key = key.lower()
        if key not in MOTION_KEYS:
            return
        pending = self.pending_releases.pop(key, None)
        if pending is not None:
            root.after_cancel(pending)
        handle = root.after(
            self.release_debounce_ms,
            lambda: self.finish_key_release(key),
        )
        self.pending_releases[key] = handle

    def finish_key_release(self, key):
        self.pending_releases.pop(key, None)
        self.active_keys.discard(key)
        if not self.active_keys:
            self.stop_now()

    def stop_now(self, root=None):
        self.active_keys.clear()
        if root is not None:
            for handle in self.pending_releases.values():
                root.after_cancel(handle)
        self.pending_releases.clear()
        self.last_linear = 0.0
        self.last_angular = 0.0
        self.stop_publishes_remaining = self.stop_burst
        self.publish_motion(0.0, 0.0)
        self.stop_publishes_remaining -= 1

    def adjust_speed(self, direction):
        self.linear_speed = max(
            0.04,
            min(0.4, self.linear_speed + direction * self.speed_step),
        )
        angular_delta = direction * self.speed_step * 3.0
        self.angular_speed = max(
            0.15,
            min(1.5, self.angular_speed + angular_delta),
        )
        print(f'linear={self.linear_speed:.2f} m/s angular={self.angular_speed:.2f} rad/s')

    def tick(self):
        now = time.monotonic()
        linear, angular = self.desired_motion()
        moving = bool(self.active_keys)
        changed = linear != self.last_linear or angular != self.last_angular

        if moving and (changed or now - self.last_publish_time >= self.publish_period):
            self.publish_motion(linear, angular)
            self.last_linear = linear
            self.last_angular = angular
            return

        should_publish_stop = (
            self.stop_publishes_remaining > 0
            and now - self.last_publish_time >= self.publish_period
        )
        if should_publish_stop:
            self.publish_motion(0.0, 0.0)
            self.stop_publishes_remaining -= 1


def make_window(node):
    root = tk.Tk()
    root.title('OrphBot Teleop')
    root.geometry('420x180')
    root.resizable(False, False)

    label = tk.Label(root, text=HELP, padx=16, pady=16)
    label.pack(fill='both', expand=True)

    speed_label = tk.Label(root)
    speed_label.pack(pady=(0, 16))

    def refresh_label():
        speed_label.config(
            text=f'linear {node.linear_speed:.2f} m/s   angular {node.angular_speed:.2f} rad/s'
        )
        root.after(100, refresh_label)

    def key_name(event):
        if event.keysym == 'space':
            return 'space'
        return event.char.lower() if event.char else event.keysym.lower()

    root.bind('<KeyPress>', lambda event: node.set_key_down(root, key_name(event)))
    root.bind('<KeyRelease>', lambda event: node.set_key_up(root, key_name(event)))
    root.protocol('WM_DELETE_WINDOW', lambda: (node.stop_now(root), root.destroy()))
    root.after(100, refresh_label)
    root.focus_force()
    return root


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTeleop()
    root = None
    try:
        root = make_window(node)

        def spin_and_tick():
            if not rclpy.ok():
                root.destroy()
                return
            rclpy.spin_once(node, timeout_sec=0.0)
            node.tick()
            root.after(20, spin_and_tick)

        root.after(20, spin_and_tick)
        root.mainloop()
    except tk.TclError as exc:
        raise RuntimeError(
            'keyboard_teleop needs a GUI display for real key press/release events. '
            'On WSL, install python3-tk and use WSLg or another X server.'
        ) from exc
    except KeyboardInterrupt:
        node.stop_now()
    finally:
        node.stop_now()
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
