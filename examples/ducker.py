import argparse
import time

from pyatem.command import SendFairlightLevelsCommand, FairlightStripPropertiesCommand
from pyatem.field import FairlightMeterLevelsField
from pyatem.protocol import AtemProtocol

switcher: AtemProtocol = None

release_timer = time.time()


def on_disconnected():
    print("Hardware has disconnected")
    exit(0)


def run(device, main, sidechain, threshold, mode, release=0.3, ratio=2, duck_level=-30):
    global switcher

    # Parse the channel index, for split channels the format can be 1.1 for the right channel instead of just 1
    if '.' in main:
        main_index, main_sub = map(int, main.split('.'))
        main_strip = main
    else:
        main_index = int(main)
        main_sub = -1
        main_strip = f'{main}.0'

    if '.' in sidechain:
        side_index, side_sub = map(int, sidechain.split('.'))
    else:
        side_index = int(sidechain)
        side_sub = 0

    def on_connected():
        global switcher

        print("Connection successful")
        model = switcher.mixerstate['product-name']
        print(f"Detected hardware: {model.name}")
        fw = switcher.mixerstate['firmware-version']
        print(f"Firmware: {fw}")
        print()

        # Trigger receiving audio channels
        cmd = SendFairlightLevelsCommand(True)
        switcher.send_commands([cmd])

    def on_levels(level: FairlightMeterLevelsField):
        global release_timer
        if level.index == side_index and level.subchannel == side_sub:
            # Grab the output peak level
            val = sum(level.output[0:2]) / 2.0

            if val > threshold:
                gr = val - threshold
                if mode == 'compress':
                    new_vol = -int(gr * 100)
                else:
                    new_vol = duck_level

                if new_vol < switcher.mixerstate['fairlight-strip-properties'][main_strip].volume:
                    cmd = FairlightStripPropertiesCommand(main_index, main_sub, volume=-int(gr * 100))
                    switcher.send_commands([cmd])
                release_timer = time.time()
            elif switcher.mixerstate['fairlight-strip-properties'][main_strip].volume < 0 and (
                    time.time() - release_timer) > release:
                cur = switcher.mixerstate['fairlight-strip-properties'][main_strip].volume
                new_vol = int((cur * 0.9) * 1)
                cmd = FairlightStripPropertiesCommand(main_index, main_sub, volume=new_vol)
                switcher.send_commands([cmd])

    print(f"Connecting to {device}...")
    switcher = AtemProtocol(device)
    switcher.on('connected', on_connected)
    switcher.on('disconnected', on_disconnected)
    switcher.on('change:fairlight-meter-levels:*', on_levels)
    switcher.connect()
    while True:
        switcher.loop()


def main():
    parser = argparse.ArgumentParser(description="Duck channel volume on incoming audio of other channels")
    parser.add_argument('device', help="Device ip address or 'usb'")
    parser.add_argument('main', help='Channel number for the channel that needs to be reduced in level')
    parser.add_argument('sidechain', help='Channel number for the detection channel')
    parser.add_argument('--threshold', type=float, default=-30.0, help='Trigger level on the detection channel')
    parser.add_argument('--mode', choices=['compress', 'duck'], help='Method for selecting the reduction level',
                        default='duck')
    parser.add_argument('--level', type=float, default=-30, help='Target level for duck mode')
    parser.add_argument('--release', type=float, default=300, help='Release time in milliseconds')
    args = parser.parse_args()
    run(args.device, args.main, args.sidechain, args.threshold, mode=args.mode, duck_level=args.level,
        release=args.release / 1000)


if __name__ == '__main__':
    main()
