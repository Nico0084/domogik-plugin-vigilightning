#!/usr/bin/python
#-*- coding: utf-8 -*-

from domogik.tests.common.helpers import configure, delete_configuration
from domogik.common.utils import get_sanitized_hostname

plugin =  "vigilightning"

host_id = get_sanitized_hostname()
delete_configuration("plugin", plugin, host_id)

configure("plugin", plugin,  host_id, "wssource", "ws.blitzortung.org")
configure("plugin", plugin,  host_id, "checktimes",  "3")
