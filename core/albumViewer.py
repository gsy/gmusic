#!/usr/bin/env python
# -*- coding:utf-8 -*-
import pygtk
pygtk.require('2.0')
import gtk
import urllib2
from albumCover import getAlbumCover
import os
import cairo, Image

class albumBoard(gtk.DrawingArea):
    def __init__(self):
        super(albumBoard, self).__init__()
        
        self.album_width = 200
        self.album_height = 200
        self.x_padding = 10
        self.y_padding = 10
        self.connect("expose_event", self.on_expose)

    def on_expose(self, widget, event):

        self.context = self.window.cairo_create()
        self.context.rectangle(event.area.x, event.area.y,
                               event.area.width, event.area.height)
        self.context.clip()
        self.draw_background(widget)
        # self.draw_album_thumbnail("gmusic.png", 20, 20, 200, 200)
        albums = ["gmusic.png", "1.png", "gmusic.png"]
        self.draw_all_albums(widget, albums)

    def draw_background(self, widget):
        self.context.save()
        
        self.context.set_source_rgb(0.1, 0.1, 0)
        self.context.rectangle(0, 0, *widget.window.get_size())
        self.context.fill()

        self.context.restore()        
        
    def draw_album_thumbnail(self, file, top, left, height, width):
        """ A thumbnail is an iamge file on disk, scale and draw it on
        the drawing arae
        
        Arguments:
        - `file`: image file on disk
        - `top`: top coordinate of the drawing starting point 
        - `left`: left coordinate of the drawing starting point 
        - `height`: fixed size
        - `width`: fixed size 
        """
        self.context.save()
        if file.endswith(".jpg"):
            file = os.path.basename(file)
            image = Image.open(file)
            name = os.path.splitext(file)[0]
            print name
            image.save(name + ".png")

        self.image_surface = cairo.ImageSurface.create_from_png(file)
            
        # calculate the scale factor
        
        self.image_height = self.image_surface.get_height()
        self.image_width = self.image_surface.get_width()
        height_ratio =  float(height) /float(self.image_height) 
        width_ratio =  float(width) / float(self.image_width)
        scale_xy = min(height_ratio, width_ratio)
        self.context.translate(left, top)
        self.context.scale(scale_xy, scale_xy)
        
        self.context.set_source_surface(self.image_surface)
        self.context.paint()            
            
        self.context.restore()
        
    def draw_all_albums(self, widget, albums):
        (self.window_width, self.window_height) = widget.window.get_size()
        if (self.window_width <= self.album_width + 2*self.x_padding) or (self.window_height <= self.album_height + 2*self.y_padding):
            print "DEBUG:drawing area too small"
            return False

        columns = (int)(self.window_width - self.x_padding) / (self.album_width + self.x_padding)
        
        left = 0
        top = 0
        count = 0
        # 横着安排album
        for i,album in enumerate(albums):
            left = (i%columns) * (self.album_width + self.x_padding)
            top = (i/columns) * (self.album_height + self.y_padding)
            
            left += self.x_padding
            top += self.y_padding
            
            print 
            print "-"*10, "count=",count, "-"*10
            print "left=", left
            print "top=", top

            self.draw_album_thumbnail(album, top, left, self.album_height, self.album_width)        

if __name__ == '__main__':
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.connect("destroy", lambda w:gtk.main_quit())
    window.set_size_request(300, 300)
    
    albumview = albumBoard()
    window.add(albumview)
    window.show_all()
    gtk.main()
        


