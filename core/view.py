#!/usr/bin/env python
# -*- coding:utf-8 -*-
import pygtk
pygtk.require('2.0')
import gtk
import urllib2
from albumCover import getAlbumCover
import os

class albumBoard(gtk.DrawingArea):
    def __init__(self):
        super(albumBoard).__init__()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", lambda w:gtk.main_quit())        


        self.liststore = gtk.ListStore(gtk.gdk.Pixbuf)
        self.treeview = gtk.TreeView()
        self.treeview.set_model(self.liststore)
        self.load_cover("1.jpg")
        self.create_column()
        
        self.window.add(self.treeview)
        self.window.show_all()

    def create_column(self):
        renderer = gtk.CellRendererPixbuf()
        self.cover_column = gtk.TreeViewColumn("", renderer)
        self.cover_column.add_attribute(renderer, "pixbuf", 0)
        self.treeview.append_column(self.cover_column)

    def load_cover(self, file):
        pixbuf = gtk.gdk.pixbuf_new_from_file(file)
        scaled_buf = pixbuf.scale_simple(250, 250, gtk.gdk.INTERP_BILINEAR)
        self.liststore.append([scaled_buf])

    def main(self):        
        gtk.main()

    def pinImage(self, file, left, right, top, buttom, xpadding, ypadding):
        print "show file:", file
        image = gtk.Image()        
        # scale it
        pixbuf = gtk.gdk.pixbuf_new_from_file(file)
        scaled_buf = pixbuf.scale_simple(200, 200, gtk.gdk.INTERP_BILINEAR)
        image.set_from_pixbuf(scaled_buf)        
        self.table.attach(image, left, right, top, buttom, gtk.FILL|gtk.EXPAND, gtk.FILL|gtk.EXPAND, xpadding, ypadding)
    

if __name__ == '__main__':
    handler = getAlbumCover("test.mp3")
    artist = "陈奕迅"
    album = "get a life"
    title = "浮夸"
    coverAddr = handler.getCoverAddrFromDouban(artist+album)
    print coverAddr
    file = handler.downloadFile(coverAddr)    
    print "file: ", file
    filepath = os.path.realpath(file)
    print "real path:", filepath
    UI().main()
