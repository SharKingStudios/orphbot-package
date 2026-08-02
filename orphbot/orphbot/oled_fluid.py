import math
import time

from sensor_msgs.msg import Imu
import rclpy
from rclpy.node import Node


G_TO_MS2 = 9.80665


class SSD1306:
    def __init__(self, bus, address, width=128, height=64):
        self.bus = bus
        self.address = int(address)
        self.width = int(width)
        self.height = int(height)
        self.pages = self.height // 8
        self.buffer = bytearray(self.width * self.pages)
        self._initialize()

    def command(self, *values):
        for value in values:
            self.bus.write_i2c_block_data(self.address, 0x00, [int(value) & 0xff])

    def _initialize(self):
        self.command(
            0xae, 0xd5, 0x80, 0xa8, self.height - 1, 0xd3, 0x00, 0x40,
            0x8d, 0x14, 0x20, 0x00, 0xa1, 0xc8, 0xda, 0x12,
            0x81, 0xcf, 0xd9, 0xf1, 0xdb, 0x40, 0xa4, 0xa6, 0xaf,
        )
        self.clear()
        self.show()

    def clear(self):
        for index in range(len(self.buffer)):
            self.buffer[index] = 0

    def show(self):
        self.command(0x21, 0, self.width - 1, 0x22, 0, self.pages - 1)
        for start in range(0, len(self.buffer), 32):
            chunk = list(self.buffer[start:start + 32])
            self.bus.write_i2c_block_data(self.address, 0x40, chunk)

    def pixel(self, x, y, value=True):
        x = int(x)
        y = int(y)
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        index = x + (y // 8) * self.width
        mask = 1 << (y & 7)
        if value:
            self.buffer[index] |= mask
        else:
            self.buffer[index] &= ~mask

    def line(self, x0, y0, x1, y1):
        x0 = int(round(x0))
        y0 = int(round(y0))
        x1 = int(round(x1))
        y1 = int(round(y1))
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def rect(self, x0, y0, x1, y1):
        self.line(x0, y0, x1, y0)
        self.line(x1, y0, x1, y1)
        self.line(x1, y1, x0, y1)
        self.line(x0, y1, x0, y0)

    def fill_circle(self, cx, cy, radius):
        r2 = radius * radius
        for y in range(int(cy - radius), int(cy + radius) + 1):
            for x in range(int(cx - radius), int(cx + radius) + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    self.pixel(x, y)

    def close(self):
        self.clear()
        self.show()
        close = getattr(self.bus, 'close', None)
        if close is not None:
            close()


class OLEDFluid(Node):
    def __init__(self):
        super().__init__('oled_fluid')
        self.declare_parameter('bus', 1)
        self.declare_parameter('address', 0x3c)
        self.declare_parameter('width', 128)
        self.declare_parameter('height', 64)
        self.declare_parameter('display_rate', 15.0)
        self.declare_parameter('particle_count', 42)
        self.declare_parameter('imu_topic', 'imu/data_raw')
        self.declare_parameter('splash_seconds', 1.5)

        bus_number = int(self.get_parameter('bus').value)
        address = int(self.get_parameter('address').value)
        width = int(self.get_parameter('width').value)
        height = int(self.get_parameter('height').value)
        rate = max(1.0, float(self.get_parameter('display_rate').value))
        count = max(8, int(self.get_parameter('particle_count').value))
        topic = str(self.get_parameter('imu_topic').value)
        self.splash_seconds = max(
            0.0,
            float(self.get_parameter('splash_seconds').value),
        )

        self.display = self._open_display(bus_number, address, width, height)
        self.particles = self._make_particles(count, width, height)
        self.last_time = time.monotonic()
        self.start_time = self.last_time
        self.imu_time = 0.0
        self.accel_x = 0.0
        self.accel_y = 0.0
        self.accel_z = G_TO_MS2

        self.create_subscription(Imu, topic, self.imu_callback, 10)
        self.create_timer(1.0 / rate, self.tick)
        self.get_logger().info(
            f'OLED fluid display ready at 0x{address:02x} on I2C bus {bus_number}'
        )

    def _open_display(self, bus_number, address, width, height):
        try:
            from smbus2 import SMBus
        except ImportError as exc:
            raise RuntimeError(
                'No smbus2 module found. Install python3-smbus2 on the Pi.'
            ) from exc
        try:
            return SSD1306(SMBus(bus_number), address, width, height)
        except OSError as exc:
            raise RuntimeError(
                f'OLED did not respond at 0x{address:02x} on I2C bus {bus_number}.'
            ) from exc

    def _make_particles(self, count, width, height):
        particles = []
        cols = max(1, int(math.sqrt(count * 2)))
        for index in range(count):
            x = 14 + (index % cols) * 6
            y = height - 12 - (index // cols) * 5
            particles.append([float(x), float(y), 0.0, 0.0])
        return particles

    def imu_callback(self, msg):
        self.accel_x = float(msg.linear_acceleration.x)
        self.accel_y = float(msg.linear_acceleration.y)
        self.accel_z = float(msg.linear_acceleration.z)
        self.imu_time = time.monotonic()

    def tick(self):
        now = time.monotonic()
        dt = max(0.01, min(0.08, now - self.last_time))
        self.last_time = now
        self._step_particles(dt, now)
        self._draw(now)
        try:
            self.display.show()
        except OSError as exc:
            self.get_logger().error(f'OLED write failed: {exc}')

    def _step_particles(self, dt, now):
        if self.imu_time and now - self.imu_time < 1.5:
            force_x = max(-1.0, min(1.0, -self.accel_y / G_TO_MS2)) * 65.0
            force_y = max(-1.0, min(1.0, self.accel_x / G_TO_MS2)) * 35.0
            force_y += 55.0
        else:
            force_x = math.sin(now * 1.6) * 18.0
            force_y = 55.0

        min_x = 6.0
        max_x = self.display.width - 7.0
        min_y = 18.0
        max_y = self.display.height - 6.0
        radius = 2.7

        for p in self.particles:
            p[2] = (p[2] + force_x * dt) * 0.90
            p[3] = (p[3] + force_y * dt) * 0.90
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if p[0] < min_x:
                p[0] = min_x
                p[2] *= -0.45
            elif p[0] > max_x:
                p[0] = max_x
                p[2] *= -0.45
            if p[1] < min_y:
                p[1] = min_y
                p[3] *= -0.45
            elif p[1] > max_y:
                p[1] = max_y
                p[3] *= -0.45

        for i, a in enumerate(self.particles):
            for b in self.particles[i + 1:]:
                dx = b[0] - a[0]
                dy = b[1] - a[1]
                dist2 = dx * dx + dy * dy
                min_dist = radius * 1.7
                if 0.01 < dist2 < min_dist * min_dist:
                    dist = math.sqrt(dist2)
                    push = (min_dist - dist) * 0.12
                    nx = dx / dist
                    ny = dy / dist
                    a[0] -= nx * push
                    a[1] -= ny * push
                    b[0] += nx * push
                    b[1] += ny * push

    def _draw(self, now):
        self.display.clear()
        self.display.rect(2, 14, self.display.width - 3, self.display.height - 3)
        self.display.line(8, 11, self.display.width - 9, 11)
        if now - self.start_time < self.splash_seconds:
            self._draw_splash(now)
        for x, y, _vx, _vy in self.particles:
            self.display.fill_circle(x, y, 2.0)
        self._draw_imu_dot(now)

    def _draw_splash(self, now):
        span = int((math.sin(now * 8.0) + 1.0) * 18.0) + 12
        mid = self.display.width // 2
        self.display.line(mid - span, 6, mid + span, 6)
        self.display.line(mid - span // 2, 3, mid + span // 2, 3)

    def _draw_imu_dot(self, now):
        if not self.imu_time or now - self.imu_time > 1.5:
            self.display.rect(118, 3, 124, 9)
            return
        ax = max(-1.0, min(1.0, self.accel_x / G_TO_MS2))
        ay = max(-1.0, min(1.0, self.accel_y / G_TO_MS2))
        self.display.fill_circle(121 + ax * 3.0, 6 + ay * 3.0, 1.5)

    def destroy_node(self):
        try:
            self.display.close()
        finally:
            super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = OLEDFluid()
        rclpy.spin(node)
    except RuntimeError as exc:
        temp_node = node
        if temp_node is None:
            temp_node = rclpy.create_node('oled_fluid_startup_error')
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
