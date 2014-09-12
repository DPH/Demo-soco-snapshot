"""
Demo 2 of snapshot plugin
all Sonos zones
"""

import soco
from soco.plugins.snapshot import Snapshot
import sys
import time

alert = "x-file-cifs://DoorPi/DoorPiPublic/doorbell/sounds/Tinkle5sec.mp3"

# get any Sonos player
start_zp = soco.SoCo('192.168.1.64')


def to_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s

# take snapshot of current state
for grp in start_zp.all_groups:
    for zp in grp:

        #for every device
        print 'Zone Player:', zp.player_name,\
              ' - Coordinator', grp.coordinator.player_name

        # create a new plugin, pass it the soco instance to it
        zp.my_snap = Snapshot(zp)

        # take snap of current state
        zp.my_snap.snap()

        # FYI get the image saved and print it out (really only for testing)
        img = zp.my_snap.image
        print img

        #time.sleep(1)

        print ('   > Image print for zone: %s' % zp.player_name)
        for x, y in img.iteritems():
            output = to_utf8(y)
            #output = output.encode('utf-8')
            print '     {0: >10}: {1}'.format(x, output)
        print #create blank line


        # play sound / tune / voice - only play on coordinators
        if zp.is_coordinator:
            zp.play_uri(uri=alert)


#reset the zone to the state when the snap was taken
time.sleep(6)
print ('resetting zones')

for grp in start_zp.all_groups:
    for zp in grp:
        #for every device
        print 'Resetting Zone Player:', zp.player_name
        zp.my_snap.restore(fade=True)


