#!/usr/bin/env python
# coding:utf-8
import pygst
pygst.require('0.10')
import gobject
gobject.threads_init()
import gst
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import os,time

PAUSE_FADE_LENGTH = gst.SECOND / 2
# 顶层控制，由3部分组成：streambin, adder, outputbin

# controller
# 实现状态转移

# Setting GST_DEBUG_DUMP_DOT_DIR enviroment variable enable us to have
# a dotfile generated
os.environ["GST_DEBUG_DUMP_DOT_DIR"] = "/tmp"
os.putenv('GST_DEBUG_DUMP_DOT_DIR', '/tmp')

# 音量控制误差
EPSILON = 0.001

FADING_IN_START = 0
FADING_IN_END = 1
FADING_IN_DURATION = 1.5

FADING_OUT_START = 1
FADING_OUT_END = 0
FADING_OUT_DURATION = 1.2
class Engine(gobject.GObject):
    def __init__(self, player):
        gobject.GObject.__init__(self)
        self.player = player

        self.player.connect("to-play", self.schedule_play)
        self.player.connect("to-pause", self.schedule_pause)
        self.player.connect("to-stop", self.schedule_stop)
        self.player.connect("fade-out-done", self.schedule_fade_out)

    def schedule_play(self, instance, data):
        print data
        if data in [ "WAITING", "PAUSED", "STOP" ]:
            self.player.fade_in(FADING_IN_START, FADING_IN_END, FADING_IN_DURATION)
            self.player.pipeline.set_state(gst.STATE_PLAYING)
        elif data == "FADING_IN_DONE":
            pass
        elif data == "PLAYING":
            pass        
        else :
            print "state change error in schedule_play"
        
        self.player.state = "PLAYING"
        return True

    def schedule_pause(self, instance, data):
        print data
        if data in [ "WAITING", "PAUSED", "STOP" ]:
            print "stream is not playing"        
        elif data == "PLAYING":
            self.player.fade_out(FADING_OUT_START, FADING_OUT_END, FADING_OUT_DURATION)
        else:
            print "state change error in schedule_pause"
            
        self.player.state  = "PAUSED"
        return True

    def schedule_stop(self, instance, data):
        print "in schedule stop, previous state: ", data
        if data in [ "WAITING", "PAUSED" ]:
            print "stream is not playing"
        elif data == "PLAYING":
            self.player.fade_out(1, 0.1, 1)
        else:
            print "state change error in schedule_stop"
        self.player.state  = "STOP"
        return True

    def schedule_fade_out(self, instance, data):
        print "in schedule fade_out, previous state: ", data
        if data in [ "WAITING", "PLAYING" ]:
            print "stream change error"
        elif data == "PAUSED":
            self.player.pipeline.set_state(gst.STATE_PAUSED)
            self.player.state = "PAUSED"
        elif data == "STOP":
            self.player.pipeline.set_state(gst.STATE_NULL)
            self.player.state = "STOP"

        return True
