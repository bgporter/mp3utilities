#! /usr/bin/bash

''' Utility to move and rename MP3 files into a master repository location.
Requires that you have the mutagen ID parsing library installed.
'''
import doctest
import os
import shutil
import sys

from mutagen.easyid3 import EasyID3


kTargetBasePath = "/Volumes/homes/MusicLibrary"

def DebugLog(src, dest):
   print "->%s\n<-%s\n" % (src, dest)
   
ops = {'debug' : DebugLog, 'move' : shutil.move, 'copy': shutil.copyfile }

def Scrub(s):
   '''
      Remove any characters that we don't want in filenames or paths from a
      string.
      >>> Scrub("No Illegal characters")
      'No Illegal characters'
      >>> Scrub("this: <should> /be\\ shorter?")
      'this should be shorter'

   '''
   kIllegals = ":/\\?<>"
   for c in kIllegals:
      s = s.replace(c, "")
   return s



def TargetPath(id3):
   '''
      @param id3 Dict containing track metadata that we use to generate the
      target path that can elsewhere be appended to the base path for our file
      move.
      The path that we'll generate will have the forms:

      Artist/Album
      or
      Artist/Album (disc #)

      >>> kTargetBasePath = ''
      >>> d1 = {'album' : 'Low Electrical Worker', 'artist': 'Kneebody'}
      >>> TargetPath(d1)
      'Kneebody/Low Electrical Worker'
      >>> d1['discnumber'] = '2/3'
      >>> TargetPath(d1)
      'Kneebody/Low Electrical Worker (disc 2)'
   '''
   discNumber = ""
   try:
      discNum = id3['discnumber'][0]
      disc, of = discNum.split('/')
      if of != "1":
         discNumber = " (disc %s)" % disc
   except KeyError:
      print "!!! EXCEPTION !!!"
      pass

   try:
      album = id3["album"][0]
   except KeyError:
      album = "(no album)"

   id3["discNumber"] = discNumber
   return os.path.join(kTargetBasePath, Scrub(id3["artist"][0]), Scrub("%s%s" % (album, discNumber)))

def Filename(id3):
   '''
      Constructs a filename (without extension) from the provided ID3
      metadata.

      Format: <trackNo>-<title>
      >>> d1 = { 'tracknumber': '1', 'title' : "Teddy Ruxpin"}
      >>> Filename(d1)
      '01-Teddy Ruxpin'
      >>> d1['tracknumber'] = '2/3'
      >>> Filename(d1)
      '02-Teddy Ruxpin'
      >>> del d1['tracknumber']
      >>> Filename(d1)
      'Teddy Ruxpin'



   '''
   try:
      trackNum = id3['tracknumber'][0]
      # Amazon track numbers are sometimes in the form 'x/y')
      trackNum = trackNum.split('/')[0]
      trackNum = "%02d-" % int(trackNum)
   except (KeyError, ValueError):
      trackNum = ""

   return "%s%s" % (trackNum, Scrub(id3['title'][0]))


def FullTargetPath(f):
   '''
      @param f path/name of the file we want to rename and move. The output of
      this function is the complete path and filename of the destination.
      >>> kTargetBasePath = "/foo/"
   '''

   extension = os.path.splitext(f)[1]
   meta = EasyID3(f)
   filename = Filename(meta) + extension

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
      print "ERROR -- file `%s' already exists."

def HandleDir(root, files, mode="copy"):
   '''
      Operate on the files in a given directory. 
      root = the directory 
      files = list of files in the directory
      mode = move/copy/debug
   '''
   outputPath = ""
   others = []
   for f in files:
      base, ext = os.path.splitext(f)
      path = os.path.join(root, f)
      if ext.lower() in (".mp3",):
         dest = FullTargetPath(path)
         DupeFile(path, dest, mode)
         if not outputPath:
            outputPath = os.path.split(FullTargetPath(path))[0]
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
         HandleDir(root, files, "debug")





