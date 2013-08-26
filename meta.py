#! /usr/bin/env python

import codecs
import csv
import os.path

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import mutagen

kMetadataFields = ["artist", "title", "album", "tracknumber", "genre", "date", "bitrate",  "length", "filename"]

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
      tracknumber 
      genre
      bitrate
      date
      length
   '''
   audio = MP3(f)

   try:
      meta = EasyID3(f)
   except mutagen.id3.ID3NoHeaderError:
      meta = {}

   metaDict = {}
   metaFields = "artist album title tracknumber genre date".split()
   for field in metaFields:
      try:
         metaDict[field] = meta[field][0]
      except KeyError:
         metaDict[field] = u""

   try:
      length = MsToMinSec(meta['length'][0])
   except KeyError:
      length = u"--:--"
   metaDict['length'] = length 
   metaDict['bitrate'] = audio.info.bitrate

   # the tracknumber value may be in the format 'x/y' -- we only want the 'x'
   if metaDict['tracknumber']:
      metaDict['tracknumber'] = GetTrackNumber(metaDict['tracknumber'])

   return metaDict

def GetTrackNumber(tn):
   ''' returns just the track number -- if we're passed in the string '5/6', 
      we'll return just the 5 (also as a string)
   '''
   tn = str(tn)
   return tn.split('/')[0]


def ShowFile(f):

   meta = GetMetadataFields(f)

   print "Artist:\t{0}".format(meta['artist']) 
   print "Album:\t{0}".format(meta['album']) 
   print "Title:\t{0}".format(meta['title']) 
   print "Track:\t{0}".format(meta['tracknumber']) 
   print "Genre:\t{0}".format(meta['genre']) 
   print "Bitrate\t{0}".format(meta['bitrate'])
   print "Date:\t{0}".format(meta['date']) 
   print "Dur:\t{0}".format(meta['length'])

def WriteCsvFile(fileName, topDir):
   with open(fileName, "wb") as f:
      writer = csv.DictWriter(f, kMetadataFields)
      try:
         writer.writeheader()
      except AttributeError:
         pass

      commonPath = len(topDir)         
      for root, dirs, files in os.walk(topDir):
         for theFile in files:
            name, ext = os.path.splitext(theFile)
            if (".mp3" == ext.lower()):
               filePath = os.path.join(root, theFile)
               print filePath
               fields = GetMetadataFields(filePath)
               # the field values are unicode data -- encode them as utf-8 before writing.
               utfDict = {}
               for k, v in fields.items():
                  #print "{0}: {1}".format(k, repr(v))
                  utfDict[k] = unicode(v).encode("utf-8")
               # we'll include the full path to the file as a unique key.   
               utfDict['filename'] = filePath[commonPath:]

               writer.writerow(utfDict)

def UpdateFileMetadata(basePath, rowData):
   '''
      'basePath' is the common path used by all the files
      'rowData' consists of a list of strings as written out by the WriteCsvFile() function
      above.
   '''

   filePath = os.path.join(basePath, rowData[-1])
   print filePath
   meta = EasyID3(filePath)
   for i in range(5):
      fieldName = kMetadataFields[i]
      try:
         old = meta[fieldName][0]
      except KeyError:
         old = "<<not set>>"
      # convert from utf-8 back into unicode. The CSV reader is unicode unaware.
      # !!! we should really require that this be done before passing the row data in. !!!
      new = rowData[i].decode("utf-8")
      if not new:
         new = u"<<not set>>"
      if new != old:
         print "   Changing {0}".format(fieldName)
         print "       from {0}".format(old.encode("utf-8"))
         print "       to   {0}".format(new.encode("utf-8"))



if __name__ == "__main__":
   # show metadata for any MP3 files in the current directory.
   import glob
   files = glob.glob("*.mp3")
   for f in files:
      print f
      ShowFile(f)
      print 

      
