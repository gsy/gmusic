#!/usr/bin/env python
# -*- coding: utf-8
import pygtk
pygtk.require('2.0')
import gtk

class albumViewer:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", lambda w:gtk.main_quit())

        self.table = gtk.Table(1, 2, False)
        self.table.set_row_spacings(10)
        self.table.set_col_spacings(10)
        
        image1 = gtk.Image()
        image1.set_from_file("1.jpg")
        self.table.attach(image1, 0, 1, 0, 1, gtk.FILL|gtk.EXPAND, gtk.FILL|gtk.EXPAND, 10, 10)
        self.scaleImage(image1, "1.jpg")
        
        image2 = gtk.Image()
        image2.set_from_file("2.jpg")
        self.table.attach(image2, 0, 1, 1, 2, gtk.FILL|gtk.EXPAND, gtk.FILL|gtk.EXPAND, 10, 10)
        self.scaleImage(image2, "2.jpg")
        
        self.window.add(self.table)
        self.window.show_all()

    def scaleImage(self, image, file):
        pixbuf = gtk.gdk.pixbuf_new_from_file(file)
        scaled_buf = pixbuf.scale_simple(200, 200, gtk.gdk.INTERP_BILINEAR)
        image.set_from_pixbuf(scaled_buf)    

    def main(self):
        gtk.main()

if __name__ == '__main__':
    albumViewer().main()
    
