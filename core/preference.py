#!/usr/bin/env python
# coding:utf-8
import gtk
from config import config
# 把结果写入config file里
class PreferenceDialog(gtk.Window):
    def __init__(self, title, parent):

        gtk.Window.__init__(self)
        self.set_title(title)
        self.set_resizable(False)
        # self.set_size_request(200, 200)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_border_width(12)
        self.set_property("skip-taskbar-hint", True)        

        # 禁止跟同一类应用的其他窗口交互
        # Modal windows prevent interaction with other
        # windows in the same application
        self.set_modal(True)
        self.set_transient_for(parent)

        btn = gtk.Button(stock=gtk.STOCK_CLOSE)
        btn.connect("clicked", self.on_destroy)
        box_btn = gtk.HBox()
        box_btn.pack_end(btn, False, False)
        
        self.main_vbox = gtk.VBox(spacing = 6)
        
        gtk.Window.add(self, gtk.VBox(spacing=12))
        self.child.pack_start(self.main_vbox)
        self.child.pack_start(box_btn)        

        self.notebook = gtk.Notebook()
        self.add(self.notebook)
        
        self.lyric_page = self.make_lyric_page()
        self.notebook.append_page(self.lyric_page, self.make_tab("lyric", gtk.STOCK_PREFERENCES))        

        self.connect("delete-event", self.on_destroy)
        self.show_all()

        self.font_info = None
        self.bg_color = None        

        
        config.load()      # 先读入，改变时重写回去
        
    def on_destroy(self, *args):
        # 不能在最后才写入文件，要在设置时就看见变化
        # self.config.write()     # 在退出时写入配置文件
        self.destroy()

    def add(self, widget):
        self.main_vbox.pack_start(widget, False, False)

    # label和stock打包在一起
    def make_tab(self, label, stock):
        tab = gtk.HBox(False, 6)
        image = gtk.Image()
        image.set_from_stock(stock, gtk.ICON_SIZE_MENU)
        tab.pack_start(image, False, False)
        tab.pack_start(gtk.Label(label), False, False)
        tab.show_all()
        return tab

    # 将一页打包起来
    def make_page(self):
        page = gtk.VBox(False, 6)
        return page

    def make_lyric_page(self):
        lyric_preference_page = self.make_page()
        
        # ---------------- Font -----------------
        font_title = self.make_title_label("Font")
        
        font_box = gtk.HBox(False, 6)
        font_label = gtk.Label("font: ")
        fontbutton = gtk.FontButton()        
        fontbutton.connect("font-set", self.on_font_set)
        font_box.pack_start(font_label)
        font_box.pack_start(fontbutton)

        # -------------- Background -------------
        bg_title = self.make_title_label("Background")

        bg_box = gtk.HBox(False, 6)
        bg_label = gtk.Label("background: ")
        bg_color_btn = gtk.ColorButton()
        bg_color_btn.connect("color-set", self.on_background_set)
        bg_box.pack_start(bg_label, False, False)
        bg_box.pack_start(bg_color_btn, False, False)        
        
        lyric_preference_page.pack_start(font_title)
        lyric_preference_page.pack_start(font_box)
        lyric_preference_page.pack_start(bg_title)
        lyric_preference_page.pack_start(bg_box)
        return lyric_preference_page

    def on_font_set(self, widget):
        print "on font set cb"
        print widget.get_font_name()
        self.font_info = widget.get_font_name()
        
        config.set("OSD","font", self.font_info)        
        config.write()

    def on_background_set(self, widget):
        self.bg_color = widget.get_color()
        print "background color set to ", self.bg_color.to_string()
        print self.bg_color.red
        print self.bg_color.green
        print self.bg_color.blue
        
        config.set("OSD","background_red", self.bg_color.red)
        config.set("OSD","background_green", self.bg_color.green)
        config.set("OSD","background_blue", self.bg_color.blue)
        config.write()
        
    def make_title_label(self, str):
        label = gtk.Label("<b>" + str + "</b>")
        label.set_use_markup(True)
        label.set_alignment(0, 1)
        label.set_size_request(0, 22)
        return label    

# if __name__ == '__main__':
#     main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
#     dialog = PreferenceDialog("hello dialog", main_window)
    
#     gtk.main()    
