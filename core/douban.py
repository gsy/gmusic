#!/usr/bin/env python
# -*- coding:utf-8 -*-
import pygtk
pygtk.require('2.0')
import gtk
import pygst
pygst.require('0.10')
import gst
import urllib
import urllib2
import httplib
import json
import re
import random
import contextlib
import os
from Cookie import SimpleCookie
from gmusic import GUI_Controller

class DoubanLoginException(Exception):
    pass

class GUI:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_default_size(300,200)
        self.window.set_title('douban player')
        self.window.connect('destroy',lambda w:gtk.main_quit())
        
        self.mainbox = gtk.VBox(False,0)
        self.hbox = gtk.HBox(True,2)
        
        self.playbutton = gtk.Button('play')
        self.playbutton.connect("clicked",self.on_play_pause)
        self.nextbutton = gtk.Button('next')
        self.nextbutton.connect("clicked",self.on_next)
        self.hbox.pack_start(self.playbutton,False,False,0)
        self.hbox.pack_start(self.nextbutton,False,False,0)

        # self.pixbuf = gtk.gdk.pixbuf_new_from_file("cover.jpg")
        # self.image_scroll = gtk.ScrolledWindow()
        # self.image_scroll.set_size_request(200,200)
        # self.image_scroll.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
        self.image = gtk.Image()        
        self.image.set_from_file('penguin.jpg')        
        # self.image.set_size_request(400,400)
        
        self.viewbox = gtk.HBox(False,0)
        
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
        self.channels_view.connect("row-activated",self.on_select_channel)

        self.channels_scroll.add(self.channels_view)
        self.channels_scroll.set_size_request(120,-1)

        self.viewbox.pack_start(self.channels_scroll,False)
        self.viewbox.pack_start(self.image,False)        

        self.mainbox.pack_start(self.hbox,False)
        self.mainbox.pack_start(self.viewbox,False)
        self.window.add(self.mainbox)
        self.window.show_all()

        DoubanFM.get_channels()
        for channel in DoubanFM.channels:
            # print channel            
            self.channels_store.append(channel)

        # DoubanFM.get_json_data_from_douban()
        self.play_list_store = []
        self.current_song = None
        # self.get_play_list()


        # song is a hash table
        # keys:public_time, aid, sid, title, like, album, picture(url),
        # ssid, albumtitle, url, company, artist, rating_avg,
        # length, subtype
    def get_play_list(self):
        self.play_list_store = DoubanFM.new_play_list()
        # print self.play_list_store

    def get_play_file(self):
        song_len = len(self.play_list_store)
        if song_len == 0:
            self.get_play_list()
            
        self.current_song = self.play_list_store.pop()
        print 'current song: %s' % self.current_song['title']
        print song_len,' songs total'
        
        self.album = self.current_song['albumtitle']
        self.artist = self.current_song['artist']
        self.title = self.current_song['title']
        
        self.song_url = self.current_song['url']
        print 'song url: ',self.song_url
        self.pic_url = self.current_song['picture']
        print 'picture url: ',self.pic_url
        
        Player.set_play_uri(self.song_url)

    def on_play_pause(self,widget):
        if not gst.STATE_PLAYING in Player.get_state():
            if not self.current_song:
                self.get_play_file()
            Player.play()
            self.set_play_status()
        else:
            Player.pause()

    def on_next(self,widget):
        Player.stop()
        self.get_play_file()
        Player.play()
        self.set_play_status()
        
    def set_play_status(self):
        self.window.set_title(self.artist + '-' +self.title)
        self.draw_pic(self.pic_url)
        
    def draw_pic(self,pic_url):        
        # urllib.urlretrieve(pic_url,"./cover.jpg")
        # self.image.set_from_file("./cover.jpg")
        response = urllib2.urlopen(self.pic_url)
        self.loader = gtk.gdk.PixbufLoader()
        self.loader.write(response.read())
        self.loader.close()
        
        self.pixbuf = self.loader.get_pixbuf()
        self.pixbuf = self.pixbuf.scale_simple(200,200,gtk.gdk.INTERP_BILINEAR)
        self.image.set_from_pixbuf(self.pixbuf)

    def on_select_channel(self,treeview,path,view_column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        channel_name = model.get_value(iter,0)
        channel_id = model.get_value(iter,1)
        
        print '%s channel selected(id %s)' % (channel_name,channel_id)
        
        DoubanFM.set_channel(channel_id)
        Player.stop()
        self.get_play_list()
        self.get_play_file()
        Player.play()
        self.set_play_status()

    def run(self):
        gtk.main()        

class DoubanRadio:
    def __init__(self):
        self.bid = "11111111111"
        self.request_params = None
        self.request_url = ''        
        self.current_channel = 0

    def login(self,username,password):        
        # 发起HTTP请求
        conn = httplib.HTTPConnection("www.douban.com")
        conn.request("GET","/")
        resp = conn.getresponse()
        print resp.read()
        cookie = resp.getheader('Set-Cookie')
        print cookie
        cookie = SimpleCookie(cookie)
        conn.close()
        if not cookie.has_key('bid'):
            print "cookie_error"
            raise DoubanLoginException        
        else:
            self.bid = cookie['bid']
            print self.bid
            # return self.bid
        
        # login douban

        data = urllib.urlencode({'source:':'simple',
                                 'form_email':username,
                                 'form_password':password,
                                 'remember':'on'})
        contentType = "application/x-www-form-urlencoded"
        print data
        
        cookie = 'bid="%s"' % self.bid
        print cookie
        
        headers = {"Content-Type":contentType,"Cookie":cookie}
        with contextlib.closing(httplib.HTTPSConnection("www.douban.com")) as conn:
            conn.request("POST","/accounts/login",data,headers)

            r1 = conn.getresponse()
            print r1.read()
            
            resultCookie = SimpleCookie(r1.getheader('Set-Cookie'))
            print resultCookie
            # # 通过不了有验证码的情况
            if not resultCookie.has_key('dbcl2'):
                raise DoubanLoginException()

            dbcl2 = resultCookie['dbcl2'].value
            if dbcl2 is not None and len(dbcl2) > 0:
                self.dbcl2 = dbcl2
                uid = self.dbcl2.split(':')[0]
                self.uid = uid

    def get_channels(self):
        f = urllib2.urlopen('http://www.douban.com/j/app/radio/channels')
        data = f.read()
        f.close()
        # 频道列表
        self.channels = []
        # 单个频道列表,第一项是频道名字，第二项是频道id      
        channels = json.loads(data)
        for c in channels['channels']:
            # print channel
            self.channel = []
            for key in c.keys():
                # print key, "=", c[key]
                if key == 'name':
                    self.channel.append(c[key])
                elif key == 'channel_id':
                    self.channel.append(c[key])
            # print self.channel
            self.channels.append(self.channel)

        # print channels['channels']
            # for k in channel.keys():
            #     print k,"=", channel[k]
            # self.channels[channel['name_en']] = channel['channel_id']

    def set_channel(self,channel):
        self.current_channel = channel

    def get_json_data_from_douban(self):
        page_url = 'http://douban.fm/j/mine/playlist?type=n&'
        channel_url = 'channel=%s' % self.current_channel
        site_url = '&from=mainsite'
        
        # getPlayList
        request_url = page_url + channel_url + site_url
        print request_url
        
        page_source = None
        
        try:
            # 使用urllib请求
            page_source = urllib2.urlopen(request_url)
        except Exception,data:
            print Exception,":",data
        # 抓取页面数据
        page_data = page_source.read()
        # 这里的pageData是str类型
        # 使用JsonLIB将数据解析为Json
        self.jsonData = json.loads(page_data)
        # print self.jsonData
        
    def new_play_list(self):
        self.get_json_data_from_douban()
        playlist = []
        for song in self.jsonData['song']:
            # print song
            playlist.append(song)

        return playlist
        
    # 返回json数据控制douban.fm
    def set_douban_json(self):
        start_url = "http://douban.fm/?start=%sg%sg0" % (self.sid,self.ssid)
        print "start url: ",start_url
        
class gstPlayer:
    def __init__(self):
        self.player = gst.Pipeline("player")

        # Elements
        self.source = gst.element_factory_make("uridecodebin")
        self.conv = gst.element_factory_make("audioconvert")
        self.rsmpl = gst.element_factory_make("audioresample")
        self.sink = gst.element_factory_make("alsasink")

        self.source.connect("pad-added",self.on_pad_added)
        self.player.add(self.source,self.conv,self.rsmpl,self.sink)
        
        gst.element_link_many(self.conv,self.rsmpl,self.sink)
        
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos",self.on_eos)
        self.bus.connect("message::error",self.on_error)

    def set_play_uri(self,uri):
        self.source.set_property('uri',uri)
    
    def play(self):
        self.player.set_state(gst.STATE_PLAYING)
    
    def pause(self):
        self.player.set_state(gst.STATE_PAUSED)        

    def stop(self):
        self.player.set_state(gst.STATE_NULL)

    def get_state(self):
        return self.player.get_state()    

    def on_pad_added(self,element,pad):
        caps = pad.get_caps()
        name = caps[0].get_name()
        print 'on_pad_added',name
        if name == 'audio/x-raw-float' or name == 'audio/x-raw-int':
            if not self.conv.get_pad('sink').is_linked():
                pad.link(self.conv.get_pad('sink'))

    def on_eos(self,bus,msg):
        print 'on_eos'
        # self.player.set_state(gst.STATE_NULL)
        MyGUI.on_next(None)

    def on_error(self,bus,msg):
        error = msg.parse_error()
        print 'on_error:',error[:]
        
if __name__ == "__main__":
    DoubanFM = DoubanRadio()
    MyGUI = GUI()
    Player = gstPlayer()

    MyGUI.run()
    
    # DoubanFM.login("gtcxg@hotmail.com","wilkii")
    # DoubanFM.get_json_data_from_douban()
    # DoubanFM.new_play_list()
    # MyGUI.get_play_list()
    # MyGUI.get_play_file()
    
