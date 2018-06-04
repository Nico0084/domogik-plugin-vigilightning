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

import traceback

try :
    # Python3
    from io import BytesIO as StreamIO
except :
    import StringIO as StreamIO

import time
import math, operator
import urllib
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
        self._alertLevel = 0
        self._direction = ""
        self._strikes = StrikesList([], self._stop)
        self.setDevice(dmgDevice)

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

    def HandleAlertLevel(self):
        """ Handle general level alert
        """
        self.run = True
        self.log.info(u"Start to Handle general level alert for {0}".format(self.device_name))
        while not self._stop.isSet() and self.run:
            try :
                direction, nbStrike, last = self.computeStrikes(0, 3)
                if nbStrike != 0 :
                    if last['time'] + self.releasetimes < time.time():
                        self.setAlertLevel(2, direction)
                    else :
                        self.setAlertLevel(3, direction)
                else :
                    direction, nbStrike, last = self.computeStrikes(0, 2)
                    if nbStrike != 0 :
                        if last['time'] + self.releasetimes < time.time() :
                            self.setAlertLevel(1, direction)
                        else :
                            self.setAlertLevel(2, direction)
                    else :
                        direction, nbStrike, last = self.computeStrikes(0, 1)
                        if nbStrike != 0 :
                            if last['time'] + self.releasetimes < time.time() :
                                self.setAlertLevel(0, direction)
                            else :
                                # Check if lightning is in approach
                                if nbStrike >= 4 : # filter isolate strike
                                    self.setAlertLevel(1, direction)
                self._stop.wait(1)
            except :
                self.log.error(u"Check device {0} error: {1}".format(self.device_id, (traceback.format_exc())))
        self.run = False
        self.log.info(u"Stopped lightning vigilance checking for {0}".format(self.device_name))

    def setAlertLevel(self, level, direction):
        if level != self._alertLevel:
            if level < self._alertLevel :
                self.log.debug(u"Release level {0} to {1}".format(self._alertLevel, level))
                if level == 0 :
                    self.log.info(u"End of ligtning alert for {0}".format(self.device_name))
                    self._strikes[:] = []
                elif level == 1 :
                    self.log.info(u"Lightning roll away to {0}".format(self.device_name))
                elif level == 2 :
                    self.log.info(u"Lightning calms down to {0}".format(self.device_name))
            else :
                self.log.debug(u"Increase level {0} to {1}".format(self._alertLevel, level))
                if level == 1 :
                    self.log.info(u"Lightning in approach from the {0} to {1}".format(direction, self.device_name))
                elif level == 2 :
                    self.log.info(u"Lightning from the {0} close to {1}".format(direction, self.device_name))
                elif level == 3 :
                    self.log.info(u"Critical alert from the {0} for {1}".format(direction, self.device_name))
            self._alertLevel = level
            self.log.debug(u"************ Set level alert to {0} {1} *****************".format(self._alertLevel, direction))
            self._send(self.device_id, self.device_name, {'AlertLevel': self._alertLevel})
            self._direction = direction
        if self._direction != direction and self._alertLevel == level:
            self._direction = direction
            self.log.info(u"************ level alert {0} change direction {1} *****************".format(self._alertLevel, direction))

    def receiveStrike(self, data):
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
        if strikeTime + self.releasetimes >= time.time() :
            alertLevel = 0
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
                self.manager.setLastStrikeAlert({"time": strikeTime, "device_id": self.device_id, 'alertLevel': alertLevel})
                self._strikes.append({"time": strikeTime, 'latitude':  data['lat'], 'longitude':  data['lon'], 'alertLevel': alertLevel, 'direction': direction})
                toSend = {'CriticalStrike': "{0},{1}".format(data['lat'], data['lon']), "atTimestamp": data['time']/TIME_FACTOR}
                self._send(self.device_id, self.device_name, toSend)

    def getStrikes(self):
        return self._strikes

    def getDirection(self, angle):
        for d in DIRECTIONS.values() :
            if angle > d[1] and angle <= d[2] :
                return d[0]
        return DIRECTIONS["N"][0]

    def computeStrikes(self, delais=0, level=0):
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


