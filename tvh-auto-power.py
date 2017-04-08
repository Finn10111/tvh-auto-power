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
import httplib
import subprocess
import argparse
import datetime


def main():
    parser = argparse.ArgumentParser(description='Tvheadend automativ shutdown and wakeup script')
    parser.add_argument('-d', '--debug', action='store_true', help='turn on debug mode')
    args = parser.parse_args()
    debug = args.debug

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

    # The system must at least being up for min_uptime seconds for being allowed to shut down
    min_uptime = 3600

    # Detect Tvheadend version and use given urls
    subscriptions_url, recordings_url = get_tvh_urls(base_url, username, password)

    # Get list of subscriptions
    subscriptions = get_json(base_url + subscriptions_url, username, password)

    # Don't shutdown of clients are connected
    if len(subscriptions['entries']) > 0:
        shutdown_allowed = False
        if debug:
            print "Shutdown now allowed, there are some active subscriptions."

    # Get list of recordings
    recordings = get_json(base_url + recordings_url, username, password)

    for r in recordings['entries']:
        if int(r['start']) < first_rectime:
            first_rectime = int(r['start'])
        if r['start'] < (int(time.time()) + pre_recording_shutdown_time):
            shutdown_allowed = False
            if debug:
                print "Shutdown now allowed, there are some active or pending recordings."

    devnull = open('/dev/null', 'w')
    # Check also if somebody is connected via SSH or if there is a HTTP connection
    if subprocess.call('netstat -pantu 2>/dev/null| egrep "(`ip addr | grep -Po \'((?<=inet )([\d\.]*)(?=.*global))\' | paste -d\'|\' -s`)\:(9981|9982|22)"', stdout=devnull, shell=True) == 0:
        shutdown_allowed = False
        if debug:
            print "Shutdown now allowed, there are some SSH, Tvheadend webinterface or HTSP connections."

    if first_rectime == 2147483647 or first_rectime < int(time.time()):
        # If no recordings are scheduled or there is only one recording which is running wake up the next day
        waketime = int(time.time()) + 86400
    else:
        # If a recording is scheduled wake up X minutes before it begins
        waketime = first_rectime - pre_recording_wakeup_time

    # Clear previously set wake up time
    subprocess.call('echo 0 > /sys/class/rtc/rtc0/wakealarm', shell=True)
    time.sleep(1)
    # Set the new wake up time
    if debug:
        print "Setting wake up time to %s" % datetime.datetime.fromtimestamp(waketime).strftime('%Y-%m-%d %H:%M:%S')
    subprocess.call('echo %s > /sys/class/rtc/rtc0/wakealarm' % waketime, shell=True)
    time.sleep(1)
    subprocess.call('/usr/sbin/rtcwake -m no -t %s' % waketime, stdout=devnull, shell=True)
    time.sleep(1)

    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        # Do not shut down within the first hour after boot
        if uptime_seconds < min_uptime:
            shutdown_allowed = False
            if debug:
                print "System is running less than %s seconds, not shutting down." % min_uptime;

    if shutdown_allowed:
        # Shutdown
        subprocess.call('/usr/sbin/rtcwake -m off -t %s' % waketime, stdout=devnull, shell=True)
        #subprocess.call('/sbin/shutdown -h now', shell=True)

    if debug:
        print "shutdown allowed: " + str(shutdown_allowed)


def get_json(url, username=None, password=None):
    # Use credentials if supplied
    if username is not None and password is not None:
        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, username, password)
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


def get_tvh_urls(base_url, username, password):
    subscriptions_url = 'subscriptions'
    recordings_url = 'dvrlist_upcoming'
    try:
        # This works only for Tvheadend 3.x
        get_json(base_url + subscriptions_url)
    except httplib.BadStatusLine as e:
        # This exception is thrown when using Tvheadend 4.x
        subscriptions_url = 'api/status/connections'
        recordings_url = 'api/dvr/entry/grid_upcoming'
    return subscriptions_url, recordings_url


if __name__ == '__main__':
        sys.exit(main())
