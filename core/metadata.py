#!usr/bin/env python
#-*- coding:utf-8 -*-
import os, sys
import logging
from mutagen import File as MutagenFile
import sqlite3

# """
# Mutagen Tag support
# """
# from mutagen import File as MutagenFile
# from mutagen.asf import ASF
# from mutagen.apev2 import APEv2File
# from mutagen.flac import FLAC
# from mutagen.id3 import ID3FileType
# from mutagen.oggflac import OggFLAC
# from mutagen.oggspeex import OggSpeex
# from mutagen.oggtheora import OggTheora
# from mutagen.oggvorbis import OggVorbis
# from mutagen.trueaudio import TrueAudio
# from mutagen.wavpack import WavPack
# try: from mutagen.mp4 import MP4 #@UnusedImport
# except: from mutagen.m4a import M4A as MP4 #@Reimport
# from mutagen.musepack import Musepack
# from mutagen.monkeysaudio import MonkeysAudio
# from mutagen.optimfrog import OptimFROG

# open a directory and read files recursive

# log
logging.basicConfig(
    filename = "metadata.log",
    format = "%(levelname)-10s %(asctime)s %(message)s",
    level = logging.INFO)
log = logging.getLogger("metadata")
log.debug("logging metadata")

GENERAL_KEYS = {
    "title" : "title",
    "artist" : "artist",
    "album" : "album",
    "tracknumber" : "tracknumber",
    # "discnumber" : "discnumber",
    "date" : "date",
    "genre" : "genre"    
    }
MP3_KEYS = {
    "TIT2" : "title",
    "TPE1" : "artist",
    "TALB" : "album",
    "TRCK" : "tracknumber",
    "TDRC" : "date",
    "TCON" : "genre"
    }
MP4_KEYS = {
    "\xa9nam" : "title",
    "\xa9ART" : "artist",
    "\xa9alb" : "album",
    "trkn"    : "tracknumber",
    "disk"    : "discnumber",
    "\xa8day" : "date",
    "\xa8gen" : "genre"
    }
class FileReader(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.supported_media_formats = ["mp3","wav","ogg","m4a","flac","mp4","mp2","aac","flv","ape"]
        self.files = []

    # def get_file(self, filepath):
    #     if os.path.isdir(filepath):
    #         for subdir in os.listdir(filepath):
    #             subdir = filepath + os.path.sep + subdir
    #             self.get_file(subdir)
    #     elif os.path.isfile(filepath):
    #         print filepath
    #         yield filepath

    def filter(self):
        if os.path.isfile(self.filepath):
            filename = self.file_filter(self.filepath)
        elif os.path.isdir(self.filepath):
            self.directory_filter(self.filepath)
        else:
            print 'uncorrect path'            

    def file_filter(self,filename):
        format = str(filename.split('.')[-1]).lower()
        if format in self.supported_media_formats:
            # print "%s - %s format supported" % (filename, format)
            self.files.append(filename)
        else:
            print "%s - unknown format" % filename
            
    def directory_filter(self,directory):
        for subdir in os.listdir(directory):
            subdir = directory + os.path.sep + subdir
            # print subdir
            if os.path.isfile(subdir):
                self.file_filter(subdir)
            elif os.path.isdir(subdir):
                self.directory_filter(subdir)
                
class MetadataParser(object):
    def __init__(self,filename):
        self.filename = filename
        self.dict = {}
        self.dict['filepath'] = unicode(os.path.abspath(self.filename),"utf-8", errors="ignore")
        self.dict['title'] = ''
        self.dict['artist'] = ''
        self.dict['album'] = ''
        self.dict['tracknumber'] = -1
        self.dict['date'] = ''
        self.dict['genre'] = ''
        
    def parse(self):
        print os.path.abspath(self.filename)
        tag = MutagenFile(self.filename)
        if tag == None:
            print self.filename
        else:
            for key, value in tag.iteritems():
                if key in GENERAL_KEYS.keys():
                    self.dict[ GENERAL_KEYS[key] ] = unicode(value)
                elif key in MP3_KEYS.keys():
                    self.dict[ MP3_KEYS[key] ] = unicode(value)
                elif key in MP4_KEYS.keys():
                    self.dict[ MP4_KEYS[key] ] = unicode(value)
                    
    def convert_to_tuple(self):
        self.tuple_data = (self.dict['filepath'],
                           self.dict['title'], 
                           self.dict['artist'],
                           self.dict['album'],
                           self.dict['tracknumber'],
                           self.dict['date'],
                           self.dict['genre'])
        return self.tuple_data

class database(object):
    def __init__(self):
        self.conn = sqlite3.connect('metadata.db')        
        self.cur = self.conn.cursor()
        self.cur.execute("DROP TABLE IF EXISTS metadata")
        self.cur.execute('''CREATE TABLE metadata
(filepath text, title text, artist text, album text, tracknumber real, date text, genre text)''')
                    
    def store(self, tuple_data):
        self.cur.execute("INSERT INTO metadata VALUES (?, ?, ?, ?, ?, ?, ?)",tuple_data)

    def query(self, parameter):
        sql = "SELECT %s FROM metadata" % parameter
        self.cur.execute(sql)
        rows = self.cur.fetchall()
        for row in rows:
            print "%s - %s" % (parameter, row[0])

if len(sys.argv) != 2:
    print 'usage: ./metadata.py filepath'
else:
    fr = FileReader(sys.argv[1])
    fr.filter()
    db = database()

    for f in fr.files:
        mp = MetadataParser(f)
        mp.parse()
        tuple_data = mp.convert_to_tuple()        
        print tuple_data
        for key, value in mp.dict.iteritems():
            print key, '-' , value
        # print 'tuple metadata ', tuple(mp.dict.values())
        # print tuple(mp.dict.values())
        db.store(tuple_data)
        
    db.query('artist')
