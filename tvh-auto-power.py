#!/usr/bin/env python2
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# README:
#
# Step 1:
# Copy this script to some directory like /usr/local/bin and
# make it executeable.
#
# Step 2:
# Change URL, username and password if necessary.
#
# Step 3:
# Add a cronjob like this to get this script running:
# */5 * * * * sleep 15m && /usr/local/bin/tvh-auto-power.py
#
# The sleep commands prevents the server to shutdown
# immeadeatly after boot.

import os
import sys
import json
import time
import urllib2
import subprocess


def main():
    # Change these if necessary.
    base_url = 'http://localhost:9981/'
    username = None
    password = None
    # Wakeup X seconds before recording
    pre_recording_wakeup_time = 900
    # Don't shutdown if a recordings is scheduled within the next X seconds
    pre_recording_shutdown_time = 1800

    shutdown_allowed = True
    first_rectime = 2147483647
    subscriptions_url = 'subscriptions'
    recordings_url = 'dvrlist_upcoming'

    # Get list of subscriptions
    subscriptions = get_json(base_url + subscriptions_url, username, password)

    # Don't shutdown of clients are connected
    if len(subscriptions['entries']) > 0:
        shutdown_allowed = False

    # Get list of recordings
    recordings = get_json(base_url + recordings_url, username, password)

    for r in recordings['entries']:
        if int(r['start']) < first_rectime:
            first_rectime = int(r['start'])
        if r['start'] < (int(time.time()) + pre_recording_shutdown_time):
            shutdown_allowed = False

    devnull = open('/dev/null', 'w')
    # Check also if somebody is connected via SSH or if there is a HTTP connection
    if subprocess.call('netstat -pantu | egrep "192.168.1.8:(9981|22)"', stdout=devnull, shell=True) == 0:
        shutdown_allowed = False

    if shutdown_allowed:
        if first_rectime == 2147483647:
            # If no recordings are scheduled wake up the next day
            waketime = int(time.time()) + 86400
        else:
            # If a recording is scheduled wake up X minutes before it begins
            waketime = first_rectime - pre_recording_wakeup_time
        # Clear previously set wake up time
        subprocess.call('echo 0 > /sys/class/rtc/rtc0/wakealarm', shell=True)
        time.sleep(1)
        # Set the new wake up time
        subprocess.call('echo %s > /sys/class/rtc/rtc0/wakealarm' % waketime, shell=True)
        time.sleep(1)
        # Shutdown
        subprocess.call('/sbin/shutdown -h now', shell=True)


def get_json(url, username=None, password=None):
    # Use credentials if supplied
    if username is not None and password is not None:
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, 'autopower', 'autopower')
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
    try:
        response = urllib2.urlopen(url)
    except urllib2.HTTPError as e:
        print e
        sys.exit(1)
    json_object = response.read()
    response_dict = json.loads(json_object)
    return response_dict


if __name__ == '__main__':
        sys.exit(main())
