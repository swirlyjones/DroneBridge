import argparse
import os
import subprocess

import pyric.pyw as pyw
import pyric.utils.hardware as iwhw
from subprocess import Popen
from socket import *

from CColors import CColors
from Chipset import is_atheros_card, is_realtek_card, is_ralink_card
from common_helpers import read_dronebridge_config, PI3_WIFI_NIC, HOTSPOT_NIC, get_bit_rate

COMMON = 'COMMON'
GROUND = 'GROUND'
UAV = 'AIR'
GND_STRING_TAG = 'DroneBridge GND: '
UAV_STRING_TAG = 'DroneBridge UAV: '
DRONEBRIDGE_BIN_PATH = os.path.join(os.sep, "root", "dronebridge")


def parse_arguments():
    parser = argparse.ArgumentParser(description='This script starts all DroneBridge modules. First setup the wifi '
                                                 'adapters.')
    parser.add_argument('-g', action='store_true', dest='gnd', default=False,
                        help='start modules running on the ground station - if not set we start modules for UAV')
    return parser.parse_args()


def start_gnd_modules():
    """
    Reads the settings from the config file. Performs some checks and starts the DroneBridge modules on the ground station.
    :return:
    """
    config = read_dronebridge_config()
    if config is None:
        exit(-1)
    communication_id = config.getint(COMMON, 'communication_id')
    cts_protection = config.get(COMMON, 'cts_protection')
    fps = config.getfloat(COMMON, 'fps')
    video_blocks = config.getint(COMMON, 'video_blocks')
    video_fecs = config.getint(COMMON, 'video_fecs')
    video_blocklength = config.getint(COMMON, 'video_blocklength')
    datarate = config.getint(GROUND, 'datarate')
    interface_selection = config.get(GROUND, 'interface_selection')
    interface_control = config.get(GROUND, 'interface_control')
    interface_tel = config.get(GROUND, 'interface_tel')
    interface_video = config.get(GROUND, 'interface_video')
    interface_comm = config.get(GROUND, 'interface_comm')
    interface_proxy = config.get(GROUND, 'interface_proxy')
    en_control = config.get(GROUND, 'en_control')
    en_video = config.get(GROUND, 'en_video')
    en_comm = config.get(GROUND, 'en_comm')
    en_plugin = config.get(GROUND, 'en_plugin')
    rc_proto = config.getint(GROUND, 'rc_proto')
    en_rc_overwrite = config.get(GROUND, 'en_rc_overwrite')
    port_smartphone_ltm = config.getint(GROUND, 'port_smartphone_ltm')
    comm_port_local = config.getint(GROUND, 'comm_port_local')
    proxy_port_local_remote = config.getint(GROUND, 'proxy_port_local_remote')
    joy_interface = config.getint(GROUND, 'joy_interface')
    fwd_stream = config.get(GROUND, 'fwd_stream')
    fwd_stream_port = config.getint(GROUND, 'fwd_stream_port')
    video_mem = config.get(GROUND, 'video_mem')

    # ---------- pre-init ------------------------
    print(GND_STRING_TAG + "Communication ID: " + str(communication_id))
    print(GND_STRING_TAG + "Trying to start individual modules...")
    if interface_selection == 'auto':
        interface_control = get_interface()
        print("Using: " + interface_control + " for all modules")
        interface_tel = interface_control
        interface_video = get_all_monitor_interfaces(True)
        interface_comm = interface_control
        interface_proxy = interface_control
    frametype = determine_frametype(cts_protection, get_interface())  # TODO: scan for WiFi traffic on all interfaces

    # ----------- start modules ------------------------
    print(UAV_STRING_TAG + "Starting ip checker module...")
    Popen(["python3 " + os.path.join(DRONEBRIDGE_BIN_PATH, 'communication', 'db_ip_checker.py')],
          shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_comm == 'Y':
        print(GND_STRING_TAG + "Starting communication module...")
        Popen(["python3 " + os.path.join(DRONEBRIDGE_BIN_PATH, 'communication', 'db_comm_ground.py') + " -n "
               + interface_comm+" -p 1604 -u "+str(comm_port_local) + " -m m -c "+str(communication_id)+" &"],
              shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    print(GND_STRING_TAG + "Starting status module...")
    Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'status', 'status') + " -n " + interface_tel
           + " -m m -c "+str(communication_id)+" &"], shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    print(GND_STRING_TAG + "Starting proxy & telemetry module...")
    Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'proxy', 'proxy') + " -n "+interface_proxy+" -m m -p "
           + str(proxy_port_local_remote)+" -c "+str(communication_id) + " -i "+interface_tel+" -l "
           + str(port_smartphone_ltm) + " -f " + str(frametype) + " -b " + str(get_bit_rate(datarate)) + " &"],
          shell=True, stdin=None, stdout=None,stderr=None, close_fds=True)

    if en_control == 'Y':
        print(GND_STRING_TAG + "Starting control module...")
        Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'control', 'control_ground') + " -n " + interface_control + " -j "
               + str(joy_interface)+" -m m -v "+str(rc_proto) + " -o "+en_rc_overwrite+" -c "
               + str(communication_id) + " -t " + str(frametype) + " -b " + str(get_bit_rate(datarate)) + " &"],
              shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_plugin == 'Y':
        print(GND_STRING_TAG + "Starting plugin module...")
        Popen(["python3 " + os.path.join(DRONEBRIDGE_BIN_PATH, 'plugin', 'db_plugin.py') + " -g &"], shell=True,
              stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_video == 'Y':
        print(GND_STRING_TAG + "Starting video module... (FEC: "+str(video_blocks)+"/"+str(video_fecs)+"/"+str(video_blocklength)+")")
        # db_video_receive = Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'legacy', 'rx') + " -p 0 -d 1 -b "+str(video_blocks)
        #                     + " -r "+str(video_fecs)+" -f " + str(video_blocklength)+" " + interface_video],
        #                     stdout=subprocess.PIPE, stdin=None, stderr=None, close_fds=True, shell=True)
        db_video_receive = Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'video_gnd') + " -d "+str(video_blocks)
                            + " -r "+str(video_fecs)+" -f " + str(video_blocklength) + " -c " + str(communication_id)
                             + " -p N -v " + str(fwd_stream_port) + " " + interface_video],
                            stdout=subprocess.PIPE, stdin=None, stderr=None, close_fds=True, shell=True)
        print(GND_STRING_TAG + "Starting video player...")
        Popen([get_video_player(fps)], stdin=db_video_receive.stdout, stdout=None, stderr=None, close_fds=True, shell=True)


