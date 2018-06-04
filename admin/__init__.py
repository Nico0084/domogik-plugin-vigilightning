# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, abort, jsonify, request

from domogik.common.utils import get_packages_directory, get_sanitized_hostname
from domogik.admin.application import app, render_template
from domogik.admin.views.clients import get_client_detail, get_client_devices
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

from jinja2 import TemplateNotFound
import traceback
import sys

### package specific imports
import subprocess

#from domogik.common.plugin import Plugin.get_config ???


### package specific functions

def get_request(client_id, action, data, abort = False):
    resData = {u'error': u'', u'data': {}}
    if not abort :
        cli = MQSyncReq(app.zmq_context)
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

def get_informations(devices):
    locationsList = []
    for a_device in devices:
        strikePts= get_StrikePoints(a_device['id'])
        strikePts = [] if not strikePts['status'] else  strikePts['strikes']
        locationsList.append({'id': a_device['id'],
                              'name': a_device['name'],
                              'latitude': a_device['parameters']['latitude']['value'],
                              'longitude': a_device['parameters']['longitude']['value'],
                              'criticalradius': a_device['parameters']['criticalradius']['value'],
                              'nearbyradius': a_device['parameters']['nearbyradius']['value'],
                              'approachradius': a_device['parameters']['approachradius']['value'],
                              'strikes': strikePts})
    return locationsList


def get_errorlog(cmd, log):
    print("Command = %s" % cmd)
    errorlog = subprocess.Popen([cmd, log], stdout=subprocess.PIPE)
    output = errorlog.communicate()[0]
    if isinstance(output, str):
        output = unicode(output, 'utf-8')
    return output

def get_StrikePoints(device_id):
    data = {u'status': u'fail', u'strikes': [], u'error': u''}
    cli = MQSyncReq(app.zmq_context )
    msg = MQMessage()
    msg.set_action('vigilightning.manager.getstrikes')
    msg.add_data('device_id', device_id)
    res = cli.request('plugin-vigilightning.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
    if res is not None:
        data = res.get_data()
    else : data['error'] =  u'Plugin timeout response.'
    print(u"********* get_StrikePoints : {0}".format(data))
    return data

### common tasks
package = "plugin_vigilightning"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)
geterrorlogcmd = "{0}/{1}/admin/geterrorlog.sh".format(get_packages_directory(), package)
logfile = "/var/log/domogik/{0}.log".format(package)

plugin_vigilightning_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)


@plugin_vigilightning_adm.route('/<client_id>')
def index(client_id):
    detail = get_client_detail(client_id)      # vigilightning plugin configuration
    devices = get_client_devices(client_id)     # vigilightning plugin devices list
    deviceInfos = get_informations(devices)
    print("Locations list: %s" % format(deviceInfos))
    try:
        return render_template('plugin_vigilightning.html',
            clientid = client_id,
            client_detail = detail,
            mactive ="clients",
            active = 'advanced',
            locationsList = deviceInfos,
            logfile = logfile,
            errorlog = get_errorlog(geterrorlogcmd, logfile))

    except TemplateNotFound:
        abort(404)

@plugin_vigilightning_adm.route('/<client_id>/log')
def log(client_id):
    detail = get_client_detail(client_id)
    with open(logfile, 'r') as contentLogFile:
        content_log = contentLogFile.read()
    try:
        return render_template('plugin_vigilightning_log.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            logfile = logfile,
            contentLog = content_log)

    except TemplateNotFound:
        abort(404)

@plugin_vigilightning_adm.route('/<client_id>/request/<mq_request>')
def plugin_request(client_id, mq_request):
    print(u"Plugin {0} recieved MQ Request : {1}".format(client_id, mq_request))
    data = {}
    for k, v in request.args.iteritems():
        data[k] = v
    reply, msg = get_request(str(client_id), str(mq_request), data)
    print(u"Plugin {0} recieved MQ response : {1} - {2}".format(client_id, reply, msg))
    if 'error'in msg and msg['error'] !="":
        return jsonify(result='error', reply=reply, content = msg)
    else :
        return jsonify(result='success', reply=reply, content = msg)
