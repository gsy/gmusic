#!/usr/bin/env python
#-*- coding:utf-8 -*-
import pygtk
pygtk.require('2.0')
import gtk
import cairo
import pango
import pangocairo
import gobject
import codecs
import re

FONT = "微软雅黑 18"

class lyricparser:
    def __init__(self,filepath):
        self.lyricfile = codecs.open(filepath,'r',encoding='utf-8')
        self.infopattern = re.compile(r'^\[(ti|ar|al|by):(\D*)\]')
        self.lyricpattern = re.compile(r'^\[(\d{2}):(\d{2}).(\d{2})\](\W*)')
        self.line_count = 0
        
    def __iter__(self):
        return self
    
    def next(self):
        if self.lyricfile.closed:
            raise StopIteration
        
        line = self.lyricfile.readline()
        if not line:
            self.lyricfile.close()
            raise StopIteration

        info = {}        
        if self.infopattern.search(line):
            group = self.infopattern.search(line).groups()
            if group[0] == 'ti':
                info['title'] = group[1]
            elif group[0] == 'ar':
                info['artist'] = group[1]
            elif group[0] == 'al':
                info['album'] = group[1]
            elif group[0] == 'by':
                info['author'] = group[1]
            return info
        elif self.lyricpattern.search(line):
            group = self.lyricpattern.search(line).groups()
            info['id'] = self.line_count
            self.line_count += 1
            info['timestamp'] = int(group[0])*60 + int(group[1])
            info['min'] = group[0]
            info['sec'] = group[1]
            info['msec'] = group[2]
            if len(info) > 2:
                info['lyric'] = group[3]
            return info
        else:
            return None        
        
class draft:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("draft")
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.set_default_size(400, 700)
        self.window.set_app_paintable(True)        
        self.window.connect("destroy",lambda w:gtk.main_quit())
        # self.window.connect("expose_event",self.on_expose)
        # self.window.connect("configure_event",self.on_expose)
        
        gobject.timeout_add(1000,self.update_lyrics)
        self.mainbox = gtk.VBox()        
        
        self.lyric_pos = 0
        self.font_height = 30
        self.lyric_offset = 0
        self.current_play_lyric_id = 5
        self.darea = gtk.DrawingArea()
        self.darea.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.darea.connect("expose_event",self.on_expose)
        # self.darea.connect("configure_event",self.on_expose)
        self.darea.set_redraw_on_allocate(True)
        self.darea.show()
        
        self.mainbox.pack_start(self.darea,True,True,0)
        self.window.add(self.mainbox)
        
        self.window.show_all()

        self.lyrics = lyricparser("/home/gsy/Music/陈奕迅/裙下之臣.lrc")
        self.background_drawn_flag=False

    def on_expose(self,widget,event):
        print "expose event"
        print widget        
        self.cr = widget.window.cairo_create()
        self.draw_background(widget)
        self.draw_lyric() 
        
        # self.update_lyrics()

        return True
        # return True

    def draw_background(self,widget):        
        self.cr.save()        
        print "draw background call"
        self.cr.set_source_rgb(0.8, 0.9, 0.8)
        self.cr.rectangle(0, 0, *widget.window.get_size())
        self.cr.fill()
        self.cr.restore()
        self.background_drawn_flag=True

    def draw_lyric(self):
        print "draw lyric call"
        self.cr.save()
        self.lyrics = lyricparser("/home/gsy/Music/陈奕迅/裙下之臣.lrc")
        layout = pangocairo.CairoContext.create_layout(self.cr)
        layout.set_alignment(pango.ALIGN_CENTER)
        desc = pango.FontDescription(FONT)
        layout.set_font_description(desc)
        
        layout.set_text("hello world")
        
        # 清理屏幕
        # self.cr.save()
        # self.cr.set_operator(cairo.OPERATOR_CLEAR)
        # self.cr.paint()
        # self.cr.restore()
            
        print "current play line: %s" % self.current_play_lyric_id
        self.cr.translate(0,-(20*self.current_play_lyric_id))
        for info in self.lyrics:
            if 'lyric' in info:
                # print info['lyric']
                layout.set_text(info['lyric'])
                # print info['lyric']
                if info['id'] == self.current_play_lyric_id: 
                    self.cr.set_source_rgba(0.15, 0.02, 0.28, 0.2)
                else:
                    self.cr.set_source_rgb(0.64, 0.62, 0.98)
                pangocairo.CairoContext.update_layout(self.cr, layout)
                pangocairo.CairoContext.show_layout(self.cr, layout)
                self.cr.move_to(50, 30 * (info['id']))
                # self.cr.translate(0, 30 * info['id'])
                                
        self.cr.restore()
        
    def update_lyrics(self):
        self.current_play_lyric_id += 1
        if self.window.window == None:
            return False
        self.window.queue_draw()
        return True
        
    # 这里比较神奇，如果self.lyrics不重新初始化的话，for循环会从上次结束的地方
    # 开始        
    def test(self):
        self.count = 0
        for info in self.lyrics:
            if self.count > 10:
                break
            self.count += 1
            if 'lyric' in info:
                print "%d %s" % (self.count,info['lyric'])

        self.count = 0
        self.lyrics = lyricparser("/home/gsy/Music/陈奕迅/裙下之臣.lrc")
        for info in self.lyrics:
            if self.count > 20:
                break
            self.count += 1
            if 'lyric' in info:
                print "%d %s" % (self.count,info['lyric'])

if __name__ == "__main__":
    t=draft()
    # t.test()
    gtk.main()
