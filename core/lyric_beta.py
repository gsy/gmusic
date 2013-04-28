#!/urs/bin/env pyhon
#-*- coding:utf-8 -*-
# 显示歌词的控件
import pygtk
pygtk.require('2.0')
import gtk
import gobject

import cairo
import pango
import pangocairo
import math
import logging
import os, codecs, re, sys

from preference import PreferenceDialog
from config import config
from cliplayer import Player, Engine, cliplayserver
from dbus.mainloop.glib import DBusGMainLoop

# 用pango渲染字体
# 需要收集信息：
# + 整个窗口的尺寸,window_width, window.height
# + 一行字的尺寸,font_width, font_height
# 需要计算：
# + 垂直方向：行间距
# + 水平方向：离窗口右端的距离，以便在一行显示不下时移动句子
# update:以上的信息可以在pango layout 里得到
# 歌词匹配：
# 从播放器得到当前播放的时间，从歌词文件找到在播放时间范围内的歌词，渲染成不同的句子。
# 滚动：滚动的总距离是一个句子的长度，总时间是一句歌词的时间，速度可算。定时匀速滚动。
# Todo:如何渲染layout中的一个特定句子。

LYRIC ="""
              少壮不努力
              老大徒悲伤"""

class Lyric(object):
    def __init__(self):
        self.text = None
        self.start_time = None
        self.end_time = None
        self.linecount = None
        
    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text

    def set_start_time(self, minute, second, msecond):            
        # Todo: raise exception if time fommat not correct
        self.start_time = float(minute) * 60.0 + float(second) + float(msecond) / 1000.0

    def get_start_time(self):
        return self.start_time

    def set_end_time(self, minute, second, msecond):
        self.end_time = float(minute) * 60.0 + float(second) + float(msecond) / 1000.0
        
    def get_end_time(self):
        return self.end_time

    def get_duration(self):
        return (self.end_time - self.start_time)

    def get_linecount(self):
        return self.linecount

# 想法：把整个lyric file解析出来，把整个歌词一次写入到pango layout上，
# 当前句的背景色和歌词颜色单独设置。滚动效果是靠定时+cairo.translate或者
# cairo.move_to实现的，就是写的时候坐标先定下来，然后画板的坐标向上移，
# 看起来，就是歌词下移
class LyricParser(object):    
    TITLE_RE = r'^\s*\[(ti)\s*:\s*(.*)\]\s*$'
    ARTIST_RE = r'^\s*\[(ar)\s*:\s*(.*)\]\s*$'
    ALBUM_RE = r'^\s*\[(al)\s*:\s*(.*)\]\s*$'
    AUTHOR_RE = r'^\s*\[(by)\s*:\s*(.*)\]\s*$'
    
    LYRIC_RE = r'^\[(\d{2}):(\d{2}).(\d{2})\](.*)$'
    BLANK_RE = r'^\s*$'    

    def __init__(self, filename):
        filename = os.path.expanduser(filename)
        # self.file = codecs.open(filename, 'r', encoding='utf-8')        
        self.file = filename
        self.title = None
        self.artist = None
        self.album = None
        self.author = None      # 歌词文件的作者

        self.linecount = 0
        self.lyrics = []
        self.text = ""
        
        try:
            self.read_file()
        except IOError:
            sys.stderr.write(
                "Could not read {filename}\n".format(filename=self.file))
        self.sort()

        # self.test()
            
    def read_file(self):        
        with open(self.file) as file:
            for line in file.readlines():
                if self.is_blank(line): pass
                elif self.is_title(line): pass
                elif self.is_artist(line): pass
                elif self.is_album(line): pass
                elif self.is_author(line): pass
                elif self.is_lyric(line): pass                    
            
    def is_blank(self, line):
        return re.match(self.BLANK_RE, line)
    
    def is_title(self, line):
        match = re.match(self.TITLE_RE, line)
        if match:
            key = match.group(1)
            val = match.group(2)
            # print key, ' --- ', val
            
    def is_artist(self, line):
        match = re.match(self.ARTIST_RE, line)
        if match:
            key = match.group(1)
            val = match.group(2)
            # print key, ' --- ', val

    def is_album(self, line):
        match = re.match(self.ALBUM_RE, line)
        if match:
            key = match.group(1)
            val = match.group(2)
            # print key, ' --- ', val

    def is_author(self, line):
        match = re.match(self.AUTHOR_RE, line)
        if match:
            key = match.group(1)
            val = match.group(2)
            # print key, ' --- ', val

    def is_lyric(self, line):
        match = re.match(self.LYRIC_RE, line)
        if match:
            minute = match.group(1)
            second = match.group(2)
            msecond = match.group(3)
            text = match.group(4)
            
            # print minute, second, msecond, text
            
            # 创建对象
            lyric = Lyric()
            lyric.set_text(text)
            lyric.set_start_time(minute, second, msecond)
            
            self.lyrics.append(lyric)
            self.text += text
            self.text += "\n"

    def sort(self):
        """根据开始时间把lyric排序"""
        sorted(self.lyrics,
               cmp=lambda x, y: cmp(x.start_time, y.start_time))

        for i,lyric in enumerate(self.lyrics):
            self.lyrics[i].linecount = i
        
        for i, lyric in enumerate(self.lyrics):
            if i is not len(self.lyrics)-1:
                self.lyrics[i].end_time = self.lyrics[i+1].start_time
        

        for lyric in self.lyrics:
            print lyric.start_time
            print lyric.linecount, ' - ', lyric.text
            print lyric.end_time
            print "------------------------\n"
                
            # print "start:{start} -- {text} :end{end}".format(start=lyric.start_time, text=lyric.text, end = lyric.end_time)
        
    def get_lyric_by_time(self, time):
        """根据给出的时刻，返回包含这个时刻的lyric"""
        for lyric in self.lyrics:
            if lyric.start_time <= time and lyric.end_time >= time:
                return lyric

    def get_lyric_by_range(self, start, end):
        result = []
        for i in range(start, end):
            print i
            result.append(self.lyrics[i].text)

        return result

    def test(self):
        print self.get_lyric_by_time(171).text
        result = self.get_lyric_by_range(0, 10)
        for lyric in result:
            print lyric
        
