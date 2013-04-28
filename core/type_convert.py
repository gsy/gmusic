#!/usr/bin/env python
# Todo:
# + GIO observe a directory
# + mutagen extract music file info
# + sqlite3 create a datebase for saving file info

# import pygst
# pygst.require('0.10')
# import gst
# import gobject
# import sys, time

# # file finder
# # A gstreamer element with one sink and two sources
# # * sink should be some audio stream
# # * audiosrc will output audio/x-raw-int, for playback
# # * filesrc will output audio/mpeg, to be saved on disk
# # Will do The right thing whether the source is an MP3 
# # stream or other format.
# class autotranscoder(gst.Bin):
#     def __init__(self):
#         gst.Bin.__init__(self)
        
#         self.typefind = gst.element_factory_make('typefind')
#         self.typefind.connect('have-type', self.have_type)
#         self.add(self.typefind)
        
#         # sink pad (to receive the audio stream)
#         self.sink = gst.GhostPad('sink', self.typefind.get_pad('sink'))
        
#         # source pads (to be connected once pipeline is complete)
#         self.audiosrc = gst.ghost_pad_new_notarget('audiosrc', gst.PAD_SRC)
#         self.filesrc = gst.ghost_pad_new_notarget('filesrc', gst.PAD_SRC)
        
#         # add pads to self
#         for p in (self.sink, self.audiosrc, self.filesrc):
#             self.add_pad(p)
            
#     def have_type(self, tf, prob, caps):
#         print "got file type: %s" % caps[0].get_name()

#         ismp3 = (caps[0].get_name() == 'audio/mpeg' and
#                  caps[0]['mpegversion'] == 1 and
#                  caps[0]['layer'] == 3)
#         if ismp3:
#             tee = gst.element_factory_make('tee', 'sink')
#             audio_q = gst.element_factory_make('queue')
#             file_q = gst.element_factory_make('queue', 'filesrc')
#             mad = gst.element_factory_make('mad', 'audiosrc')
#             self.add(tee, audio_q, file_q, mad)
            
#             gst.element_link_many(tee, audio_q, mad)
#             tee.get_request_pad('src%d').link(file_q.get_pad('sink'))
#         else:
#             decodebin = gst.element_factory_make('decodebin', 'sink')
#             convert = gst.element_factory_make('audioconvert')
#             tee = gst.element_factory_make('tee')
#             audio_q = gst.element_factory_make('queue','audiosrc')
#             file_q = gst.element_factory_make('queue')
#             lame =  gst.element_factory_make('lame', 'filesrc')
#             self.add(decodebin, convert, tee, audio_q, file_q, lame)

#             gst.element_link_many(convert, tee, file_q, lame)
#             tee.link(audio_q)
#             decodebin.connect('new-decoded-pad', self.new_decoded_pad,
#                               convert.get_pad('sink'))
#             self.typefind.link(self.get_by_name('sink'))
#             self.filesrc.set_target(self.get_by_name('filesrc').get_pad('src'))
#             self.audiosrc.set_target(self.get_by_name('audiosrc').get_pad('src'))
#             self.set_state(gst.STATE_PLAYING)
            
#         def new_decoded_pad(self, dbin, pad, islast, target):
#             pad.link(target)

# class StreamRecorder:
#     def __init__(self, uri, filename, audiosink):
#         self.pipeline = gst.Pipeline()
        
#         # create stream reader and automatic MP3 transcoder/decoder
#         self.stream = gst.element_make_from_uri(gst.URI_SRC, uri)
#         self.filter = autotranscoder()
#         self.pipeline.add(self.stream, self.filter)
        
#         # create audio and/or file sinks
#         self.audiosink = audiosink or gst.element_factory_make('fakesink')
#         if filename:
#             self.filesink = gst.element_factory_make('filesink')
#             self.filesink.set_property('location', filename)
#         else:
#             self.filesink = gst.element_factory_make('fakesink')
#         self.pipeline.add(self.audiosink, self.filesink)
        
#         # assemble pipeline
#         self.stream.link(self.filter)
#         self.filter.link_pads('audiosrc', self.audiosink, None)
#         self.filter.link_pads('filesrc', self.filesink, None)
        
#     def start(self):
#         print "starting recorder..."
#         self.pipeline.set_state(gst.STATE_PLAYING)
#         print "started recorder."

#     def stop(self):
#         self.pipeline.set_state(gst.STATE_NULL)

# def main(args):
#     from time import sleep
    
#     if len(args) != 4:
#         print 'usage: %s stream-uri output-filename duration-in-seconds' % args[0]
#         return -1
#     else:
#         uri, filename, duration = args[1:]

#     streamer = StreamRecorder(uri, filename,
#                               gst.element_factory_make('alsasink'))
#     streamer.start()
    
#     mainloop = gobject.MainLoop()
#     def end():
#         time = streamer.pipeline.query_position(gst.Format(gst.FORMAT_TIME))[0] / 1000000000.0

