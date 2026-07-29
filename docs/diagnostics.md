# OrphBot Diagnostics

This log captures the working state before and during package bringup. Commands were run from WSL Ubuntu 24.04 unless noted.

## Baseline Repo State

Local repo path:

```bash
/home/logan/orphbot_ws/src/orphbot-package
```

Remote:

```bash
origin git@github.com:sharkingstudios/orphbot-package.git
```

Git state at start:

```bash
## main...origin/main
cde73a9 (HEAD -> main, origin/main, origin/HEAD) Create initial ROS 2 orphbot package
44cedee Initial commit
```

Initial files were a minimal ROS 2 Python package skeleton:

```text
README.md
orphbot/package.xml
orphbot/setup.py
orphbot/setup.cfg
orphbot/orphbot/__init__.py
orphbot/resource/orphbot
orphbot/test/test_copyright.py
orphbot/test/test_flake8.py
orphbot/test/test_pep257.py
```

Initial `package.xml` already listed the core ROS dependencies:

```text
rclpy
geometry_msgs
sensor_msgs
nav_msgs
tf2_ros
robot_state_publisher
xacro
```

Initial `setup.py` had no console scripts and did not install launch, URDF, RViz, config, or docs files.

## Local Build Check

Requested command:

```bash
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep orphbot
```

Result:

```text
bash: line 1: rosdep: command not found
```

Follow-up build without `rosdep`:

```bash
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg list | grep orphbot
```

Result:

```text
Starting >>> orphbot
Finished <<< orphbot [0.83s]

Summary: 1 package finished [0.95s]
orphbot
```

The initial skeleton package built locally.

## Robot SSH State

Target:

```bash
ssh ubuntu@orphbot.local
```

Name resolution from WSL:

```text
10.0.0.99 orphbot.local
```

First SSH attempt failed because WSL could not prompt for the new host key:

```text
Host key verification failed.
```

Verbose SSH showed the robot presented this host key:

```text
ssh-ed25519 SHA256:LDn2Qq7cOy/+9IyRNFEQOUp/YoD5/RbtJyiN4rFo1qY
```

After using `StrictHostKeyChecking=accept-new`, the host key was added, but login still failed:

```text
Warning: Permanently added 'orphbot.local' (ED25519) to the list of known hosts.
ubuntu@orphbot.local: Permission denied (publickey,password).
```

Historical note: SSH initially reached the robot but authentication was not available. This was later fixed by adding the laptop public key to the robot authorized keys file.

## IMU Checks Still Needed On Robot

Run these once SSH authentication works:

```bash
hostname
uname -a
cat /etc/os-release
echo "RMW=$RMW_IMPLEMENTATION"
echo "DOMAIN=$ROS_DOMAIN_ID"
echo "LOCALHOST=$ROS_LOCALHOST_ONLY"
ls -l /dev/i2c* || true
groups
grep -n "i2c" /boot/firmware/config.txt || true
i2cdetect -y 1 || true
sudo i2cdetect -y 1 || true
for b in /dev/i2c-*; do n=${b#/dev/i2c-}; echo "Bus $n"; sudo i2cdetect -y "$n"; done
```

Expected MPU6050 addresses:

```text
AD0 -> GND: 0x68
AD0 -> 3V3: 0x69
```

If `/dev/i2c-1` exists and scans show all `--`, the Pi I2C bus is enabled but the MPU6050 is not responding. Recheck power, ground, SDA/SCL orientation, AD0, solder joints/header continuity, and module voltage compatibility.


## Implementation Summary

Implemented package files:

```text
orphbot/orphbot/motor_driver.py
orphbot/orphbot/keyboard_teleop.py
orphbot/orphbot/simple_auton.py
orphbot/orphbot/odom_publisher.py
orphbot/orphbot/mpu6050_node.py
orphbot/launch/bringup.launch.py
orphbot/launch/auton.launch.py
orphbot/launch/rviz.launch.py
orphbot/urdf/robot.urdf.xacro
orphbot/rviz/orphbot.rviz
orphbot/config/orphbot.yaml
README.md
```

Notes:

- No joint state publisher was added. The wheel links use fixed joints in URDF so `robot_state_publisher` does not need `/joint_states`.
- Odometry is command-based dead reckoning from `/cmd_vel`. It publishes `/odom`, `/path`, and TF from `odom` to `base_link`.
- The IMU node is part of bringup by default and reports clear errors if I2C or the MPU6050 is unavailable.
- The motor driver uses Raspberry Pi GPIO directly and is intended to run on the robot.

## Local Validation After Implementation

Python syntax check:

```bash
cd ~/orphbot_ws/src/orphbot-package
python3 -m py_compile orphbot/orphbot/*.py orphbot/launch/*.launch.py
```

Result: passed.

URDF/xacro check:

```bash
cd ~/orphbot_ws/src/orphbot-package
source /opt/ros/jazzy/setup.bash
xacro orphbot/urdf/robot.urdf.xacro >/tmp/orphbot_robot.urdf
```

Result: passed.

Workspace build:

```bash
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Result:

```text
Starting >>> orphbot
Finished <<< orphbot [0.56s]

