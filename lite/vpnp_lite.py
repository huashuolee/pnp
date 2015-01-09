#!/usr/bin/python
# -*- encoding = utf8 -*-
# develop
import socket
import time
import datetime
import os
import sys
import signal

import thread
from multiprocessing import Pool

from prints import *
import vpnp_config

def net_send(obj_socket, data) :
    print_msg('F','net_send called. send data = %s'%data)
    if isinstance(obj_socket, socket.socket) == False :
        print_msg('E', 'Variable is not a socket instance')
        return False
    obj_socket.send(data)
    recvdata = client_socket.recv(1024)
    if recvdata != data :
        print_msg('E','Recv[%s] != Send[%s]'%(recvdata, data))
        return False
    else :
        return True


def monsoon_power_on() :
    global client_socket
    print_msg('F', 'monsoon power on')
    data = 'PMON_ON#'
    net_send(client_socket, data)
    time.sleep(1)


def monsoon_power_off() :
    global client_socket
    print_msg('F', 'monsoon power off')
    data = 'PMON_OFF#'
    net_send(client_socket, data)
    time.sleep(1)


def is_usb_on() :
    global client_socket
    print_msg('F', 'is_usb_on called')
    adb_state = os.popen("adb get-state")
    dev_state = adb_state.read().strip()
    if dev_state == "device" :
        print_msg('M','[USB STATE] USB ON')
        return True
    else :
        print_msg('M','[USB STATE] USB OFF')
        return False


def usb_on() :
    global client_socket
    print_msg('F', 'usb_on called')
    if is_usb_on() == True :
        return
    else:
        data = "USB_ON#"
        net_send(client_socket, data)
        time.sleep(3)


def usb_off() :
    global client_socket
    print_msg('F','usb_off called')
    if is_usb_on() == False :
        return
    else :
        data = "USB_OFF#"
        net_send(client_socket, data)
        time.sleep(3)


def usb_toggle(dest_usb_state, try_time):
    print_msg('F',"USB TOGGLE  TARGET: %s  TRY_TIME: %s"%(dest_usb_state, try_time))
    trytime = try_time
    if is_usb_on() == dest_usb_state :
        print_msg('M', 'USB is Already %s'%dest_usb_state)
        return True

    while is_usb_on() != dest_usb_state :
        if(dest_usb_state == True) :
            usb_off()
            usb_on()
        else :
            usb_on()
            usb_off()
        if trytime > 0 :
            trytime -= 1
        else :
            # Failed
            print_msg('M','Failed to Toggle USB state to %s'%dest_usb_state)
            return False
    # Toggle success
    print_msg('M','Succeed to toggle USB state to %s'%dest_usb_state)
    return True


def is_device_on() :
    print_msg('F','is_device_on called')
    if is_usb_on() == True :
        adb_ro = os.popen("adb shell getprop ro.bootmode")
        bootmode = adb_ro.read()
        bootmode = bootmode.strip()
        if bootmode == "charger" :
            print_msg('M', 'CHARGER Mode Detect')
            device_state = "CHARGER"
        elif bootmode == "main" :
            print_msg('M', 'ACTIVE Mode Detect')
            device_state = "ACTIVE"
        else :
            print_msg('M', 'UNKNOWN Mode Detect')
            device_state = "UNKNOWN"
    else :
        print_msg('A', 'USB is off, connect USB before check device state')
        device_state = "USBOFF"
    return device_state


def device_adb_reboot(sec) :
    global client_socket
    print_msg('F','is_device_on called')
    print_msg('M','Adb Reboot')
    os.popen("adb reboot");
    print_msg('M','Waiting %s seconds...'%sec)
    time.sleep(sec)


def get_cases_list(case_filename) :
    print_msg('F', 'get_cases_list called')
    if os.path.exists(case_filename) == False :
        print_msg('E', 'case_file [%s] not exist'%case_filename)
        return False
    with open(case_filename,'r') as case_file :
        all_lines = case_file.readlines()

    cases = list()
    for line in all_lines :
        line = line.strip()
        if line != "" and line[0] != '#' :
            print line
            cases.append(line)
    return cases


