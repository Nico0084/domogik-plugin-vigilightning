#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Vigilightning

Implements
==========

- VigilightningManager

"""

from domogik.common.plugin import Plugin
from domogikmq.message import MQMessage
from domogik_packages.plugin_vigilightning.lib.vigilightning import VigiLocation
from ws4py.client.threadedclient import WebSocketClient
import random
import time
import json

import threading
import traceback

class VigiLightningManager(Plugin):
    """ Get lightning vigilances
    """

#    CalmMonitoring = 10.0 * 60.0 # 10 minutes monitoring
#    OutputMonitoring = 40.0 * 60.0 # 40 minutes monitoring
    CalmMonitoring = 3.0 * 60.0 # 10 minutes monitoring
    OutputMonitoring = 5.0 * 60.0 # 40 minutes monitoring

    def __init__(self):
        """ Init plugin
        """
        Plugin.__init__(self, name='vigilightning')

        # check if the plugin is configured. If not, this will stop the plugin and log an error
        #if not self.check_configured():
        #    return

        # get plugin parameters and web site source parameters
        self.vigiSource = self.get_config("wssource")
        self.checkTimes = self.get_config("checktimes") * 60.0 # convert in second
        self._lastStrike = {"time": 0.0, "device_id": 0, 'alertLevel': 0}
        self._startCheck = 0.0
        self._EndCheck = 0.0
        self._connexionStatus = "On Wait"

        # get the devices list
        self.devices = self.get_device_list(quit_if_no_device = False)

        # get the sensors id per device :
        self.sensors = self.get_sensors(self.devices)

        # create a VigiStrike and thread for each device
        self.vigi_Threads = {}
        self.vigi_List = {}
        self._loadDMGDevices()
        self.webSockect = None
        # Callback for new/update devices
        self.log.info(u"==> Add callback for new/update devices.")
        self.register_cb_update_devices(self.reload_devices)
        self._wsServer = None
        # Start websocket service to source web
        ws = threading.Thread(None,self.handle_connexion, "vigilightning-websocket-source", (),{})
        ws.start()
        self.register_thread(ws)
        self.ready()

    def _loadDMGDevices(self):
        """ Check and load domogik device if necessary
        """
        vigi_List = {}
        for a_device in self.devices:
            try:
                if a_device['device_type_id'] == "vigilocation" :
                    device_id = a_device["id"]
                    if device_id not in self.vigi_List :
                        self.log.info(u"Create device ({0}) lightning vigilance for '{1}'".format(device_id, a_device["name"]))
                        vigi_List[device_id] = VigiLocation(self, self.send_data, a_device)
                        # start the vigipollens thread
                        thr_name = "vigiStrike_{0}".format(device_id)
                        self.vigi_Threads[thr_name] = threading.Thread(None,
                                                  vigi_List[device_id].HandleAlertLevel,
                                                  thr_name,
                                                  (),
                                                  {})
                        self.vigi_Threads[thr_name].start()
                        self.register_thread(self.vigi_Threads[thr_name])
                    else :
                        self.vigi_List[device_id].setDevice(a_device)
                        vigi_List[device_id] = self.vigi_List[device_id]
                else:
                    self.log.error(u"### device type '{0}' not supported.".format(a_device['device_type_id']))
            except:
                self.log.error(u"{0}".format(traceback.format_exc())) # we don't quit plugin if an error occured, a vigipollens device can be KO and the others be ok
        # Check deleted devices
        for device_id in self.vigi_List :
            if device_id not in vigi_List :
                thr_name = "vigilightning_{0}".format(device_id)
                if thr_name in self.vigi_Threads :
                    self.vigi_List[device_id].run = False
                    self.unregister_thread(self.vigi_Threads[thr_name])
                    del self.vigi_Threads[thr_name]
                    self.log.info(u"Device {0} removed".format(device_id))

        self.vigi_List = vigi_List

    def send_data(self, device_id, device_name, dataSensors):
        """ Send the sensors values over MQ
        """
        data = {}
        for sensor, value in dataSensors.iteritems():
            if sensor == 'atTimestamp' :
                data['atTimestamp'] = value
            elif sensor in self.sensors[device_id] :
                data[self.sensors[device_id][sensor]] = value
        self.log.info(u"==> 0MQ PUB for {0} (id={1}) sended = {2} " .format(device_name, device_id, format(data)))

        try:
            self._pub.send_event('client.sensor', data)
        except:
            self.log.debug(u"Bad MQ message to send : {0}".format(data))
            pass

    def reload_devices(self, devices):
        """ Called when some devices are added/deleted/updated
        """
        self.devices = devices
        self.sensors = self.get_sensors(devices)
        self._loadDMGDevices()
        self.log.info(u"==> Reload Device called, All updated")

    def on_mdp_request(self, msg):
        # display the req message
        Plugin.on_mdp_request(self, msg)
        # call a function to reply to the message depending on the header
        action = msg.get_action().split(".")
        self.log.debug(u"MQ Request {0}".format(msg))
        if action[0] == 'vigilightning' :
            handled = False
            self.log.debug(u"Handle MQ request action {0}.".format(action))
            if action[1] == "manager" :
                if action[2] == 'getstrikes' :
                    data = msg.get_data()
                    reply_msg = MQMessage()
                    reply_msg.set_action("{0}.{1}.{2}".format(action[0], action[1], action[2]))
                    if 'device_id' in data :
                        handled = True
                        if data['device_id'] in self.vigi_List :
                            report = self.vigi_List[data['device_id']].getStrikes()
                            # send the reply
                            reply_msg.add_data('status', True)
                            reply_msg.add_data('strikes', report)
                            self.log.debug(u"==> MQ Response {0}".format(report))
                            self.reply(reply_msg.get())
                        else :
                            reply_msg.add_data('status', False)
                            reply_msg.add_data('reason', u"Unknown device {0}".format(data['device_id']))
                    else :
                        reply_msg.add_data('status', False)
                        reply_msg.add_data('reason', u"Abording command, no extra key 'device_id' in MQ command: {0}".format(data))
                if action[2] == 'setdeviceparams' :
                    data = msg.get_data()
                    reply_msg = MQMessage()
                    reply_msg.set_action("{0}.{1}.{2}".format(action[0], action[1], action[2]))
                    if 'device_id' in data :
                        handled = True
                        self.log.debug(u"setdeviceparams : {0}".format(self.devices))
                        self.log.debug(u"setdeviceparams : {0}".format(data.keys()))
                        for a_device in self.devices :
                            if a_device['id'] == int(data['device_id']):
                                nbParam = 0
                                nb = 0
                                for p in data :
                                    if self.getDeviceParamId(a_device, p): nbParam +=1
                                for p in data :
                                    paramid = self.getDeviceParamId(a_device, p)
                                    if paramid :
                                        nb += 1
                                        topublish = (nb == nbParam)
                                        self.log.debug(u"udpate_device_param {0}: id {1} valule {2}".format(p, paramid, data[p]))
                                        self.udpate_device_param(paramid, data[p], topublish)
                            # send the reply
                            reply_msg.add_data('status', True)
                            self.log.debug(u"==> MQ Response OK")
                            self.reply(reply_msg.get())
                        else :
                            reply_msg.add_data('status', False)
                            reply_msg.add_data('reason', u"Unknown device {0}".format(data['device_id']))
                    else :
                        reply_msg.add_data('status', False)
                        reply_msg.add_data('reason', u"Abording command, no extra key 'device_id' in MQ command: {0}".format(data))
            elif action[1] == "plugin" :
                if action[2] == 'getlog' :
                    handled = True
                    data = msg.get_data()
                    report = self.getLoglines(data)
                    # send the reply
                    reply_msg = MQMessage()
                    reply_msg.set_action("{0}.{1}.{2}".format(action[0], action[1], action[2]))
                    for k, item in report.items():
                        reply_msg.add_data(k, item)
                    self.reply(reply_msg.get())
            if not handled :
                self.log.warning(u"MQ request unknown action {0}.".format(action))
                self.log.warning(u"Abording command, no extra key in command MQ: {0}".format(data))
                reply_msg.add_data('status', False)
                reply_msg.add_data('reason', u"Abording command, no extra key in MQ command: {0}".format(data))

    def getDeviceParamId(self, device, key):
        if key in device['parameters'] :
            return device['parameters'] [key]['id']
        else :
            return False

    def setLastStrikeAlert(self, data):
        self._lastStrike = data

    def handle_connexion(self):
        """ Handle time to reconnect websocket
            During calm weather connection is stopped and restart every self.checkTimes during 10 minutes.
            If no event detected next to location websocket is closed.
        """
        self.run = True
        self._lastUpdate = 0
        self.vigiSource
        self._EndCheck = time.time() - self.checkTimes
        lastEvent = 0
        self.log.info(u"Start to check lightning vigilance source '{0}' every {1} sec.".format(self.vigiSource, self.checkTimes))
        try :
            while not self._stop.isSet() and self.run :
                try :
                    checkConnection = False
                    currentTime = time.time()
                    if self._lastStrike['time'] + self.OutputMonitoring >= currentTime :
                        if self._connexionStatus != "Lightning monitoring" or self._lastStrike['time'] != lastEvent :
                            self.log.debug(u"**** Status on OutputMonitoring remaining {0:.2f} sec.".format(self._lastStrike['time'] + self.OutputMonitoring - currentTime))
                            lastEvent = self._lastStrike['time']
                        self._connexionStatus = "Lightning monitoring"
                        checkConnection = True
                    else :
                        if self._startCheck + self.CalmMonitoring >= currentTime :
                            if self._connexionStatus != "Calm monitoring" :
                                self.log.debug(u"**** Status on CalmMonitoring remaining {0:.2f} sec.".format(self._startCheck + self.CalmMonitoring - currentTime))
                            self._connexionStatus = "Calm monitoring"
                            checkConnection = True
                        elif self._EndCheck + self.checkTimes <= currentTime :
                            if self._connexionStatus != "CheckTimes monitoring" :
                                self.log.debug(u"+++ Status on checkTimes, restart monitoring.")
                            self._connexionStatus = "CheckTimes monitoring"
                            checkConnection = True
                        else :
                            if self.webSockect is not None :
                                self.log.debug(u"--- Status no strike, connexion will close")
                                self._EndCheck = currentTime
                                self.webSockect.close()
                                self.webSockect = None
                            else :
                                if self._connexionStatus != "Wait next monitoring" :
                                    self.log.debug(u"**** Status on wait for {0:.2f} sec., Nothing to do".format((self._EndCheck + self.checkTimes) - currentTime))
                                self._connexionStatus = "Wait next monitoring"
                        if checkConnection :
                            self._EndCheck = currentTime
                            if self.webSockect is None :
                                self._startCheck = 0
                                self.createWSClient()
                                self._startCheck = currentTime
                except :
                    self.log.error(u"Check lightning {0} error: {1}".format(self.vigiSource, (traceback.format_exc())))
                self._stop.wait(10)
        except :
            self.log.error(u"Check lightning {0} error: {1}".format(self.vigiSource, (traceback.format_exc())))
        self.run = False
        self.log.info(u"Stopped lightning vigilance checking for {0}".format(self.vigiSource))

    def createWSClient(self):
        port = int(round(random.random() * 40 + 8050))
        url = 'ws://{0}:{1}'.format(self.vigiSource, port)
        self.log.info(u"Start Connection to {0}".format(url))
        self.webSockect = WSClient(url, onMessage=self.receivedData, log=self.log)
        try :
            self.webSockect.connect()
            th = threading.Thread(None, self.webSockect.run_forever, "th_WSClient_forever-vigilightining", (), {})
            self.add_stop_cb(self.webSockect.close);
            self.register_thread(th)
            self.log.info("WSClient start forever mod to {0}".format(url))
            th.start()
        except :
            self.webSockect = None
            self.log.warning("WSClient to <{0}>, Create error : {1}".format(url, traceback.format_exc()))

    def receivedData(self, data):
        if set(("time", "lat", "lon", "alt", "pol", "mds", "mcg", "sig", "delay",)) <= set(data):
#            self.log.debug(u"Strike event received, publishing to all vigilance device...")
            for id in self.vigi_List :
                self.vigi_List[id].receiveStrike(data)
        else :
            self.log.warning(u"Receive unknown data : {0}".format(data))

class WSClient(WebSocketClient):

    def __init__(self, url, onMessage=None, log=None):
        WebSocketClient.__init__(self, url, protocols=['http-only', 'chat'])
        self.connected = False
        self.log = log
        self._onMessage = onMessage

    def opened(self):
        self.log.info(u"Opening {0}".format(self.url))
        self.send('{"sig":false}')
        self.log.info(u"Connected to {0}".format(self.url))
        self.connected = True
        self._lastConnection = time.time()

    def closed(self, code, reason=None):
        self.log.info(u"Closed down {0}, {1} {2}".format(self.url, code, reason))
        self.connected = False

    def received_message(self, m):
        m = json.loads(str(m))
        self._onMessage(m)

if __name__ == "__main__":
    vigilightning = VigiLightningManager()
