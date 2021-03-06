#!/usr/bin/env python
#-*- coding:utf-8 -*-
import pygst
pygst.require('0.10')
import gobject
gobject.threads_init()
from threading import Thread, Lock
import gst
import sys, os
import select
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

# player:about to finish

# stable states
wating = 1
PLAYING = 2
PAUSED = 4
STOP = 8

# transition states
FADING_IN = 32
FADING_OUT = 64
FADING_OUT_PAUSED = 4096

class outputbin(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)
        
        # 用来存stream片段
        self.streams = []
        self.current_volume = 1.0
        self.bus_watch_id = None
        
        caps = gst.caps_from_string("audio/x-raw-int, channels=2, rate=44100, width=16, depth=16")
        self.pipeline = gst.Pipeline("outputplayer")

        try:
            self.output = gst.Bin("output")
            self.adder = gst.element_factory_make("adder", "outputadder")
            self.blocker = gst.element_factory_make("identity", "outputblocker")
            self.capsfilter = gst.element_factory_make("capsfilter", "outputcapsfilter")
            
            audioconvert = gst.element_factory_make("audioconvert", "outputaudioconvert")
            audioresample = gst.element_factory_make("audioresample", "ouputaudioresample")
            self.volume = gst.element_factory_make("volume", "outputvolume")
            customsink = os.environ.get("LISTEN_GST_SINK", "gconfaudioisnk")
            try:
                self.sink = gst.element_factory_make(customsink)
            except:
                self.sink = gst.element_factory_make("autoaudiosink")
                
        except(gobject.GError, gst.PluginNotFoundError):
            raise FailedBuildGstElement("player bin")            

        self.volume.set_property("volume", self.current_volume)
        try:
            self.sink.set_property("profile", 1)
        except TypeError:
            pass
        self.capsfilter.set_property("caps", caps)
        
        self.output.add(self.capsfilter, audioconvert, audioresample,
                        self.volume, self.sink)        

        gst.element_link_many(self.capsfilter, audioconvert,
                              audioresample, self.volume, self.sink)
        
        output_sink_pad = self.capsfilter.get_pad("sink")
        output_ghost_sink_pad = gst.GhostPad("sink", output_sink_pad)
        self.output.add_pad(output_ghost_sink_pad)
        
        # create silence bin
        self.silencebin = gst.Bin("silencebin")
        audiotestsrc = gst.element_factory_make("audiotestsrc", "silence")
        audiotestsrc.set_property("wave", 4)
        audioconvert = gst.element_factory_make("audioconvert", "silenceconvert")
        capsfilter = gst.element_factory_make("capsfilter", "silencecapsfilter")
        capsfilter.set_property("caps", caps)
        
        self.silencebin.add(audiotestsrc, audioconvert, capsfilter)
        gst.element_link_many(audiotestsrc, audioconvert, capsfilter)
        
        silence_src_pad = capsfilter.get_pad("src")
        silence_ghost_src_pad = gst.GhostPad("src", silence_src_pad)
        self.silencebin.add_pad(silence_ghost_src_pad)

        # assembe stuff:
        # - add everything to the pipeline
        # - link adder to output bin
        # - link silence bin to adder
        
        self.pipeline.add(self.silencebin, self.adder, self.output)
        
        adder_req_sink_pad = self.adder.get_request_pad("sink%d")
        silence_ghost_src_pad.link(adder_req_sink_pad)
        
        adder_src_pad = self.adder.get_pad("src")
        adder_src_pad.link(output_ghost_sink_pad)
        
        self.blocker = self.adder
        self.sink_state = "SINK_STOPPED"        

    def add_stream(self, stream):
        self.streams.insert(0, stream)
        
    def link_stream(self, stream):
        pass        
        
        