class LyricBoard(gtk.DrawingArea):
    def __init__(self):
        super(LyricBoard, self).__init__()
        # self.fontdes = pango.FontDescription(fontdes)
        self.connect("expose_event", self.on_expose)
        
        # 不是同一个config
        # self.config = Config()
        # self.config.load()      # 读入
        
        config.load()           # 先读入，不然什么都找不到
        # config.connect("config-changed", self.draw)
        config.connect("config-changed", self.get_font_and_bgcolor)
        
        # --------------- logger --------------
        self.logger = logging.getLogger("lyricboard")
        # 低于level的log会被抛弃
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(levelname)-8s %(message)s")
        handler = logging.StreamHandler()        
        handler.setFormatter(formatter)
        
        # add some handler to log
        self.logger.addHandler(handler)

        handler = logging.FileHandler('lyricboard', 'w')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # self.logger.debug("hello world")        

        # 初始化字体和颜色
        self.get_font_and_bgcolor()   

        # 定时滚动歌词
        gobject.timeout_add(1000, self.on_time_out)
        self.time_count = 0

        # 当前播放时刻，定时查询
        self.current_play_time = None
        self.current_lyric = None
        self.current_linecount = None
        self.lyrictext = parser.text        
        
    def get_font_and_bgcolor(self, *args):
        self.font = config.get("OSD", "font")
        self.bg_red = config.get("OSD","background_red")
        self.bg_green = config.get("OSD","background_green")
        self.bg_blue = config.get("OSD","background_blue")
        
        if self.font is None:
            self.font = "Sans 12"
        if self.bg_red is None:
            self.bg_red = 0
        if self.bg_green is None:
            self.bg_green = 0
        if self.bg_blue is None:
            self.bg_blue = 0

    def on_expose(self, widget, event):
        """
        self.context  ---->    cairo context
        self.pc       ---->    pangocairo context
        self.px       ---->    pango context
        """
        # print widget, event
        # create the cairo context
        # 上下文环境，用于保存全局信息
        self.context = self.window.cairo_create()        
        self.pc = pangocairo.CairoContext(self.context)
        self.px = self.get_pango_context()
         
        self.context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        self.context.clip()
        self.draw_background(widget)
        self.draw_lyric(widget)

    def draw_background(self, widget):
        
        # 保护上下文环境
        self.context.save()
        # print "--------------- color -----------------"
        # print self.bg_red, self.bg_green, self.bg_blue
        # print "------------ end color ----------------"
        self.context.set_source_rgb(float(self.bg_red)/65536.0,
                                    float(self.bg_green)/65536.0,
                                    float(self.bg_blue)/65536.0)
        # 整个widget大小
        # 整个lyricboard大小
        self.context.rectangle(0, 0, *widget.window.get_size())
        self.context.fill()
        
        # 恢复环境
        self.context.restore()

    def draw_lyric(self, widget):
        self.context.save()        
        string = "Cairo"

        self.window_x = widget.get_allocation().x
        self.window_y = widget.get_allocation().y
        self.window_width = widget.get_allocation().width
        self.window_height = widget.get_allocation().height
        
        self.context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                                      cairo.FONT_WEIGHT_NORMAL)

        self.context.set_font_size(52.0)
        extents = self.context.text_extents(string)
        x_bearing, y_bearing, ex_width, ex_height, x_advance, y_advance = extents
        start_x = self.window_width/2 - (ex_width/2 + x_bearing)
        start_y = self.window_height/2 - (ex_height/2 + y_bearing)
        self.context.move_to(start_x, start_y)
        
        self.context.set_source_rgba(0, 0, 255, 0.8)
        self.context.show_text(string)
        
        # draw helping lines
        self.context.set_source_rgba(1, 0.2, 0.2, 0.5)
        self.context.set_line_width(6.0)
        
        # start dot
        self.context.arc(start_x, start_y, 10, 0, 2*math.pi)
        self.context.fill()

        self.context.move_to(self.window_width/2, 0)
        self.context.line_to(self.window_width/2, self.window_height)
        # self.context.rel_line_to(self.window_width/2, self.window_height)
        self.context.move_to(0, self.window_height/2)
        self.context.line_to(self.window_width, self.window_height/2)
        # self.context.rel_line_to(self.window_width, self.window_height/2)
        self.context.stroke()        
        
        self.context.restore()
        self.rendertext(self.time_count)

    def rendertext(self, count):
        """with pango as front end, cairo as backend to render"""        
        # pango context structure stores global information
        # used to control the itemization process        
        self.context.save()

        self.pango_layout = self.pc.create_layout()   
        self.pango_font = pango.FontDescription(self.font)
        self.pango_layout.set_font_description(self.pango_font)        
        self.pango_layout.set_alignment(pango.ALIGN_CENTER)

        # self.attr_list = pango.AttrList()
        # attr_foreground = pango.AttrForeground(0, 0, 0)
        # self.attr_list.insert(attr_foreground)
        # self.pango_layout.set_attributes(self.attr_list)
        # self.pango_line = self.pango_layout.get_line(0)
        # # print self.pango_line.get_extents()        
        
        metrics = self.px.get_metrics(self.pango_font)
        ascent = metrics.get_ascent()
        descent = metrics.get_descent()

        # extents = self.px.get_extents()
        # 一句歌词的高度，不是ink distance
        self.font_size_px = pango.PIXELS(ascent + descent)
        # print "font size pixel -- ", self.font_size_px
        
        # if self.current_play_time is not None:
        try:
            self.current_lyric = parser.get_lyric_by_time(self.current_play_time)
            self.current_linecount = self.current_lyric.get_linecount()
        except:
            pass

        # -------------------------------
        # 上部分收集排版信息，下部分写入歌词
        # -------------------------------

        # # 设置歌词
        # # self.pango_layout.set_text(LYRIC)
        # # print self.lyrictext        
        
        # # 一种莫名其妙，但是不错的效果
        # # try:
        # #     self.context.save()
        # #     for i,lyric in enumerate(parser.lyrics):
        # #         self.context.move_to(10, self.font_size_px * i)              
        # #         if i is self.current_linecount:
        # #             self.context.set_source_rgb(1, 0, 0)
                    
        # #         self.pango_layout.set_text(lyric.text)
        # #         self.pc.update_layout(self.pango_layout)
        # #         # self.pc.show_layout(self.pango_layout)
        # #         self.context.layout_path(self.pango_layout)

        # #     self.context.restore()
        # # except:
        # #     pass        
        # self.pango_layout.set_text(self.lyrictext)

        
        # # for lyric in parser.lyrics:
        # #     print lyric.text  
        
        # self.context.new_path()
        # self.context.set_line_width(0.6)
        # # 设置字体颜色
        # self.context.set_source_rgba(0.2, 0.3, 0.1, 1)
        
        # # self.context.save()
        # # for (i,lyric) in enumerate(parser.lyrics):
        # #     if i == self.current_linecount:
        # #         print i
        # #     # 已经跑到最底下
        # #     self.context.move_to(0, self.font_size_px * i)
        # #     self.pango_layout.set_text(lyric.text)            
        # #     self.pc.update_layout(self.pango_layout)        
        # #     # 不交给pango去渲染
        # #     # self.pc.show_layout(self.pango_layout)
        # #     # 交给cairo渲染        
        # #     self.context.layout_path(self.pango_layout)
        # #     if i is self.current_linecount:
        # #         self.context.set_source_rgba(0.2, 0.3, 0.1, 1)
        # #     # self.context.stroke_preserve()        
        # #     else:
        # #         self.context.set_source_rgba(0.1, 0, 0, 1)
   
        # # self.context.restore()

        # # 先移动到屏幕中间
        # self.context.translate(10, self.window_height/2)        
        # # 移动歌词
        # # self.context.move_to(0, self.font_size_px * count * 0.1)
        # if self.current_linecount is not None:
        # # 画当前显示的背景色
        #     self.context.save()
        #     print "current line: ", self.current_linecount
        #     self.context.translate(-10, 0)
        #     self.context.set_source_rgb(0.8, 0.2, 0.1)
        #     self.context.set_source_rgba(
        #         float(self.bg_red)/65536 - 0.1,
        #         float(self.bg_green)/65536 - 0.1,
        #         float(self.bg_blue)/65526 - 0.1,
        #         0.8)
                                        
        #     # self.context.translate(0, self.window_height/2)
        #     self.context.rectangle(0, 0, self.window_width, self.font_size_px)
        #     self.context.fill()
        #     self.context.restore()
        #     # 移动歌词
        #     self.context.translate(0, -(self.font_size_px * self.current_linecount))
        # else:
        #     pass

        # self.pc.update_layout(self.pango_layout)
        # # self.pc.show_layout(self.pango_layout)
        # self.context.layout_path(self.pango_layout)
        # self.context.fill()
        # self.context.restore()

        
        # ---------------- for test ------------------------
        self.context.translate(10, self.window_height/2)
        
        # 画当前显示的背景色
        self.context.save()
        print "current line: ", self.current_linecount
        self.context.translate(-10, 0)
        self.context.set_source_rgb(0.8, 0.2, 0.1)
        self.context.set_source_rgba(
            float(self.bg_red)/65536 - 0.1,
            float(self.bg_green)/65536 - 0.1,
            float(self.bg_blue)/65526 - 0.1,
            0.8)
        # self.context.translate(0, self.window_height/2)
        self.context.rectangle(0, 0, self.window_width, self.font_size_px)
        self.context.fill()
        self.context.restore()

        
        
        if self.current_linecount is not None:
            self.context.translate(0, -(self.font_size_px * self.current_linecount))
        else:
            pass        
        
        for i,lyric in enumerate(parser.lyrics):
            self.context.move_to(self.window_width/2 - 150, self.font_size_px * i)
            self.pango_layout.set_text(lyric.text)
            if i is self.current_linecount:
                self.context.set_source_rgba(0.15, 0.02, 0.28, 1)
            else:
                self.context.set_source_rgba(0.64, 0.62, 0.98, 1)

            pangocairo.CairoContext.update_layout(self.context, self.pango_layout)
            pangocairo.CairoContext.show_layout(self.context, self.pango_layout)            

        self.context.restore()
        
    def draw(self,*args):    
        # 用gtk.Widget.queue_draw()重绘整个图形
        # 用gtk.Widget.queue_draw_area()重绘部分图形
        
        # self.get_font_and_bgcolor()
        
        # self.draw_background(self)
        # self.draw_lyric(self)
        # 上面两句是bug!!!
        
        self.queue_draw()       # 再次发射expose-event
        
    def on_time_out(self):
        self.time_count += 1
        self.draw()
        
        try:
            self.current_play_time = player.query_position()
        except:
            pass
        
        # 只有return True 才能不停的调用        
        return True
        
    
