#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys,os,time,thread
import pygtk
import random
pygtk.require('2.0')
import gtk,gobject
import pygst
pygst.require('0.10')
import gst
import pango
import warnings
import json
# from lyric import Lyricsboard

class GUI_Controller:
    """ The GUI Controller for the application """
    def __init__(self):
        self.select_file = None
        self.select_path = None
        self.current_tree_iter = None
        # dirty
        self.track_iter_list = []

        # self.file_cycle_mode = myConfig.file_cycle_mode
        # self.shuffle_mode = myConfig.shuffle_mode
        # self.play_list_mode = myConfig.play_list_mode

        self.supported_media_formats = ["mp3","wav","ogg","m4a","flac","mp4","mp2","aac","flv","MP3","WAV","OGG","M4A","FLAC","MP4","MP2","AAC","FLV"]
        # a vertical box to organize the widgets
        self.mainbox = gtk.VBox()
        
        self.menu_media = gtk.Menu()
        self.menu_play = gtk.Menu()
        self.menu_edit = gtk.Menu()
        self.menu_effect = gtk.Menu()
        self.menu_views = gtk.Menu()
        
        # Media items
        self.item_open_file = gtk.MenuItem("Open File")        
        self.item_open_file.connect("activate",self.on_open_file)
        self.item_open_directory = gtk.MenuItem("Open Directory")
        self.item_open_directory.connect("activate",self.on_open_directory)
        self.menu_media.append(self.item_open_file)
        self.menu_media.append(self.item_open_directory)
        
        # Play items
        self.item_repeat_mode = gtk.MenuItem("Repeat Mode")
        self.item_repeat_mode.connect("activate",self.enable_repeat_mode)
        self.item_shuffle_mode = gtk.MenuItem("Shuffle Mode")
        self.item_shuffle_mode.connect("activate",self.enable_shuffle_mode)
        self.menu_play.append(self.item_repeat_mode)
        self.menu_play.append(self.item_shuffle_mode)
        

        # Edit items
        self.item_delete_from_library = gtk.MenuItem("Remove form library")
        self.item_delete_from_library.connect("activate",self.on_delete_from_library)
        self.item_delete_library = gtk.MenuItem("Remove library")
        self.item_delete_library.connect("activate",self.on_delete_library)
        self.menu_edit.append(self.item_delete_from_library)
        self.menu_edit.append(self.item_delete_library)

        # Effect items        
        self.item_equalizer = gtk.MenuItem("Equalizer")
        self.item_equalizer.connect("activate", self.on_set_equalizer)
        self.menu_effect.append(self.item_equalizer)

        # views items
        self.item_artist_view = gtk.MenuItem("Artist View")
        self.item_album_view = gtk.MenuItem("Album View")
        self.menu_views.append(self.item_artist_view)
        self.menu_views.append(self.item_album_view)
        
        self.item_media = gtk.MenuItem("Media")        
        self.item_play = gtk.MenuItem("Play")
        self.item_edit = gtk.MenuItem("Edit")
        self.item_effect = gtk.MenuItem("Effect")
        self.item_views = gtk.MenuItem("Views")

        self.item_media.set_submenu(self.menu_media)
        self.item_play.set_submenu(self.menu_play)
        self.item_edit.set_submenu(self.menu_edit)
        self.item_effect.set_submenu(self.menu_effect)
        self.item_views.set_submenu(self.menu_views)

        # create a menu-bar to hold the menus
        self.menubar = gtk.MenuBar()
        self.menubar.append(self.item_media)
        self.menubar.append(self.item_play)
        self.menubar.append(self.item_edit)
        self.menubar.append(self.item_effect)
        self.menubar.append(self.item_views)
        
        # the root window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("gmusic-player")
        # self.window.set_default_size(800,600)
        # self.window.set_position(gtk.WIN_POS_CENTER)
        
        # self.window.set_default_size(myConfig.window_width,myConfig.window_height)
        # self.window.move(myConfig.window_xpos,myConfig.window_ypos)

        
        self.window.drag_dest_set(0,[],0)
        self.window.connect("drag_motion",self.on_drag_motion)
        self.window.connect("drag_drop",self.on_drag_drop)
        self.window.connect("drag_data_received",self.on_drag_data_received)
        self.window.connect("delete_event",self.on_window_delete)
        self.window.connect("destroy",gtk.main_quit,"WM destroy")
        self.window.add(self.mainbox)
        
        self.mainbox.pack_start(self.menubar,False,False,2)
        # horizatal box to holds the control buttons
        self.controlbox = gtk.HBox(False,0)        
        self.mainbox.pack_start(self.controlbox,False)
        
        # a Fixed container to contain buttons
        self.fix = gtk.Fixed()
        # self.align = gtk.Alignment(0,0,0,0)
        # self.button_layout = gtk.Layout()
        
        # self.controlbox.pack_start(self.button_layout,False,True,0)
        self.controlbox.pack_start(self.fix,False,False,0)
        
        temp_tooltip = gtk.Tooltips()
        # backward button
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_MEDIA_PREVIOUS,gtk.ICON_SIZE_BUTTON)
        self.backwardbutton = gtk.Button()
        self.backwardbutton.add(image)
        self.backwardbutton.set_size_request(30,30)
        self.backwardbutton.connect("clicked",self.on_play_prev)
        temp_tooltip.set_tip(self.backwardbutton,"play prev")
        # self.controlbox.pack_start(self.backwardbutton,False,False,0)
        self.fix.put(self.backwardbutton,0,5)
        # self.button_layout.put(self.backwardbutton,0,0)
        # self.buttonbox.add(self.backwardbutton)
        
        # play button
        self.image = gtk.Image()
        self.image.set_from_stock(gtk.STOCK_MEDIA_PLAY,gtk.ICON_SIZE_BUTTON)
        self.playbutton = gtk.Button()
        self.playbutton.add(self.image)
        self.playbutton.set_size_request(30,30)
        # self.playbutton.connect("clicked",self.on_select_file)
        self.playbutton.connect("clicked",self.on_play_pause)  
        temp_tooltip.set_tip(self.playbutton,"play/pause")
        self.fix.put(self.playbutton,30,5)
        # self.button_layout.put(self.playbutton,30,0)
        
        # forward button
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_MEDIA_NEXT,gtk.ICON_SIZE_BUTTON)
        self.forwardbutton = gtk.Button()
        self.forwardbutton.add(image)
        self.forwardbutton.set_size_request(30,30)
        self.forwardbutton.connect("clicked",self.on_play_next)
        temp_tooltip.set_tip(self.forwardbutton,"play next")
        # self.butpppton_layout.put(self.forwardbutton,60,0)
        self.fix.put(self.forwardbutton,60,5)

        # test button
        self.test_button = gtk.ToggleButton("test")
        # self.test_button.connect("clicked",self.on_open_file)
        self.test_button.connect("toggled",self.on_test)
        # self.test_button.set_mode(True)
        self.fix.put(self.test_button,90,5)
        # self.button_layout.put(self.test_button,90,0)

        self.view_button = gtk.Button("views")
        self.view_button.connect_object("event", self.change_view, self.menu_views)

        self.fix.put(self.view_button, 128, 5)
        
        self.pane = gtk.HPaned()
        # an entry to display the file path
        self.entry = gtk.Entry()
        self.entry.set_alignment(1.0)
        # self.controlbox.pack_start(self.entry,True,True,0)
        
        self.mainbox2 = gtk.VBox(False,0)
        # self.controlbox.pack_start(self.mainbox2)        
        # a slider to display the play progress
        self.slider = gtk.HScale(adjustment=None)
        self.slider.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.slider.set_digits(1)
        self.slider.set_value_pos(gtk.POS_TOP)
        self.slider.set_draw_value(False)
        # self.slider.set_range(0,100)
        self.slider.set_increments(1,10)
        self.slider.connect("value-changed",self.on_slider_change)
        self.mainbox2.pack_start(self.slider,True,False,0)        
        # label for display the play status
        self.time_label = gtk.Label()
        self.time_label.set_text("00:00 / 00:00")
        self.mainbox2.pack_start(self.time_label,True,False,0)  
        
        self.pane.pack1(self.entry,True,True)
        self.pane.pack2(self.mainbox2,True,True)
        self.controlbox.pack_start(self.pane,True,True,0)        

        # self.volume_button = gtk.ScaleButton(size=gtk.ICON_SIZE_BUTTON,
        #                                      min=0,
        #                                      max=1,
        #                                      step=0.02)
        self.volume_button = gtk.VolumeButton()
        self.volume_button.connect("value-changed",self.on_volume_changed)
        
        # self.volume_button.set_value(myConfig.volume)
        
        self.controlbox.pack_end(self.volume_button,False,False,0)

        # browser_hbox:left -- artists, right -- browser window
        self.viewbox = gtk.HBox(False,0)
        self.mainbox.pack_start(self.viewbox,True)
        
        # scrolledwindow contain the artist frame
        self.artist_scroll = gtk.ScrolledWindow()
        self.artist_treeview = gtk.TreeView()
        
        self.artists = []
        self.artist_list_store = gtk.ListStore(str)
        self.artist_list_store.append(['ALL'])
        
        self.artist_treeview.columns = [None]*1
        self.artist_treeview.columns[0] = gtk.TreeViewColumn('Artists')
        self.artist_treeview.columns[0].cell = gtk.CellRendererText()
        self.artist_treeview.columns[0].pack_start(self.artist_treeview.columns[0].cell,True)
        self.artist_treeview.columns[0].set_attributes(
            self.artist_treeview.columns[0].cell,text=0)

        self.artist_treeview.append_column(self.artist_treeview.columns[0])
        self.artist_treeview.set_model(self.artist_list_store)
        self.artist_treeview.connect("row-activated",self.on_filter_artist)

        self.artist_scroll.add(self.artist_treeview)
        self.artist_scroll.set_size_request(120,-1)
        
        self.viewbox.pack_start(self.artist_scroll,False,False,10)
        
        # scrolledwindow contain the songs browser window
        self.scrolledwindow = gtk.ScrolledWindow()
        self.viewbox.pack_start(self.scrolledwindow,True)
        # self.mainbox.pack_start(self.scrolledwindow,True)
        # self.liststore = gtk.ListStore(str)
        self.play_list_store = self.create_model()
        # self.play_list_store.foreach(self.load_play_list_func,self.play_list_store)
        
        # 加载播放列表
        # self.load_play_list()

        # artist filter model
        self.artist_show_list = self.artists[:]
        self.artist_filter_model = self.play_list_store.filter_new()
        self.artist_filter_model.set_visible_func(self.artist_visibel_cb,self.artist_show_list)
        
        # create the treeview using self.liststore as its model
        self.treeview = gtk.TreeView(self.play_list_store)
        self.treeview.set_enable_search(True)
        self.treeview.set_search_column(3)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_rules_hint(True)        
        self.create_columns(self.treeview)
        self.treeview.connect("row-activated",self.on_row_activated)

        # self.treeview.connect("button-press-event",self.block_input_func)
        
        self.tree_selection = self.treeview.get_selection()
        self.tree_selection.set_mode(gtk.SELECTION_MULTIPLE)
        
        # self.tree_selection.connect("changed",self.on_selection_changed)
        # self.tree_selection.connect("changed",self.on_select_changed)
        # self.tree_selection.connect("changed",self.on_play_list)
        
        self.scrolledwindow.add(self.treeview)        
        
        # 托盘
        # self.systray = gtk.StatusIcon()
        # self.systray.set_from_file("/home/gsy/code/python/gmusic/icons/g.png")

        # self.systray.connect("activate",self.on_systray_activate)
        # self.systray.set_tooltip("gmusic")
        # self.systray.set_visible(True)
        
        self.window.show_all()
        # fm gui initialize
        self.fm_gui()
        
    def on_set_equalizer(self, widget):
        print "set equalizer callback"

        self.combo_mandatory = {}
        self.combo_mandatory["Classical"] = "0.0:0.0:0.0:0.0:0.0:0.0:-7.2:-7.2:-7.2:-9.6"
        self.combo_mandatory["Club"] = "0.0:0.0:8:5.6:5.6:5.6:3.2:0.0:0.0:0.0"
        self.combo_mandatory["Dance"] = "9.6:7.2:2.4:0.0:0.0:-5.6:-7.2:-7.2:0.0:0.0"
        self.combo_mandatory["Full Bass"] = "-8:9.6:9.6:5.6:1.6:-4:-8:-10.4:-11.2:-11.2"
        self.combo_mandatory["Full Bass and Treble"] = "7.2:5.6:0.0:-7.2:-4.8:1.6:8:11.2:12:12"
        self.combo_mandatory["Full Treble"] = "-9.6:-9.6:-9.6:-4:2.4:11.2:16:16:16:16.8"
        self.combo_mandatory["Laptop Speakers/Headphones"] = "4.8:11.2:5.6:-3.2:-2.4:1.6:4.8:9.6:12.8:14.4"
        self.combo_mandatory["Large Hall"] = "10.4:10.4:5.6:5.6:0.0:-4.8:-4.8:-4.8:0.0:0.0"
        self.combo_mandatory["Live"] = "-4.8:0.0:4:5.6:5.6:5.6:4:2.4:2.4:2.4"
        self.combo_mandatory["Party"] = "7.2:7.2:0.0:0.0:0.0:0.0:0.0:0.0:7.2:7.2"
        self.combo_mandatory["Pop"] = "-1.6:4.8:7.2:8:5.6:0.0:-2.4:-2.4:-1.6:-1.6"
        self.combo_mandatory["Reggae"] = "0.0:0.0:0.0:-5.6:0.0:6.4:6.4:0.0:0.0:0.0"
        self.combo_mandatory["Rock"] = "8:4.8:-5.6:-8:-3.2:4:8.8:11.2:11.2:11.2"
        self.combo_mandatory["Ska"] = "-2.4:-4.8:-4:0.0:4:5.6:8.8:9.6:11.2:9.6"
        self.combo_mandatory["Soft"] = "4.8:1.6:0.0:-2.4:0.0:4:8:9.6:11.2:12"
        
        # equalizer bands
        labels = {
            0:("20Hz"),
            1:("45Hz"),
            2:("90Hz"),
            3:("200Hz"),
            4:("430Hz"),
            5:("930Hz"),
            6:("2KHz"),
            7:("4.3KHz"),
            8:("9.3KHz"),
            9:("20KHz")
            }
        self.eq_dialog = gtk.Dialog("equalizer",
                                    self.window,
                                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                    None)
        self.eq_dialog.set_size_request(500, 180)
        self.equalizer_enable = False
        
        self.band_hbox = gtk.HBox(True, 5)
        self.eq_button_hbox = gtk.HBox(False, 5)

        self.combo = gtk.combo_box_entry_new_text()
        for name in self.combo_mandatory.keys():
            self.combo.append_text(name)
        self.combo.connect("changed", self.on_eq_combo_change)
        self.combo.show()

        self.eq_check_button = gtk.CheckButton("Enable",False)
        # self.eq_check_button.connect("toggled", self.on_eq_enable)
        self.eq_check_button.show()


        # Todo: add callback funtion to save button
        self.eq_save_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_SAVE,gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.eq_save_button.add(image)
        image.show()
        self.eq_save_button.show()

        # Todo: add callback funtion to delete button
        self.eq_delete_button = gtk.Button()
        image = gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.eq_delete_button.add(image)
        image.show()
        self.eq_delete_button.show()

        self.eq_button_hbox.pack_start(self.combo, True, True, 0)
        self.eq_button_hbox.pack_start(self.eq_check_button, False, False, 0)
        self.eq_button_hbox.pack_start(self.eq_save_button, False, False, 0)
        self.eq_button_hbox.pack_start(self.eq_delete_button, False, False, 0)
        self.eq_button_hbox.show()

        self.eq_band = {}
        
        for i in range(10):
            # bind scale and label together
            bind_box = gtk.VBox()
            
            eq_adjustment = gtk.Adjustment(value=0, lower=-24, upper=12, step_incr=0.1, page_incr=1, page_size=0)
            eq_band = gtk.VScale(adjustment=eq_adjustment)
            eq_band.set_draw_value(False)
            # 翻转
            eq_band.set_inverted(True)
            eq_band.set_update_policy(gtk.UPDATE_CONTINUOUS)
            # band_freq *= 2
            # self.eq_band[i].add_mark(12.0, gtk.POS_TOP, "%sHz" % (band_freq-1))
            eq_band.connect("value-changed", self.on_set_eq_band, i)
            eq_band.show()
            self.eq_band[i] = eq_band

            label = gtk.Label("<small>" + labels[i] + "</small>")
            label.set_use_markup(True)
            label.show()
            
            bind_box.pack_start(self.eq_band[i], True, True)
            bind_box.pack_start(label, False, False)
            bind_box.show()            
                
            self.band_hbox.pack_start(bind_box, True, True, 0)

        db_label = gtk.Label("<small>" + ("12 dB\n\n\n0dB\n\n\n\n-24 dB") + "</small>")
        db_label.set_use_markup(True)
        db_label.show()
        
        empty_label = gtk.Label("<small> </small>")
        empty_label.set_use_markup(True)
        empty_label.show()
        
        self.band_hbox.pack_start(db_label, True, True)
        # self.band_hbox.pack_start(empty_label, True, True)

        self.band_hbox.show()        
        self.eq_dialog.vbox.pack_start(self.eq_button_hbox,False, False, 0)
        self.eq_dialog.vbox.pack_start(self.band_hbox, True, True, 0)
        response = self.eq_dialog.run()
        self.eq_dialog.destroy()

    
    def on_eq_combo_change(self, widget):
        text = self.combo.get_active_text()
        print text
        values = self.combo_mandatory[text]
        print values
        value = values.split(":")
        for i, gain in enumerate(value):
            print i,gain
            # FIXME: block while change
            self.eq_band[i].set_value(float(gain))

    
    def on_eq_enable(self, widget):  
        if widget.get_active():
            print "equalizer enable"
            self.equalizer_enable = True
        else:
            print "equalizer disable"
            self.equalizer_enable = False
    

    def on_set_eq_band(self, widget, data):
        band_gain = widget.get_value()
        band = "band" + str(data)
        myPlayer.set_equalizer_band(band, band_gain)
                
    def fm_gui(self):        
        self.fm_viewbox = gtk.HBox(False,0)
        self.channelbox = gtk.VBox(False,0)
        
        # 显示专辑图片
        self.album_image = gtk.Image()        
        self.album_image.set_from_file('penguin.jpg')
        self.album_image.show()
        self.image.set_size_request(120,120)
        
        # 频道列表
        self.channels = []
        self.channels_store = gtk.ListStore(str,int)
        self.channels_store.append(["ALL",0])

        self.channels_scroll = gtk.ScrolledWindow()
        self.channels_view = gtk.TreeView()
        
        self.channels_column = [None]
        self.channels_column = gtk.TreeViewColumn('Channels')
        self.channels_column.cell = gtk.CellRendererText()
        self.channels_column.pack_start(self.channels_column.cell,True)
        self.channels_column.set_attributes(self.channels_column.cell,text=0)
        self.channels_view.append_column(self.channels_column)
        self.channels_view.set_model(self.channels_store)
        # self.channels_view.connect("row-activated",self.on_select_channel)
        self.channels_view.show()
        self.channels_scroll.add(self.channels_view)
        self.channels_scroll.set_size_request(120,300)
        self.channels_scroll.show()        
        

        # self.lyricboard = Lyricsboard("/home/gsy/Music/陈奕迅/裙下之臣.lrc")
        
        # self.lyricsroll = gtk.ScrolledWindow()
        # self.lyricsroll.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
        # self.lyricsroll.add_with_viewport(self.lyricboard)
        # self.lyricboard.show()
        # self.lyricsroll.show()        

        self.channelbox.pack_start(self.channels_scroll,False)
        self.channelbox.pack_start(self.album_image,False)
        
        self.fm_viewbox.pack_start(self.channelbox,False)        
        # self.fm_viewbox.pack_start(self.lyricsroll,True)
        
        self.channelbox.show()
        self.fm_viewbox.show()

    def on_test(self,widget):
        if widget.get_active():
            self.mainbox.remove(self.viewbox)            
            self.mainbox.pack_start(self.fm_viewbox,True)
            self.on_load_channels()

        else:
            self.mainbox.remove(self.fm_viewbox)
            self.mainbox.pack_start(self.viewbox,True)

    def change_view(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            widget.popup(None, None, None, event.button, event.time)
            return True
        return False
        

    def on_load_channels(self):
        DoubanFM.get_channels()
        for channel in DoubanFM.channels:
            # print channel
            self.channels_store.append(channel)
            
    def on_systray_activate(self,widget):
        if self.window.get_property('visible'):
            self.window.hide()
        else:
            self.window.show()        

    def default_gui(self):
         self.slider.set_value(0)
         self.time_label.set_text("00:00 / 00:00")
         self.entry.set_text(self.select_file)
         self.play_thread_id = None
         # if self.current_tree_iter:
         #     self.play_list_store.set(self.current_tree_iter,6,None)

    def on_open_file(self,widget,data=None):
        dialog = gtk.FileChooserDialog("Open..",
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL,
                                        gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN,
                                        gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        # dialog.set_current_folder("~")
        
        dialog.set_current_folder(myConfig.most_recent_directory)
        
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("Music")
        filter.add_mime_type("music/mp3")
        filter.add_mime_type("music/wav")
        filter.add_mime_type("music/ogg")
        filter.add_mime_type("music/flac")
        filter.add_pattern("*.mp3")
        filter.add_pattern("*.wav")
        filter.add_pattern("*.ogg")
        filter.add_pattern("*.flac")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.temp_value = dialog.get_filename()
            print self.temp_value,'selected'
            self.temp_tag = self.get_file_tag(self.temp_value)
            self.fill_store(self.temp_tag)

        elif response == gtk.RESPONSE_CANCEL:
            print 'Closed,no files selected'            
            
        myConfig.most_recent_directory = dialog.get_current_folder()
            
        dialog.destroy()        

    def on_open_directory(self,widget,data=None):
        dialog = gtk.FileChooserDialog("Open..",
                                       self.window,
                                       gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                                       (gtk.STOCK_CANCEL,
                                        gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN,
                                        gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)        
        dialog.set_current_folder(myConfig.most_recent_directory)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            print dialog.get_filename(),"selected"
            self.current_directory = dialog.get_current_folder()
        elif response == gtk.RESPONSE_CANCEL:
            print "Close,no folder selected"            

        myConfig.most_recent_directory = dialog.get_current_folder()
        
        dialog.destroy()
        self.play_list_store.clear()

        # # THIS is for test purpose
        # self.current_directory = unicode("/home/gsy/Music",'utf8')
        
        # # AND THIS is the FINAL version 
        # self.current_directory = unicode(self.current_directory,'utf8')
        # pass directory to file_filter and then parse file to get
        # file info from there 
        # self.file_filter(self.current_directory)

        # another direction: pass directory to parse and then store
        # the infomations about the song in database
        self.parse_file_in_directory(self.current_directory)


    def on_delete_from_library(self,widget,data=None):
        self.play_list_store.remove(self.current_tree_iter)
        # position stay unchange
        self.select_path = self.play_list_store.get_path(self.current_tree_iter)
        self.current_tree_iter = self.play_list_store.iter_next(self.current_tree_iter)
        self.treeview.row_activated(self.select_path,self.treeview.get_column(1))

    def on_delete_library(self,widget,data=None):
        self.play_list_store.clear()

    def on_drag_motion(self,window,context,x,y,time):
        context.drag_status(gtk.gdk.ACTION_COPY,time)
        # returning True which means "I accepte this data".
        return True
    
    def on_drag_drop(self,window,context,x,y,time):
        self.drop_target_types = ["UTF8_STRING","text/uri-list"]

        for t in context.targets:
            print t
            if t in self.drop_target_types:
                window.drag_get_data(context,t,time)
                # only want to process the dropped data once
                break
            
        return True
    
    def on_drag_data_received(self,window,context,x,y,data,info,time):
        # got data
        receive_data = None
        try:
            received_data = data.get_text().splitlines()
        except:
            try:
                received_data = data.get_uris()
            except:
                received_data = None
                
        if received_data:
            value = received_data[0]
            value = received_data[0].split("://")[1]
            # received_data = received_data.split("://")[1]
            temp = urllib.unquote(value)
            # print value
            # print type(value)
            # print temp
            # print type(temp)
            tag = self.get_file_tag(temp)
            self.fill_store(tag)
        context.finish(True,False,time)        
        
    def create_model(self):
        '''
        Fileds:
        0 - The track number
        1 - The file path
        2 - the status of this paticular item
            FLASE = NULL
            True  = PLAYING
        3 - The title of the track,obtained from metadata
        4 - the name of the artist
        5 - the album of the track
        6 - play or pause state indicator
        7 - the duration of the track (new)
        '''
        store = gtk.ListStore(gobject.TYPE_STRING,
                              gobject.TYPE_STRING,
                              gobject.TYPE_BOOLEAN,
                              gobject.TYPE_STRING,
                              gobject.TYPE_STRING,
                              gobject.TYPE_STRING,
                              gobject.TYPE_STRING,
                              gobject.TYPE_STRING)
        return store
    
    def create_columns(self,treeView):
        self.pixbuf_renderer = gtk.CellRendererPixbuf()
        self.pixbuf_column = gtk.TreeViewColumn()
        self.pixbuf_column.pack_start(self.pixbuf_renderer,False)
        self.pixbuf_column.add_attribute(self.pixbuf_renderer,"stock-id",6)

        treeView.append_column(self.pixbuf_column)
        
        self.state_renderer = gtk.CellRendererText()
        self.state_column = gtk.TreeViewColumn("",
                                               self.state_renderer,
                                               text = 0)
        treeView.append_column(self.state_column)
        self.state_column.set_sort_column_id(0)
        
        self.title_renderer = gtk.CellRendererText()
        self.title_column = gtk.TreeViewColumn("Title",
                                               self.title_renderer,
                                               text = 3)
        self.title_column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.title_column.set_expand(False)
        self.title_column.set_resizable(True)
        treeView.append_column(self.title_column)
        self.title_column.set_sort_column_id(3)

        self.artist_renderer = gtk.CellRendererText()
        self.artist_column = gtk.TreeViewColumn("Artist",
                                                self.artist_renderer,
                                                text = 4)
        self.artist_column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.artist_column.set_expand(False)
        self.artist_column.set_resizable(True)
        treeView.append_column(self.artist_column)
        self.artist_column.set_sort_column_id(4)

        self.album_renderer = gtk.CellRendererText()
        self.album_column = gtk.TreeViewColumn("Album",
                                              self.album_renderer,
                                              text = 5)
        self.album_column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.album_column.set_expand(False)
        self.album_column.set_resizable(True)

        treeView.append_column(self.album_column)
        self.album_column.set_sort_column_id(5)

        
        self.duration_renderer = gtk.CellRendererText()
        self.duration_column = gtk.TreeViewColumn("Duration",
                                                 self.duration_renderer,
                                                 text = 7)
        treeView.append_column(self.duration_column)

    def load_play_list(self):        
        # for path in myConfig.play_list_file_path:
        #     # print path
        #     if path:
        #         tag = self.get_file_tag(path)
        #         # print tag
        #         self.fill_store(tag)

        # change to load from database
        self.load_from_db()
                
    def get_file_tag(self,filepath):
        taginfo = self.tag_init()
        taginfo['file_path'] = filepath
        # print filepath
        
        tagged_file = mutagen.File(filepath)
        if tagged_file == None:
            taginfo['title'] = filepath.split("/")[-1]
        else:
            taglist = tagged_file.keys()
            # MP3 id3 file tag            
            if "TIT2" in taglist:
                taginfo['title'] = tagged_file.get('TIT2')
                if "TPE1" in taglist:
                    taginfo['artist'] = tagged_file.get("TPE1")
                if "TALB" in taglist:
                    taginfo['album'] = tagged_file.get('TALB')
                if "TRCK" in taglist:
                    taginfo['track_num'] = tagged_file.get('TRCK')
            # m4a tags
            # elif "\xa9nam" in taglist:
                    
            # flac or ogg vorbis tags
            elif "title" in taglist:
                taginfo['title'] = tagged_file.get('title')[0]
                if "artist" in taglist:
                    taginfo['artist'] = tagged_file.get('artist')[0]
                if "album" in taglist:
                    taginfo['album'] = tagged_file.get('album')[0]
                if "tracknumber" in taglist:
                    taginfo['track_num'] = tagged_file.get('tracknumber')[0]

        # try:
        #     myPlayer.set_play_file(filepath)
        #     # self.play()
        #     myPlayer.pause()
        #     dur_sec = myPlayer.query_duration()
        #     print dur_sec            
        # except gst.QueryError:
        #     pass            
                    
        return taginfo
                
    # def get_file_tag(self,filepath):
    #     taginfo = self.tag_init()
    #     taginfo['file_path'] = filepath
    #     print filepath

    #     myTag.set_file(filepath)
    #     myTag.run()
    #     taginfo['artist'] = myTag.taginfo['artist']
    #     taginfo['album'] = myTag.taginfo['album']
    #     taginfo['title'] = myTag.taginfo['title']
    #     taginfo['track_num'] = myTag.taginfo['track-number']
        
    #     return taginfo

    def file_filter(self,directory):
        for subdir in os.listdir(directory):
            if os.path.splitext(subdir)[1].split(".")[-1] in self.supported_media_formats:
                filepath = directory + os.path.sep + subdir
                tag = self.get_file_tag(filepath)
                self.fill_store(tag)                
            if os.path.isdir(directory + os.path.sep + subdir):
                self.file_filter(directory + os.path.sep + subdir)
                
    def tag_init(self):
        tag = {}
        tag['track_num'] = None
        tag['title'] = None
        tag['file_path'] = None
        tag['status'] = False
        tag['artist'] = None
        tag['album'] = None
        return tag
    
    # take a dictionary tag as parameter
    def fill_store(self,tag):
        print tag['file_path']
        self.play_list_store.append([tag['track_num'],tag['file_path'],False,tag['title'],tag['artist'],tag['album'],None])
        
        artist_str = str(tag['artist'])
        artist_already_add_flag = True
        if not artist_str in self.artists:
            print artist_str
            self.artists.append(artist_str)
            self.artist_list_store.append([artist_str])
        # print self.artists

        # print 'artist',artist_str
        # for item in self.artist_list_store:
        #     print item[0] == artist_str
        #     if item[0] == artist_str:
        #         artist_already_add_flag = False
            
        # if artist_already_add_flag:
        #     self.artist_list_store.append([artist_str])


    def parse_file_in_directory(self, directory):
        parser.walk(directory)
        self.load_from_db()

    # 从数据库转载数据，更新视图
    def load_from_db(self):
        songs = parser.loadFromDB()
        for song in songs:
            print song
            tracknumber = song[0]
            filepath = song[1]
            title = song[2]
            artist = song[3]
            album = song[4]
            duration = song[5]
            self.play_list_store.append([tracknumber,filepath,False,title,artist,album,None,duration])
            
        # 更新artists数据
        artists = parser.queryDB("artist")

        for artist in artists:
            self.artist_list_store.append([artist[0]])
            self.artists.append(artist)            
        
    def on_filter_artist(self,treeview,path,view_column):
        # print self.artist_show_list[0][:]
        self.treeview.set_model(self.artist_filter_model)
        select_artist = treeview.get_model()[path][0]
        print "select artist:", select_artist
        del self.artist_show_list[:]

        if select_artist == "ALL":
            # print self.artists
            # 这里不能直接用self.artist_show_list = self.artists[:]
            print 'on_filter_artist: select all'
            print self.artists
            for artist in self.artists:
                self.artist_show_list.append(artist[0])
        else:
            self.artist_show_list.append(select_artist)
            
        self.artist_filter_model.refilter()

    def artist_visibel_cb(self,model,iter,data):
        # print "in artist visible callback:"
        # print model.get_value(iter,4)
        return model.get_value(iter,4) in data
    
    def set_current_play(self,data):
        self.select_file = data
        
    def get_current_play(self):
        return self.select_file
    
    def show_current_play(self):
        self.entry.set_text(self.select_file)
    
    def set_play_status(self):
        self.is_playing = True
        # self.image.set_from_file(PAUSE_ICON)

        self.play_list_store.set(self.current_tree_iter,6,gtk.STOCK_MEDIA_PLAY)
        # self.treerowref.get_model().set(temp_iter,6,gtk.STOCK_MEDIA_PLAY)
        
        self.image.set_from_stock(gtk.STOCK_MEDIA_PAUSE,gtk.ICON_SIZE_BUTTON)
        new_title = self.play_list_store.get_value(self.current_tree_iter,3)
        self.window.set_title("gmusic -" + new_title)
        # self.treeview.row_activated(self.play_list_store.get_path(self.current_tree_iter),self.treeview.get_column(3))
        self.show_current_play()

    def set_pause_status(self):
        self.is_playing = False
        if self.current_tree_iter:
            self.play_list_store.set(self.current_tree_iter,6,gtk.STOCK_MEDIA_PAUSE)
        self.image.set_from_stock(gtk.STOCK_MEDIA_PLAY,gtk.ICON_SIZE_BUTTON)

    def set_current_play_from_entry(self,widget):
        filepath = self.entry.get_text()
        print "%s" % filepath
        if os.path.isfile(filepath):
            if self.select_file and self.select_file != filepath:
                print "a new song"
                self.new_track_flag = True
                self.replay_mode = True
            self.set_current_play(widget,filepath)
        else:
            self.select_file = None
            self.new_track_flag = False             

    def play(self):
        myPlayer.play(self.select_file)
        self.set_play_status()
        gobject.timeout_add(100,self.on_update_progress)

    def pause(self):
        myPlayer.pause()
        self.set_pause_status()
                
    def on_play_pause(self,widget,data=None):
        if not gst.STATE_PLAYING in myPlayer.get_state():
            if self.current_tree_iter == None:
                self.current_tree_iter = self.play_list_store.get_iter_first()
                
            value = self.play_list_store.get_value(self.current_tree_iter,1)            
            print value + " is playing..."
            self.set_current_play(value)
            self.play()
        else:
            myPlayer.pause()
            self.set_pause_status()

    def on_play_next(self,widget):        
        myPlayer.stop()
        if self.shuffle_mode:
            if self.track_iter_list == []:
                self.enable_shuffle_mode(None)
                
            tree_iter = self.track_iter_list[random.randint(0,len(self.track_iter_list)-1)]
        else:
            if self.treeview.get_model() == self.play_list_store:
                tree_iter = self.treeview.get_model().iter_next(self.current_tree_iter)
            elif self.treeview.get_model() == self.artist_filter_model:
                temp_iter = self.artist_filter_model.convert_child_iter_to_iter(self.current_tree_iter)
                tree_iter = self.artist_filter_model.iter_next(temp_iter)

        self.on_new_track_select(tree_iter)
        
    def on_play_prev(self,widget):
        myPlayer.stop()
        if self.treeview.get_model() == self.play_list_store:
            tree_iter = self.iter_prev(self.current_tree_iter,self.play_list_store)
        elif self.treeview.get_model() == self.artist_filter_model:
            temp_iter = self.artist_filter_model.convert_child_iter_to_iter(self.current_tree_iter)
            tree_iter = self.iter_prev(temp_iter,self.artist_filter_model)

        self.on_new_track_select(tree_iter)
        
    def iter_prev(self,iter,model):
        path = model.get_path(iter)
        position = path[-1]
        if position == 0:
            return None
        prev_path = list(path)[:-1]
        prev_path.append(position - 1)
        prev = model.get_iter(tuple(prev_path))
        return prev

    def enable_repeat_mode(self,widget):
        print "Repeat mode enable"
        self.file_cycle_mode = True
        
    def on_play_cycle(self,widget):
        print "Cycle play mode enable"
        self.file_cycle_mode = True
        self.shuffle_mode = False
        
    def fill_track_iter_list_func(self,model,path,iter):
        self.track_iter_list.append(iter)    

    def enable_shuffle_mode(self,widget):
        print "shuffle mode enable"
        self.file_cycle_mode = False
        self.shuffle_mode = True
        self.track_iter_list = []
        self.play_list_store.foreach(self.fill_track_iter_list_func)

    def on_volume_changed(self,widget,value):
        myPlayer.set_volume(value)
        
    def on_slider_change(self,slider):
        seek_time_secs = slider.get_value()
        myPlayer.seek_simple(seek_time_secs)

    def on_update_progress(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if not gst.STATE_PLAYING in myPlayer.get_state():
                return False
            try:
                pos_sec = myPlayer.query_position()
                dur_sec = myPlayer.query_duration()
                self.slider.handler_block_by_func(self.on_slider_change)
                self.slider.set_range(0,float(dur_sec))
                self.slider.set_value(float(pos_sec))

                pos_str = self.convert_sec(pos_sec)
                dur_str = self.convert_sec(dur_sec)
                self.time_label.set_text(pos_str + "/" + dur_str)
                self.slider.handler_unblock_by_func(self.on_slider_change)
                
                return True
            except gst.QueryError:
                return False
            
    def on_row_activated(self,treeview,path,view_column):
        tree_iter = treeview.get_model().get_iter(path)
        # self.treerowref = gtk.TreeRowReference(treeview.get_model(),path)
        # print self.treerowref
        # print treeview.get_model() == self.play_list_store
        # print self.artist_filter_model.get_model()
        
        # print view_column
        # value = treeview.get_model()[path][view_column]
        self.on_new_track_select(tree_iter)

    def on_new_track_select(self,tree_iter):
        print "on new track select callback"
        myPlayer.stop()
        
        if self.current_tree_iter:
            self.play_list_store.set(self.current_tree_iter,6,None)
            
        # filepath = treeview.get_model().get_value(tree_iter,1)
        # print filepath
        # self.set_current_play(filepath)
        
        if self.treeview.get_model() == self.play_list_store:            
            self.current_tree_iter = tree_iter
        if self.treeview.get_model() == self.artist_filter_model:
            self.current_tree_iter = self.artist_filter_model.convert_iter_to_child_iter(tree_iter)

        filepath = self.play_list_store.get_value(self.current_tree_iter,1)
        print filepath
        self.set_current_play(filepath)

        self.play()        
        
    def on_window_delete(self,widget,data=None):
        myConfig.write_to_file(self)
        return False
    
    def convert_sec(self,s):
    # def convert_ns(self,t):
        # s,ns = divmod(t,1000000000)
        m,s = divmod(s,60)

        if m < 60:
            return "%02i:%02i" %(m,s)
        else:
            h,m = divmod(m,60)
            return "%i:%02i:%02i" %(h,m,s)
                    
    def main(self):
        gtk.main()
        return 0
        
        
    
if __name__ == "__main__":
    # myConfig = Preferences()
    myGUI = GUI_Controller()    
    gtk.gdk.threads_init()
    myGUI.main()
