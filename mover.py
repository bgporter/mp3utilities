#! /usr/bin/env python

''' Utility to move and rename MP3 files into a master repository location.
Requires that you have the mutagen ID parsing library installed.
'''
import doctest
import errno
import hashlib
import os
import re
import shutil
import subprocess
import sys

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
try:
   from titlecase import titlecase
except ImportError:
   def titlecase(s): return s




kTargetBasePath = "/Volumes/zappa_files/music"

class MetadataException(Exception):
   pass

def DebugLog(src, dest, rate=0):
   print src
   print dest.encode("utf-8")
   print "Rate = %s" % rate
   print 

def ErrorLog(s):
   print s
   with open("MoverErrorLog.txt", "wt") as f:
      f.write("{0}\n".format(s))   

def PrepFile(src, dest, rate):
   ''' create the directories needed for our copy or move. The attempt to
   create the directory may fail either because it already exists (not really
   an error), or because we were unable to create it for some other reason
   (drive not mounted, permissions, etc. If we try this and get an OSError
   with an errno value of errno.EEXIST, we swallow the exception and proceed,
   otherwise we re-raise the exception.
   '''
   DebugLog(src, dest, rate)
   targetPath = os.path.split(dest)[0]
   try:
      os.makedirs(targetPath)
   except OSError, e:
      if e.errno != errno.EEXIST:
         msg = "Unable to handle src file {0}".format(src)
         ErrorLog(msg)
         raise


def CopyFile(src, dest, rate=0):
   '''
      if rate is zero, copy the file as is from source to dest. 
      if rate is > 0, use lame to change the bitrate of the file.
      if rate is a string starting with 'V', use a variable bitrate encoding, 
      V0 == highest quality, V9 == lowest quality.
      05 Aug 2012: If the rate of the file we're copying is less than or equal
      to the target rate, copy the file without doing any transcoding.
   '''
   try:
      PrepFile(src, dest, rate)
   except OSError:
      # We're trying to do something with a directory that didn't have any MP3
      # files contained in it, so there's no good place to put this file. 
      # Display an error message and move on.
      return
      
   # only try to get rate info if this is actually an MP3 file.
   try:
      intRate = int(rate)
   except ValueError:
      intRate = 0

   base, ext = os.path.splitext(src)
   if ext in (".mp3",):
      if intRate:
         audio = MP3(src)
         actualRate = audio.info.bitrate / 1000
         if actualRate <= rate:
            print "file rate = %d, target rate = %d -- skipping transcode." % (actualRate, rate)
            # set the rate to zero to force a simple copy.
            rate = 0
   else:
      rate = 0

   if 0 == intRate:
      print "simple copy"
      shutil.copyfile(src, dest)
   else:
      print "transcoding"
      cmd = ['lame', '-h']
      if rate.upper().startswith("V"):
         # they want VBR encoding; the next char should be a digit 0..9
         try:
            int(rate[1])
         except ValueError:
            print "ERROR -- need a value from 0..9 for VBR quality."
            sys.exit(0)
         vbr = rate[1]
         cmd.extend(["-V", vbr])
      else:
         cmd.extend(["-b", rate])

      # okay, so the transcode rate stuff is set. Now we try to get the metadata
      # out of the MP3 so we can correctly write ID3 tags. We'll always use ID3V2 tags.
      cmd.append("--id3v2-only")

      # a list of tuples where
      # [0] is the command line flag to pass to LAME
      # [1] is the attribute name inside of the mutagen ID3 object.
      kFields = [ ("--tt", "title"),
                  ("--ta", "artist"),
                  ("--tl", "album"),
                  ("--ty", "date"),
                  ("--tn", "tracknumber"),
                  ("--tg", "genre")
                 ]
      id3 = EasyID3(src)
      for (flag, field) in kFields:
         val = id3.get(field, [u""])[0]
         if val:
            # get rid of leading/trailing double quotes that I may have 
            # stupidly put there.
            val = val.strip('"')
            cmd.extend([flag, u'{0}'.format(val)])

      # okay, all the metadata & other args are set. Pass in the src & dest 
      # values and make this go.       
      cmd.extend(['--mp3input', src, dest])

      try:
         print u" ".join(cmd)
      except UnicodeDecodeError, e:
         print "Error because there's unicode data here... {0}".format(e)
      subprocess.call(cmd)


def MoveFile(src, dest, rate):
   ''' rate is ignored when we're moving files; files are always moved
   as-is'''
   try:
      PrepFile(src, dest, rate)
      shutil.move(src, dest)
   except OSError:
      pass
   
ops = {'debug' : DebugLog, 'move' : MoveFile, 'copy': CopyFile }

