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
      print "Disc # = %s" % discNum
      disc, of = discNum.split('/')
      print "Disc %s of %s" % (disc, of)
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
   return os.path.join(Scrub(id3["artist"][0]), Scrub("%s%s" % (album, discNumber)))

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

   return os.path.join(kTargetBasePath, TargetPath(meta), filename)


   



if __name__ == "__main__":
   if len(sys.argv) >= 2 and sys.argv[1] == "-t":
      print "TESTING..." 
      doctest.testmod()
      print "DONE."

