# OrphBot Internal Bringup Runbook

This is engineering documentation for writing the Waypoint guide later. It should stay literal and specific to what worked on the example robot.

## Verified Robot State

Robot identity and OS were checked over SSH on July 29, 2026:

```bash
ssh ubuntu@10.0.0.99 "hostname; cat /proc/device-tree/model; uname -a; uname -m; getconf LONG_BIT; cat /etc/os-release"
```

Observed:

```text
hostname: orphbot
model: Raspberry Pi Zero 2 W Rev 1.0
kernel: Linux orphbot 6.8.0-1057-raspi #61-Ubuntu SMP PREEMPT_DYNAMIC Tue May 26 22:12:44 UTC 2026
architecture: aarch64
word size: 64
OS: Ubuntu 24.04.4 LTS (Noble Numbat)
```

Conclusion: the Pi Zero 2 W is actually running Ubuntu 24.04 64-bit ARM. `aarch64` plus `getconf LONG_BIT` returning `64` is the proof.

## Fresh Robot Install Path

Flash the Pi:

1. Use Raspberry Pi Imager.
2. Choose Ubuntu Server 24.04 64-bit for Raspberry Pi.
3. Set hostname to `orphbot` if the imager allows it.
4. Enable SSH. The simple fallback that worked is creating an empty file named `ssh` on the boot partition.
5. Boot the Pi and SSH in:

```bash
ssh ubuntu@orphbot.local
```

The example robot password is `ubuntu`.

If laptop key auth is needed, add the laptop public key on the robot:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
printf '%s\n' '<laptop public ssh key>' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Verify the OS and architecture:

```bash
hostname
cat /proc/device-tree/model
uname -m
getconf LONG_BIT
cat /etc/os-release
```

Expected for this bot:

```text
Raspberry Pi Zero 2 W Rev 1.0
aarch64
64
Ubuntu 24.04.x LTS
```

## Install ROS 2 Jazzy On The Robot

Set locale and add the ROS 2 apt repository:

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
```

Install robot-side ROS and hardware packages:

```bash
sudo apt install -y \
  ros-jazzy-ros-base \
  ros-jazzy-rmw-cyclonedds-cpp \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-gpiozero \
  python3-lgpio \
  python3-smbus2 \
  i2c-tools \
  git
```

Initialize rosdep once:

```bash
sudo rosdep init || true
rosdep update
```

Make sure the `ubuntu` user can access GPIO and I2C, then reboot or log out/in:

```bash
sudo usermod -aG gpio,i2c ubuntu
sudo reboot
```

## Robot I2C And MPU6050 Setup

The working config is:

```text
/boot/firmware/config.txt:
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=100000
```

Set it with:

```bash
grep -q '^dtparam=i2c_arm=on' /boot/firmware/config.txt || echo 'dtparam=i2c_arm=on' | sudo tee -a /boot/firmware/config.txt
if grep -q '^dtparam=i2c_arm_baudrate=' /boot/firmware/config.txt; then
  sudo sed -i 's/^dtparam=i2c_arm_baudrate=.*/dtparam=i2c_arm_baudrate=100000/' /boot/firmware/config.txt
else
  echo 'dtparam=i2c_arm_baudrate=100000' | sudo tee -a /boot/firmware/config.txt
fi
sudo reboot
```

After reboot, verify:

```bash
ls -l /dev/i2c*
groups
grep -n i2c /boot/firmware/config.txt
i2cdetect -y 1
python3 -c 'from smbus2 import SMBus; b=SMBus(1); print(hex(b.read_byte_data(0x68,0x75))); b.close()'
```

Expected on the example robot:

```text
/dev/i2c-1 exists
ubuntu is in the i2c group
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=100000
i2cdetect shows 68 on bus 1
WHO_AM_I prints 0x68
```

What was wrong with the IMU path:

- Earlier scans showed a working I2C bus but no device.
- During this session the MPU6050 appeared at `0x68`, so the wiring/device path became valid.
- The Pi config had `dtparam=i2c_arm_baudrate=50000`, not the intended `100000`.
- We changed it to `100000`, rebooted, and verified the MPU6050 still appeared at `0x68`.
- The ROS node publishes real `/imu/data_raw` using `smbus2`.

## Build OrphBot On The Robot

```bash
mkdir -p ~/orphbot_ws/src
cd ~/orphbot_ws/src
if [ -d orphbot-package ]; then
  cd orphbot-package
  git pull