class streambin(gobject.GObject):
    __gproperties__ = {
        'state' : (gobject.TYPE_INT,
                   "state of the player", # nick name
                   "player's state",      # desciption
                   0,                     # mininum value
                   4096,                  # maximum value
                   0,                     # default value
                   gobject.PARAM_READWRITE) # flags
            }
    __gsignals__ = {
        'state-changed' : (gobject.SIGNAL_RUN_LAST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_INT,))
        }

    def __init__(self):
        
        gobject.GObject.__init__(self)        
        self.state = 0
        self.player = gst.Pipeline("stream-player")

        self.filesrc = gst.element_factory_make("filesrc", "file-source")
        self.preroll_queue = gst.element_factory_make("queue", "preroll-queue")
        self.decoder = gst.element_factory_make("decodebin2", "decoder")
        self.decoder.connect("new-decoded-pad", self.onDynamicPad)
        self.convertor = gst.element_factory_make("audioconvert", "audioconvert")
        self.rgvolume = gst.element_factory_make("rgvolume", "rgvolume")
        self.audioresample = gst.element_factory_make("audioresample", "audioresample")
        self.queue = gst.element_factory_make("queue", "queue")
        self.volume = gst.element_factory_make("volume", "volume")
        self.sink = gst.element_factory_make("alsasink", "sink")

        self.player.add_many(self.filesrc, self.preroll_queue, self.decoder, self.convertor, self.rgvolume, self.audioresample, self.queue, self.volume, self.sink)
        
        gst.element_link_many(self.filesrc, self.preroll_queue,
                              self.decoder)
        
        gst.element_link_many(self.convertor, self.rgvolume,
                              self.audioresample, self.queue,
                              self.volume, self.sink)        

        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)

        volume_src_pad = self.volume.get_pad("src")
        self.ghost_src_pad = gst.GhostPad("src", volume_src_pad)

        # bind signal to a callback function
        self.volume_signal_id = self.volume.connect("notify::volume", self.volume_change_cb)

        # 这里一旦设置成interpolation mode 之后，音量就变成线性调整的，
        # 就是可以设置各个时刻的音量，然后随着时间的变化，整个音量连成直线
        # 而且不能手动调整了，这就是说，要把整个音轨(track) 分割成一段
        # 一段播放，每段看成一个stream，播放时插入，放完了删除
        self.fader = gst.Controller(self.volume, "volume")
        self.fader.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)        
        self.fade_start = 0.0
        self.fade_end = 1.0
        self.fade_duration = 5
        self.fading = False
        
        self.lock = Lock()        
        
    def do_get_property(self, property):
        if property.name == 'state':
            return self.state
        else:
            raise AttributeError, 'unknown property %s' % property.name
        
    def do_set_property(self, property, value):
        if property.name == 'state':
            self.state = value
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def update_state(self):
        print 'in player, state update to', self.state
        self.set_property('state', self.state)        
        
    def set_file_source(self, filepath):
        self.playfile = os.path.abspath(filepath)
        print self.playfile
        if not os.path.exists(self.playfile):
            print "File not exist"
        else:
            self.filesrc.set_property("location", self.playfile)
        
    def play(self):
        print "playing %s" % self.playfile
        # # if not self.fading:
        # #     self.fader.unset_all("volume")
        # #     self.volume.set_property("volume", 1.0)
        # self.state = PLAYING
        # self.update_state()
        self.player.set_state(gst.STATE_PLAYING)

    def stop(self):
        # self.state = STOP
        # self.update_state()
        self.player.set_state(gst.STATE_NULL)
        
    def pause(self):
        # self.state = PAUSED
        # self.update_state()
        self.player.set_state(gst.STATE_PAUSED)
        
    def onDynamicPad(self, dbin, pad, islast):
        # print dbin, pad, islast
        pad.link(self.convertor.get_pad("sink"))
        # pad.link(sinkpad)

    def set_volume(self, value):
        print "in set_volume, volume set to ", value
        self.volume.set_property("volume", float(value))
        # self.volume.set_passthrough(False)

    def volume_change_cb(self, element, gspec):
        message = None
        self.lock.acquire()        
        vol = self.volume.get_property("volume")
        print "self.state = ", self.state
        print "volume change callback: ", vol

        # 通过音量检测fading 是否已经完成，通知上层
        # post app messages on the bus when fades complete.
        if self.state == FADING_IN and vol >= self.fade_end - 0.05:
            self.fading = False 
            self.state = PLAYING
            self.update_state()
            message = "FADE IN DONE AND PLAY"
                
        elif self.state == FADING_OUT and vol <= self.fade_end + 0.05:
            self.fading = False
            self.state = FADING_OUT_PAUSED
            self.update_state()
            message = "FADE OUT DONE AND DIE"                

        self.volume.set_passthrough(False)
        self.lock.release()
        # force the volume element out of passthrought mode so it
        # continues to update the controller (otherwise, if the 
        # fade out starts at 1.0, it never gets anywhere)
        # self.volume.set_passthrough(False)
        
        # emit the message
        if message:
            st = gst.Structure(message)
            msg = gst.message_new_application(element, st)
            self.volume.post_message(msg)
        
    # starts a volume slide on a stream.
    # volume_changed_cb watches the volume change
    # and posts a message on the bus when the slide is done.
    def start_fade(self, start_volume, end_volume, duration):
        self.fade_start = start_volume
        self.fade_end = end_volume
        self.fade_duration = duration
        
        format = gst.FORMAT_TIME
        try:
            result = self.volume.query_position(format)
        except gst.QueryError:
            result = None
        if result:
            pos, qformat = result
        else:
            pos, qformat = 0.0, format
        print pos, qformat                
        
        # def handler_block_by_func(callable)
        # blocks the all signal handler connected ot a specific callble
        # from being invoked until the callable is unblocked.
        self.volume.handler_block_by_func(self.volume_change_cb)
        # block，不会对这个函数做出响应
        self.volume.set_passthrough(False)
        
        self.volume.set_property("volume", self.fade_start)
        
        # self.fader.unset_all("volume") # bring volume change to its knee
        self.fader.set("volume", pos, start_volume)
        self.fader.set("volume", 0.0, start_volume)
        
        fade_duration = duration * gst.SECOND
        if fade_duration > 10 * gst.SECOND:
            fade_duration = 3.5 * gst.SECOND
        print "fade time: ", fade_duration / gst.SECOND
        
        self.fader.set("volume", pos + fade_duration, end_volume)        
        
        # def handler_unblock_by_func(callable)
        # unblocks all signal handler connected to a specified callable
        # thereby allowing it to be invoked when the associated signals
        # are emitted
        self.volume.handler_unblock_by_func(self.volume_change_cb)
        # self.volume继续对self.volume_change_cb 做出响应
        
        # tiny hack: if the controlled element is in passthrought mode
        # the controller won't get updated.
        self.volume.set_passthrough(False)
        
    def fade_in(self):
        self.state = FADING_IN
        self.update_state()
        self.fade_start = 0.3
        self.fade_end = 1.0
        self.fade_duration = 8
        self.start_fade(0.3, 1.0, 2)
        self.fading = True
        
    def fade_out(self):                
        self.state = FADING_OUT
        self.update_state()

        self.fade_start = 1.0
        self.fade_end = 0.3
        self.fade_duration = 5
        self.start_fade(1.0, 0.3, 1)
        self.fading = True
        
    def get_adder_pad(self):
        self.adder.get_request_pad("sink%d")

    def test(self):
        print "This is a test for dbus control."
        
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            print "End of stream"
            
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err,debug
            
        elif t == gst.MESSAGE_APPLICATION:
            structure = message.structure
            name = structure.get_name()
            print name
            if self.state == FADING_OUT_PAUSED:
                self.pause()            


