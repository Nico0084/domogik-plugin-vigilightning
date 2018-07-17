#!/usr/bin/python
# -*- coding: utf-8 -*-

import zmq
from zmq.eventloop.ioloop import IOLoop
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.pubsub.subscriber import MQAsyncSub
from domogikmq.message import MQMessage
from domogik.common.plugin import STATUS_ALIVE, STATUS_STOPPED
import json

name = 'vigilightning'
host = 'vmserver16'

print(u"Request plugin startup to the manager for '{0}' on '{1}'".format(name, host))
cli = MQSyncReq(zmq.Context())
msg = MQMessage()
msg.set_action('plugin.start.do')
msg.add_data('type', "plugin")
msg.add_data('name', name)
msg.add_data('host', host)
result = cli.request('manager', msg.get(), 10)
print(u"Result start: {0}".format(result))
