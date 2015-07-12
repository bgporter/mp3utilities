
import errno
import hashlib
import os
import re
import shutil
import subprocess
import time
import unicodedata

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

import fileSource
import trackHistory

kModes = ("copy", "move")
kOnDupe = ("force", "skip", "ask")

#                 0    1    2    3    4    5    6
kVbrEquivalents = [245, 225, 190, 175, 165, 130, 115]


kMp3FileStrFormat = u'''Album Artist: {0.albumArtist}
Track Artist: {0.trackArtist}
Album:        {0.album}
Title:        {0.title}
Track #:      {0.trackNum}
Year:         {0.year}
Disc #:       {0.discNumber}
Genre:        {0.genre}
Bitrate:      {0.bitrate}
'''

# Usually false. Set this true when reorganizing files or moving to a different 
# drive -- when this is true, we use the *existing* move date in the history file
# instead of setting it to now.
qReorganize = True


class MetadataException(Exception):
   def __init__(self, txt):
      self.txt = txt

   def __str__(self):
      return self.txt


class InvalidFileException(Exception):
   pass


def NormalizeFilename(filename):
   return unicodedata.normalize('NFC', filename).encode('utf-8')

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

   kIllegals = u":/\\?<>,!"
   # get rid of quotes/dots but don't leave space.
   kIllegal2 = u"\"'."
   try:
      for c in kIllegals:
         s = s.replace(c, u" ")
      for c in kIllegal2:
         s = s.replace(c, u"")

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
      # Always get rid of any trailing dots -- this causes problems when 
      # used as a directory name. 
      s = s.rstrip('.')

      return s
   except UnicodeDecodeError, e:
      return Scrub(s.decode("utf-8"))


def ArtistSort(s):
   '''
      Convert artist names that are in the form "The Beatles" to just "Beatles".
      We don't bother appending a ", The"; it doesn't seem useful and just adds another
      4 characters to things. We do protect against one unusual case, the band "The The" is 
      kept as is. Maybe someday I'll have something by them in my collection. 
      >>> ArtistSort(u"Weather Report")
      u'Weather Report'
      >>> ArtistSort(u"They Might Be Giants")
      u'They Might Be Giants'
      >>> ArtistSort(u"The Beatles")
      u'Beatles'
      >>> ArtistSort(u"The The")
      u'The The'
   '''
   s = s.strip()
   if s.lower().startswith("the "):
      if s.lower() != "the the":
         s = s[4:]
   return s

class Metadata(object):
   def __init__(self, id3):
      ''' id3 is probably an instance of mutagen.easyid3.EasyId3 '''
      self.data = id3
      self.dirty = False

   def __setitem__(self, key, value):
      self.data[key] = unicode(value)
      self.dirty = True

   def __getattr__(self, key):
      ''' look at the id3 metadata to get the desired value out of it. If that key
         isn't found, we return ''
      '''
      try:
         val = self.data[key][0]
      except KeyError:
         val = ''

      return val

   def Save(self):
      ''' Attempt to write any changes back to the file (if there is one)'''
      if self.dirty:
         try:
            self.data.save()
            self.dirty = False
         except AttributeError:
            # we were passed a regular dict, and cant' save...
            pass