def Scrub(s):
   '''
      1. convert the string into lowercase & strip outer whitespace
      2. Remove any characters that we don't want in filenames or paths from a
      string, eliminating multiple whitespace chars within
      3. Replace whitespace with '-'
      >>> Scrub(u"No Illegal characters")
      u'no-illegal-characters'
      >>> Scrub(u"this: <should> /be\\ shorter?")
      u'this-should-be-shorter'

   '''
   #s = s.lower()

   kIllegals = u":/\\?<>,!\""
   try:
      for c in kIllegals:
         s = s.replace(c, u" ")
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



def TargetPath(destPath, id3):
   '''
      @param id3 Dict containing track metadata that we use to generate the
      target path that can elsewhere be appended to the base path for our file
      move.
      The path that we'll generate will have the forms:

      Artist/Album
      or
      Artist/Album (disc #)

      >>> d1 = {'album' : [u'Low Electrical Worker'], 'artist': [u'Kneebody']}
      >>> TargetPath(u'', d1)
      u'kneebody/low-electrical-worker'
      >>> d1['discnumber'] = [u'2/3']
      >>> TargetPath(u'', d1)
      u'kneebody/low-electrical-worker_(disc_2)'
   '''
   discNumber = u""
   try:
      discNum = id3['discnumber'][0]
      disc, of = map(int, discNum.split('/'))
      if disc > 0 and of > 1:
         discNumber = u"_(disc_%d)" % disc
   except (ValueError, KeyError):
      # ignore the error
      pass

   try:
      artist = Scrub(id3["artist"][0])
   except KeyError:
      artist = ''

   try:
      performer = Scrub(id3['performer'][0])
   except KeyError:
      performer = ''

   # if both artist and performer are defined, use whichever one is shorter.
   if artist:
      if performer:
         if len(artist) > len(performer):
            artist = performer
   else:
      if performer:
         artist = performer
      else:
         artist = u"unknown-artist"
   # 7/4/13 -- add a leading year before the album name so that albums sort
   # chronologically.
   try:
      year = id3['date'][0]
      year = year + u'_'
   except KeyError:
      year = ''



   try:
      album = id3["album"][0]
   except KeyError:
      album = u"unknown-album"

   return os.path.join(destPath, artist, Scrub(u"%s%s%s" % (year, album, discNumber)))

def Filename(id3, base):
   '''
      Constructs a filename (without extension) from the provided ID3
      metadata.

      Format: <trackNo>-<title>
      >>> d1 = { 'tracknumber': [u'1'], 'title' : [u"Teddy Ruxpin"]}
      >>> Filename(d1, u"")
      u'01_teddy-ruxpin'
      >>> d1['tracknumber'] = [u'2/3']
      >>> Filename(d1, u"")
      u'02_teddy-ruxpin'
      >>> del d1['tracknumber']
      >>> Filename(d1, u"")
      u'teddy-ruxpin'
   '''
   try:
      trackNum = id3['tracknumber'][0]
      # Amazon track numbers are sometimes in the form 'x/y')
      trackNum = trackNum.split('/')[0]
      trackNum = u"%02d_" % int(trackNum)
   except (KeyError, ValueError):
      trackNum = u""

   try:
      return u"%s%s" % (trackNum, Scrub(id3['title'][0]))
   except KeyError:
      # no id3 title, so fall back to using the original file name.
      print "base = ", base
      return u"%s%s" % (trackNum, Scrub(base))


def FullTargetPath(destPath, f, base, extension):
   '''
      @param f path/name of the file we want to rename and move. The output of
      this function is the complete path and filename of the destination.
      >>> kTargetBasePath = "/foo/"
   '''

   try:
      meta = EasyID3(f)
   except mutagen.id3.ID3NoHeaderError:
      meta = {}
   filename = Filename(meta, base) + extension

   return os.path.join(TargetPath(destPath, meta), filename)


def TrackInfo(mp3File, md5):
   id3Data = EasyID3(mp3File)
   mp3Data = MP3(mp3File)
   for attr in ('title', 'artist', 'album'):
      print "   %s: %s" % (attr, id3Data[attr][0])
   print "   bitrate: %d" % (int(mp3Data.info.bitrate) / 1000)
   duration = int(mp3Data.info.length + 0.5)
   print "   duration: %d:%d" % (duration / 60, duration % 60)
   print "   MD5: %s" % md5
   print


