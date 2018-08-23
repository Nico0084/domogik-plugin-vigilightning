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

vigilightning

Implements
==========

- VigiLocation device

"""

import zmq
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

import traceback
import time
import math
from datetime import datetime

EARTH_RADIUS = 6378137 #  Terre = sphere radius 6378km
TIME_FACTOR = 1000000000.0

DIRECTIONS = {
            "N": ["North", 337.5, 22.5],
            "E": ["East", 67.5, 112.5],
            "S": ["South", 157.5, 202.5],
            "W": ["West", 247.5, 292.5],
            "NE": ["Northeast", 22.5, 67.5],
            "SE": ["Southeast", 112.5, 157.5],
            "SW": ["Southwest", 202.5, 247.5],
            "NW": ["Northwest", 292.5, 337.5]}

class VigiLightningException(Exception):
    """
    Vigilightning exception
    """

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)

class StrikesList(list):
    """ Handle list with dict specific data format :
        {"time": strikeTime, 'alertLevel': alertLevel, 'direction': direction}
    """

    from threading import Thread

    def __init__(self, values, stop):
        super(StrikesList, self).__init__(values)
        self._stop = stop
        self._running = False
        self.lifetime = 2700 # default 45 minutes monitoring
#        self.lifetime = 120 # debug monitoring
        self._thread = self.Thread(target=self.run)
        self._thread.start()
        print(u"StrikesList initialized")

    def __del__(self):
        super(StrikesList, self).__del__()
        self._running = False

    def run(self):
        print(u"\nStrikesList started")
        self._running = True
        while not self._stop.isSet() and self._running :
            self._checkStrikes()
            time.sleep(3)
        print(u"StrikesList finished")

    def _checkStrikes(self):
#        print(u"************************************************** {0}".format(len(self)))
        for strike in self :
#            print(u"Check {0}".format(strike))
            if strike['time'] + self.lifetime < time.time() :
                self.remove(strike)
#        print(u"++++++++++++++++++++++++++++++++++++++++++++++++++ {0}".format(len(self)))

    def getLastFrom(self, delais = 0, level = 0):
        """ Return list of all strike from delais (sec) with optionnal level
        """
        result = []
        currentTime = time.time()
        if delais == 0 : delais = self.lifetime * 1.2
        for strike in self :
            if currentTime - strike['time'] <= delais :
                if level == 0 :
                    result.append(strike)
                elif strike['alertLevel'] == level :
                    result.append(strike)
        return result

class VigiLocation:
    """ handle a dmg_device Vigilightning
    """

    def __init__(self, manager, send, dmgDevice):
        """ Init vigilightning object
            @param log : log instance
            @param send : send
            @param stop : stop flag
            @param device : domogik device
        """
        self.manager = manager
        self.log = manager.log
        self._send = send
        self._stop = self.manager.get_stop()
        self.run = False
        self._direction = ""
        self._strikes = StrikesList([], self._stop)
        self.setDevice(dmgDevice)
        self._alertLevel = self.getLastAlertLevel()
        self._status = 'unknown'
        if self._alertLevel == 0 :
            self._status = "calm"
        elif self._alertLevel == 1 :
            self._status = "in approach"
        elif self._alertLevel == 2 :
            self._status = "close to"
        elif self._alertLevel == 3 :
            self._status = "critical"

    def setDevice(self, dmgDevice):
        if dmgDevice["device_type_id"] == 'vigilocation' :
            self.device_id = dmgDevice["id"]
            self.device_name = dmgDevice["name"]
            self.latitude = float(self.manager.get_parameter(dmgDevice, "latitude"))
            self.longitude = float(self.manager.get_parameter(dmgDevice, "longitude"))
            self.criticalradius = float(self.manager.get_parameter(dmgDevice, "criticalradius"))
            self.nearbyradius = float(self.manager.get_parameter(dmgDevice, "nearbyradius"))
            self.approachradius = float(self.manager.get_parameter(dmgDevice, "approachradius"))
            self.releasetimes = float(self.manager.get_parameter(dmgDevice, "releasetimes")) * 60.0 # convert in second
            self.log.info(u"Device updated device data '{0}'".format(dmgDevice))
            self._strikes.lifetime = self.releasetimes * 1.2
            # set sensor for location monitoring point"
            self._send(self.device_id, self.device_name, {'LocationPoint': "{0},{1}".format(self.latitude, self.longitude)})
            self.log.info(u"Device {0} parameters updated.".format(self.device_name))

    def handleAlertLevel(self):
        """ Handle general level alert
        """
        self.run = True
        self.log.info(u"Start to Handle general level alert for {0}".format(self.device_name))
        while not self._stop.isSet() and self.run:
            try :
                direction, nbStrike, last = self.computeStrikesDirecton(0, 3)
                if nbStrike != 0 :
                    if last['time'] + self.releasetimes < time.time():
                        self.setAlertLevel(2, direction)
                    else :
                        self.setAlertLevel(3, direction)
                else :
                    direction, nbStrike, last = self.computeStrikesDirecton(0, 2)
                    if nbStrike != 0 :
                        if last['time'] + self.releasetimes < time.time() :
                            self.setAlertLevel(1, direction)
                        else :
                            self.setAlertLevel(2, direction)
                    else :
                        direction, nbStrike, last = self.computeStrikesDirecton(0, 1)
                        if nbStrike != 0 :
                            if last['time'] + self.releasetimes < time.time() :
                                self.setAlertLevel(0, direction)
                            else :
                                # Check if lightning is in approach
                                if nbStrike >= 2 : # filter isolate strike
                                    self.setAlertLevel(1, direction)
                        else :
                            if self._status != 'calm' :
                                self.setAlertLevel(0, direction)
                                self._status = 'calm'
                                print(u"************ handleAlertLevel, {0}".format(self._status))
                                self.manager.publishMsg("vigilightning.device.alertstatus", {"device_id": self.device_id,  "device_name": self.device_name,
                                                                 "AlertLevel": self._alertLevel, "Direction": direction, "Status": self._status, "Msg": self.getAlertMsg()})

                self._stop.wait(1)
            except :
                self.log.error(u"Check device {0} error: {1}".format(self.device_id, (traceback.format_exc())))
        self.run = False
        self.log.info(u"Stopped lightning vigilance checking for {0}".format(self.device_name))

    def setAlertLevel(self, level, direction):
        if level != self._alertLevel:
            if level < self._alertLevel :
                step = 0
                if level == 0 :
                    self._status = "end"
                    self._strikes[:] = []
                elif level == 1 :
                    self._status = "roll away"
                elif level == 2 :
                    self._status = "calms down"
            else :
                step = 1
                if level == 1 :
                    self._status = "in approach"
                elif level == 2 :
                    self._status = "close to"
                elif level == 3 :
                    self._status = "critical"
            self._alertLevel = level
            self._direction = direction
            self._send(self.device_id, self.device_name, {'AlertStatus': step})
            self._send(self.device_id, self.device_name, {'AlertLevel': self._alertLevel})
            self.manager.publishMsg("vigilightning.device.alertstatus", {"device_id": self.device_id,  "device_name": self.device_name,
                                             "AlertLevel": self._alertLevel, "Direction": direction, "Status": self._status, "Msg": self.getAlertMsg()})
        if self._direction != direction and self._alertLevel == level:
            self._direction = direction
            self.manager.publishMsg("vigilightning.device.alertstatus", {"device_id": self.device_id,  "device_name": self.device_name,
                                             "AlertLevel": self._alertLevel, "Direction": direction, "Status": self._status,
                                             "Msg": u"Level alert {0} change direction {1}".format(self._alertLevel, direction)})

    def getAlertMsg(self):
        if self._status == "calm" :
            msg = u"No lightning."
        elif self._status == "end" :
            msg = u"End of lightning alert."
        elif self._status == "roll away" :
            msg = u"Lightning roll away."
        elif self._status == "calms down" :
            msg = u"Lightning calms down."
        elif self._status == "in approach" :
            msg = u"Lightning in approach from the {0}.".format(self._direction)
        elif self._status == "close to" :
            msg = u"lightning coming from the {0} very close.".format(self._direction)
        elif self._status == "critical" :
            msg = u"Critical alert from the {0}.".format(self._direction)
        else :
            msg = u"No status defined."
        return msg

    def getAlertStatus(self):
        return {"device_id": self.device_id,  "device_name": self.device_name,
                    "AlertLevel": self._alertLevel, "Direction": self._direction, "Status": self._status,
                    "Msg": self.getAlertMsg()}

    def receiveStrike(self, data):
            alertLevel, strikeTime, lat, lon, direction = self.computeStrike(data)
            if alertLevel <> 0 :
                self.manager.setLastStrikeAlert({"time": strikeTime, "device_id": self.device_id, 'alertLevel': alertLevel})
                self._strikes.append({"time": strikeTime, 'latitude':  lat, 'longitude':  lon, 'alertLevel': alertLevel, 'direction': direction})
                toSend = {'Strike': "{0},{1}".format(lat, lon), "atTimestamp": strikeTime}
                self._send(self.device_id, self.device_name, toSend)
                self.manager.publishMsg("vigilightning.device.newstrike", {"device_id": self.device_id,  "device_name": self.device_name,
                                                 "time": strikeTime, 'latitude':  lat, 'longitude':  lon, 'alertLevel': alertLevel, 'direction': direction})

    def getStrikes(self):
        return self._strikes

    def computeStrike(self, data):
        rlo1 = math.radians(self.longitude) #  CONVERSION
        rla1 = math.radians(self.latitude)
        rlo2 = math.radians(data['lon'])
        rla2 = math.radians(data['lat'])
        dlo = (rlo2 - rlo1) / 2
        dla = (rla2 - rla1) / 2
        a = (math.sin(dla) * math.sin(dla)) + math.cos(rla1) * math.cos(rla2) * (math.sin(dlo) * math.sin(dlo))
        d = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dkm = (EARTH_RADIUS * d) / 1000.0
        strikeTime = data['time'] / TIME_FACTOR
#        self.log.debug ("{0} Handle Strike event at : {0}, distance {1} km / {2} deg ({3}) since {4} s".format(datetime.fromtimestamp(data['time']/TIME_FACTOR),
#                dkm, math.degrees(a), self.getDirection(math.degrees(a)),
#                data['delay']))
        # Angle P1/P2 / Nord
        if math.sin(rlo2-rlo1) >=0 :
            rAngle=math.acos((math.sin(rla2)-math.sin(rla1)*math.cos(d))/(math.sin(d)*math.cos(rla1)))
        else :
            rAngle=2*math.pi-math.acos((math.sin(rla2)-math.sin(rla1)*math.cos(d))/(math.sin(d)*math.cos(rla1)))
        alertLevel = 0
        direction = ""
        if strikeTime + self.releasetimes >= time.time() :
            if dkm <= self.criticalradius :
                alertLevel = 3
            elif dkm <= self.nearbyradius :
                alertLevel = 2
            elif dkm <= self.approachradius :
                alertLevel = 1
            if alertLevel <> 0 :
                direction = self.getDirection(math.degrees(rAngle))
                self.log.info ("Strike level {0} at : {1}, distance {2} km / {3} deg ({4}) since {5} s".format(alertLevel,
                        datetime.fromtimestamp(data['time']/TIME_FACTOR),
                        dkm, math.degrees(a), direction,
                        data['delay']))
        return (alertLevel, strikeTime, data['lat'], data['lon'], direction)

    def getDirection(self, angle):
        for d in DIRECTIONS.values() :
            if angle > d[1] and angle <= d[2] :
                return d[0]
        return DIRECTIONS["N"][0]

    def computeStrikesDirecton(self, delais=0, level=0):
        """ Return a computed direction between all strike at level during specific delais
        """
        strikes = self._strikes.getLastFrom(delais, level)
        stats = {"North": 0,"East": 0, "South": 0, "West": 0,"Northeast": 0, "Southeast": 0, "Southwest": 0, "Northwest": 0}
        for s in strikes : stats[s['direction']] += 1
        iMax = ""
        max = 0
        for i in stats :
            if stats[i] > max :
                iMax = i
                max = stats[i]
#        if max != 0 :
#            self.log.debug(u"Alert level {0} from the {1} ({2} strikes)".format(level, iMax, len(strikes)))
        return iMax, 0 if iMax=="" else stats[iMax], strikes[0] if strikes else []

    def getLastAlertLevel(self):
        """ Return last alert level history"""
        sensor_id = self.manager.getSensorId(self.device_id, 'AlertLevel')
        level = None
        if sensor_id :
            cli = MQSyncReq(zmq.Context())
            msg = MQMessage()
            msg.set_action('sensor_history.get')
            msg.add_data('sensor_id', sensor_id)
            msg.add_data('mode', 'last')
            msg.add_data('number', 1)
            res = cli.request('admin', msg.get(), timeout=10)
            if res is not None :
                resData = res.get_data()
                print(u"getLastAlertLevel : {0}".format(resData))
                if resData['values'] and resData['values'][0]['value_num'] is not None :
                    level = int(resData['values'][0]['value_num'])
        return level

    def getLastHistoryAlert(self, number=1):
        """ Return strike history"""
        sensor_id = self.manager.getSensorId(self.device_id, 'AlertLevel')
        if sensor_id :
            cli = MQSyncReq(zmq.Context())
            msg = MQMessage()
            msg.set_action('sensor_history.get')
            msg.add_data('sensor_id', sensor_id)
            msg.add_data('mode', 'last')
            msg.add_data('number', number*7) # 7 = Max process level (0,1,2,3,2,1,0)
            res = cli.request('admin', msg.get(), timeout=10)
            strikeEvents = []
            if res is not None :
                resData = res.get_data()
                begin = 0
                end = 0
                maxLevel = 0
                if resData['values'] :
                    for alert in reversed(resData['values']) :
                        if alert['value_num'] == 0 :
                            if end != 0 :
                                strikeEvents.append({'begin': begin, 'end': alert['timestamp'], 'level': maxLevel})
                                begin = 0
                                end = 0
                                maxLevel = 0
                        else :
                            if begin == 0 : begin = alert['timestamp']
                            end = alert['timestamp']
                            if maxLevel < alert['value_num']: maxLevel = alert['value_num']
                    if maxLevel != 0 :
                        strikeEvents.append({'begin': begin, 'end': 0, 'level': maxLevel})
                    if len(strikeEvents) > number :
                        print(u"***** {0} > {1}".format(len(strikeEvents), number))
                        print(strikeEvents)
                        strikeEvents = strikeEvents[len(strikeEvents)-number:]
                        print(strikeEvents)
                self.log.debug(u"{0} find last event(s):{1}".format(self.device_name, strikeEvents))
        return strikeEvents

    def getEventHistoryStrike(self, eventAlert):
        """ Return strike history"""
        sensor_id = self.manager.getSensorId(self.device_id, 'Strike')
        self.log.debug(u"{0} Get history strike(s): {1}".format(self.device_name, eventAlert))
        strikesList = []
        if sensor_id :
            begin = eventAlert['begin'] if eventAlert['begin'] != 0 else time.time()
            end = eventAlert['end'] if eventAlert['end'] != 0 else time.time()
            cli = MQSyncReq(zmq.Context())
            msg = MQMessage()
            msg.set_action('sensor_history.get')
            msg.add_data('sensor_id', sensor_id)
            msg.add_data('mode', 'period')
            msg.add_data('from', begin)
            msg.add_data('to', end)
            res = cli.request('admin', msg.get(), timeout=10)
            resData = ""
            if res is not None :
                resData = res.get_data()
                self.log.debug(u"{0} find {1} strike(s) for event alert".format(self.device_name, len(resData)))
                for strike in resData['values'] :
                    lat, lon = strike['value_str'].split(",")
                    data = {'time': strike['timestamp']*TIME_FACTOR, 'lat':  float(lat), 'lon':  float(lon), 'delay': 0}
                    alertLevel, strikeTime, lat, lon, direction = self.computeStrike(data)
                    strikesList.append({"time": strikeTime, 'latitude':  lat, 'longitude':  lon, 'alertLevel': alertLevel, 'direction': direction})
        return strikesList
