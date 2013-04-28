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

class outputbin(gst.Bin):
    def __init__(self):
        # gobject.GObject.__init__(self)
        
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
        adder_pad = get_adder_pad()
        for stream in self.streams:
            adder_pad = self.get_adder_pad()
            stream.ghost_src_pad.link(adder_pad)

    def get_adder_pad(self):
        return self.adder.get_request_pad("sink%d")

    def play(self):
        for stream in self.streams:
            stream.player.set_state(gst.STATE_PLAYING)
        self.set_state(gst.STATE_PLAYING)
        
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
                              self.volume)
        
        self.ghost_src_pad = gst.GhostPad("src", self.volume.get_pad("src"))

    def onDynamicPad(self, dbin, pad, islast):
        # print dbin, pad, islast
        pad.link(self.convertor.get_pad("sink"))
        # pad.link(sinkpad)

    def set_file_source(self, filepath):
        self.playfile = os.path.abspath(filepath)
        print self.playfile
        if not os.path.exists(self.playfile):
            print "File not exist"
        else:
            self.filesrc.set_property("location", self.playfile)

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
        stream.set_file_source(sys.argv[1])
        
        playbin = outputbin()
        playbin.add_stream(stream)
        # sch = scheduler(stream)
        
        DBusGMainLoop(set_as_default=True)        
        # cliplayerservice = cliplayserver(stream)
        # stream.play()
        
        playbin.play()

        loop.run()


if __name__ == '__main__':
    main()
