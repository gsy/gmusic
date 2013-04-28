# vim: ts=4
###
#
# Listen is the legal property of mehdi abaakouk <theli48@gmail.com>
# Copyright (c) 2006 Mehdi Abaakouk
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA
#
###

import gobject
from time import time, sleep
import gst
import gst.interfaces
import sys

from config import config
from vfs import get_uris_from_asx, get_uris_from_m3u, get_uris_from_pls, get_mime_type, get_uris_from_xspf

from helper import Dispatcher
from library import ListenDB

from lastfm_player import LastFmPlayer, LastFmNotConnected
from player.fadebin import PlayerBin

from logger import Logger

from audioscrobbler_manager import AudioScrobblerManager

DEBUG = False
"""
gst.LEVEL_COUNT    gst.LEVEL_ERROR    gst.LEVEL_LOG      gst.LEVEL_WARNING
gst.LEVEL_DEBUG    gst.LEVEL_INFO     gst.LEVEL_NONE
"""
#gst.debug_set_default_threshold(gst.LEVEL_INFO)

class ListenPlayer(gobject.GObject, Logger):
    __gsignals__ = {
        "play-end" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                ()),
        "new-song" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                (gobject.TYPE_PYOBJECT,)),
        "instant-new-song" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                (gobject.TYPE_PYOBJECT,)),
        "paused" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                ()),
        "played" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                ()),
        "stopped" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                ()),
        "seeked" : (gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                ())
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        self.song = None
        self.__source = None
        self.__need_load_prefs = True
        self.__current_stream_seeked = False
        self.__next_already_called = False
        self.__emit_signal_new_song_id = None

        self.stop_after_this_track = False

        self.__current_song_reported = False
        
        self.__current_duration = None

        ListenDB.connect("simple-changed", self.__on_change_songs)
        LastFmPlayer.connect("new-song", self.__on_lastfm_newsong)

        self.bin = PlayerBin()
        self.bin.connect("eos", self.__on_eos)
        self.bin.connect("error", self.__on_error)
        self.bin.connect("tags-found", self.__on_tag)
        self.bin.connect("tick", self.__on_tick)
        self.bin.connect("playing-stream", self.__on_playing)

    def save_state(self):
        if self.song:
            config.set("player", "uri", self.song.get("uri"))
            config.set("player", "seek", str(self.get_position()))
            if not self.is_playable():
                state = "stop"
            elif self.is_paused():
                state = "paused"
            else:
                state = "playing"
            config.set("player", "state", state)
            self.loginfo("player status saved, %s", state)

    def load(self):
        if not self.__need_load_prefs : return
        uri = config.get("player", "uri")
        seek = int(config.get("player", "seek"))
        state = config.get("player", "state")
        play = False
        self.loginfo("player load %s in state %s at %d", uri, state, seek)
        if config.getboolean("player", "play_on_startup") and state == "playing":
            play = True

        if uri:
            song = ListenDB.get_song(uri)
            if song:
                # Disable bugged seek on startup
                self.set_song(song, play , self.get_crossfade() * 2 , seek / 1000)

    def set_source(self, source):
        # source must have get_previous_song, and get_next_song for now 
        # In the future source must be a interface and can be change
        # no check for now because source is always the current playlist
        self.__source = source
        
    def __on_playing(self, bin, uri):
        """ Signal emitted by fadebin when a new stream previously queue start """
        if uri == self.song.get("uri"):
            self.loginfo("signal playing-stream receive by %s", uri)
            config.set("player", "play", "true")
            self.emit("played")
            self.__emit_signal_new_song()

    def __emit_signal_new_song(self):
        def real_emit_signal_new_song():
            self.emit("new-song", self.song)
            self.__emit_signal_new_song_id = None

        if self.__emit_signal_new_song_id is not None:  
            gobject.source_remove(self.__emit_signal_new_song_id)
            self.__emit_signal_new_song_id = None
        self.__emit_signal_new_song_id = gobject.timeout_add(5000, real_emit_signal_new_song)

    def __on_lastfm_newsong(self, lastfmplayer, song):
        self.emit("instant-new-song", song)
        self.__emit_signal_new_song()

    def __on_change_songs(self, db, songs):
        """ Update tag of playing song """
        #FIXME: Check if it's useful
        if self.song in songs:
            self.song = songs[songs.index(self.song)]
        
    def __on_tick(self, bin, pos, duration):
        if not duration or duration <= 0:
            return
        else:
            if not self.song.get("#duration"):
                ListenDB.set_property(self.song, {"#duration": duration * 1000})
        
        self.perhap_report(pos, duration)
        
        crossfade = self.get_crossfade()
        if crossfade < 0: crossfade = 0
        remaining = duration - pos
        if crossfade:
            if remaining < crossfade:
                if not self.__next_already_called and remaining > 0:
                    self.loginfo("request new song: on tick and play-end not emit")
                    self.next(gapless=True, auto=True)
                    self.emit("play-end")
                    self.__next_already_called = True
            else:
                self.__next_already_called = False
        else:
            self.__next_already_called = False

    def __on_error(self, bin, uri):
        self.logdebug("gst error received for %s", uri)
        # Stop LastFmPlayer of the previous song
        if self.song and self.song.get("uri").find("lastfm://") == 0:
            LastFmPlayer.stop()
        self.bin.xfade_close()
        config.set("player", "play", "false")
        self.emit("paused")

        if uri == self.song.get("uri") and not self.__next_already_called:
            self.loginfo("request new song: error and play-end not emit")
            self.emit("play-end")
            self.next(gapless=True , auto=True)

        self.__next_already_called = False

    def __on_eos(self, bin, uri):
        self.loginfo("received eos for %s", uri)

        if uri == self.song.get("uri") and not self.__next_already_called:
            self.loginfo("request new song: eos and play-end not emit")
            self.emit("play-end")
            self.next(gapless=True, auto=True)

        self.__next_already_called = False
    
    def perhap_report(self, pos=None, duration=None):
        """ report song to audioscrobbler if all prerequis match
        
        Must be only call before self.song changed and uri load in fadebin to get the correct behavior """
        if not duration: duration = self.get_length()
        if not pos: pos = self.get_position()
        if self.song \
                and not self.__current_stream_seeked \
                and not self.__next_already_called \
                and not self.__current_song_reported \
                and duration > 10 and pos and \
                pos >= min(duration / 2, 240 * 1000):
            
            ListenDB.set_property(self.song, {"#playcount":self.song.get("#playcount", 0) + 1})
            ListenDB.set_property(self.song, {"#lastplayed":time()})
            stamp = str(int(time()) - duration)
            self.__current_song_reported = True
            AudioScrobblerManager.report_song(self.song, stamp)

    def __on_tag(self, bin, taglist):
        """ TAG wrapper for iRadio """
        #TODO: check this code
        if self.song and not self.song.get("title") and ListenDB.song_has_capability(self.song, "gstreamer_tag_refresh"):
            IDS = {
                "title": "artist",
                #"genre": "genre",
                #"artist": "artist",
                #"album": "album",
                #"bitrate": "#bitrate",
                #'track-number':"#track"
            }
            self.loginfo("tag found %s", taglist)
            mod = {}
            for key in taglist.keys():
                if IDS.has_key(key): 
                    if key == "lenght":    
                        value = int(taglist[key]) * 1000
                    elif key == "bitrate":
                        value = int(taglist[key] / 100)
                    elif isinstance(taglist[key], long):
                        value = int(taglist[key])   
                    else:
                        value = taglist[key]
                    mod[IDS[key]] = value
            ListenDB.set_property(self.song, mod)
    
    def current_stream_seeked(self):
        return self.__current_stream_seeked

    def get_crossfade(self):
        if config.getboolean("player", "crossfade"):
            try: crossfade = float(config.get("player", "crossfade_time"))
            except: crossfade = 3.5
            if crossfade > 50: crossfade = 3.5
        else:
            crossfade = -1
        return crossfade

    def play_new(self, song, crossfade=None, seek=None):
        self.set_song(song, True, crossfade, seek)

    def set_song(self, song, play=False, crossfade=None, seek=None):
        self.perhap_report()
        
        self.stop_after_this_track = False
       
        self.__need_load_prefs = False
        
        if seek:
            self.__current_stream_seeked = True
        else:
            self.__current_stream_seeked = False
            

        if crossfade is None: 
            crossfade = self.get_crossfade()

        uri = song.get("uri")
        
        self.loginfo("player try to load %s", uri)

        # Stop LastFmPlayer of the previous song
        if self.song and self.song.get("uri").find("lastfm://") == 0:
            if not crossfade or crossfade <= 0 or uri.find("lastfm://") == 0:
                LastFmPlayer.stop()
            else:
                gobject.timeout_add(crossfade, LastFmPlayer.stop)

        if song.get("podcast_local_uri"):
            uri = song.get("podcast_local_uri")
        elif uri.find("lastfm://") == 0:
            def play_cb(info, song):
                if info and song == self.song:
                    uri = LastFmPlayer.get_uri()
                    ListenDB.set_property(song, { "info_supp" : _("Connected, Station Found.") })
                    ret = self.bin.xfade_open(uri)
                    if ret: 
                        if play: self.play(crossfade)
                    else:
                        ListenDB.set_property(song, { "info_supp": _("Connected, Station not found!") })
                        gobject.timeout_add(5000, self.emit, "play-end")

                
            def handshake_cb(connected, song):
                if song == self.song:
                    if connected:
                        ListenDB.set_property(song, { "info_supp": _("Connected, Find station...") })
                        LastFmPlayer.change_station(song, play_cb)
                    else:
                        ListenDB.set_property(song, { "info_supp": _("Authentication failed") })
                        gobject.timeout_add(5000, self.emit, "play-end")


            LastFmPlayer.handshake(handshake_cb, song)
            ListenDB.set_property(song, {"info_supp" : _("Connection...") })
            self.song = song
            self.__current_song_reported = False
            self.emit("instant-new-song", song)
            return True

        mime_type = get_mime_type(uri)
        if mime_type in [ "audio/x-scpls", "audio/x-mpegurl", "video/x-ms-asf", "application/xspf+xml" ]:
            # TODO: Read playlist need to be async
            ntry = 2
            uris = None
            while not uris:
                if mime_type == "audio/x-scpls":
                    uris = get_uris_from_pls(uri)
                elif mime_type == "audio/x-mpegurl":
                    uris = get_uris_from_m3u(uri)
                elif mime_type == "video/x-ms-asf":
                    uris = get_uris_from_asx(uri)
                elif mime_type == "application/xspf+xml":
                    uris = get_uris_from_xspf(uri)
                ntry += 1
                if ntry > 3: break

            # TODO: Improve multiple webradio url
            if uris:
                self.loginfo("%s choosen in %s", uris[0], uri)
                uri = uris[0]
            else:
                self.loginfo("no playable uri found in %s", uri)
                uri = None


        # Remove old stream for pipeline excepted when need to fade
        if self.song and (crossfade == -1 or self.is_paused() or not self.is_playable()):
            self.logdebug("Force remove stream: %s", self.song.get("uri"))
            self.bin.xfade_close(self.song.get("uri"))

        self.song = song
        self.__current_song_reported = False

        self.emit("instant-new-song", self.song)
        ret = uri and self.bin.xfade_open(uri)
        if not ret:
            gobject.idle_add(self.emit, "play-end")
            self.next(auto=True)
        elif play: 
            self.play(crossfade, seek)
    
    def play(self, crossfade= -1, seek=None):
        if seek:
            crossfade = -1
        ret = self.bin.xfade_play(crossfade)
        if not ret:
            self.emit("paused")
            config.set("player", "play", "false")
            gobject.idle_add(self.emit, "play-end")
        else:
            if seek: self.seek(seek)
            self.emit("played")
        return ret
    
    def is_paused(self):
        return not self.bin.xfade_playing()

    def pause(self):
        self.bin.xfade_pause()
        config.set("player", "play", "false")
        self.emit("paused")

    def stop(self):
        self.stop_after_this_track = False
        self.update_skipcount()

        # Stop LastFmPlayer of the previous song
        if self.song and self.song.get("uri").find("lastfm://") == 0:
            LastFmPlayer.stop()

        self.bin.xfade_close()
        config.set("player", "play", "false")
        self.emit("stopped")

    def is_playable(self):
        return self.bin.xfade_opened()

    def set_volume(self, v):
        self.__volume = v
        self.bin.set_volume(v)

    def get_volume(self):
        return self.bin.get_volume()
    volume = property(get_volume, set_volume)


    def get_position(self):
        p = self.bin.xfade_get_time()
        if p and self.song and self.song.get("uri").find("lastfm://") == 0:
            if not self.song.get("#stream_offset"):
                ListenDB.set_property(self.song , {"#stream_offset": p })
            else:
                p = p - self.song.get("#stream_offset")
        return int(p)

    def get_length(self):
        if self.song is not None:
            p = self.bin.xfade_get_duration()
            if p != -1:
                if not self.song.get("#duration"):
                    ListenDB.set_property(self.song, {"#duration": p * 1000})
                return p
            elif self.song.get("#duration"):
                return self.song.get("#duration") / 1000
        return 0

    def seek(self, pos):
        if self.song and self.song.get("uri").find("lastfm://") == 0: return False
        if self.bin.xfade_seekable():
            self.__current_stream_seeked = True
            pos = max(0, pos)
            self.bin.xfade_set_time(pos)
            self.emit("seeked")
        else:
            self.logdebug("current song is not seekable")


    def fadeout_and_stop(self):
        remaining = self.get_length() - self.get_position()
        if remaining <= 0:
            # when there is no crossfade
            self.stop()
        else:
            handler_id = self.bin.connect("eos", lambda * args: self.stop())
            gobject.timeout_add(remaining, lambda * args: self.bin.disconnect(handler_id) is not None, handler_id)
        self.loginfo("playlist finished")

    def update_skipcount(self):
        # if not played until the end
        if not self.__current_song_reported and self.song: 
            ListenDB.set_property(self.song, {"#skipcount":self.song.get("#skipcount", 0) + 1})

        
    def previous(self):
        self.update_skipcount()
        if self.__source:
            song = self.__source.get_previous_song()
            if song:   
                self.play_new(song)
                return 
        self.stop()

    def next(self, gapless=False, auto=False):
        self.update_skipcount()
        if not self.__source: return 
        if self.stop_after_this_track and auto:
            self.loginfo("Stop after this track request")
            self.fadeout_and_stop()
        else:
            data = self.__source.get_next_song()
            if data:
                song, stop_after_this_track = data
                if gapless and \
                        config.getboolean("player", "crossfade") and \
                        config.getboolean("player", "crossfade_gapless_album") and \
                        self.song and song.get("album") == self.song.get("album"):
                    self.logdebug("request gapless to the backend")
                    self.play_new(song, 0)
                else:
                    self.play_new(song)

                self.stop_after_this_track = stop_after_this_track
                return 
            else:
                # Let's die the song
                self.fadeout_and_stop()

    def rewind(self):
        length = self.get_length()
        if not length:
            self.loginfo("Can't rewind a stream with no duration")
            return 
        jump = max(5, length * 0.05)
        pos = self.get_position()
        if pos >= 0:
            pos = max(0, pos - jump)
            self.seek(pos)

    def forward(self):
        length = self.get_length()
        if not length:
            self.loginfo("Can't forward a stream with no duration")
            return 
        jump = max(5, length * 0.05)
        pos = float(self.get_position())
        if pos >= 0: 
            print pos, jump, length
            pos = float(min(pos + jump, length)) 
            self.logdebug("request seek to %d", pos)
            self.seek(pos)

    def playpause(self):
        self.logdebug("is paused ? %s", self.is_paused())
        if not self.is_paused():
            self.pause()
        else:
            self.logdebug("is playable ? %s", self.is_playable())
            if self.is_playable():
                self.play(-1)
            else:
                self.logdebug("have song ? %s", self.song)
                if self.song:
                    # Reload the current song
                    self.play_new(self.song)
                else:
                    # not useful because it maybe already stopped
                    self.stop()

Player = ListenPlayer()

