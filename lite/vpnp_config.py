#!/usr/bin/python
# -*- encoding = utf8 -*-

from ConfigParser import ConfigParser
import os
from prints import *

class vpnpConfig() :
    def __init__(self, filename) :
        print_msg('F','vpnpConfig __init__ called')

        if os.path.exists(filename) == False :
            raise ValueError('Failed to create vpnpConfig Instance: File %s not exist'%filename)
        else :
            self.filename = filename
            pass
        print_msg('C','vpnpConfig class Initialized')


    def get_configs(self) :
        print_msg('F',"vpnpConfig get_configs called")
        self.config = ConfigParser()
        with open(self.filename,'r') as cfgfile :
            self.config.readfp(cfgfile)
            self.server             = self.config.get('config', 'server')
            self.port               = int(self.config.get('config', 'port'))
            self.auto_flash_count   = self.config.get('config', 'auto_flash_count')
            self.run_case_count     = int(self.config.get('config', 'run_case_count'))
            self.flash_only         = self.config.get('config', 'flash_only')  == str(True)
            self.run_case_only      = self.config.get('config', 'run_case_only') == str(True)
            self.auto_mode          = self.config.get('config', 'auto_mode') == str(True)
            self.bootType           = self.config.get('config', 'bootType')
            self.platform           = self.config.get('config', 'platform')
            self.dpst               = self.config.get('config', 'dpst')

            self.s_port             = self.config.get('serial', 'port')
            self.s_baudrate         = int(self.config.get('serial', 'baudrate'))

            self.cam_device         = self.config.get('camera', 'device')
            self.cam_width          = int(self.config.get('camera', 'width'))
            self.cam_height         = int(self.config.get('camera', 'height'))

            self.hb_serial          = self.config.get('heartbeat', 'serial')
            self.hb_camera          = self.config.get('heartbeat', 'camera')

    def __del__(self) :
        # Can not call print_msg here,
        #Since python does not guarantees print_msg will delete after Class __del__
        #print_msg('C',"vpnpConfig Object deleted")
        print "vpnpConfig Object deleted"


#if __name__ ==  '__main__' :
#    obj_vpnpConf = vpnpConfig('client.conf')
#    obj_vpnpConf.get_configs()
