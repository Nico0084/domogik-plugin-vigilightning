#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ######################################
NETWORK_ID = "ZwaveNetwork"
DRIVER="/tmp/ttyS0"
##################################################

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

plugin =  "vigilightning"

def create_device():
    ### create the device, and if ok, get its id in device_id
    print(u"Creating the vigilocation device...")
    td = TestDevice()
    td.create_device("plugin", plugin, get_sanitized_hostname(), "test_vigilocation", "vigilightning.vigilocation")
    td.configure_global_parameters({"latitude " : "46.739868", "longitude" : "2.328084",
                "criticalradius" : 1, "nearbyradius" : 3, "approachradius" : 5,
                "releasetimes" : 3})
    print "Device vigilocation configured"

if __name__ == "__main__":
    create_device()
