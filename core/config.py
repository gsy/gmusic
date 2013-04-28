#!/usr/bin/env python
#-*- coding:utf-8 -*-
import os
import gobject
from ConfigParser import RawConfigParser
from xdg.BaseDirectory import save_config_path

class Config(gobject.GObject):
    __gsignals__ = {
        'config-changed': (gobject.SIGNAL_RUN_LAST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_STRING))
        }
    def __init__(self):
        gobject.GObject.__init__(self)
        self.config = RawConfigParser()
        self.getboolean = self.config.getboolean
        self.getinit = self.config.getint
        self.getfloat = self.config.getfloat        
    
    def set(self, section, option, value):
        """设置section下的option为value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, option, value)        
        self.emit("config-changed", section, option, value)

    def get(self, section, option, default=None):
        """从section中取出option"""
        if default is None:
            return self.config.get(section, option)
        else:
            try:
                return self.config.get(section, option)
            except:
                return default
            
    def load(self):
        """读入config"""
        self.config.read(os.path.join(save_config_path("gmusic"), "config"))        
        
    def write(self):
        """写入config文件,路径由xdg决定"""        
        filename = os.path.join(save_config_path("gmusic"), "config")
        with open(filename, "w") as configfile:
            self.config.write(configfile)

# 这个config是全局的，并且要是唯一的，只通过一个config改变config file,同时，
# 也只有这个config能知道改变。
config = Config()