# view
class Player(gobject.GObject):
    __gsignals__ = {
        'to-play' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_STRING,)),

        'to-pause' : (gobject.SIGNAL_RUN_LAST,
                      gobject.TYPE_NONE,
                      (gobject.TYPE_STRING,)),
        
        'to-stop' : (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_STRING,)), 
        
        'fade-out-done' : (gobject.SIGNAL_RUN_LAST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,))
        }
    def __init__(self):        
        gobject.GObject.__init__(self)

        self.pipeline = gst.Pipeline("player")        
        self.outputbin = outputbin()        
        self.adder = gst.element_factory_make("adder", "adder")        
        # add element
        self.pipeline.add(self.adder, self.outputbin)

        # link element
        adder_src_pad = self.adder.get_pad("src")
        adder_src_pad.link(self.outputbin.ghost_sink_pad)

        self.playing_stream = None
        
        # self.add_and_link_stream(stream2)        
        # # stream2.fade_out_and_die()
        # self.unlink_stream(stream2)

        self.state = "WAITING"

        # watch the bus
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)

    def set_play_file(self,filepath):        
        filepath = os.path.abspath(filepath)
        print filepath
        if os.path.isfile(filepath):
            print 'in gst player:filepath:%s'  % filepath
            # self.player.get_by_name("source").set_property("uri","file://" + filepath)
            self.playing_stream.filesrc.set_property("location",filepath)
        else:
            print "file doesn't exists"
    
    def play(self,filepath):
        if self.playing_stream == None:
            # 先新建stream bin,并连接
            stream = streambin(self)
            self.playing_stream = stream
            self.add_and_link_stream(self.playing_stream)
            
        self.set_play_file(filepath)
        self.emit("to-play", self.state)
    def debug(self):
        import pdb
        # dump to dot file
        dotfile = "/tmp/debug-graph.dot"
        pngfile = "/tmp/pipeline.png"
        if os.access(dotfile, os.F_OK):
            os.remove(dotfile)
        if os.access(pngfile, os.F_OK):
            os.remove(pngfile)
                
        gst.DEBUG_BIN_TO_DOT_FILE(
            self.pipeline,
            gst.DEBUG_GRAPH_SHOW_ALL,
            'debug-graph')

        dot = '/usr/bin/dot'
        os.system(dot + " -Tpng -o " + pngfile + " " + dotfile)
        pdb.set_trace()

    def set_volume(self, vol):
        self.outputbin.set_volume(vol)    

    def get_adder_pad(self):
        pad = self.adder.get_request_pad("sink%d")
        print pad
        return pad

    def add_and_link_stream(self,stream):
        self.pipeline.add(stream)
        adder_sink_pad = self.get_adder_pad()
        stream.adder_pad = adder_sink_pad
        stream.ghost_src_pad.link(adder_sink_pad)

    # 两边切断连接,通过设置异步的回调函数来切断
    def unlink_stream(self, stream):
        stream.ghost_src_pad.set_blocked_async(True, self.unlink_block_cb, stream)
        
    def unlink_block_cb(self, pad, blocked, stream):
        if stream.adder_pad == None:
            print "stream is already unlinked"
        else:
            stream.ghost_src_pad.unlink(stream.adder_pad)

        adder_sink_pad = stream.adder_pad
        adder_sink_pad.get_parent().release_request_pad(adder_sink_pad)
        
        # teturn True, 不再往下传递
        return True

    def fade_in(self, start, end, duration):
        self.playing_stream.fade_in(start, end, duration)
        
    def fade_out(self, start, end, duration):
        self.playing_stream.fade_out(start, end, duration)
    
    # 担当了部分engine的角色
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            print "End of stream"
            
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            
        elif t == gst.MESSAGE_APPLICATION:
            structure = message.structure
            name = structure.get_name()
            print name
            if name == "FADE OUT DONE":
                self.emit("fade-out-done", self.state)
        
    def get_state(self):
        ret = self.pipeline.get_state()[1]
        return ret
    
    def query_position(self):
        if gst.STATE_PLAYING == self.get_state():
            try:
                res = self.pipeline.query_position(gst.FORMAT_TIME)
            except gst.QueryError:
                res = None
            if res:
                pos, format = res
                pos -= self.playing_stream.base_time
                pos /= gst.SECOND

        return pos
        
    def query_duration(self):
        if gst.STATE_PLAYING == self.get_state():
            return self.pipeline.query_duration(gst.FORMAT_TIME, None)[0] / gst.SECOND
        
    def seek_simple(self, second):
        # event = gst.event_new_seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, gst.SEEK_TYPE_CUR, second * gst.SECOND, gst.SEEK_TYPE_NONE, -1)
        # ret = self.pipeline.send_event(event)
        # print ret
        self.playing_stream.seek(second)
    