def print_case(case_dict) :
    print "***"*15,' CASE DETAIL ','***' * 14
    print "Case Name      : %-20s   Case KPI     : %-15s   Case Count : %-5s   Case Time: %-5s    Case Path: %s"%(
            case_dict['case_name'], case_dict['case_kpi'], case_dict['case_count'], case_dict['case_time'], case_dict['case_path'])
    print "Collect SocData: %-20s   SOCWatch Time: %-15s   SOCWATCH BW: %-10s"%(
            case_dict['collect_socdata'], case_dict['socwatch_time'], case_dict['socwatch_bw'])
    if case_dict['collect_socdata'] == False :
        print_msg('A', 'Param socwatch_time[%s] and socwatch_bw[%s] are ignored'%(case_dict['socwatch_time'], case_dict['socwatch_bw']))
    print "Collect Power  : %-20s   Monsoon Time : %-15s   With USB: %s "%(case_dict['collect_power'], case_dict['monsoon_time'], case_dict['with_usb'])
    if case_dict['collect_power'] == False :
        print_msg('A', 'Param Monsoon Time[%s] ignored'%(case_dict['monsoon_time']))
    print "Self-define 1  : %-20s   Self-define 2: %-20s"%(case_dict['self-define1'], case_dict['self-define2'])
    print "Enable HB      : %-20s "%case_dict['enable_hb']
    print "Media File     : %s"%case_dict['media_file']
    print "***"*34


def get_case_detail(case_string) :
    print_msg('F', 'get_case_detail called')
    case = {}
    case_detail = case_string.split('|')
    case['case_name']       = case_detail[0]
    case['case_kpi']        = case_detail[1]
    case['case_count']      = int(case_detail[2])
    case['case_path']       = case_detail[3]
    case['case_time']       = int(case_detail[4])
    case['collect_socdata'] = case_detail[5] == str(True)
    case['socwatch_time']   = int(case_detail[6])
    case['socwatch_bw']     = case_detail[7]
    case['collect_power']   = case_detail[8] == str(True)
    case['monsoon_time']    = int(case_detail[9])
    case['with_usb']        = case_detail[10] == str(True)
    case['media_file']      = case_detail[11]
    case['enable_hb']       = case_detail[12] == str(True)
    case['self-define1']    = case_detail[13]
    case['self-define2']    = case_detail[14]
    print_case(case)
    return case


def socwatch_start(cases_id, single_case_id, case_detail) :
    print_msg('F', 'socwatch_start() Called')
    print_msg('M', 'CASE NAME : %s CASE KPI: %s CASES_ID = %s SINGLE CASE ID = %s'%(case_detail['case_name'] , case_detail['case_kpi'], cases_id, single_case_id))
    socwatch_filename = "%s_%s_%s_%s"%(case_detail['case_name'], case_detail['case_kpi'], cases_id, single_case_id)
    os.system('socwatch/socwatch_start.sh %s %s %s'%(socwatch_filename, case_detail['socwatch_time'], case_detail['socwatch_bw']))
    time.sleep(8)  #DELAY TIME FOR SOCWATCH EXECUTION
    print_msg('M', 'socwatch_filename = %s'%socwatch_filename)


def monsoon_collect_power(cases_id, single_case_id, case_detail) :
    global client_socket
    print_msg('F', 'monsoon run() called')
#data = "MOSOON_RUN#%s#%s_%s#%s#%s#%s#"%(case_detail['monsoon_time'], case_detail['case_name'], case_detail['case_kpi'], cases_id, case_detail['case_count'], single_case_id)
    case_name_kpi = "%s_%s_%s"%(case_detail['case_name'], case_detail['case_kpi'], case_detail['socwatch_bw'])
    data = "MOSOON_RUN#%s#%s#%s#%s#%s#"%(case_detail['monsoon_time'], case_name_kpi, cases_id, case_detail['case_count'],single_case_id)
    print_msg('M', data)
    net_send(client_socket, data)


