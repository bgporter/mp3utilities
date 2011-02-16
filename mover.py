#! /usr/bin/env python

''' Utility to move and rename MP3 files into a master repository location.
Requires that you have the mutagen ID parsing library installed.
'''
import doctest
import errno
import os
import shutil
import sys

import mutagen
from mutagen.easyid3 import EasyID3


kTargetBasePath = "/Volumes/homes/temp/music"

class MetadataException(Exception):
   pass

def DebugLog(src, dest):
   print src
   print dest.encode("utf-8")
   print 

def PrepFile(src, dest):
   ''' create the directories needed for our copy or move. The attempt to
   create the directory may fail either because it already exists (not really
   an error), or because we were unable to create it for some other reason
   (drive not mounted, permissions, etc. If we try this and get an OSError
   with an errno value of errno.EEXIST, we wallow the exception and proceed,
   otherwise we re-raise the exception.
   '''
   try:
      targetPath = os.path.split(dest)[0]
      os.makedirs(targetPath)
      DebugLog(src, dest)
   except OSError, e:
      if e.errno != errno.EEXIST:
         raise


def CopyFile(src, dest):
   PrepFile(src, dest)
   shutil.copyfile(src, dest)

def MoveFile(src, dest):
   PrepFile(src, dest)
   shutil.move(src, dest)
   
ops = {'debug' : DebugLog, 'move' : MoveFile, 'copy': CopyFile }

def Scrub(s):
   '''
      Remove any characters that we don't want in filenames or paths from a
      string.
      >>> Scrub(u"No Illegal characters")
      u'No Illegal characters'
      >>> Scrub(u"this: <should> /be\\ shorter?")
      u'this should be shorter'

   '''
   kIllegals = u":/\\?<>"
   try:
      for c in kIllegals:
         s = s.replace(c, u"")
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
      u'Kneebody/Low Electrical Worker'
      >>> d1['discnumber'] = [u'2/3']
      >>> TargetPath(u'', d1)
      u'Kneebody/Low Electrical Worker (disc 2)'
   '''
   discNumber = u""
   try:
      discNum = id3['discnumber'][0]
      disc, of = discNum.split('/')
      if of != "1":
         discNumber = u" (disc %s)" % disc
   except (ValueError, KeyError):
      # ignore the error
      pass

   try:
      artist = Scrub(id3["artist"][0])
   except KeyError:
      artist = u"unknown artist"

   try:
      album = id3["album"][0]
   except KeyError:
      album = u"unknown album"

   return os.path.join(destPath, artist, Scrub(u"%s%s" % (album, discNumber)))

def Filename(id3, base):
   '''
      Constructs a filename (without extension) from the provided ID3
      metadata.

      Format: <trackNo>-<title>
      >>> d1 = { 'tracknumber': [u'1'], 'title' : [u"Teddy Ruxpin"]}
      >>> Filename(d1, u"")
      u'01-Teddy Ruxpin'
      >>> d1['tracknumber'] = [u'2/3']
      >>> Filename(d1, u"")
      u'02-Teddy Ruxpin'
      >>> del d1['tracknumber']
      >>> Filename(d1, u"")
      u'Teddy Ruxpin'
   '''
   try:
      trackNum = id3['tracknumber'][0]
      # Amazon track numbers are sometimes in the form 'x/y')
      trackNum = trackNum.split('/')[0]
      trackNum = u"%02d-" % int(trackNum)
   except (KeyError, ValueError):
      trackNum = u""

   try:
      return u"%s%s" % (trackNum, Scrub(id3['title'][0]))
   except KeyError:
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


def DupeFile(src, dest, mode="copy"):
   '''
      create a copy of the file in the correct location (unless there's
      already one there!). Mode is one of:
      - "move"
      - "copy"
      - "debug" (just print the two files)
   '''
   if not os.path.exists(dest):
      ops[mode](src, dest)
   else:
      print "ERROR -- file `%s' already exists." % dest

def HandleDir(root, files, destPath, mode="copy"):
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
               DupeFile(srcFile, destFile, mode)
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
      if ext.lower() in ('.jpg', '.gif', '.png', '.txt'):
         dest = os.path.join(outputPath, f)
         src = os.path.join(root, f)
         DupeFile(src, dest, mode)




if __name__ == "__main__":
   # TODO:
   # - add real arg parsing
   # - test file moving
   import argparse
   parser = argparse.ArgumentParser("Move and rename MP3 files.")
   parser.add_argument("-t", "--test", action='store_true', 
      help ="run unit tests")
   parser.add_argument("-s", "--src", action="store", nargs="?",
      default=os.getcwd(), help="Source directory containing mp3 files")
   parser.add_argument("-d", "--dest", action="store", nargs="?",
      default=kTargetBasePath, help="Destination directory for mp3 files")
   parser.add_argument("-m", "--mode", action="store", nargs="?",
      default = "copy", choices=["debug", "copy", "move"], 
      help = "Move/copy/debug")

   args = parser.parse_args()

   if args.test:
      import doctest
      doctest.testmod()
   else:
      for root, dirs, files in os.walk(args.src):
         HandleDir(root, files, args.dest, args.mode)
   print "Done."         






