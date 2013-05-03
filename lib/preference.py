#!/usr/bin/env python

import os

"""set default preference"""
class configException:
    pass

class preference:
    def __init__(self):
        self.most_recent_directory = os.path.expanduser("~/Music")
        self.config_paths = [os.path.expanduser("~/.gmusic.conf"),"./.gmusic.conf"]
        self.volume = 1.0
        self.file_cycle_mode = False
        self.shuffle_mode = False
        self.play_list_mode = True
        self.window_xpos = 0
        self.window_ypos = 0
        self.window_width = 800
        self.window_height = 600    

    def load_from_file(self, instance):
        config_file = None
        for path in self.config_paths:
            try:
                config_file = open(path,'r')
                self.path_to_config = path
            except:
                continue
        if config_file:
            config_data = config_file.read()
            config_items = config_data.splitlines()
            for line in config_items:
                key,value = line.split("=")
                if key == "file_cycle_mode":
                    self.file_cycle_mode = bool(int(value))
                elif key == "shuffle_mode":
                    self.shuffle_mode = bool(int(value))
                elif key == "volume":
                    self.volume = float(value)
                elif key == "window_xpos":
                    self.window_xpos = int(value)
                elif key == "window_ypos":
                    self.window_ypos = int(value)
                elif key == "window_width":
                    self.window_width = int(value)
                elif key == "window_height":
                    self.window_height = int(value)
        else:
            raise configException


    def write_to_file(self, instance):
        """
        write config to file.
        if config file does not exist, create one.
        """        
        if self.path_to_config == Nonpe:
            self.path_to_config = self.config_paths[0]
            
        config_file = open(self.path_to_config,"w")        
        config_data = ""
        config_data += "volume=" + str(instance.volume_button.get_value()) + "\n"
        config_data += "file_cycle_mode=" + str(int(instance.file_cycle_mode)) + "\n"
        config_data += "shuffle_mode=" + str(int(instance.shuffle_mode)) + "\n"
        config_data += "window_width=" + str(instance.window.get_size()[0]) + "\n"
        config_data += "window_heigh=" + str(instance.window.get_size()[1]) + "\n"
        config_data += "window_xpos=" + str(instance.window.get_position()[0]) + "\n"
        config_data += "window_ypos=" + str(instance.window.get_position()[1]) + "\n"
        config_file.write(config_data)

if __name__ == '__main__':
    p = preference()
    
