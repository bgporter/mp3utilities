
import os
import re
import shutil
import subprocess

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3


kModes = ("copy", "move", "debug")
kOnDupe = ("force", "ignore", "ask")

#                 0    1    2    3    4    5    6
kVbrEquivalents = [245, 225, 190, 175, 165, 130, 115]


kMp3FileStrFormat = '''Album Artist: {0.albumArtist}
Track Artist: {0.trackArtist}
Album:        {0.album}
Title:        {0.title}
Track #:      {0.trackNum}
Year:         {0.year}
Disc #:       {0.discNumber}
Bitrate:      {0.bitrate}
Genre:        {0.genre}
'''


class MetadataException(Exception):
   pass


class InvalidFileException(Exception):
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

      try:
         audio = MP3()
         self.bitrate = audio.info.bitrate / 1000
      except (IOError, AttributeError):
         # fake it.
         self.bitrate = 128

      originalFilename = os.path.basename(pathToFile)
      baseName, ext = os.path.splitext(originalFilename)
      # This class can only handle MP3 files.
      if ext.lower() not in (u".mp3"):
         raise InvalidFileException

      try:
         discNum = self.meta.discnumber
         disc, of = map(int, discNum.split('/'))
         if disc > 0 and of > 1:
            self.discNumber = "(disc {0})".format(disc)
      except (ValueError, KeyError):
         # ignore the error & carry on.
         self.discNumber = u""

      # If the date is in the YYYY-MM-DD format, make sure we 
      # only use the year.
      self.year = self.meta.date[:4]


      self.album = self.meta.album
      self.genre = self.meta.genre

      if not self.album:
         self.album = u"unknown album"

      # if the disc # is present in the album name in the metadata, 
      # do *not* append it again. 
      m = re.search(r"disc \d+", self.album.lower())
      if m:
         self.discNumber = u""   

      performer = self.meta.performer

      artist = self.meta.artist
      self.trackArtist = u""
      self.albumArtist = artist
      self.compilation = False
      if performer.lower() != artist.lower():
         if performer.lower().startswith("various artists"):
            # treat this as a compilation.
            self.compilation = True
            self.albumArtist = performer
            self.trackArtist = artist

         elif performer:
            # we know performer but not artist
            if not artist:
               self.albumArtist = performer

         # else we know the artist but not performer, which we don't care about.
      else:
         # performer & artist are the same -- if they're empty, label 
         # the artist as unknown.
         if not artist:
            self.albumArtist = "unknown artist"


      try:
         trackNum = self.meta.tracknumber
         # Amazon track numbers are sometimes in the form 'x/y')
         trackNum = trackNum.split('/')[0]
         trackNum = u"%02d" % int(trackNum)
      except (KeyError, ValueError):
         trackNum = u""

      self.trackNum = trackNum

      self.title = self.meta.title
      if not self.title:
         self.title = baseName

   def __str__(self):
      return kMp3FileStrFormat.format(self)

   @property
   def artist(self):
      ''' when we put metadata into a transcoded file, we need to know the
         'correct' artist name to use, which may vary if this is a compilation.
      '''
      if self.compilation:
         return self.trackArtist
      else:
         return self.albumArtist


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
      >>> d1 = {"artist" : ["Kneebody"], "album": ["Low Electrical Worker DISC 2"], 
      ... "date": ["2008"], "discnumber" : ["1/2"]}
      >>> m = Mp3File('', d1)
      >>> m.DestPath()
      u'Kneebody/2008_Low-Electrical-Worker-DISC-2'
      >>> d = { "artist" : ["Baloney Bob"], "album" : ["Greatest Hits of the Naughts"],
      ...    "performer" : ["Various Artists"], "date": ["2011"], "title" : ["Bla Bla Bla"],
      ...    "tracknumber" : "5"}
      >>> m = Mp3File('', d)
      >>> m.DestPath()
      u'Various-Artists/2011_Greatest-Hits-of-the-Naughts'

      '''

      albumName = "_".join(w for w in [self.year, self.album, self.discNumber] if w)
      return os.path.join(Scrub(self.albumArtist), Scrub(albumName))


   def DestFile(self):
      '''
      >>> d1 = {"artist" : ["Kneebody"], "album": ["Low Electrical Worker"], 
      ...   "date": ["2008"], "tracknumber" : ['4'], "title": ["Dr. Beauchef"]}
      >>> m = Mp3File('', d1)
      >>> m.DestFile()
      u'04_Dr.-Beauchef.mp3'
      >>> d = { "artist" : ["Baloney Bob"], "album" : ["Greatest Hits of the Naughts"],
      ...    "performer" : ["Various Artists"], "date": ["2011"], "title" : ["Bla Bla Bla"],
      ...    "tracknumber" : "5"}
      >>> m = Mp3File('', d)
      >>> m.DestFile()
      u'05_Baloney-Bob_Bla-Bla-Bla.mp3'

      >>> d1 = {"artist" : ["Kneebody"], "album": ["Low Electrical Worker"], 
      ...   "date": ["2008"], "tracknumber" : ['4']}
      >>> m = Mp3File('foo/bar/originalFilename.mp3', d1)
      >>> m.DestFile()
      u'04_originalFilename.mp3'

      '''

      name = "_".join(Scrub(w) for w in (self.trackNum, self.trackArtist, self.title) if w)
      return u"{0}.mp3".format(name)






class FileDestination(object):
   def __init__(self, baseDir, mode="copy", onDupe="force", rate="0"):
      """
      >>> f = FileDestination(".", "copy", "force", "V4")
      >>> f.vbr
      True

      """
      assert(mode in kModes)
      assert(onDupe in kOnDupe)

      self.baseDir = baseDir
      self.mode = mode
      self.onDupe = onDupe
      # we need to handle VBR separately from 
      self.vbr = False
      if rate.lower().startswith('v'):
         self.vbr = True
         rate = rate[1:]

      self.rate = int(rate)

      self.currentOutputDir = ""

      if self.mode == "copy":
         if self.vbr or (self.rate > 0):
            self.MusicHandler = self._DoTranscode
         else:
            self.MusicHandler = self._DoCopy
         self.OtherHandler = self._DoCopy
      elif self.mode == "move":
         self.MusicHandler = self._DoMove
         self.OtherHandler = self._DoMove
      elif self.mode == "debug":
         self.MusicHandler = self._DoDebug
         self.OltherHandler = self._DoDebug



   def PrepDestination(self):
      '''
         Assumes that self.currentOutputDir has been set already.
         Create the directories needed for our copy or move. The attempt to
         create the directory may fail either because it already exists (not really
         an error), or because we were unable to create it for some other reason
         (drive not mounted, permissions, etc. If we try this and get an OSError
         with an errno value of errno.EEXIST, we swallow the exception and proceed,
         otherwise we re-raise the exception.
      '''

      try:
         os.makedirs(self.currentOutputDir)
      except OSError, e:
         if e.errno != errno.EEXIST:
            # !!! display/log the error
            # and re-raise it.
            raise


   def HandleFile(self, type, pathToFile):
      '''
         type -- one of fileSource.kDirectory, fileSource.kMusic, or 
         fileSource.kOtherFile.
         pathToFile -- full path to the existing source file.

         returns True/False to indicate the success/fail whether this file 
         was handled.
      '''

      handlers = {fileSource.kDirectory   : self.HandleDir,
                  fileSource.kMusic       : self.HandleMusic,
                  fileSource.kOtherFile   : self.HandleOtherFile
                  }

      handler = handlers.get(type, None)
      retval = False
      if handler:
         retval = handler(pathToFile)
      else:
         ### !!! log the weirdness
         print "ERROR: Unknown file type {0}".format(type)

      return retval


   def _DoMove(self, srcFile, destFile):
      ''' move the file from its current location to its new destination.'''
      shutil.move(srcFile, destFile)

   def _DoCopy(self, srcFile, destFile):
      ''' simple copy from src-->dest. No rate change of MP3 files. '''
      shutil.copyfile(srcFile, destFile)

   def _DoTranscode(self, srcFile, destFile):
      ''' create a new copy of the srcFile at destFile, changing its encoding
         bit rate as we go. Requires that LAME is installed.
      '''
      original = Mp3File(srcFile)

      # !!!TODO: compare rate of source file; if it's less than what our
      # target rate is, copy the file as is instead of transcoding. We only
      # transcode to lower bitrates.

      cmd = ['lame', '-h']
      if self.vbr:
         cmd.extend(["-V", self.rate])
      else:
         cmd.extend(["-b", self.rate])

      ## make sure that the metadata gets put in the new file correctly.
      cmd.append("--id3v2-only")
      # a list of tuples where
      # [0] is the command line flag to pass to LAME
      # [1] is the attribute name inside of the mutagen ID3 object.
      kFields = [ ("--tt", "title"),
                  ("--ta", "artist"),
                  ("--tl", "album"),
                  ("--ty", "year"),
                  ("--tn", "trackNum"),
                  ("--tg", "genre")
                 ]

      for (flag, field) in kFields:
         try:
            val = getattr(original, field)
            # apparently there's some chance of bogus leading/trailing 
            # double quotes?
            val = val.strip('"')
            cmd.extend([flag, u"{0}".format(val)])
         except AttributeError:
            # that metadata field is missing from this file; skip it.
            pass

      # okay, all the metadata & other args are set. Pass in the src & dest 
      # values and make this go.       
      cmd.extend(['--mp3input', src, dest])

      try:
         print u" ".join(cmd)
      except UnicodeDecodeError, e:
         print "Error because there's unicode data here... {0}".format(e)
      subprocess.call(cmd)      

      

   def _DoDebug(self, srcFile, destFile):
      ''' t/b/d -- debug only no-op version of the move/copy functions.'''
      pass


   def HandleDir(self, path):
      # when we see a new directory, we clear the current output path...
      self.currentOutputDir = ""
      return True

   def HandleMusic(self, path):
      m = Mp3File(path)
      destPath = m.DestPath()
      destFile = m.DestFile()

      destPath = os.path.join(self.baseDir, destPath)
      if destPath != self.currentOutputDir:
         # writing to a new directory. Make sure that it exists.
         self.currentOutputDir = destPath
         try:
            self.PrepDestination()
         except IOError, e:
            print "ERROR creating destination directory {0}".format(destPath)
            return False
      self.MusicHandler(path, os.join(destPath, destFile))




   def HandleOtherFile(self, path):
      ''' the destination of this file is currentOutputDir + originalFilename '''



if __name__ == "__main__":
   import doctest
   doctest.testmod()