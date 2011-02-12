#! /usr/bin/bash

''' Utility to move and rename MP3 files into a master repository location.
Requires that you have the mutagen ID parsing library installed.
'''

def Scrub(s):
   '''
      Remove any characters that we don't want in filenames or paths from a
      string.
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
   '''
   discNumber = ""
   try:
      discNumber = id3['discnumber']
      disc, of = discNumber.split('/')
      if disc != of:
         discNumber = " (disc %s)" % disc
   except KeyError:
      pass

   try:
      id3["album"]
   except KeyError:
      id3["album"] = "(no album)"

   id3["discNumber"] = discNumber
   return os.path.join(id3["artist"], "%(album)s%(discNumber)s" % id3)




