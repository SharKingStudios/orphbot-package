# OrphBot ROS 2 Package

OrphBot is a small Raspberry Pi Zero 2 W skid-steer robot for the Hack Club Waypoint guide. This package provides the real robot bringup nodes, keyboard teleop, command-based odometry, an MPU6050 IMU node, a simple autonomous routine, and RViz assets.

The robot can drive from `/cmd_vel`, publish `/odom`, `/path`, TF from `odom` to `base_link`, and publish raw IMU data on `/imu/data_raw` once the MPU6050 is visible on I2C.

## Hardware

- Raspberry Pi Zero 2 W with Ubuntu 24.04 64-bit
- Two DRV8833 motor driver modules
- Four DC motors in skid steer
- MPU6050 IMU breakout
- 9 V battery for motors only
- 5 V buck converter for the Pi only
- Common ground between Pi, motor drivers, battery, and buck converter

Never feed 9 V into the Pi.

## Wiring Summary

Use BCM GPIO numbers in software.

Left DRV8833:

| DRV8833 pin | Pi GPIO | Physical pin |
| --- | --- | --- |
| IN1 | GPIO5 | 29 |
| IN2 | GPIO6 | 31 |
| IN3 | GPIO13 | 33 |
| IN4 | GPIO19 | 35 |
| EEP/SLP | GPIO12 or 3V3 | 32 or 1 |

Right DRV8833:

| DRV8833 pin | Pi GPIO | Physical pin |
| --- | --- | --- |
| IN1 | GPIO20 | 38 |
| IN2 | GPIO21 | 40 |
| IN3 | GPIO23 | 16 |
| IN4 | GPIO24 | 18 |
| EEP/SLP | GPIO12 or 3V3 | 32 or 1 |

MPU6050:

| MPU6050 pin | Pi pin |
| --- | --- |
| VCC | 3V3, physical pin 1 |
| GND | GND, physical pin 6 |
| SDA | GPIO2/SDA, physical pin 3 |
| SCL | GPIO3/SCL, physical pin 5 |
| AD0 | GND for `0x68`, 3V3 for `0x69` |
| INT | not used by the current node; GPIO4/physical pin 7 if connected |

## Flash And SSH

1. Flash Ubuntu Server 24.04 64-bit for Raspberry Pi.
2. On the boot partition, create an empty file named `ssh`.
3. Boot the Pi and find it as `orphbot.local`.
4. SSH in:

```bash
ssh ubuntu@orphbot.local
```

## Install ROS 2 Jazzy

On the robot, install a minimal ROS setup plus robot hardware tools:

```bash
sudo apt update
sudo apt install -y locales software-properties-common curl git
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe
sudo apt update
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-jazzy-rmw-cyclonedds-cpp python3-colcon-common-extensions python3-rosdep python3-gpiozero python3-lgpio python3-smbus2 i2c-tools git
```

On the laptop, install the desktop tools so RViz is available:

```bash
sudo apt update
sudo apt install -y locales software-properties-common curl git
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe
sudo apt update
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-rmw-cyclonedds-cpp python3-colcon-common-extensions python3-rosdep git
```

Initialize `rosdep` once per machine if it has not been initialized:

```bash
sudo rosdep init
rosdep update
```

## ROS Networking

Set the same ROS networking variables on both laptop and robot:

```bash
# Use the env scripts after cloning/building:
# Robot: source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
# WSL laptop: source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
```

For convenience, add those lines to `~/.bashrc` on both machines. The robot should have this block near the end of `~/.bashrc`:

```bash
# OrphBot ROS 2 networking
# Use the env scripts after cloning/building:
# Robot: source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
# WSL laptop: source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
```


## Windows WSL Networking

For Windows laptops, run Ubuntu 24.04 in WSL 2. Native Linux users can skip this section.

Create `%UserProfile%\.wslconfig` on Windows:

```ini
[wsl2]
networkingMode=mirrored
```

Restart WSL from PowerShell:

```powershell
wsl --shutdown
```

If WSL can SSH to the robot but `ros2 topic list` does not show robot topics, add this in an Administrator PowerShell window, replacing `10.0.0.99` with the robot IP if needed:

```powershell
New-NetFirewallHyperVRule `
  -Name "OrphBot-ROS2-DDS-from-10.0.0.99" `
  -DisplayName "OrphBot ROS 2 DDS from robot" `
  -Direction Inbound `
  -VMCreatorId "{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}" `
  -Protocol UDP `
  -RemoteAddresses 10.0.0.99 `
  -Action Allow `
  -Enabled True
```

## Clone And Build

On each machine:

```bash
mkdir -p ~/orphbot_ws/src
cd ~/orphbot_ws/src
git clone https://github.com/SharKingStudios/orphbot-package.git
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install
source install/setup.bash
```

Update later with:

```bash
cd ~/orphbot_ws/src/orphbot-package
git pull
cd ~/orphbot_ws
colcon build --symlink-install
source install/setup.bash
```

## Run Bringup On The Robot

Put the robot on a stand with the wheels off the ground for first tests. The motor driver talks to the Raspberry Pi GPIO pins, so run bringup on the robot.

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 launch orphbot bringup.launch.py max_pwm:=0.35
```

The bringup starts the motor driver, robot description, odometry, MPU6050 node, and a static `map` to `odom` transform for RViz. If the IMU is not detected, fix I2C before treating the robot as complete.

For a first controlled motor check from another terminal on the robot, keep the robot on the stand and publish a short slow command:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.16}, angular: {z: 0.0}}" -r 10 -t 20 -w 0 --keep-alive 0.1
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}" --once -w 0 --keep-alive 0.1
```

## Motor Direction Test

Yellow TT motors may need more than very low PWM to visibly move. With the robot on a stand and bringup stopped, test one motor at a time:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 run orphbot motor_test left_front --pwm 0.55 --seconds 1.5
```

Repeat with `left_rear`, `right_front`, and `right_rear`. If one motor only spins one direction, check that motor's two DRV8833 input wires, GPIO pins, solder joints, and driver channel.

## Drive From The Laptop

In a laptop terminal with the same ROS environment variables:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
ros2 run orphbot keyboard_teleop
```

Keys: hold `W` forward, hold `S` backward, hold `A` left, hold `D` right, `X` or Space stop, `+` faster, `-` slower, `Q` quit. The laptop teleop republishes while a movement key is repeating and sends a short burst of stop commands when the key stream stops, which keeps odometry and the real motor watchdog aligned even through WSL/Windows terminal repeat behavior.

## Run RViz From The Laptop

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
ros2 launch orphbot rviz.launch.py
```

The default RViz view is intentionally sparse: robot model, origin axes at `map`, and the `/path` trail. The `map` frame is an identity visualization frame equal to `odom`; there is no SLAM map.

## Robot Model Mesh

The URDF uses a simple box body unless a renderable body mesh exists at `orphbot/meshes/orphbot_body.stl`. STEP files belong in `orphbot/cad/` as source CAD. RViz does not directly render STEP through URDF, so export or convert the STEP body to STL, rebuild with `colcon build --symlink-install`, and the launch files will pick up the STL automatically.

## Run Simple Auton

Tell everyone nearby before running autonomy. Keep the robot on a stand for the first run.

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 launch orphbot auton.launch.py max_pwm:=0.35
```

This drives forward briefly, stops, turns, stops, then drives forward again.

## MPU6050 Checks

The MPU6050 is required for the final robot. Start by confirming the bus and address:

```bash
ls -l /dev/i2c*
groups
grep -n "i2c" /boot/firmware/config.txt
i2cdetect -y 1
sudo i2cdetect -y 1
```

`/boot/firmware/config.txt` should include:

```text
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=100000
```

If the baud rate is different, set it and reboot:

```bash
sudo sed -i 's/^dtparam=i2c_arm_baudrate=.*/dtparam=i2c_arm_baudrate=100000/' /boot/firmware/config.txt
sudo reboot
```

If AD0 is connected to GND, expect `0x68`. If AD0 is connected to 3V3, expect `0x69`.

If bus 1 shows all `--`, scan every I2C bus:

```bash
for b in /dev/i2c-*; do n=${b#/dev/i2c-}; echo "Bus $n"; sudo i2cdetect -y "$n"; done
```

If no bus shows `68` or `69`, recheck power at the IMU VCC/GND pins, common ground, SDA/SCL not swapped, AD0, header solder joints, and whether the breakout is safe for Pi 3.3 V I2C logic. Do not connect VCC to 5 V unless the exact breakout is known to be 5 V compatible and not pulling SDA/SCL up to 5 V.

## Troubleshooting

If topics do not appear across Wi-Fi, confirm both machines use the same values:

```bash
echo $RMW_IMPLEMENTATION
echo $ROS_DOMAIN_ID
echo $ROS_LOCALHOST_ONLY
ros2 topic list
```

If SSH was not enabled during imaging, shut down the Pi, mount the boot partition, and create the empty `ssh` file again.

Optional tools like `htop`, router client lists, and advanced Cyclone DDS XML configs are useful for debugging, but they are not part of the main path.

For the exact internal procedure, see `docs/runbook.md`.
