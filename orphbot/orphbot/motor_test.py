import argparse
import time


def pin_pair(name):
    pins = {
        'left_front': (5, 6),
        'left_rear': (13, 19),
        'right_front': (20, 21),
        'right_rear': (23, 24),
    }
    return pins[name]


def set_pair(forward, reverse, speed):
    if speed > 0:
        forward.value = speed
        reverse.value = 0.0
    elif speed < 0:
        forward.value = 0.0
        reverse.value = -speed
    else:
        forward.value = 0.0
        reverse.value = 0.0


def main():
    parser = argparse.ArgumentParser(description='Test one OrphBot motor channel on real GPIO.')
    parser.add_argument('motor', choices=['left_front', 'left_rear', 'right_front', 'right_rear'])
    parser.add_argument('--pwm', type=float, default=0.55)
    parser.add_argument('--seconds', type=float, default=1.5)
    parser.add_argument('--pause', type=float, default=0.8)
    parser.add_argument('--reverse-first', action='store_true')
    args = parser.parse_args()

    pwm = max(0.0, min(1.0, args.pwm))
    first = -pwm if args.reverse_first else pwm
    second = pwm if args.reverse_first else -pwm
    fwd_pin, rev_pin = pin_pair(args.motor)

    from gpiozero import PWMOutputDevice
    from gpiozero.pins.lgpio import LGPIOFactory

    factory = LGPIOFactory()
    forward = PWMOutputDevice(fwd_pin, pin_factory=factory)
    reverse = PWMOutputDevice(rev_pin, pin_factory=factory)

    try:
        print(f'testing {args.motor}: pins {fwd_pin}/{rev_pin}, pwm={pwm:.2f}')
        print('phase 1')
        set_pair(forward, reverse, first)
        time.sleep(args.seconds)
        print('stop')
        set_pair(forward, reverse, 0.0)
        time.sleep(args.pause)
        print('phase 2')
        set_pair(forward, reverse, second)
        time.sleep(args.seconds)
    finally:
        print('stop')
        set_pair(forward, reverse, 0.0)
        forward.close()
        reverse.close()


if __name__ == '__main__':
    main()
