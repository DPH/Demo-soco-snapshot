# -*- coding: utf-8 -*-
"""
Snapshot Plugin

Captures the current state of a zone player
Allows retrieval of the image to save or change
Allows reset of the zone player using the saved image

Note:   on a coordinator zone (master) changes what is playing etc.
        on a slave only sets volumes
"""

from __future__ import unicode_literals
from ..plugins import SoCoPlugin
from ..utils import really_utf8
from urllib import unquote
import logging

__all__ = ['Snapshot']

log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(levelname)-8s-> %(message)s  "
                           "(%(module)s: %(lineno)s)",
                    datefmt="%m/%d/%Y %I:%M:%S")
logging.getLogger(__name__).setLevel(logging.DEBUG)

class Snapshot(SoCoPlugin):
    """
    A SoCo Plug-in class to capture a snapshot of a  master zone
    and to restore the state at a later point.

    Use case: zone playing - snapshot zone, play an announcement,
              then restore zone to previous playing state.
    Handles everything for a zone: volume, mute, what's playing

    Public functions::
        snap() -- Captures current state of a zone
        restore(optional image dictionary) -- sets zone back to snapped state

    Properties::
        image -- state info in a dictionary can be stored and used later.
    """

    # list of non stream sources:
    SOURCE_LIST = {'x-rincon-queue':'queue',
                   'x-file-cifs':'file',
                   'x-rincon':'slave',
                   'x-sonosapi-stream':'stream',
                   '': 'no music'}

    def __init__(self, soco):
        """ Initialize the plug-in"""
        super(Snapshot, self).__init__(soco)
        self.snapped = {}

    @property
    def image(self):
        """ image property can be extracted"""
        return self.snapped

    def snap(self):
        """
        Captures current state of a zone player and stores information
        in an internal dictionary snapped{}

        Details captured are those applicable to the state of the zone.
            Always capture:
                volume = integer
                mute = True / False
                media_uri (shows full media source)
                source - an interpretation of media_uri prefix:
                    'stream': playing radio or other stream
                    'queue':  playing form queue
                    'file':   direct play of file
                    'slave':  music source is a coordinator zone player
                    'no music':  nothing was playing or queued

            stream source capture:
                media_meta (Current URI MetaData)

            queue source capture:
                track_no (playlist track number)
                position (time played)

            if source is coordinator (master) - not slave:
                state = PLAYING / STOPPED / TRANSITIONING / PAUSED_PLAYBACK

        """
        self.snapped['mute'] = self.soco.mute
        self.snapped['volume'] = self.soco.volume

        media_info = self.soco.avTransport.GetMediaInfo([('InstanceID', 0)])
        self.snapped['media_uri'] = media_info['CurrentURI']

        source = self.SOURCE_LIST.get(
            self.snapped['media_uri'].split(':')[0],'unknown')
        self.snapped['source'] = source

        if source == 'unknown':
            log.error('unknown Sonos source: {}'.
                      format(self.snapped['media_uri'].split(':')[0]))

        if source == 'stream':
            # meta data only used on stream
            self.snapped['media_meta'] = media_info['CurrentURIMetaData']

        if source == 'queue':
            # only need this if playing from queue
            track_info = self.soco.get_current_track_info()
            self.snapped['track_no'] = track_info['playlist_position']
            self.snapped['position'] = track_info['position']

        # only need for master zones
        if source != 'slave':
            self.snapped['state'] = self.\
                soco.get_current_transport_info()['current_transport_state']

    def restore(self, fade=False, img=None):
        """
        restore zone state

        :param fade: fade in (ToDo)
        :param img: image to use (default is internal captured image
        :return:
        """

        if not img:
            # use internal snapshot if none provided
            img = self.snapped

        if img['source'] != 'slave':
            # for masters (coordinators) not slaves

            # determine what was playing based on source and re-in-state
            if img['source'] in ["queue", "stream"]:

                # set the URI to the queue or stream that was playing
                # include meta data if it existed else ''

                #meta = img.get('media_meta', '').encode('utf-8')
                # print img

                restore_meta = img.get('media_meta', '')
                # restore_meta = restore_meta #.encode('utf-8')
                # print type(restore_meta)

                self.soco.avTransport.SetAVTransportURI([
                            ('InstanceID', 0),
                            ('CurrentURI', img['media_uri']),
                            ('CurrentURIMetaData', restore_meta)
                            ])

            if img['source'] == "queue" and img['track_no']>'0':
                # was playing track in queue - must be an integer Track
                # if track number 0 then nothing in queue - so skip

                # set the track number in queue with seek command
                # use direct call as play_from_queue starts track playing
                self.soco.avTransport.Seek([
                        ('InstanceID', 0),
                        ('Unit', 'TRACK_NR'),
                        ('Target', int(img['track_no']))
                        ])

                # set position in track with seek command
                # seek requires 2 digit hour only 1 returned from soco so add it
                self.soco.avTransport.Seek([
                        ('InstanceID', 0),
                        ('Unit', 'REL_TIME'),
                        ('Target', ('0' + img['position']))
                        ])

            if img['state'] == "PLAYING":
                self.soco.play()

        # --reset mute
        self.soco.mute = img['mute']

        # --restore volume
        # can't change if zone player set to fixed volume so check first
        # fixed volume always has volume set to 100 (we have the volume stored)
        # but could be real volume so check (read OutputFixed from zone)
        if img['volume'] == 100:
            fixed_vol = self.soco.renderingControl.GetOutputFixed(
                [('InstanceID', 0)])['CurrentFixed']
        else:
            fixed_vol = False

        if not fixed_vol:
            if fade:
                # set volume to 0 and fade up (non blocking)
                self.soco.volume = 0
                self.soco.renderingControl.RampToVolume(
                    [('InstanceID', 0), ('Channel', 'Master'),
                    ('RampType','SLEEP_TIMER_RAMP_TYPE'),
                    ('DesiredVolume', img['volume']),
                    ('ResetVolumeAfter', False), ('ProgramURI', '')])
            else:
                self.soco.volume = img['volume']


