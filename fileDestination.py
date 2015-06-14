
import os
import re

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3


kModes = ("copy", "move", "debug")
kOnDupe = ("force", "ignore", "ask")


class MetadataException(Exception):
   pass

def TitleCase(s):
   words = s.split()
   return ' '.join(w.capitalize() for w in words)


def Scrub(s):
   '''
      1. convert the string into lowercase & strip outer whitespace
      2. Remove any characters that we don't want in filenames or paths from a
      string, eliminating multiple whitespace chars within
      3. Replace whitespace with '-'
      >>> Scrub(u"No Illegal characters")
      u'No-Illegal-characters'
      >>> Scrub(u"this: <should> /be\\ shorter?")
      u'this-should-be-shorter'

   '''
   #s = s.lower()

   kIllegals = u":/\\?<>,!\""
   try:
      for c in kIllegals:
         s = s.replace(c, u" ")
      #  replace square brackets with parens -- they freak out other 
      #  code of mine that uses glob to process file names.
      s = s.replace('[', '(')
      s = s.replace(']', ')')   
      # replace multiple whitespace chars with a single space
      s = re.sub("\s+", u" ", s)
      # get rid of any whitespace on the outside
      s = s.strip()
      # replace each space w a dash
      s = s.replace(u' ', u'-')
      # replace multiple dashes with a single dash
      s = re.sub("-+", u'-', s)

      return s
   except UnicodeDecodeError, e:
      return Scrub(s.decode("utf-8"))


class Metadata(object):
   def __init__(self, id3):
      ''' id3 is probably an instance of mutagen.easyid3.EasyId3 '''
      self.data = id3

   def __getattr__(self, key):
      ''' look at the id3 metadata to get the desired value out of it. If that key
         isn't found, we return ''
      '''
      try:
         val = self.data[key][0]
      except KeyError:
         val = ''

      return val


class Mp3File(object):
   def __init__(self, pathToFile, metadata=None):
      if not metadata:
         id3 = EasyID3(pathToFile)
      else:
         id3 = metadata
      self.meta = Metadata(id3)
      self.compilation = False

   def DestPath(self):
      ''' Return a new path where this file should be stored relative to however 
      the FileDestination that we're working with wants things to be. In general, 
      this is going to be Artist/Year_Album with possible exception cases for:
      1. multi-disc albums (which should have a "(disc n)" appended)
      2. Various Artists compilations, which will instead have the actual Artist
         name encoded as part of the filename instead.
      >>> d1 = {"artist" : ["Kneebody"], "album": ["Low Electrical Worker"], "date": ["2008"]}
      >>> m = Mp3File('', d1)
      >>> m.DestPath()
      u'Kneebody/2008_Low-Electrical-Worker'
      >>> d1 = {"artist" : ["Kneebody"], "album": ["Low Electrical Worker"], 
      ... "date": ["2008"], "discnumber" : ["1/2"]}
      >>> m = Mp3File('', d1)
      >>> m.DestPath()
      u'Kneebody/2008_Low-Electrical-Worker_(disc-1)'

      >>> d = { "artist" : ["Baloney Bob"], "album" : ["Greatest Hits of the Naughts"],
      ...    "performer" : ["Various Artists"], "date": ["2011"], "title" : ["Bla Bla Bla"]}
      >>> m = Mp3File('', d)
      >>> m.DestPath()
      u'Various-Artists/2011_Greatest-Hits-of-the-Naughts'

      '''
      try:
         discNum = self.meta.discnumber
         disc, of = map(int, discNum.split('/'))
         if disc > 0 and of > 1:
            discNumber = "(disc-{0})".format(disc)
      except (ValueError, KeyError):
         # ignore the error & carry on.
         discNumber = u""

      year = self.meta.date

      album = self.meta.album
      if not album:
         album = "unknown album"

      performer = self.meta.performer

      artist = self.meta.artist

      if performer.lower() != artist.lower():
         if performer.lower().startswith("various artists"):
            # treat this as a compilation.
            self.compilation = True
            artist = performer

         elif performer:
            # we know performer but not artist
            if not artist:
               artist = performer

         # else we know the artist but not performer, which we don't care about.
      else:
         # performer & artist are the same -- if they're empty, label 
         # the artist as unknown.
         if not artist:
            artist = "unknown artist"


      albumName = "_".join(w for w in [year, album, discNumber] if w)
      return os.path.join(Scrub(artist), Scrub(albumName))







class FileDestination(object):
   def __init__(self, baseDir, mode="copy", onDupe="force", rate="0"):
      assert(mode in kModes)
      assert(onDupe in kOnDupe)

      self.baseDir = baseDir
      self.mode = mode
      self.onDupe = onDupe
      self.rate = rate


   def HandleFile(self, type, pathToFile):
      '''
         type -- one of fileSource.kDirectory, fileSource.kMusic, or 
         fileSource.kOtherFile.
         pathToFile -- full path to the existing source file.
      '''
      if type == fileSource.kDirectory:
         return self.HandleDir(pathToFile)
      elif type == fileSource.kMusic:
         return self.HandleMusic(pathToFile)
      elif type == fileSource.kOtherFile:
         return self.HandleOtherFile(pathToFile)
      else:
         ### !!! log the weirdness
         print "ERROR: Unknown file type {0}".format(type)
         return None


   def HandleDir(self, path):
      pass

   def HandleMusic(self, path):
      pass

   def HandleOtherFile(self, path):
      pass


if __name__ == "__main__":
   import doctest
   doctest.testmod()