def start_uav_modules():
    """
    Reads the settings from the config file. Performs some checks and starts the DroneBridge modules on the UAV.
    :return:
    """
    config = read_dronebridge_config()
    if config is None:
        exit(-1)
    communication_id = config.getint(COMMON, 'communication_id')
    cts_protection = config.get(COMMON, 'cts_protection')
    datarate = config.getint(UAV, 'datarate')
    interface_selection = config.get(UAV, 'interface_selection')
    interface_control = config.get(UAV, 'interface_control')
    interface_tel = config.get(UAV, 'interface_tel')
    interface_video = config.get(UAV, 'interface_video')
    interface_comm = config.get(UAV, 'interface_comm')
    en_control = config.get(UAV, 'en_control')
    en_video = config.get(UAV, 'en_video')
    en_comm = config.get(UAV, 'en_comm')
    en_plugin = config.get(UAV, 'en_plugin')
    en_tel = config.get(UAV, 'en_tel')
    video_blocks = config.getint(COMMON, 'video_blocks')
    video_fecs = config.getint(COMMON, 'video_fecs')
    video_blocklength = config.getint(COMMON, 'video_blocklength')
    extraparams = config.get(UAV, 'extraparams')
    keyframerate = config.getint(UAV, 'keyframerate')
    width = config.getint(UAV, 'width')
    heigth = config.getint(UAV, 'heigth')
    fps = config.getfloat(COMMON, 'fps')
    video_bitrate = config.get(UAV, 'video_bitrate')
    video_channel_util = config.getint(UAV, 'video_channel_util')
    serial_int_tel = config.get(UAV, 'serial_int_tel')
    tel_proto = config.get(UAV, 'tel_proto')
    baud_tel = config.getint(UAV, 'baud_tel')
    serial_int_cont = config.get(UAV, 'serial_int_cont')
    baud_control = config.getint(UAV, 'baud_control')
    serial_prot = config.getint(UAV, 'serial_prot')
    pass_through_packet_size = config.getint(UAV, 'pass_through_packet_size')
    enable_sumd_rc = config.get(UAV, 'enable_sumd_rc')
    serial_int_sumd = config.get(UAV, 'serial_int_sumd')

    # ---------- pre-init ------------------------
    if interface_selection == 'auto':
        interface_control = get_interface()
        interface_tel = interface_control
        interface_video = get_all_monitor_interfaces(True)
        interface_comm = interface_control
    frametype = determine_frametype(cts_protection, get_interface())  # TODO: scan for WiFi traffic on all interfaces
    if video_bitrate == 'auto' and en_video == 'Y':
        video_bitrate = int(measure_available_bandwidth(video_blocks, video_fecs, video_blocklength, frametype,
                                                    datarate, get_all_monitor_interfaces(False)))
        print(UAV_STRING_TAG + "Available bandwidth is " + str(video_bitrate / 1000) + " kbit/s")
        video_bitrate = int(video_channel_util/100 * int(video_bitrate))
        print(CColors.OKGREEN + UAV_STRING_TAG + "Setting video bitrate to " + str(video_bitrate/1000) + " kbit/s"
              + CColors.ENDC)

    # ---------- Error pre-check ------------------------
    if serial_int_cont == serial_int_tel and en_control == en_tel and en_control == 'Y':
        print(UAV_STRING_TAG + "Error - Control module and telemetry module are assigned to the same serial port. "
                               "Disabling telemetry module. Control module only supports MAVLink telemetry.")
        en_tel = 'N'
    if serial_int_cont == serial_int_sumd and en_control == 'Y' and enable_sumd_rc == 'Y':
        print(UAV_STRING_TAG + "Error - Control module and SUMD output are assigned to the same serial port. Disabling "
                               "SUMD.")
        enable_sumd_rc = 'N'
    print(UAV_STRING_TAG + "Communication ID: " + str(communication_id))
    print(UAV_STRING_TAG + "Trying to start individual modules...")

    # ----------- start modules ------------------------
    if en_comm == 'Y':
        print(UAV_STRING_TAG + "Starting communication module...")
        Popen(["python3 " + os.path.join(DRONEBRIDGE_BIN_PATH, 'communication', 'db_comm_air.py') + " -n " +
               interface_comm + " -m m -c " + str(communication_id) + " &"],
              shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_tel == 'Y':
        print(UAV_STRING_TAG + "Starting telemetry module...")
        Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'telemetry', 'telemetry_air') + " -n "+interface_tel+" -f "
               + serial_int_tel+" -r "+str(baud_tel)+" -t " + str(frametype) + " -m m -c " +
               str(communication_id) + " -l "+str(tel_proto) + " -b " + str(get_bit_rate(2)) + " &"],
              shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_control == 'Y':
        print(UAV_STRING_TAG + "Starting control module...")
        Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'control', 'control_air') + " -n " + interface_control + " -u "
               + serial_int_cont + " -m m -c "
               + str(communication_id) + " -v " + " -t " + str(frametype)
               + str(serial_prot) + " -l " + str(pass_through_packet_size) + " -r " + str(baud_control) + " -e "
               + enable_sumd_rc + " -s " + serial_int_sumd + " -b " + str(get_bit_rate(2)) + " &"],
              shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_plugin == 'Y':
        print(UAV_STRING_TAG + "Starting plugin module...")
        Popen(["python3 " + os.path.join(DRONEBRIDGE_BIN_PATH, 'plugin', 'db_plugin.py') + " &"], shell=True,
              stdin=None, stdout=None, stderr=None, close_fds=True)

    if en_video == 'Y':
        print(UAV_STRING_TAG + "Starting video transmission, FEC "+str(video_blocks)+"/"+str(video_fecs)+"/"
              + str(video_blocklength)+": "+str(width)+" x "+str(heigth)+" "+str(fps)+" fps, video bitrate: "
              + str(video_bitrate)+" bit/s, Keyframerate: " + str(keyframerate) + " frametype: "+str(frametype) + " "
              + get_all_monitor_interfaces(False))
        raspivid_task = Popen(["raspivid -w "+str(width)+" -h "+str(heigth)+" -fps "+str(fps)+" -b "+str(video_bitrate)
                              + " -g " + str(keyframerate)+" -t 0 "+extraparams+" -o -"], stdout=subprocess.PIPE,
                              stdin=None, stderr=None, close_fds=True, shell=True)
        Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'video_air') + " -d "+str(video_blocks)+" -r "
              + str(video_fecs)+" -f " + str(video_blocklength)+" -t "+str(frametype)+" -b "
              + str(get_bit_rate(datarate)) + " -c " + str(communication_id) + " " + interface_video],
              stdin=raspivid_task.stdout, stdout=None, stderr=None, close_fds=True, shell=True)
        # Popen([os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'legacy', 'tx_rawsock') + " -p 0 -b "+str(video_blocks)+" -r "
        #       + str(video_fecs)+" -f " + str(video_blocklength)+" -t "+str(video_frametype)+" -d "
        #       + str(get_bit_rate(datarate))+" -y 0 " + interface_video], stdin=raspivid_task.stdout, stdout=None,
        #       stderr=None, close_fds=True, shell=True)