class streambin(gst.Bin):
    def __init__(self, player):
        gst.Bin.__init__(self)
        
        self.filesrc = gst.element_factory_make("filesrc", "filesrc")
        self.preroll_queue = gst.element_factory_make("queue", "preq")
        self.decoder = gst.element_factory_make("decodebin2", "decodebin")
        self.decoder.connect("new-decoded-pad", self.on_new_decoded_pad)
        self.audioconvert = gst.element_factory_make("audioconvert", "audioconvert")
        self.rgvolume = gst.element_factory_make("rgvolume", "rgvolume")
        self.audioresample = gst.element_factory_make("audioresample", "audioresample")
        self.queue = gst.element_factory_make("queue", "queue")
        
        self.volume = gst.element_factory_make("volume", "volume")
        self.volume.connect("notify::volume", self.on_volume_change)
        
        self.volume_controller = gst.Controller(self.volume, "volume")
        self.volume_controller.set_interpolation_mode("volume", gst.INTERPOLATE_LINEAR)        
  
        self.add(self.filesrc, self.preroll_queue, self.decoder,self.audioconvert, self.rgvolume, self.audioresample, self.queue, self.volume)
        gst.element_link_many(self.filesrc, self.preroll_queue, self.decoder)
        gst.element_link_many(self.audioconvert, self.rgvolume, self.audioresample, self.queue, self.volume)
        
        # 对外连接的端口
        self.volume_src_pad = self.volume.get_pad("src")
        self.volume_src_pad.add_event_probe(self.volume_src_pad_cb)
        self.ghost_src_pad = gst.GhostPad("src", self.volume_src_pad)
        self.add_pad(self.ghost_src_pad)
        
        # 连接上的adder的端口
        self.adder_pad = None

        # fade 设置
        self.fade_start_volume = 0.0
        self.fade_end_volume = 0.0
        self.fade_duration = 0
        self.fading = False        

        self.player = player

        # seek 
        self.base_time = None
        self.adjust_probe_id = None

    def on_new_decoded_pad(self, dbin, pad, islast):
        pad.link(self.audioconvert.get_pad("sink"))

    def volume_src_pad_cb(self, pad, event):
        if event.type == gst.EVENT_EOS:
            st = gst.Structure("STREAM_EOS_MESSAGE")
            msg = gst.message_new_application(self, st)
            print msg
        elif event.type == gst.EVENT_NEWSEGMENT:
            self.adjust_stream_base_time()
        elif event.type in [ gst.EVENT_FLUSH_STOP, gst.EVENT_FLUSH_START]:
            return False
        elif event.type in [ gst.EVENT_LATENCY ]:
            # pass this signal silency
            pass
        else:
            # print event
            pass

        return True
    
    def adjust_stream_base_time(self):
        format = gst.FORMAT_TIME
        
        try:
            res = self.adder_pad.get_parent().query_position(format)
        except gst.QueryError:
            res = Nonep
        if res:
            output_pos, format = res
            self.base_time = output_pos
            print "output position:%s" % output_pos
    
        try:
            res = self.volume.query_position(format)
        except gst.QueryError:
            res = None
        if res:
            stream_pos, format = res
            print "stream position:%s" % stream_pos
            self.base_time -= stream_pos

            if self.adjust_probe_id is not None:
                print "self.adjust_probe_id is not None"
                self.ghost_src_pad.remove_buffer_probe(self.adjust_probe_id)
                self.adjust_probe_id = None
                
        else:
            if self.adjust_probe_id is None:
                self.adjust_probe_id = self.ghost_src_pad.add_buffer_probe(self.adjust_probe_id)

    def set_file_source(self, filepath):
        self.playfile = os.path.abspath(filepath)        
        if not os.path.exists(self.playfile):
            print 'File not exists'
        else:
            print "open file ", self.playfile
            self.filesrc.set_property("location", self.playfile)
            

    def set_volume(self, val):
        self.volume.set_property("volume", val)
        
    def get_volume(self):
        return self.volume.get_property("volume")

    def on_volume_change(self, element, gspec):
        message = None
        vol = self.volume.get_property("volume")
        # print "volume changed to:", vol    

        # 通过音量检测fading是否已经完成，通知上层
        # post app messages on the bus when fades complete.
        # if self.state == FADING_IN and vol >= self.fade_end_volume - 0.05:
        if self.player.state == "FADING_IN" and vol >= self.fade_end_volume - EPSILON:            
            message = "FADE IN DONE" 
                
        elif self.player.state in [ "PAUSED", "STOP" ] and vol <= 0.3 + EPSILON:
            message = "FADE OUT DONE"
            
        self.volume.set_passthrough(False)        
        # force the volume element out of passthrought mode so it
        # continues to update the controller (otherwise, if the 
        # fade out starts at 1.0, it never gets anywhere)
        
        # emit the message
        if message:
            st = gst.Structure(message)
            msg = gst.message_new_application(element, st)
            self.volume.post_message(msg)

    def fade_in(self, start, end, duration):
        self.fade_start_volume = start
        self.fade_end_volume = end
        self.fade_duration = duration * gst.SECOND
        self.fading = True
        self.start_to_fade()

    def fade_out(self, start, end, duration):
        self.fade_start_volume = start
        self.fade_end_volume = end
        self.fade_duration = duration * gst.SECOND
        self.fading = True
        self.start_to_fade()

    def start_to_fade(self):
        format = gst.FORMAT_TIME
        try:
            result = self.volume.query_position(format)
        except gst.QueryError:
            result = None
        if result:
            pos, qformat = result
        else:
            pos, qformat = 0.0, format

        if self.fade_duration > 10 * gst.SECOND:
            self.fade_duration = 3.5 * gst.SECOND
            
        self.volume.handler_block_by_func(self.on_volume_change)        
        self.volume_controller.set("volume", pos, self.fade_start_volume)
        self.volume_controller.set("volume", 0.0, self.fade_start_volume)
        self.volume_controller.set("volume", pos + self.fade_duration, self.fade_end_volume)        

        self.volume.handler_unblock_by_func(self.on_volume_change)
        self.volume.set_passthrough(False)
        
    def seek(self, second):
        print second
        event = gst.event_new_seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, gst.SEEK_TYPE_SET, second * gst.SECOND, gst.SEEK_TYPE_NONE, -1)
        ret = self.volume.get_pad("src").send_event(event)
        # ret = self.volume.send_event(event)
        print ret        
        