Summary: 1 package finished [0.61s]
```

Motor runtime test:

The motor driver now uses real Raspberry Pi GPIO only. Do not run it on the laptop. First runtime validation must happen on the robot with the wheels off the ground and `max_pwm:=0.35`.

Local IMU startup check:

```bash
ros2 run orphbot mpu6050_node
```

Result on WSL laptop:

```text
No SMBus module found. Install python3-smbus or python3-smbus2 on the Pi.
```

This is expected off the Raspberry Pi and confirms the node fails with a clear message.

## Historical Robot SSH Blocker

Direct PowerShell SSH check:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 ubuntu@orphbot.local hostname
```

Result:

```text
ubuntu@orphbot.local: Permission denied (publickey,password).
```

WSL SSH check after accepting the host key showed the same authentication failure. Because SSH authentication is blocked, these robot checks remain unverified:

- OS and kernel on the Pi.
- ROS environment variables on the Pi.
- Whether the repo is present and current on the Pi.
- Whether `/dev/i2c-1` exists.
- Whether `/boot/firmware/config.txt` contains the required I2C settings.
- Whether user `ubuntu` is in the `i2c` group.
- Whether `i2cdetect -y 1` differs with `sudo`.
- Whether the MPU6050 appears on bus 0, bus 1, or any other bus.

## Current IMU Diagnosis

Previous information says `i2cdetect -y 1` returned a valid grid containing only `--`. That means the I2C controller existed and scanned, but no device acknowledged on bus 1.

Most likely causes to resolve for the guide:

1. MPU6050 board is not powered at its actual VCC/GND pins.
2. SDA and SCL are swapped or not making contact.
3. AD0 is floating or tied differently than expected. GND should produce `0x68`; 3V3 should produce `0x69`.
4. Header solder joints or jumper continuity are bad.
5. Breakout board voltage behavior is incompatible with Pi 3.3 V I2C logic.
6. The MPU6050 module is damaged.

Do not recommend 5 V power unless the exact breakout is confirmed 5 V compatible and does not pull SDA/SCL up to 5 V.


## Final Local Test Pass

After style cleanup and dependency cleanup:

```bash
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
colcon test --packages-select orphbot --event-handlers console_direct+
```

Result:

```text
Summary: 1 package finished [0.64s]
2 passed, 1 skipped in 0.16s
```

`test_copyright.py` was skipped by the generated ROS 2 package test setup. `test_flake8.py` and `test_pep257.py` passed.


## Robot Bringup Session - July 29, 2026

SSH authentication was fixed by adding the laptop public key to `~/.ssh/authorized_keys` on the robot. Direct PowerShell SSH then worked:

```powershell
ssh ubuntu@orphbot.local hostname
```

Result:

```text
orphbot
```

Robot OS:

```text
hostname: orphbot
Ubuntu 24.04.4 LTS
kernel: 6.8.0-1057-raspi
aarch64 Raspberry Pi
```

ROS environment variables were not set by default in the SSH shell:

```text
RMW=
DOMAIN=
LOCALHOST=
```

For guide runs, set:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=17
export ROS_LOCALHOST_ONLY=0
```

Robot I2C state:

```text
/dev/i2c-1 exists
/dev/i2c-2 exists
ubuntu is in the i2c group
/boot/firmware/config.txt contains dtparam=i2c_arm=on
/boot/firmware/config.txt currently contains dtparam=i2c_arm_baudrate=50000
```

`i2cdetect -y 1` now shows the MPU6050 at `0x68`:

```text
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
```

Direct SMBus check:

```bash
python3 -c 'from smbus2 import SMBus; b=SMBus(1); print(hex(b.read_byte_data(0x68,0x75)))'
```

Actual result from the register read was:

```text
0x68
```

The Python libraries needed by the hardware nodes are available on the robot:

```text
gpiozero=ok
lgpio=ok
smbus2=ok
```

`python3-smbus` is not installed, but `smbus2` is installed and the node supports it.

Robot repo update and build:

```bash
cd ~/orphbot_ws/src/orphbot-package
git pull
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Result:

```text
Updating cde73a9..3115046
Fast-forward
Starting >>> orphbot
Finished <<< orphbot [16.3s]
Summary: 1 package finished [18.4s]
```

Installed robot executables:

```text
orphbot keyboard_teleop
orphbot motor_driver
orphbot mpu6050_node
orphbot odom_publisher
orphbot simple_auton
```

ROS IMU node verification:

```bash
ros2 run orphbot mpu6050_node
ros2 topic echo /imu/data_raw --once
```

Result: `/imu/data_raw` published a real IMU sample. Example values:

```text
frame_id: imu_link
angular_velocity.x: 0.13509647797879773
angular_velocity.y: 0.0019984686091538122
angular_velocity.z: -0.004529862180748642
linear_acceleration.x: -0.26336218261718747
linear_acceleration.y: -0.24181436767578124
linear_acceleration.z: 9.215282189941405
```

Current IMU conclusion: the MPU6050 is detected and publishing through ROS. For the final guide setup, change the I2C baud rate to `100000` and reboot:

```bash
sudo sed -i 's/^dtparam=i2c_arm_baudrate=.*/dtparam=i2c_arm_baudrate=100000/' /boot/firmware/config.txt
sudo reboot
```

## Real Motor Bringup Still Needed

The robot build is complete and the IMU works. The remaining robot-side validation is to run bringup with the robot on a stand, then publish one conservative `/cmd_vel` command and verify all wheels spin in the intended directions. Do not publish drive commands until the operator has confirmed the robot is safe on the stand.
