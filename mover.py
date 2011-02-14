#! /usr/bin/bash

''' Utility to move and rename MP3 files into a master repository location.
Requires that you have the mutagen ID parsing library installed.
'''
import doctest
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

def CopyFile(src, dest):
   try:
      targetPath = os.path.split(dest)[0]
      os.makedirs(targetPath)
   except OSError:
       # dir already there or can't be created -- if it can't be created, then
       # the next call will also fail.
       pass
   DebugLog(src, dest)
   shutil.copyfile(src, dest)
   
ops = {'debug' : DebugLog, 'move' : shutil.move, 'copy': CopyFile }

def Scrub(s):
   '''
      Remove any characters that we don't want in filenames or paths from a
      string.
      >>> Scrub("No Illegal characters")
      'No Illegal characters'
      >>> Scrub("this: <should> /be\\ shorter?")
      'this should be shorter'

   '''
   kIllegals = u":/\\?<>"
   try:
      for c in kIllegals:
         s = s.replace(c, u"")
      return s
   except UnicodeDecodeError, e:
      return Scrub(s.decode("utf-8"))



def TargetPath(id3):
   '''
      @param id3 Dict containing track metadata that we use to generate the
      target path that can elsewhere be appended to the base path for our file
      move.
      The path that we'll generate will have the forms:

      Artist/Album
      or
      Artist/Album (disc #)

      >>> kTargetBasePath = u''
      >>> kTargetBasePath
      u''
      >>> d1 = {'album' : [u'Low Electrical Worker'], 'artist': [u'Kneebody']}
      >>> TargetPath(d1)
      u'Kneebody/Low Electrical Worker'
      >>> d1['discnumber'] = [u'2/3']
      >>> TargetPath(d1)
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

   return os.path.join(kTargetBasePath, artist, Scrub(u"%s%s" % (album, discNumber)))

def Filename(id3, base):
   '''
      Constructs a filename (without extension) from the provided ID3
      metadata.

      Format: <trackNo>-<title>
      >>> d1 = { 'tracknumber': [u'1'], 'title' : [u"Teddy Ruxpin"]}
      >>> Filename(d1)
      u'01-Teddy Ruxpin'
      >>> d1['tracknumber'] = [u'2/3']
      >>> Filename(d1)
      u'02-Teddy Ruxpin'
      >>> del d1['tracknumber']
      >>> Filename(d1)
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


def FullTargetPath(f, base, extension):
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

   return os.path.join(TargetPath(meta), filename)


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

def HandleDir(root, files, mode="copy"):
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
      path = os.path.join(root, f)
      if ext.lower() in (u".mp3",):
         print path
         try:
            dest = FullTargetPath(path, base, ext)
            DupeFile(path, dest, mode)
            if not outputPath:
               outputPath = os.path.split(dest)[0]
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
   if len(sys.argv) >= 2 and sys.argv[1] == "-t":
      print "TESTING..." 
      doctest.testmod()
      print "DONE."
   else:
      try:
         top = sys.argv[1]
      except IndexError:
         top = os.getcwd()
      for root, dirs, files in os.walk(top):
         HandleDir(root, files, "copy")