def single_case_setup(case_detail) :
    print_msg('A', 'single_case_setup() called')
    sd1 = case_detail['self-define1'].split('_')
    sd2 = case_detail['self-define2'].split('_')
    print_msg('M', 'self-define 1: [%s]=>%s  self-define 2: [%s]=>%s'%(sd1[0], sd1[1], sd2[0], sd2[1]))
    os.system('%s_setup %s %s %s %s'%(case_detail['case_path'], case_detail['case_name'], case_detail['case_kpi'], sd1[1], sd2[1]))
    print('%s_setup %s %s %s %s'%(case_detail['case_path'], case_detail['case_name'], case_detail['case_kpi'], sd1[1], sd2[1]))
    print_msg('M', 'single_case_setup() finished')


def single_case_start(case_detail) :
    print_msg('F','single_case_start() called')
    sd1 = case_detail['self-define1'].split('_')
    sd2 = case_detail['self-define2'].split('_')
    print_msg('F', 'self-define 1: [%s]=>%s  self-define 2: [%s]=>%s'%(sd1[0], sd1[1], sd2[0], sd2[1]))
    os.system('%s_start %s %s %s %s %s'%(case_detail['case_path'], case_detail['case_name'], case_detail['case_kpi'], sd1[1], sd2[1], case_detail['media_file']))
    print_msg('F', 'single_case_start() finished')


def single_case_stop(case_detail) :
    print_msg('F','single_case_stop ')
    sd1 = case_detail['self-define1'].split('_')
    sd2 = case_detail['self-define2'].split('_')
    print_msg('M', 'self-define 1: [%s]=>%s  self-define 2: [%s]=>%s'%(sd1[0], sd1[1], sd2[0], sd2[1]))
    os.system('%s_stop %s %s %s %s'%(case_detail['case_path'], case_detail['case_name'], case_detail['case_kpi'], sd1[1], sd2[1]))
    print_msg('M', 'single_case_stop() finished')


def RLB_run(rlb_filename) :
    global client_socket
    print_msg('F', 'RLB_run()')
    data = 'RLB_RUN#%s#'%rlb_filename
    net_send(client_socket, data)
    time.sleep(1)


def run_single_case(cases_id, single_case_id, case_detail) :
    print_msg('F','run_single_case() cases_id = %s  case name = [%s] single_case_id = %s '%(cases_id, case_detail['case_name'], single_case_id))
    # heartbeat check ignored in lite version
    print_msg('A', 'usb_toggle() called')
    usb_toggle(True, 5)
    raw_input("PRESS ANY KEY TO CONTINUE:")
    single_case_setup(case_detail)
    print_msg('D','case setup done')

    single_case_start(case_detail)
    print_msg('D','case start done')

    if case_detail['collect_socdata'] :
        socwatch_start(cases_id, single_case_id, case_detail)
        print_msg('D','socwatch start time: %s  bandwidth:%s'%(case_detail['socwatch_time'], case_detail['socwatch_bw']))

    if case_detail['with_usb'] == False :
        usb_toggle(False, 5)

    sd1 = case_detail['self-define1'].split('_')
    if sd1[1] == "RLB" :
        h_m = time.strftime('%H_%m', time.localtime(time.time()))
        rlb_file_name = "%s_%s_%s"%(case_detail['case_name'], case_detail['case_kpi'], h_m)
        RLB_run(rlb_file_name)
#        RLB_run()

    start_time = datetime.datetime.now()
    if case_detail['collect_power'] :
        # if you collect power, the usb will toggle to false (usb off)
        monsoon_collect_power(cases_id, single_case_id, case_detail)
        print_msg('D','monsoon start, collect %s seconds'%case_detail['monsoon_time'])
        cur_time = datetime.datetime.now()
        while (cur_time - start_time).seconds < case_detail['case_time'] :
            time.sleep(5)
            cur_time = datetime.datetime.now()
    else :
        cur_time = datetime.datetime.now()
        while (cur_time - start_time).seconds < case_detail['case_time'] :
            time.sleep(5)
            cur_time = datetime.datetime.now()

    usb_toggle(True, 5)
    single_case_stop(case_detail)
    print_msg('D','case stop start')

    if case_detail['collect_socdata'] :
        print_msg('M','Sleep 50s to let socwatch collect data')
        time.sleep(50)