def get_interface():
    """
    Find a possibly working wifi interface that can be used by a DroneBridge module
    :return: Name of an interface set to monitor mode
    """
    interface_names = pyw.winterfaces()
    for interface_name in interface_names:
        if interface_name != PI3_WIFI_NIC and interface_name != HOTSPOT_NIC:
            card = pyw.getcard(interface_name)
            if pyw.modeget(card) == 'monitor':
                return interface_name
    print("ERROR: Could not find a wifi adapter in monitor mode")
    exit(-1)


def get_all_monitor_interfaces(formated=False):
    """
    Find all possibly working wifi interfaces that can be used by a DroneBridge modules
    :param formated Formated to be used as input for WBC video module
    :return: List of names of interfaces set to monitor mode
    """
    w_interfaces = []
    interface_names = pyw.winterfaces()
    for interface_name in interface_names:
        if interface_name != PI3_WIFI_NIC and interface_name != HOTSPOT_NIC:
            card = pyw.getcard(interface_name)
            if pyw.modeget(card) == 'monitor':
                w_interfaces.append(interface_name)
    if formated:
        formated_str = ""
        for w_int in w_interfaces:
            formated_str = formated_str + " -n " + w_int
        return formated_str[1:]
    else:
        formated_str = ""
        for w_int in w_interfaces:
            formated_str = formated_str + " " + w_int
        return formated_str[1:]