else
  git clone https://github.com/SharKingStudios/orphbot-package.git
fi
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables orphbot
```

Expected executables:

```text
orphbot keyboard_teleop
orphbot motor_driver
orphbot mpu6050_node
orphbot odom_publisher
orphbot simple_auton
```

## Robot ROS Environment

For every robot terminal, source ROS, the workspace, and the robot env script in this order:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
```

For convenience after the package has been cloned, this can be added to the end of `~/.bashrc` for interactive robot terminals:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
```

Do not rely on `source ~/.bashrc` inside non-interactive scripts; Ubuntu `.bashrc` may return early for non-interactive shells.

## Bringup On Robot

Keep the robot on a stand for first tests.

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 launch orphbot bringup.launch.py max_pwm:=0.35
```

Expected ready logs:

```text
robot_description_publisher: Publishing STL robot description for RViz
motor_driver: Motor driver ready, max_pwm=0.35
mpu6050_node: MPU6050 publishing from bus 1, address 0x68
odom_publisher: Command-based odometry publisher ready
```

Expected graph for RViz/teleop:

```bash
ros2 node list
ros2 topic list
```

Important topics:

```text
/cmd_vel
/imu/data_raw
/odom
/path
/robot_description
/tf
/tf_static
```

Bringup also publishes a static identity transform from `map` to `odom`. This is for RViz convenience only; it is not a SLAM-generated map. With this transform, RViz can use either `map` or `odom` as the fixed frame.

## First Motor Test On Robot

Only run this with the wheels off the ground.

Terminal 1 on the robot:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 launch orphbot bringup.launch.py max_pwm:=0.35
```

Terminal 2 on the robot:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.12}, angular: {z: 0.0}}" -r 10 -t 20 -w 0 --keep-alive 0.1
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}" --once -w 0 --keep-alive 0.1
```

If a side spins backward during the forward command, set `invert_left: true` or `invert_right: true` in `orphbot/config/orphbot.yaml`, rebuild, and retest.


## Windows WSL Networking For Teleop And RViz

The Waypoint guide should assume the laptop is Windows running Ubuntu 24.04 in WSL 2. Native Linux can skip this Windows/WSL section and use the same ROS commands directly. macOS was not tested for this robot.

The working Windows path needs WSL mirrored networking plus a Windows Hyper-V firewall rule. Without the firewall rule, WSL can SSH to the robot but ROS 2 teleop/RViz may show no robot topics and `/cmd_vel` may never reach the Pi.

Check WSL version from PowerShell:

```powershell
wsl --version
```

The tested laptop used WSL `2.6.1.0` with mirrored networking. Create or edit `%UserProfile%\.wslconfig` on Windows:

```ini
[wsl2]
networkingMode=mirrored
```

Restart WSL from PowerShell:

```powershell
wsl --shutdown
```

Open Ubuntu in WSL again and confirm it is on the same LAN as the robot:

```bash
ip -brief addr
getent hosts orphbot.local
```

Expected: a `10.0.0.x/24` address in WSL and `orphbot.local` resolving to the robot IP, `10.0.0.99` on the example robot.

On the tested Windows laptop, WSL mirrored networking was enabled but the Hyper-V firewall still had inbound traffic blocked:

```powershell
Get-NetFirewallHyperVVMSetting -PolicyStore ActiveStore
```

Observed:

