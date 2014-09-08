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

__all__ = ['Snapshot']

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
                   '': 'empty'}

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
        Captures current state of a zone player and
        store information in an internal dictionary snapped{}

        Details captured are those applicable to the state of the zone.
            always:
                volume = integer
                mute = True / False
                media_uri (shows full media source)
                source (interpretation of media_uri prefix = one of:
                        'stream', 'queue', 'file', 'slave', 'empty' )
                        Note: slave means music from coordinator
                        Note: empty means nothing was playing or paused

            if playing a stream:
                media_meta (Current URI MetaData)

            if a coordinator (master) not a slave, also captures:
                state = PLAYING / STOPPED / TRANSITIONING / PAUSED_PLAYBACK

            if a coordinator playing from queue also capture:
                ### track_uri (uri of current playing track) - not used!
                track_no (playlist track number)
                position (time played)

        """

        self.snapped['mute'] = self.soco.mute
        self.snapped['volume'] = self.soco.volume

        media_info = self.soco.avTransport.GetMediaInfo([('InstanceID', 0)])
        self.snapped['media_uri'] = media_info['CurrentURI']

        if self.snapped['media_uri'].split(':')[0] in self.SOURCE_LIST:
            self.snapped['source'] = self.SOURCE_LIST[
                                    self.snapped['media_uri'].split(':')[0]]
        else:
            # stream most common and not in SORCE_LIST as multiple forms
            self.snapped['source'] = 'stream'
            # meta data only used on stream
            self.snapped['media_meta'] = media_info['CurrentURIMetaData']

        if self.snapped['source'] == 'queue':
            # only need this if playing from queue
            track_info = self.soco.get_current_track_info()

            # TODO: remove?
            # self.snapped['track_uri'] = track_info['uri']

            # starts at 1
            self.snapped['track_no'] = track_info['playlist_position']
            self.snapped['position'] = track_info['position']

        # only need for master zones
        if self.snapped['source'] != 'slave':
            self.snapped['state'] = self.soco.get_current_transport_info(
                                                )['current_transport_state']

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
            # only for masters (not slaves)

            # determine what was playing based on source and re-in-state
            if img['source'] in ["queue", "stream"]:

#                 # check if meta data exists - if not use ''
#                 if 'media_meta' in img:
#                     meta_data = img['media_meta']
#                 else:
#                     meta_data = ''

                # set the URI to the queue or stream that was playing
                self.soco.avTransport.SetAVTransportURI([
                            ('InstanceID', 0),
                            ('CurrentURI', img['media_uri']),
                            ('CurrentURIMetaData', img.get('media_meta', ''))
                            ])

            if img['source'] == "queue":
                # was playing track in queue - must be an integer Track
                # numbering starts 0!
                
                # self.soco.play_from_queue(int(img['track_no']) - 1)

                # set the track number in queue with seek command
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

#             elif img['source'] == "stream":
#                 # was playing stream - resume
#                 # self.soco.play_uri(img['media_uri'], img['media_meta'])
#
#                 # The track is enqueued, now play it.
#
# #             if img['state'] != "PLAYING":  # was't Playing
# #                 # above soco commands start playing so pause it!
# #                 self.soco.pause()

            if img['state'] == "PLAYING":
                self.soco.play()


        # reset mute
        self.soco.mute = img['mute']

        # restore volume (can't change if a fixed_vol zone - so check first!)
        fixed_vol = False
        # fixed volume always shows as 100 (but so can real volume) so check
        if img['volume'] == 100:
            fixed_vol = self.soco.renderingControl.GetOutputFixed(
                              [('InstanceID', 0)])['CurrentFixed']
        if not fixed_vol:
            if fade:
                # set volume to 0 and fade up
                self.soco.volume = 0
                # turn up volume slowly - non blocking
                self.soco.renderingControl.RampToVolume(
                    [('InstanceID', 0), ('Channel', 'Master'),
                    ('RampType','SLEEP_TIMER_RAMP_TYPE'),
                    ('DesiredVolume', img['volume']),
                    ('ResetVolumeAfter', False), ('ProgramURI', '')])
            else:
                self.soco.volume = img['volume']