def CompareFiles(src, dest, mode):
   ''' it may be that there's another file present with the same name at the
      destination, but we still want to replace it -- maybe it's a lousy old 
      low bitrate version. We'll compare hashes first; if it's an exact dupe,
      there's nothing to do. If they are different, we should let the user
      decide what to do (replace the current dest, or keep it)
   '''
   srcMd5 = hashlib.md5()
   destMd5 = hashlib.md5()
   print ("...comparing possible duplicate files")
   srcMd5.update(open(src, "rb").read())
   destMd5.update(open(dest, "rb").read())
   if srcMd5.digest() != destMd5.digest():
      print "Destination file already exists, and is different."
      if os.path.splitext(dest)[1] in (".mp3",):
         print "Existing file:"
         TrackInfo(dest, destMd5.hexdigest())
         print "New file:"
         TrackInfo(src, srcMd5.hexdigest())

      while 1:
         s = raw_input("[k]eep existing file, or [r]eplace?")
         s = s.lower()[0]
         if s in ('k', 'r'):
            if s == 'r':
               DupeFile(src, dest, mode, 0, True)
            break




def DupeFile(src, dest, mode, rate, force=False):
   '''
      create a copy of the file in the correct location (unless there's
      already one there!). Mode is one of:
      - "move"
      - "copy"
      - "debug" (just print the two files)
   '''
   exists = os.path.exists(dest)
   if force or not exists:
      ops[mode](src, dest, rate)
   else:
      CompareFiles(src, dest, mode)

def HandleDir(root, files, destPath, rate, mode="copy", force=False):
   '''
      Operate on the files in a given directory. 
      root = the directory 
      files = list of files in the directory
      mode = move/copy/debug
   '''
   print "Handling directory '%s'" % root
   outputPath = u""
   others = []
   for f in files:
      base, ext = os.path.splitext(f)
      srcFile = os.path.join(root, f)
      if ext.lower() in (u".mp3",):
         try:
            destFile = FullTargetPath(destPath, srcFile, base, ext)
            try:
               DupeFile(srcFile, destFile, mode, rate, force)
            except OSError, e:
               # can't generate the output file -- print the reason and exit
               # the app.
               sys.exit("ERROR (%d): %s - %s" % (e.errno, e.strerror, e.filename))
            if not outputPath:
               outputPath = os.path.split(destFile)[0]
         except MetadataException, e:
            sys.stderr.write("Unable to handle %s: %s\n" % (path, str(e)))
      else:
         # remember this file & move it later.
         others.append(f)
   # if there were any image files, etc, don't forget them!
   for f in others:
      base, ext = os.path.splitext(f)
      print "checking %s '%s'" % (base, ext)
      if ext.lower() in ('.jpg', '.gif', '.png', '.txt'):
         dest = os.path.join(outputPath, f)
         src = os.path.join(root, f)
         DupeFile(src, dest, mode, 0, force)
      else:
         print "ignoring %s '%s'" % (base, ext)


def HandleTree(top, dest, rate, mode, force):
   #rate = int(rate)
   for root, dirs, files in os.walk(top):
      HandleDir(root, files, dest, rate, mode, force)



if __name__ == "__main__":
   import sys
   print sys.argv


   import argparse
   parser = argparse.ArgumentParser("Move and rename MP3 files.")
   parser.add_argument("-t", "--test", action='store_true', 
      help ="run unit tests (other options ignored)")
   parser.add_argument("-f", "--force", action='store_true', 
      help="force a copy/move when duplicate files are found at the destination")
   parser.add_argument("-s", "--src", action="store", nargs="?",
      default=os.getcwd(), help="Source directory containing mp3 files")
   parser.add_argument("-d", "--dest", action="store", nargs="?",
      default=kTargetBasePath, help="Destination directory for mp3 files")
   parser.add_argument("-m", "--mode", action="store", nargs="?",
      default = "copy", choices=["debug", "copy", "move"], 
      help = "Move/copy/debug")
   parser.add_argument("-r", "--rate", action="store", nargs="?",
      default="0", help="Transcode bitrate (copy only). Use V[0..9] for VBR")


   parser.add_argument("-i", "--input", action="store", nargs="?",
      default="", 
      help="Input file containing directores to handle (1 per line, relative to `src')" )

   args = parser.parse_args()


   if args.test:
      import doctest
      doctest.testmod()
   else:
      if args.input:
         print "INPUT: %s" % args.input
         try:
            with open(args.input, "r") as f:
               for dirName in f:
                  dirName = dirName.strip()
                  if dirName:
                     src = os.path.join(args.src, dirName)
                     try:
                        HandleTree(src, args.dest, args.rate, args.mode, args.force)
                     except IOError, e:
                        print "Error handling directory at %s: %s" % (src,
                              str(e))
         except IOError:
            print "Error opening input file '%s'" % args.input
      else:
         HandleTree(args.src, args.dest, args.rate, args.mode, args.force)
   print "Done."         






