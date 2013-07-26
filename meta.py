#! /usr/bin/env python

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3


def MsToMinSec(ms):
   ''' given a duration value in milliseconds, returns a formatted string showing 
      the duration expressed in "m:ss" format (seconds always zero-padded if necessary.)
   '''
   ms = int(ms)
   seconds = ms / 1000.0
   min, sec = divmod(seconds, 60)
   return "{0}:{1:02}".format(int(min), int(sec + 0.5))


def GetMetadataFields(f):
   ''' opens the file named 'f', then returns a dict with values for the following
      metadata contained in the file:
      artistalbum
      title
      tracknumber (possibly in the format 'x/y')
      genre
      bitrate
      date
      length
   '''
   audio = MP3(f)
   meta = EasyID3(f)

   metaDict = {}
   metaFields = "artist album title tracknumber genre date".split()
   for field in metaFields:
      metaDict[field] = meta[field][0]

   metaDict['length'] = MsToMinSec(meta['length'][0])
   metaDict['bitrate'] = audio.info.bitrate

   return metaDict

def GetTrackNumber(tn):
   ''' returns just the track number -- if we're passed in the string '5/6', 
      we'll return just the 5 (also as a string)
   '''
   tn = str(tn)
   return tn.split('/')[0]


def showFile(f):

   meta = GetMetadataFields(f)

   print "Artist:\t{0}".format(meta['artist']) 
   print "Album:\t{0}".format(meta['album']) 
   print "Title:\t{0}".format(meta['title']) 
   print "Track:\t{0}".format(meta['tracknumber']) 
   print "Genre:\t{0}".format(meta['genre']) 
   print "Bitrate\t{0}".format(meta['bitrate'])
   print "Date:\t{0}".format(meta['date']) 
   print "Dur:\t{0}".format(meta['length'])