class scheduler(gobject.GObject):
    def __init__(self, player):
        gobject.GObject.__init__(self)
        self.player = player
        self.player.connect('notify::state', self.schedule)
        self.previous_state = 0
        self.current_state = 0
        
    def schedule(self,state,data=None):
        print 'scheduler observed:', self.player.get_property('state')
        self.previous_state = self.current_state
        self.current_state = self.player.get_property('state')
        print 'previous state', self.previous_state
        print 'current state', self.current_state
        
        if self.previous_state == 0:
            if self.current_state == PLAYING:
                # self.player.fade_in()
                self.player.player.set_state(gst.STATE_PLAYING)

            else:
                print 'unimplement state change'
        
        elif self.previous_state == PLAYING:
            if self.current_state == PAUSED:
                # self.player.fade_out()
                # pass
                self.player.player.set_state(gst.STATE_PAUSED)
            else:
                print 'unimplement state change'            

        elif self.previous_state == FADING_OUT:
            if self.current_state == FADING_OUT_PAUSED:
                self.player.player.set_state(gst.STATE_PAUSED)
            else:
                print 'unimplement state change'        
                
        elif self.previous_state == PAUSED:
            if self.current_state == PLAYING:
                self.player.fade_in()
                self.player.player.set_state(gst.STATE_PLAYING)
            else:
                print 'unimplement state change'
            
        else:
            print 'unknown current state'                

class cliplayserver(dbus.service.Object):
    def __init__(self, stream):
        bus_name = dbus.service.BusName('xidian.gsy.cliplayer', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/xidian/gsy/cliplayer')
        self.stream = stream
        
    @dbus.service.method('xidian.gsy.cliplayer')        
    def play(self):    
        self.stream.play()

    @dbus.service.method('xidian.gsy.cliplayer')        
    def pause(self):
        self.stream.pause()

    @dbus.service.method('xidian.gsy.cliplayer')        
    def stop(self):
        self.stream.stop()

    @dbus.service.method('xidian.gsy.cliplayer')        
    def set_volume(self, value):
        self.stream.set_volume(value)
        
    @dbus.service.method('xidian.gsy.cliplayer')                
    def fade_in(self):
        self.stream.fade_in()

    @dbus.service.method('xidian.gsy.cliplayer')                
    def fade_out(self):
        self.stream.fade_out()

    @dbus.service.method('xidian.gsy.cliplayer')                
    def test(self):
        self.stream.test()
        
def main():
    if len(sys.argv) != 2:
        print "usage: ./adder filepath method"
    else:
        loop = gobject.MainLoop()        
        
        stream = streambin()
        playbin = outputbin()
        # sch = scheduler(stream)
        
        DBusGMainLoop(set_as_default=True)        
        cliplayerservice = cliplayserver(stream)
        
        stream.set_file_source(sys.argv[1])        
        stream.play()

        loop.run()


if __name__ == '__main__':
    main()