```text
DefaultInboundAction: Block
```

That blocked ROS 2 DDS packets from the robot back into WSL. Add a scoped inbound UDP rule from the robot IP in an Administrator PowerShell window:

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

If the robot gets a different IP, replace `10.0.0.99` in the rule name, display name, and `-RemoteAddresses` value. To remove the rule later:

```powershell
Remove-NetFirewallHyperVRule -Name "OrphBot-ROS2-DDS-from-10.0.0.99"
```

After the firewall rule, restart the ROS daemon in WSL and verify discovery while robot bringup is running:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
ros2 daemon stop
ros2 topic list --no-daemon --spin-time 5
```

Expected robot topics include:

```text
/cmd_vel
/imu/data_raw
/odom
/path
/robot_description
/tf
/tf_static
```

Bringup also publishes a static identity transform from `map` to `odom`. This is for RViz convenience only; it is not a SLAM-generated map. With this transform, RViz can use either `map` or `odom` as the fixed frame.

References used for this internal note:

- Microsoft WSL networking docs: mirrored mode improves LAN compatibility and supports multicast.
- Microsoft WSL networking docs: Hyper-V firewall settings may need an inbound allow rule for WSL mirrored networking.
- ROS 2 discovery docs: `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` enables discovery on the local subnet for DDS middleware.


## One-Direction Motor Diagnosis

A yellow TT DC motor should spin both directions if the polarity across its two leads reverses. If exactly one motor only spins one direction while the other three work, the most likely causes are on that motor driver's input/channel path, not the motor itself:

- One of the two DRV8833 input wires for that motor is loose, swapped, or on the wrong Pi pin.
- One GPIO pin in the configured pair is not reaching the driver input.
- One DRV8833 channel input or output is damaged.
- A solder joint/header pin on that channel is bad.
- Less likely: one motor lead connection is intermittent and only makes contact under one vibration/load direction.

Use the per-motor diagnostic command on the robot with the wheels off the ground and bringup stopped. Yellow TT motors may need more than `0.35` PWM to visibly move, so start around `0.55` for short tests:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 run orphbot motor_test left_front --pwm 0.55 --seconds 1.5
ros2 run orphbot motor_test left_rear --pwm 0.55 --seconds 1.5
ros2 run orphbot motor_test right_front --pwm 0.55 --seconds 1.5
ros2 run orphbot motor_test right_rear --pwm 0.55 --seconds 1.5
```

Each command runs one motor forward, stops, then runs it reverse. If one phase works and the other does not, swap that motor's two DRV8833 input wires at the GPIO side or move the motor to a known-good channel to distinguish wiring from a bad driver channel. If the failure follows the motor wiring, fix that input lead/solder joint. If the failure stays with the DRV8833 channel, replace or rewire that channel.

Configured motor GPIO pairs:

```text
left_front: GPIO5/GPIO6
left_rear: GPIO13/GPIO19
right_front: GPIO20/GPIO21
right_rear: GPIO23/GPIO24
```

## Laptop Install And Build

The laptop needs desktop ROS so RViz exists. On Ubuntu 24.04 or WSL Ubuntu 24.04 with GUI support:

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
sudo rosdep init || true
rosdep update
```

Build the package on the laptop:

```bash
mkdir -p ~/orphbot_ws/src
cd ~/orphbot_ws/src
if [ -d orphbot-package ]; then
  cd orphbot-package
  git pull
else
  git clone https://github.com/SharKingStudios/orphbot-package.git
fi
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install
```

For WSL laptop terminals, source the WSL env script after ROS and workspace setup:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
```

For convenience after the package has been cloned, the same three lines can be added to the end of WSL `~/.bashrc` for interactive terminals.

## Teleop From Laptop

Robot terminal:

```bash
source ~/.bashrc
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 launch orphbot bringup.launch.py max_pwm:=0.35
```