#         print time
#         if time >= duration:
#             streamer.stop()
#             mainloop.quit()
#             return False
#         else:
#             streamer.pipeline.set_state(gst.STATE_PLAYING)
#             return True
#     gobject.timeout_add(1000, end)
#     mainloop.run()

# if __name__ == '__main__':
#     sys.exit(main(sys.argv))



#!/usr/bin/python

import pygst
pygst.require('0.10')
import gst
import gobject
import sys, time

# A gstreamer element with one sink and two sources
#   * sink should be some audio stream
#   * audiosrc will output audio/x-raw-int, for playback
#   * filesrc will output audio/mpeg, to be saved on disk
# Will do The Right Thing (tm) whether the source is an MP3
# stream or other format.

class autotranscoder(gst.Bin):
    def __init__(self):
        gst.Bin.__init__(self)

        self.typefind = gst.element_factory_make('typefind')
        self.typefind.connect('have-type', self.have_type)
        self.add(self.typefind)

        # sink pad (to receive the audio stream)
        self.sink = gst.GhostPad('sink', self.typefind.get_pad('sink'))

        # source pads (to be connected once pipeline is complete)
        self.audiosrc = gst.ghost_pad_new_notarget('audiosrc', gst.PAD_SRC)
        self.filesrc = gst.ghost_pad_new_notarget('filesrc', gst.PAD_SRC)

        # add pads to self
        for p in (self.sink, self.audiosrc, self.filesrc): self.add_pad(p)

    def have_type(self, tf, prob, caps):
        print "got file type: %s" % caps[0].get_name()

        ismp3 = (caps[0].get_name() == 'audio/mpeg' and
caps[0]['mpegversion']==1 and caps[0]['layer']==3)
        if ismp3:
            tee = gst.element_factory_make('tee', 'sink')
            audio_q = gst.element_factory_make('queue')
            file_q = gst.element_factory_make('queue', 'filesrc')
            mad = gst.element_factory_make('mad', 'audiosrc')
            self.add(tee, audio_q, file_q, mad)

            gst.element_link_many(tee, audio_q, mad)
            tee.get_request_pad('src%d').link(file_q.get_pad('sink'))
        else:
            decodebin = gst.element_factory_make('decodebin', 'sink')
            convert = gst.element_factory_make('audioconvert')
            tee = gst.element_factory_make('tee')
            audio_q = gst.element_factory_make('queue', 'audiosrc')
            file_q = gst.element_factory_make('queue')
            lame = gst.element_factory_make('lame', 'filesrc')
            self.add(decodebin, convert, tee, audio_q, file_q, lame)

            gst.element_link_many(convert, tee, file_q, lame)
            tee.link(audio_q)
            decodebin.connect('new-decoded-pad', self.new_decoded_pad,
convert.get_pad('sink'))

        self.typefind.link( self.get_by_name('sink') )
        self.filesrc.set_target( self.get_by_name('filesrc').get_pad('src') )
        self.audiosrc.set_target( self.get_by_name('audiosrc').get_pad('src') )

        self.set_state(gst.STATE_PLAYING)

    def new_decoded_pad(self, dbin, pad, islast, target):
        pad.link(target)

class StreamRecorder:
    def __init__(self, uri, filename, audiosink):
        self.pipeline = gst.Pipeline()

        # create stream reader and automatic MP3 transcoder/decoder
        self.stream = gst.element_make_from_uri(gst.URI_SRC, uri)
        self.filter = autotranscoder()
        self.pipeline.add(self.stream, self.filter)

        # create audio and/or file sinks
        self.audiosink = audiosink or gst.element_factory_make('fakesink')
        if filename:
            self.filesink = gst.element_factory_make('filesink')
            self.filesink.set_property('location', filename)
        else:
            self.filesink = gst.element_factory_make('fakesink')
        self.pipeline.add(self.audiosink, self.filesink)

        # assemble pipeline
        self.stream.link(self.filter)
        self.filter.link_pads('audiosrc', self.audiosink, None)
        self.filter.link_pads('filesrc', self.filesink, None)

    def start(self):
        print "starting recorder..."
        self.pipeline.set_state(gst.STATE_PLAYING)
        print "started recorder."

    def stop(self):
        self.pipeline.set_state(gst.STATE_NULL)

def main(args):
    from time import sleep

    if len(args) != 4:
        print "usage: %s stream-uri output-filename duration-in-seconds" % args[0]
        return -1
    else:
        uri, filename, duration = args[1:]

    streamer = StreamRecorder(uri, filename,
gst.element_factory_make('alsasink'))
    streamer.start()

    mainloop = gobject.MainLoop()
    def end():
        time = streamer.pipeline.query_position(gst.Format(gst.FORMAT_TIME))[0] / 1000000000.0
        print time
        if time >= duration:
            streamer.stop()
            mainloop.quit()
            return False
        else:
            streamer.pipeline.set_state(gst.STATE_PLAYING)
            return True
    gobject.timeout_add(1000, end)
    mainloop.run()

if __name__=='__main__': sys.exit(main(sys.argv))
