#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re, os, sys, time, urllib
urlread = lambda url: urllib.urlopen(url).read()

class getAlbumCover:
    _doubanSearchApi = "http://api.douban.com/music/subjects?q={0}&max-result=1"
    _doubanCoverPattern3 = "http://img3.douban.com/spic/s(\d+).jpg"
    _doubanCoverPattern1 = "http://img1.douban.com/spic/s(\d+).jpg"
    _doubanCoverAddr = "http://img3.douban.com/lpic/s{0}.jpg"

    artist = ""
    album = ""
    title = ""

    def __init__(self, mp3):
        print "mp3 --> ", mp3

    def getCoverAddrFromDouban(self, keywords=""):        
        if not len(keywords):
            keywords = self.artist + '' + (self.album or self.title)
            
        print keywords
        request = self._doubanSearchApi.format(urllib.quote(keywords))
        print request
        result = urlread(request)
        if not len(result):
            return False
        
        match = re.search(self._doubanCoverPattern3, result, re.IGNORECASE)
        if match:
            pass
        else:
            # 如果_doubanCoverPattern3匹配不成功,则匹配_doubanCoverPattern1
            match = re.search(self._doubanCoverPattern1, result, re.IGNORECASE)
        if match:
            return self._doubanCoverAddr.format(match.groups()[0])
        else:
            return False
        
    def downloadFile(self, url):
        cover_file = url.split('/')[-1]
        print cover_file
            
        f = file(cover_file, 'wb')
        f.write(urlread(url))
        f.close()

        return cover_file
        
if __name__ == '__main__':
    handler = getAlbumCover("test.mp3")
    artist = "陈奕迅"
    album = "get a life"
    title = "浮夸"
    coverAddr = handler.getCoverAddrFromDouban(artist+album)
    print coverAddr
    handler.downloadFile(coverAddr)
    