class outputbin(gst.Bin):
    def __init__(self):
        gst.Bin.__init__(self)        
        caps = gst.caps_from_string("audio/x-raw-int, channels=2, rate=44100, width=16, depth=16")
        
        self.blocker = gst.element_factory_make("identity", "blocker")
        
        self.capsfilter = gst.element_factory_make("capsfilter", "capasfilter")
        self.capsfilter.set_property("caps", caps)
        self.audioconvert = gst.element_factory_make("audioconvert", "audioconvert")
        self.audioresample = gst.element_factory_make("audioresample", "audioresample")
        
        self.volume = gst.element_factory_make("volume", "volume")
        
        customsink = os.environ.get("GMUSIC_GST_SINK", "gconfaudiosink")
        try:
            self.sink = gst.element_factory_make(customsink)
        except:
            self.sink = gst.element_factory_make("autoaudiosink")

        print self.sink
        
        self.add(self.blocker, self.capsfilter, self.audioconvert, self.audioresample, self.volume, self.sink)
        gst.element_link_many(self.blocker, self.capsfilter, self.audioconvert, self.audioresample, self.volume, self.sink)
        self.ghost_sink_pad = gst.GhostPad("sink", self.blocker.get_pad("sink"))
        self.add_pad(self.ghost_sink_pad)

    def set_volume(self, vol):
        self.volume.set_property("volume", float(vol))

class cliplayserver(dbus.service.Object):
    def __init__(self, player):
        bus_name = dbus.service.BusName('xidian.gsy.cliplayer', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/xidian/gsy/cliplayer')
        self.player = player
        
    @dbus.service.method('xidian.gsy.cliplayer')        
    def play(self,filepath):    
        self.player.play(filepath)

    @dbus.service.method('xidian.gsy.cliplayer')        
    def pause(self):
        self.player.pause()

    @dbus.service.method('xidian.gsy.cliplayer')        
    def stop(self):
        self.player.stop()

    @dbus.service.method('xidian.gsy.cliplayer')        
    def set_volume(self, value):
        self.player.set_volume(value)
        
    @dbus.service.method('xidian.gsy.cliplayer')                
    def fade_in(self, start, end, duration):
        self.player.fade_in(start, end, duration)

    @dbus.service.method('xidian.gsy.cliplayer')                
    def fade_out(self, start, end, duration):
        self.player.fade_out(start, end, duration)
        
    @dbus.service.method('xidian.gsy.cliplayer')
    def query_position(self):
        print self.player.query_position()
        
if __name__ == '__main__':
    loop = gobject.MainLoop()    
    
    player = Player()
    engine = Engine(player)
    
    DBusGMainLoop(set_as_default=True)
    controller = cliplayserver(player)    
    
    loop.run()