class Mp3File(object):
   def __init__(self, pathToFile, metadata=None):
      if not metadata:
         try:
            id3 = EasyID3(pathToFile)
         except mutagen.id3.ID3NoHeaderError as e:
            raise MetadataException(str(e))

      else:
         id3 = metadata
      self.meta = Metadata(id3)

      try:
         audio = MP3(pathToFile)
         self.bitrate = audio.info.bitrate / 1000
      except (IOError, AttributeError):
         # fake it.
         self.bitrate = 128

      originalFilename = os.path.basename(pathToFile)
      baseName, ext = os.path.splitext(originalFilename)
      # This class can only handle MP3 files.
      if ext.lower() not in (u".mp3"):
         raise InvalidFileException

      self.discNumber = u""
      try:
         discNum = self.meta.discnumber
         disc, of = map(int, discNum.split('/'))
         if disc > 0 and of > 1:
            self.discNumber = "(disc {0})".format(disc)
      except (ValueError, KeyError):
         # ignore the error & carry on.
         pass

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
         #if performer.lower().startswith("various artists"):
         if performer and artist:
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

      # make sure that artists get names set in correct sort order (minus 
      # a leading 'The', if one exists.)
      self.albumArtist = ArtistSort(self.albumArtist)
      self.trackArtist = ArtistSort(self.trackArtist)

      self.title = self.meta.title
      if not self.title:
         self.title = baseName

   def __str__(self):
      return kMp3FileStrFormat.format(self).encode("utf-8")

   @property
   def artist(self):
      ''' when we put metadata into a transcoded file, we need to know the
         'correct' artist name to use, which may vary if this is a compilation.
      '''
      if self.compilation:
         return self.trackArtist
      else:
         return self.albumArtist


   def Save(self):
      self.meta.Save()

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
      >>> d = {"artist" : ["The Beatles"], "album": ["Rubber Soul"], "date": ["1965"]}
      >>> m = Mp3File('', d)
      >>> m.DestPath()
      u'Beatles/1965_Rubber-Soul'
      '''

      albumName = "_".join(w for w in [self.year, self.album, self.discNumber] if w)
      return os.path.join(Scrub(self.albumArtist), Scrub(albumName))


   def DestFile(self):
      '''
      >>> d1 = {"artist" : ["Kneebody"], "album": ["Low Electrical Worker"], 
      ...   "date": ["2008"], "tracknumber" : ['4'], "title": ["Dr. Beauchef"]}
      >>> m = Mp3File('', d1)
      >>> m.DestFile()
      u'04_Dr-Beauchef.mp3'
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
   def __init__(self, baseDir, mode="copy", onDupe="force", rate="0", 
         musicOnly=False, debug=False):
      """
      >>> f = FileDestination(".", "copy", "force", "V4")
      >>> f.vbr
      True

      >>> f = FileDestination(".", "copy", "force", "128")
      >>> f.vbr
      False

      """
      assert(mode in kModes)
      assert(onDupe in kOnDupe)

      self.baseDir = baseDir
      self.mode = mode
      self.onDupe = onDupe
      self.musicOnly = musicOnly
      self.debug = debug

      # we need to handle VBR separately from 
      self.vbr = False
      if rate.lower().startswith('v'):
         # VBR rates will be specified as 'V0'..'V6'. 
         self.vbr = True
         rate = rate[1:]

      self.rate = int(rate)

      self.moveDate = int(time.time())

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

      if self.debug:
         print "CREATING output directory {0}".format(self.currentOutputDir)
      else:
         try:
            os.makedirs(self.currentOutputDir)
         except OSError, e:
            if e.errno != errno.EEXIST:
               print "ERROR creating output directory `{0}`".format(self.currentOutputDir)
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

      handlers = { 
                   fileSource.kDirectory   : self.HandleDir,
                   fileSource.kMusic       : self.HandleMusic,
                   fileSource.kOtherFile   : self.HandleOtherFile
                  }

      print "Handling {0}: {1}".format(type, pathToFile.encode("utf-8"))
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
      if self.debug:
         print "MOVING\n{0}\nto\n{1}".format(srcFile, destFile)
      else:
         shutil.move(srcFile, destFile)
      # !!! Need to account for potential exceptions here. 
      return True

   def _DoCopy(self, srcFile, destFile):
      ''' simple copy from src-->dest. No rate change of MP3 files. '''
      retval = True
      if self.debug:
         srcFile = NormalizeFilename(srcFile)
         destFile = NormalizeFilename(destFile)
         print "COPYING\n{0}\nto\n{1}".format(srcFile, destFile)
      else:
         try:
            shutil.copyfile(srcFile, destFile)
         except (Error, IOError), e:
            print str(e)
            retval = False
      return retval

   def _DoTranscode(self, srcFile, destFile):
      ''' create a new copy of the srcFile at destFile, changing its encoding
         bit rate as we go. Requires that LAME is installed.
      '''

      retval = False
      original = Mp3File(srcFile)

      # !!!TODO: compare rate of source file; if it's less than what our
      # target rate is, copy the file as is instead of transcoding. We only
      # transcode to lower bitrates.

      cmd = ['lame', '-h']
      rateString  = "{0}".format(self.rate)
      if self.vbr:
         cmd.extend(["-V", rateString])
      else:
         cmd.extend(["-b", rateString])

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
            if val:
               cmd.extend([flag, u'{0}'.format(val)])
         except AttributeError:
            # that metadata field is missing from this file; skip it.
            pass

      # okay, all the metadata & other args are set. Pass in the src & dest 
      # values and make this go.       
      cmd.extend(['--mp3input', srcFile, destFile])

      #try:
      #   print u" ".join(cmd)
      #except UnicodeDecodeError, e:
      #   print "Error because there's unicode data here... {0}".format(e)

      if self.debug:
         for i, line in enumerate(cmd):
            #print u"{0}: {1}".format(i, line.encode('utf-8'))
            print u"{0}: {1}".format(i, line)
         print u"\n\nTRANSCODING\n{0}\nto\n{1}\nwith command line\n{2}\n".format(
            srcFile, destFile, u" ".join(cmd))
         retval = True
      else:   
         result = subprocess.call(cmd)      
         retval = result == 0
      return retval

      

   def ReplaceExisting(self, srcFile, destFile):
      ''' see if we're about to overwrite a file that already exists, and if so, 
         either
         1. overwrite it always
         2. skip it always
         3. ask the user what to do.

         Return True if we want to overwrite the file.
      '''
      if self.debug:
         print u"\nSRC = {0}".format(srcFile)
         print destFile
         print u"DEST = {0}".format(destFile)

      retval = True
      if os.path.exists(destFile):
         print "destination file already exists..."
         if self.onDupe == 'force':
            retval = True
         elif self.onDupe == 'skip':
            retval = False
         else:
            def IdFile(path, byteCount=-1):
               md5 = hashlib.md5()
               with open(path, "rb") as f:
                  md5.update(f.read(byteCount))
               return md5.digest()

            # check enough of the files to see if they're the same.
            if IdFile(srcFile, 2048) != IdFile(destFile, 2048):
               print "file {0} already exists, and appears to be different.".format(destFile)
               while 1:
                  s = raw_input("[k]eep existing file or [r]eplace?")
                  s = s.lower()[0]
                  if s in ('k', 'r'):
                     retval = (s == 'r')
                     break
            else:
               # destination file exists, but appears to be the same
               print "(but is identical. Skipping.)"
               retval = False
      return retval




   def HandleDir(self, path):
      ''' when we see a new directory, we clear the current output path...'''
      self.currentOutputDir = ""
      return True

   def HandleMusic(self, path):
      ''' the File Source is sending us a new music file. '''
      m = Mp3File(path)
      destPath = m.DestPath()
      destFile = m.DestFile()

      retval = False
      destPath = os.path.join(self.baseDir, destPath)
      if destPath != self.currentOutputDir:
         # writing to a new directory. Make sure that it exists.
         self.currentOutputDir = destPath
         try:
            self.PrepDestination()
         except IOError, e:
            print "ERROR creating destination directory {0}".format(destPath)
            return False
      destPath = os.path.join(destPath, destFile)
      if self.ReplaceExisting(path, destPath):
         # ...where MusicHandler is one of _DoCopy, _DoTranscode, _DoMove
         if self.MusicHandler(path, destPath):
            retval = True
            self.UpdateHistory(path, destPath)
      return retval


   def UpdateHistory(self, srcFile, destFile):
      ''' If we're moving a track from a maintained directory to a new directory, 
         make sure that the history file at the destination is updated with the 
         correct acq/move dates.
      '''
      # split out the directory and file names.
      srcPath, srcTrack = os.path.split(srcFile)
      destPath, destTrack = os.path.split(destFile)

      # load up the history files, neither of which may actually exist!
      srcHistory = trackHistory.History(srcPath)
      destHistory = trackHistory.History(destPath)

      # ...and update the destination history using the contents of the 
      # source history.
      acq, move = srcHistory.GetTrack(srcTrack)
      if not qReorganize:
         move = self.moveDate

      destHistory.AddTrack(destTrack, acq, move)
      destHistory.Save()




   def HandleOtherFile(self, path):
      ''' the destination of this file is currentOutputDir + originalFilename '''
      ## if we are ignoring 'other' files or this is a history file, ignore it
      # by pretending that we succeeded.
      if self.musicOnly or trackHistory.IsHistoryFile(path):
         return True

      ## Create the destination file/path
      if self.currentOutputDir:
         fileName = os.path.basename(path)
         destFile = os.path.join(self.currentOutputDir, fileName)
         return self.OtherHandler(path, destFile)
      else:
         return False



if __name__ == "__main__":
   import doctest
   doctest.testmod()