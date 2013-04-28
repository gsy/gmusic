#!/usr/bin/env python
#-*- coding: utf-8
import os
import sqlite3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

class InvalidSongException(Exception):
    pass
    
class FileTagsParser:
    def __init__(self):
        self.supported_media_type = "mp3", "ogg", "flac", "m4a"
        
        # 连接数据库文件
        # 如果数据库文件不存在，则新建一个，如果存在则打开此文件
        self.conn = sqlite3.connect("songs.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # create table
        self.cursor.execute("""create table if not exists metadata  (album text not null default 'Unknown',artist text not null default 'Unknown', title text not null default 'Unknown', tracknumber text not null default '1', length text, filepath text UNIQUE)""")
        self.cursor.execute("""create table if not exists info  (length text, bitrate text, sample_rate text)""")
        
    def walk(self, d):
        """ Walk donw the file structure iteratively, gathering file names to be read in."""
        d = os.path.abspath(d)
        print "abspath " + d
        print ""

        for root,dirs,files in os.walk(d):
            print root
            for fname in files:
                print('\t%s' % fname)
                if fname.split(".")[-1].lower() in self.supported_media_type:
                    try:
                        file = os.path.join(root, fname)
                        self.parse(file)
                    except Exception, e:
                        print e.__unicode__()

        self.printDB()

    def print_dictionary(self, d):
        print "-" * 45
        print ""
        for key in d:
            print key, ' -- ', d[key]

    def parse_mp3(self, song):
        result = {}
        
        # print dir(song.info)        
        # print song.info.version
        # print song.info.layer
        # print song.info.sample_rate
        # print song.info.length
        # print song.info.bitrate

        result['length'] = song.info.length
        result['bitrate'] = song.info.bitrate
        result['sample_rate'] = song.info.sample_rate
        
        # keys = song.keys()
        # print song.pprint()
        # print '-' * 45
        # print         

        result['album'] = song['album'][0]        
        result['artist'] = song['artist'][0]
        result['title'] = song['title'][0]
        result['tracknumber'] = song['tracknumber'][0]            
        
        # self.print_dictionary(result)
        return result
    
    def parse_OggOrFlac(self, song):
        result = {}
        
        # print dir(song.info)
        if "bitrate" in dir(song.info):
            # print song.info.bitrate
            result['bitrate'] = song.info.bitrate
        # print song.info.sample_rate
        result['sample_rate'] = song.info.sample_rate

        # print song.info.length
        result['length'] = song.info.length
        # print song.info.channels
        # print song.info.pprint()
        
        # print song.keys()        
        result['album'] = song['album'][0]
        result['artist'] = song['artist'][0]
        result['title'] = song['title'][0]
        if song['tracknumber']:
            result['tracknumber'] = song['tracknumber'][0]
        else:
            result['tracknumber'] = 1

        # self.print_dictionary(result)
        return result

    def parse_mp4(self, song):
        result = {}
        # print dir(song.info)
        # bitrate, channels,length,sample_rate
        result['length'] = song.info.length
        result['bitrate'] = song.info.bitrate
        result['sample_rate'] = song.info.sample_rate

        
        # print song.keys()
        # for key in song.keys():
        #     if key != 'covr' and key != 'cpil' and key != 'pgap':
        #         print key, "=", song[key][0]
        
        result['album'] = song['\xa9alb'][0]
        result['title'] = song['\xa9nam'][0]
        result['artist'] = song['\xa9ART'][0]
        result['tracknumber'] = song['trkn'][0][0]
        
        # self.print_dictionary(result)
        return result    

    def parse(self, filename):
        """ Process and parse the music file to extract desired information.

        It may be the case that, in the future, we require more information
        from a song than is provided at this time.
        Examine all tags that can be retrieved from a mutagen.File object,
        and adjust the database's schema accordingly.        
        """        
        if ".ogg" in filename:
            print "parsing .ogg file: ", filename
            song = OggVorbis(filename)
            song = self.parse_OggOrFlac(song)
        elif ".flac" in filename:
            print "parsing .flac file: ", filename
            song = FLAC(filename)
            song = self.parse_OggOrFlac(song)
        elif ".mp3" in filename:
            print "parsing .mp3 file: ", filename
            song = MP3(filename, ID3=EasyID3)
            song = self.parse_mp3(song)
        elif ".m4a" in filename:
            print "parsing .m4a file: ", filename
            song = MP4(filename)
            song = self.parse_mp4(song)            
        else:
            raise InvalidSongException(u"Song is not supported at this time.")
        # self.buf = [ (song['album'], song['artist'], song['title'], song['tracknumber'], song['filepath']) ]
        # print 
        # print 'song:'
        # print '-' * 20
        song['filepath'] = unicode(filename,"utf8")
        song['length'] = self.convert_time(song['length'])
        self.saveInDB(song)

    def saveInDB(self, song):
        self.cursor.execute("""INSERT INTO metadata VALUES (?, ?, ?, ?, ?, ?)""", (song['album'], song['artist'], song['title'], song['tracknumber'], song['length'], song['filepath']))
        self.cursor.execute("""insert into info values (?, ?, ?)""", (song['length'], song['bitrate'], song['sample_rate']))
        self.conn.commit()

    def loadFromDB(self):
        result = []
        self.cursor.execute("select distinct * from metadata")
        rows = self.cursor.fetchall()
        for row in rows:
            result.append([row['tracknumber'], row['filepath'], row['title'], row['artist'], row['album'],row['length']])
        return result

    def queryDB(self, parameter):
        self.cursor.execute("select distinct %s from metadata" % parameter)
        rows = self.cursor.fetchall()
        
        print rows
        return rows

    def printDB(self):
        count = 0
        self.cursor.execute("select distinct * from metadata")
        rows = self.cursor.fetchall()
        for row in rows:
            count += 1
            print "count=", count            
            print "album=%s\ntitle=%s\nartist=%s\nlength=%s\n" % (row['album'], row['title'], row['artist'], row['length'])
            
        # self.cursor.execute("select count(*) from metadata")
        # count = self.cursor.fetchone()
        # print count
    
    def closeDB(self):
        self.cursor.close()
        self.conn.close()
            
    def dropTable(self):
        self.cursor.execute("DROP TABLE IF EXISTS metadata")
        self.cursor.execute("DROP TABLE IF EXISTS info")
        
    # 转化时间为(分：秒)形式
    def convert_time(self, str):
        length = float(str) * 1000 # ms
        # print length
        minute = int(length/1000)/60
        second = int(length/1000)%60
        result = "%s:%s" % (minute, second)
        # print result
        return result
        
            
        # filename = u"filename"
        # filePath, artist, title, genre, track, album, bitrate, year, month = '', '', '', '', '', '', '', '', ''
        # try:
        #     artist = song['artist'][0]
        #     title = song['title'][0]
        # except Exception:
        #     raise InvalidSongException(u"Cannot read " + filename + ": missing critical song information.")
        # if 'genre' in song:
        #     genre = songp['genre'][0]
        # else:
        #     genre = u'Unknown'
        # if 'tracknumber' in song:
        #     track = song['tracknumber'][0]
        # else:
        #     track = 0
        # if 'album' in song:
        #     album = song['album'][0]
        # else:
        #     album = u'Unknown'
        # if 'date' in song:
        #     year = song['data'][0]
        # else:
        #     year = u'Unknown'
        # try:
        #     bitrate = int(song.info.bitrate)
        # except AttributeError:  # Likely due to us messing with FLAC
        #     bitrate = 999999    # Set to a special flac value, to indicapte that this is a lossless file.
            
        # self.filecount += 1
                
                
if __name__ == '__main__':
    directory = "/home/gsy/code/python/gmusic/test/"
    parser = FileTagsParser()
    # parser.dropTable()
    parser.walk(directory)
    songs = parser.loadFromDB()
    parser.printDB()
    
    artists = parser.queryDB("artist")
    
    # print artists
    # for song in songs:
    #     count += 1
    #     print count
    #     print song
    #     for item in song:
    #         print item
    # parser.convert_time("400.35")