def measure_available_bandwidth(video_blocks, video_fecs, video_blocklength, video_frametype, datarate, interface_video):
    print(CColors.OKGREEN + UAV_STRING_TAG + "Measuring available bitrate" + CColors.ENDC)
    tx_measure = Popen(os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'legacy', 'tx_measure') + " -p 77 -b "
                       + str(video_blocks)+" -r "+str(video_fecs)+" -f " + str(video_blocklength)+" -t "
                       + str(video_frametype)+" -d "+str(get_bit_rate(datarate))+" -y 0 " + interface_video,
                       stdout=subprocess.PIPE, shell=True, stdin=None, stderr=None, close_fds=True)
    return int(tx_measure.stdout.readline())


def get_video_player(fps):
    """
    mmormota's stutter-free implementation based on RiPis hello_video.bin: "hello_video.bin.30" (for 30fps) or
    "hello_video.bin.48" (for 48 and 59.9fps)
    befinitiv's hello_video.bin: "hello_video.bin.240" (for any fps, use this for higher than 59.9fps)
    :param fps: The video fps that is set in the config
    :return: The path to the video player binary
    """

    if fps == 30:
        return os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'pi_video_player', 'hello_video.bin.30')
    elif fps <= 60:
        return os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'pi_video_player', 'hello_video.bin.48')
    else:
        return os.path.join(DRONEBRIDGE_BIN_PATH, 'video', 'pi_video_player', 'hello_video.bin.240')


def exists_wifi_traffic(wifi_interface):
    """
    Checks for wifi traffic on a monitor interface
    :param wifi_interface: The interface to listen for traffic
    :return: True if there is wifi traffic
    """
    raw_socket = socket(AF_PACKET, SOCK_RAW, htons(0x0004))
    raw_socket.bind((wifi_interface, 0))
    raw_socket.settimeout(2)  # wait x seconds for traffic
    try:
        received_data = raw_socket.recv(2048)
        if len(received_data) > 0:
            print("Detected WiFi traffic on channel")
            return True
    except timeout:
        return False
    return False


def determine_frametype(cts_protection, interface_name):
    """
    Checks if there is wifi traffic.
    :param cts_protection: The value from the DroneBridgeConfig
    :param wifi_int: The interface to listen for traffic
    @:return 2 for data frames, 1 for RTS frames
    """
    print("Determining frametype...")
    wifi_driver = iwhw.ifdriver(interface_name)
    if is_ralink_card(wifi_driver):
        return 1  # TODO: injection with rt2800usb broken? Injects some packets and then stops
    elif is_realtek_card(wifi_driver):
        return 2  # use data frames (~1Mbps with rtl8814au an RTS)
    elif cts_protection == 'Y' and is_atheros_card(wifi_driver):
        return 2  # standard data frames
    elif cts_protection == 'auto':
        if is_atheros_card(wifi_driver) and exists_wifi_traffic(interface_name):
            return 2  # standard data frames
        else:
            return 1  # RTS frames
    else:
        return 1  # RTS frames


def main():
    parsed_args = parse_arguments()
    if parsed_args.gnd:
        start_gnd_modules()
    else:
        start_uav_modules()


if __name__ == "__main__":
    main()

