#!/usr/bin/python
# -*- coding: utf-8 -*-

# TODO: Replace XplPlugin by Plugin class when domogik plugintestcase will handle non xpl
from domogik.common.plugin import Plugin
from domogik.xpl.common.plugin import XplPlugin
from domogik.tests.common.plugintestcase import PluginTestCase
from domogik.tests.common.testplugin import TestPlugin
from domogik.tests.common.testdevice import TestDevice
from domogik.tests.common.testsensor import TestSensor
from domogik.common.utils import get_sanitized_hostname

import zmq
from zmq.eventloop.ioloop import IOLoop
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

from datetime import datetime
import time
import unittest
import sys
import os
import traceback
import subprocess

class ZwaveCtrlTestCase(PluginTestCase):

    def test_0100_ctrl_status(self):
        """ check if all the xpl messages for an inbound call is sent
            Example :
            Sample messages :

            xpl-trig : schema:cid.basic, data:{'calltype': 'inbound', 'phone' : '0102030405'}
        """
        global networkid
        global driver
        global device_id
        global timer_status

        r = subprocess.check_output('ps aux | grep ozwave', shell=True)
        print (u"----- Process : {0}".format(r))

        r = subprocess.check_output('ps aux', shell=True)
        print (u"----- ALL Process : {0}".format(r))

        data = {"ctrl-status" : 1}
        self.assertTrue(self.wait_for_mq(device_id = device_id,
                                          data = data,
                                          timeout = timer_status * 2))
        time.sleep(1)
        print(u"Check that the values of the MQ message has been inserted in database")
        sensor = TestSensor(device_id, "ctrl-status")
        self.assertTrue(sensor.get_last_value()[1] == str(data['ctrl-status']))


if __name__ == "__main__":

    r = subprocess.check_output('ps aux | grep ozwave', shell=True)
    print r

    test_folder = os.path.dirname(os.path.realpath(__file__))

    ### global variables
    # the key will be the device address
    networkid = "ZwaveNetwork",
    driver = "/tmp/ttyS0"

    ### configuration

    # set up the plugin features
#    plugin = Plugin(name = 'test',
# TODO: To replace by Plugin class when domogik plugintestcase will handle non xpl
    plugin = XplPlugin(name = 'test',
                       daemonize = False,
                       parser = None,
                       test  = True)

    # set up the plugin name
    name = "ozwave"

    # set up the configuration of the plugin
    # configuration is done in test_0010_configure_the_plugin with the cfg content
    # notice that the old configuration is deleted before
    cfg = { 'configured' : True,
                'autoconfpath': "Y",
                'configpath': "/",
                'cpltmsg': "Y",
                'ozwlog': "Y"
            }

    # specific configuration for test mdode (handled by the manager for plugin startup)
    cfg['test_mode'] = True
    cfg['test_option'] = "None" # "{0}/data.json".format(test_folder)

    ### start tests

    # load the test devices class
    td = TestDevice()

    # delete existing devices for this plugin on this host
    client_id = "{0}-{1}.{2}".format("plugin", name, get_sanitized_hostname())
    try:
        td.del_devices_by_client(client_id)
    except:
        print(u"Error while deleting all the test device for the client id '{0}' : {1}".format(client_id, traceback.format_exc()))
#        sys.exit(1)

    # create a test device
    try:
#        params = td.get_params(client_id, "ozwave.primary_controller")
# TODO: To replace by td.get_params when domogik testcase will use MQ
        cli = MQSyncReq(zmq.Context())
        msg = MQMessage()
        msg.set_action('device.params')
        msg.set_data({'device_type': 'ozwave.primary_controller', 'client_id': client_id})
        response = cli.request('admin', msg.get(), timeout=15)
        if response is not None:
            response = response.get_data()
            if 'result' in response :
                print(u"{0} : The params are: {1}".format(datetime.now(), response['result']))
                params = response['result']
            else :
                print("Error when getting devices param for {0} : {1}".format(client_id, response))
        else :
            print("Error when getting devices param for {0}".format(client_id))

        # fill in the params
        params["device_type"] = "ozwave.primary_controller"
        params["name"] = "Test Ctrl Zwave"
        params["reference"] = "reference"
        params["description"] = "description"
        # global params
        for the_param in params['global']:
            if the_param['key'] == "networkid":
                the_param['value'] = networkid
            if the_param['key'] == "driver":
                the_param['value'] = driver
        # xpl params
        pass # there are no xpl params for this plugin
        # create
#        device_id = td.create_device(params)['id']
# TODO: To replace by td.create_device when domogik testcase will use MQ
        msg = MQMessage()
        msg.set_action('device.create')
        msg.set_data({'data': params})
        response = cli.request('admin', msg.get(), timeout=20)
        if response is not None:
            response = response.get_data()
            if 'result' in response :
                print(u"{0} : The new device is: {1}".format(datetime.now(), response['result']))
                device_id =  response['result']
            else :
                print("Error when creating the device : {0} : {1}".format(params, response))
        else :
            print("Error when creating the device : {0}".format(params))

    except:
        print(u"Error while creating the test devices : {0}".format(traceback.format_exc()))
        plugin.force_leave(return_code = 1)
        sys.exit(1)
    ### prepare and run the test suite
    suite = unittest.TestSuite()
    # check domogik is running, configure the plugin
    suite.addTest(ZwaveCtrlTestCase("test_0001_domogik_is_running", plugin, name, cfg))
    suite.addTest(ZwaveCtrlTestCase("test_0010_configure_the_plugin", plugin, name, cfg))

    # start the plugin
    suite.addTest(ZwaveCtrlTestCase("test_0050_start_the_plugin", plugin, name, cfg))

    # do the specific plugin tests
    # test zwave ctrl start step
    suite.addTest(ZwaveCtrlTestCase("test_0100_ctrl_status", plugin, name,  cfg))

    # do some tests comon to all the plugins
    #suite.addTest(ZwaveCtrlTestCase("test_9900_hbeat", plugin, name, cfg))
    suite.addTest(ZwaveCtrlTestCase("test_9990_stop_the_plugin", plugin, name, cfg))

    # quit
    res = unittest.TextTestRunner().run(suite)
    if res.wasSuccessful() == True:
        rc = 0   # tests are ok so the shell return code is 0
    else:
        rc = 1   # tests are not ok so the shell return code is != 0
    plugin.force_leave(return_code = rc)
