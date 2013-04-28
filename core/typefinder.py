# detect the file type 
import pygst
pygst.require('0.10')
import gst
import thread
import gobject
gobject.threads_init()
import os, sys, time

class typefinder:
    def __init__(self, filename):                
        self.pipeline = gst.Pipeline()

        self.filesrc = gst.element_factory_make('filesrc')
        self.filesrc.set_property('location', filename)

        if 'USE_DECODEBIN2' in os.environ and os.environ['USE_DEDOCEBIN2']:
            self.decodebin = gst.element_factory_make('decodebin2')
        else:
            self.decodebin = gst.element_factory_make('decodebin')

        self.typefind = self.decodebin.get_by_name('typefind')        

        self.pipeline.add(self.filesrc, self.decodebin)
        self.filesrc.link(self.decodebin)

        self.tags = {}
        self.mimetype = None        
        self.streams = []
        self.typefind.connect('have-type', self.have_type)
            
    def have_type(self, decodebin, probability, caps):
        gst.info("caps: %s" % caps.to_string())
        self.mimetype = caps.to_string()
        print "Media type %s found, probability %d" % (self.mimetype, probability)        
    def find(self):
        # typefind will only commit to PAUSED if it auctually finds a type:
        # otherwise the state change fails 
        self.pipeline.set_state(gst.STATE_PAUSED)
        # print self.pipeline.get_state()

    def stop(self):
        self.pipeline.set_state(gst.STATE_NULL)
        mainloop.quit

    def on_message(self, bus, message):
        print message.type        
   
filename = sys.argv[1:]
tf = typefinder(filename)
print tf.find()
# thread.start_new_thread(tf.find(), ())
# mainloop = gobject.MainLoop()
# mainloop.run()
    # def end():
    #     tf.stop()
    #     mainloop.quit
    #     gobject.timeout_add(2000, end)
    #     mainloop.run()


            
        