def run_single_case_loop(cases_id, case_detail) :
    global client_socket
    print_msg('F','run_single_case_loop  [cases_id=%s] called'%cases_id)
    single_case_id = 1

    while True :
        if single_case_id > case_detail['case_count'] :
            break

        if usb_toggle( True , 5 ) :
            dev_state = is_device_on()
            if dev_state == "ACTIVE" or dev_state == "CHARGER":
                device_adb_reboot(60)
                run_single_case(cases_id, single_case_id, case_detail)
                single_case_id += 1
            elif dev_state == "USBOFF" :
                print_msg('A',
'''
    usb state: usb off
    case stopped!
    case_name: %s   case_kpi: %s   case id: %s
'''%(case_detail['case_name'], case_detail['case_kpi'], single_case_id))
                sys.exit(0)
            else :
                print_msg('A',
'''
    device state : unknow
    case stopped!
    case_name: %s   case_kpi: %s   case id: %s
'''%(case_detail['case_name'], case_detail['case_kpi'], single_case_id))
                device_adb_reboot(60)
                run_single_case(cases_id, single_case_id, case_detail)
                single_case_id += 1
#                sys.exit(0)


def pull_data() :
    print_msg('F','pull data() called')
    cur_time = time.strftime("%Y%m%d_%H_%M", time.localtime())
    base_dir = "data"
    if os.path.exists(base_dir) == False :
        print_msg('M', 'BASE DIR : %s '%base_dir)
        os.makedirs(base_dir)

    path = "data/Batch_%s"%cur_time
    if os.path.exists(path) == False :
        print_msg('M', 'PATH : %s '%path)
        os.makedirs(path)

    os.system('./socwatch/data_process.sh %s'%path)


def run_all_cases(obj_vpnpconfig, case_filename) :
    global client_socket
    print_msg('F','run_all_cases() called')
    cases_list = get_cases_list(case_filename)
    cases_id = 0
    print_msg('M','run case count: %s'%obj_vpnpconfig.run_case_count)
    while cases_id < obj_vpnpconfig.run_case_count :
        for case_string in cases_list :
            case_detail = get_case_detail(case_string)
            run_single_case_loop(cases_id, case_detail)
        cases_id += 1
    
    pull_data()

def usage() :
    print '''
Usage :
    python %s [PARAMETERS]

[PARAMETERS]
    runcases    run all cases defined in cases_file
    poweron     Monsoon power enable
    poweroff    Monsoon power disable
    usbon       Toggle USB to USBON
    usboff      Toggle USB to USBOFF
'''%sys.argv[0]


def params(obj_vpnpconfig, cases_filename) :
    print_msg('F', 'params() called')
    if len(sys.argv) == 2 :
        if sys.argv[1].lower() == 'poweron' :
            monsoon_power_off()
            monsoon_power_on()
        elif sys.argv[1].lower() == 'poweroff' :
            monsoon_power_off()
        elif sys.argv[1].lower() == 'runcases' :
            run_all_cases(obj_vpnpconfig, cases_filename)
        elif sys.argv[1].lower() == 'usbon' :
            usb_toggle(True, 5)
        elif sys.argv[1].lower() == 'usboff' :
            usb_toggle(False, 5)
        else :
            usage()
            sys.exit(0)
    else :
        usage()
        sys.exit(0)


###################
#    main entry   #
###################
if __name__ == '__main__' :
    obj_vpnpconfig = vpnp_config.vpnpConfig('client.conf')
    obj_vpnpconfig.get_configs()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(30000)
    print obj_vpnpconfig.server,obj_vpnpconfig.port
    client_socket.connect((obj_vpnpconfig.server, obj_vpnpconfig.port))
    client_socket.settimeout(None)

    print_msg('M', 'connected to server [%s]'%obj_vpnpconfig.server)

    params(obj_vpnpconfig, 'cases.conf')

    # close server
    client_socket.shutdown(socket.SHUT_RDWR)
    client_socket.close()
    print_msg('M', 'server [%s] closed'%obj_vpnpconfig.server)
    sys.exit(0)
