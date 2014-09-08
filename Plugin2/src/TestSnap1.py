"""
Demo 1 of snapshot plugin
Single sonos device
"""

import soco
from soco.plugins.snapshot import Snapshot
import sys
import time

alert = "x-file-cifs://DoorPi/DoorPiPublic/doorbell/sounds/Tinkle5sec.mp3"

# get any Sonos player
zp = soco.SoCo('192.168.1.64')

# create a new plugin, pass it the soco instance to it
camera = Snapshot(zp)

# take snap of current state
camera.snap()

# play sound / tune / voice
zp.play_uri(uri=alert)


#reset the zone to the state when the snap was taken
time.sleep(6)
print ('resetting zones')
camera.restore(fade=True)