# Todo: 用config当作全局控制，不然的话，参数传送得太频繁
class main:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("show lyrics")
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.set_default_size(600, 400)
        self.window.connect("destroy", lambda widget: gtk.main_quit())

        self.lyricboard = LyricBoard()
        
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.add_with_viewport(self.lyricboard)
        
        self.vbox = gtk.VBox(False, 5)

        # 奇怪的menu bar
        # MenuBar 是个bar，bar里的元素是第一层MenuItem,append使其一字排开
        # 第一层MenuItem不直接显示，要set_submenu,吃下一个gtk.Menu()
        # Menu在包含其下的MenuItem称为子菜单,不包含子菜单的菜单不会显示
        
        # preference 主菜单
        self.menu_item_preference = gtk.MenuItem("_preference")
        # 设置子菜单
        self.menu_preference = gtk.Menu()
        self.menu_item_preference.set_submenu(self.menu_preference)
        # font子菜单
        self.menu_item_font = gtk.MenuItem("lyric")
        self.menu_item_font.connect("activate", self.on_preference)
        self.menu_preference.append(self.menu_item_font)
        
        self.menubar = gtk.MenuBar()
        self.menubar.append(self.menu_item_preference)
        
        self.accel_group = gtk.AccelGroup()
        self.menu_item_font.add_accelerator("activate",
                                            self.accel_group,
                                            ord("p"),
                                            gtk.gdk.CONTROL_MASK,
                                            gtk.ACCEL_VISIBLE)

        self.vbox.pack_start(self.menubar, False, False, 0)
        self.vbox.pack_start(self.scrolledwindow, True, True, 0)
        
        self.window.add_accel_group(self.accel_group)
        self.window.add(self.vbox)
        self.window.show_all()

    def on_preference(self, widget):
        print widget
        self.preference_dialog = PreferenceDialog("首选项", self.window)

if __name__ == '__main__':
    parser = LyricParser("~/code/python/gmusic/test/不如這樣.lrc")

    player = Player()
    engine = Engine(player)

    DBusGMainLoop(set_as_default=True)
    controller = cliplayserver(player)    
    
    main()
    gtk.main()
