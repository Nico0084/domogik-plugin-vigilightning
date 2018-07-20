#!/usr/bin/python
# -*- coding: utf-8 -*-

import zmq
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

from domogik.xpl.common.plugin import Plugin
#from domogik.tests.common.helpers import Printc
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor
from domogik.common.utils import get_sanitized_hostname
from datetime import datetime
import unittest
import sys
import os
import json
import traceback
# TODO : remove
import time

class VigilightningTestCase(PluginTestCase):

    def __init__(self, testname, plugin, name, configuration, sensorsTest=[]):
        PluginTestCase.__init__(self, testname, plugin, name, configuration)
        self.sensorsTest = sensorsTest

    def test_0100_dummy(self):
        self.assertTrue(True)

    def test_0100_wsconnection(self):
        """ Test if the websocket connection to blitzortung.org is ok
        """
        global client_id
        global device
        global device_id

        self.testDevices = []

        # do the test
#        Printc.infob(u"Check that a websocket is connected to data server.")
        print(u"Check that a websocket is connected to data server.")
        action, resData = get_request(client_id, "vigilightning.plugin.getwsstatus", {})
        self.assertEqual(resData['Error'], "")
        self.assertTrue(resData['Connected'])
        self.assertNotEqual(resData['State'], "")
        time.sleep(1)

    def test_0110_device_sensors(self):
        """ Test if the LocationPoint sensor is sent when plugin is started
        """
        global device_id

#        Printc.infob(u"Check that the values of the MQ message has been inserted in database")
        data = {"LocationPoint" : "46.739868,2.328084"}
        print(u"Check that the values of the MQ message has been inserted in database")
        sensor = TestSensor("{0}".format(device_id), "LocationPoint")
#        just to fix issue on get sensor id
        sensor.sensor_id = 1
        print(u"Sensor selected : {0} / {1}, ".format(sensor.sensor_id, sensor.sensor_reference))
        self.assertTrue(sensor.get_last_value()[1] == str(data['LocationPoint']))

def createDevice(dataJson):
    td = TestDevice()
    # create a test device
    try:
        params = td.get_params(client_id, dataJson["device_type"])
        # fill in the params
        params["device_type"] = dataJson["device_type"]
        params["name"] = dataJson['name']
        params["reference"] = "reference"
        params["description"] = "description"
        # global params
        for the_param in params['global']:
            for p in dataJson["parameters"] :
                if the_param["key"] == p["key"] :
                    the_param["value"] = p["value"]
                    break
        print params['global']
        # xpl params
        pass # there are no xpl params for this plugin
        # create
        return td.create_device(params)['id'], td
    except:
#        Printc.err(u"Error while creating the test devices {0} : {1}".format(device, traceback.format_exc()))
        print(u"Error while creating the test devices {0} : {1}".format(device, traceback.format_exc()))
        return False, td


def get_request(client_id, action, data):
    resData = {u'error': u'', u'data': {}}
    cli = MQSyncReq(zmq.Context())
    msg = MQMessage()
    msg.set_action(action)
    for key in data:
        msg.add_data(key, data[key])
    res = cli.request(client_id, msg.get(), timeout=10)
    if res is not None:
        resData = res.get_data()
        action = res.get_action()
    else : resData['error'] =  u'Plugin timeout response on request : {0}.'.format(action)
    return action, resData

if __name__ == "__main__":

    test_folder = os.path.dirname(os.path.realpath(__file__))

    ### global variables
    wssource = "ws.blitzortung.org"
    checktimes = "3"

    # set up the features
    plugin = Plugin(name = 'test',
                   daemonize = False,
                   parser = None,
                   test  = True)

    Plugin.myxpl = None # fix for non xpl plugin at PluginTestCase__init__

    # set up the plugin name
    name = "vigilightning"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = {'configured': True, 'auto_startup': 'N', "wssource": wssource," checktimes": checktimes}

    # specific configuration for test mdode (handled by the manager for plugin startup)
    cfg['test_mode'] = True
#    cfg['test_option'] = "{0}/x10_protocol_data.json".format(test_folder)

    ### start tests
    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except:
#        Printc.err(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        print(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
        sys.exit(1)

    # create a test device
    try:
        #device_id = td.create_device(client_id, "test_device_RFPlayer", "RFPlayer.electric_meter")

        params = td.get_params(client_id, "vigilocation")

        # fill in the params
        params["device_type"] = "vigilocation"
        params["name"] = "test_vigilocation"
        params["reference"] = "reference"
        params["description"] = "description"
        # global params
        for the_param in params['global']:
            if the_param['key'] == "latitude":
                the_param['value'] = "46.739868"
            elif the_param['key'] == "longitude":
                the_param['value'] = "2.328084"
            elif the_param['key'] == "criticalradius":
                the_param['value'] = 1
            elif the_param['key'] == "nearbyradius":
                the_param['value'] = 3
            elif the_param['key'] == "approachradius":
                the_param['value'] = 5
            elif the_param['key'] == "releasetimes":
                the_param['value'] = 3
        print params['global']
        # xpl params
        pass # there are no xpl params for this plugin
        # create
        device_id = td.create_device(params)['id']

    except:
#        Printc.err(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        print(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        sys.exit(1)

    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(VigilightningTestCase("test_0001_domogik_is_running", plugin, name, cfg))
    suite.addTest(VigilightningTestCase("test_0010_configure_the_plugin", plugin, name, cfg))

    # start the plugin
    suite.addTest(VigilightningTestCase("test_0050_start_the_plugin", plugin, name, cfg))

    # do the specific plugin tests
    suite.addTest(VigilightningTestCase("test_0100_wsconnection", plugin, name, cfg))

    # do the specific device tests
#    jsonFile = "x10_protocol_result.json"
#    try:
#        json_fp = open("{0}/{1}".format(test_folder, jsonFile))
#        dataJson = json.load(json_fp)
#        Printc.infob(u"Data for specific tests are loaded from {0}".format(jsonFile))
#        json_fp.close()
#    except:
#        Printc.err(u"Error while loading json tests {0} : {1}".format("{0}/{1}".format(test_folder, jsonFile), traceback.format_exc()))
#    else :
#        for device in dataJson :
#            dev_id, td = createDevice(device)
#            device['device_id'] = dev_id
#            time.sleep(5) # due to high DB flow, wait 5s
#        suite.addTest(VigilightningTestCase("test_0110_device_sensors", plugin, name, cfg, dataJson))

    suite.addTest(VigilightningTestCase("test_0110_device_sensors", plugin, name, cfg))

# do some tests comon to all the plugins
    #suite.addTest(VigilightningTestCase("test_9900_hbeat", plugin, name, cfg))
    suite.addTest(VigilightningTestCase("test_9990_stop_the_plugin", plugin, name, cfg))

    # quit
    res = unittest.TextTestRunner().run(suite)
    if res.wasSuccessful() == True:
        rc = 0   # tests are ok so the shell return code is 0
    else:
        rc = 1   # some tests are fail so the shell return code is != 1
    plugin.force_leave(return_code = rc)

