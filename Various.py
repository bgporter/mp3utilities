
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

import os
import sys


def Scrub(x):
   return x

class Metadata(object):
   def __init__(self, id3):
      ''' id3 is probably an instance of mutagen.easyid3.EasyId3 '''
      self.data = id3
      self.dirty = False

   def Save(self):
      if self.dirty:
         self.data.save()

   def __setitem__(self, key, value):
      self.data[key] = value
      self.dirty = True


   def __getattr__(self, key):
      ''' look at the id3 metadata to get the desired value out of it. If that key
         isn't found, we return ''
      '''
      try:
         val = self.data[key][0].encode('utf-8')
      except KeyError:
         val = u''

      return Scrub(val)

root = "/Volumes/zappa_files/music/"



def Edit(md):
   print "Artist: {0}".format(md.artist)
   resp = raw_input("New Artist: [blank=keep]")
   resp = resp.strip()
   if resp:
      md['artist'] = resp

   print "\nPerformer: {0}".format(md.performer)
   resp = raw_input("New Performer: [blank=keep]")
   resp = resp.strip()
   if resp:
      md['performer'] = resp





def Prompt(md, filePath):
   print filePath
   print "Album     = {0}".format(md.album)
   print "Artist    = {0}\nPerformer = {1}".format(md.artist, md.performer)
   print 
   while True:
      print "(k)eep as is | (a)rtist->performer | (p)erformer -> artist | (e)dit"
      resp = raw_input()
      resp = resp.lower()
      if resp in ('k', 'a', 'p', 'e'):
         break

   if resp == 'a':
      md.performer = md.artist
   elif resp == 'p':
      md.artist = md.performer
   elif resp == 'e':
      Edit(md)

   md.Save()

def Scan(path):   
   for (dirpath, dirs, files) in os.walk(path):
      for f in files:
         base, ext = os.path.splitext(f)
         if ext.lower() in (u".mp3",):
            fullPath = os.path.join(root, dirpath, f)
            sys.stdout.write("{0}\r".format(fullPath))
            sys.stdout.flush()
            try:
               id3 = EasyID3(fullPath)
            except mutagen._id3util.ID3NoHeaderError, e:
               print str(e)
               continue

            md = Metadata(id3)
            artist = md.artist
            performer = md.performer
            if performer and (performer.lower() != artist.lower()):
               path = os.path.join(dirpath, f)
               Prompt(md, path)


if __name__ == "__main__":
   import sys

   if len(sys.argv) > 1:
      # 1st arg is the directory to look at
      path = sys.argv[1]
else:
   path = "."
print "Scanning {0}".format(path)
Scan(path)