Laptop terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
ros2 topic list --no-daemon --spin-time 5
ros2 run orphbot keyboard_teleop
```

Teleop is hold-to-drive through a small Tk GUI window. Terminal stdin does not provide real key-release events through WSL, so the teleop node intentionally uses GUI `KeyPress` and `KeyRelease` events instead of normal text input. Focus the teleop window before driving.

Keys:

```text
Hold W forward
Hold S backward
Hold A turn left
Hold D turn right
Space or X stop
+ faster
- slower
Q quit
```

## RViz From Laptop

Robot must be running bringup first.

Laptop terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
ros2 launch orphbot rviz.launch.py
```

RViz should show:

- Fixed frame `map`.
- Grid.
- STL robot model from `/robot_description`.
- Origin axes at `map`.
- Robot axes at `base_link`, which can be shown or hidden from the Displays panel.
- `/path` trail.

The `map` frame is an identity visualization frame equal to `odom`; there is no SLAM map. The RViz config intentionally hides TF, odom arrows, and IMU displays so the guide screenshots stay focused. The URDF intentionally publishes one visual-only link, `base_link`, backed by the STL mesh. It does not include separate wheel links, an IMU link, `base_footprint`, or a joint state publisher.

## CAD And RViz Mesh Slot

Use this convention for the body model:

```text
orphbot/cad/orphbot_body.step       source CAD, kept for editing
orphbot/meshes/orphbot_body.stl     RViz-renderable mesh
```

RViz does not directly render STEP files from URDF. Export or convert the STEP body to STL, then rebuild:

```bash
cd ~/orphbot_ws
colcon build --symlink-install
source install/setup.bash
```

The launch files use `package://orphbot/meshes/orphbot_body.stl`. That STL is required; the package no longer contains a box fallback because the guide should show the actual robot model.

## Simple Autonomy

Robot on a stand for the first run:

```bash
source /opt/ros/jazzy/setup.bash
source ~/orphbot_ws/install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/robot_env.sh
ros2 launch orphbot auton.launch.py max_pwm:=0.35
```

This launches bringup and publishes the conservative timed autonomous routine.

## Current Known Gaps

- Motor direction observation still needs operator confirmation. A low-speed forward command was published from WSL and stopped, but the physical wheel direction was not reported back yet.
- RViz GUI was not opened from this environment. The ROS topics RViz needs are produced by bringup, WSL now discovers them, and the RViz config points at those topics.
- The odometry is command-based dead reckoning. It is the robot's available odometry source, but it will drift because there are no wheel encoders.


## Verified WSL Networking Result

After the Windows Hyper-V firewall rule and `cyclonedds_wsl.xml` interface pin were in place, WSL discovered the robot graph from a fresh robot bringup.

WSL command pattern that worked:

```bash
cd ~/orphbot_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
source ~/orphbot_ws/src/orphbot-package/orphbot/config/wsl_env.sh
ros2 topic list --no-daemon --spin-time 10 -t | sort
```

Observed from WSL:

```text
/cmd_vel [geometry_msgs/msg/Twist]
/imu/data_raw [sensor_msgs/msg/Imu]
/joint_states [sensor_msgs/msg/JointState]
/odom [nav_msgs/msg/Odometry]
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/path [nav_msgs/msg/Path]
/robot_description [std_msgs/msg/String]
/rosout [rcl_interfaces/msg/Log]
/tf [tf2_msgs/msg/TFMessage]
/tf_static [tf2_msgs/msg/TFMessage]
```

A WSL-published low-speed forward command matched a robot subscriber and was followed by a stop:

```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.12}, angular: {z: 0.0}}' -r 10 -t 20 -w 1 --max-wait-time-secs 8 --keep-alive 0.5
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}' --once -w 1 --max-wait-time-secs 8 --keep-alive 0.5
```

The command printed all 20 forward messages and the final stop message from WSL. Physical wheel observation is still needed to confirm motor direction.
