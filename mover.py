#! /usr/bin/env python

''' Utility to move and rename MP3 files into a master repository location.
Requires that you have the mutagen ID parsing library installed.
'''

import os


import fileSource
import fileDestination



kTargetBasePath = "/Volumes/zappa_files/music"


def DebugLog(src, dest, rate=0):
   print src
   print dest.encode("utf-8")
   print "Rate = %s" % rate
   print 

def ErrorLog(s):
   print s
   with open("MoverErrorLog.txt", "wt") as f:
      f.write("{0}\n".format(s))   






if __name__ == "__main__":
   import sys


   import argparse
   parser = argparse.ArgumentParser("Move and rename MP3 files.")
   parser.add_argument("-t", "--test", action='store_true', 
      help ="run unit tests (other options ignored)")
   parser.add_argument("-u", "--dupe", action='store', nargs='?',
      default="skip", choices=["force", "skip", "ask"], 
      help="on dupe files: force move, skip file, ask user?")
   parser.add_argument("-s", "--src", action="store", nargs="?",
      default=os.getcwd(), help="Source directory containing mp3 files")
   parser.add_argument("-d", "--dest", action="store", nargs="?",
      default=kTargetBasePath, help="Destination directory for mp3 files")
   parser.add_argument("-m", "--mode", action="store", nargs="?",
      default = "copy", choices=["debug", "copy", "move"], 
      help = "Move/copy/debug")
   parser.add_argument("-r", "--rate", action="store", nargs="?",
      default="0", help="Transcode bitrate (copy only). Use V[0..9] for VBR")
   parser.add_argument("-o", "--musiconly", action='store_true', 
      help="Only move/copy music files; skip .jpg, etc.")
   parser.add_argument('-c', '--cleanup', action="store_true", 
      help="Remove directories left empty after moving files")


   parser.add_argument("-i", "--input", action="store", nargs="?",
      default="", 
      help="Input file containing directores to handle (1 per line, relative to `src')" )

   args = parser.parse_args()


   if args.test:
      # run the module tests and exit.
      import doctest
      print "running module tests."
      doctest.testmod(fileSource)
      doctest.testmod(fileDestination)
      print "done."
      sys.exit(0)

   # Real operation -- first, get the file source object ready to go.   
   others = None
   # if there's an input file name given, it should contain one directory
   # path per line (relative to src). Create a cleaned-up list of those
   # directories.
   if args.input:
      print "INPUT: %s" % args.input
      others = []
      try:
         with open(args.input, "r") as f:
            for dirName in f:
               others.append(dirName.strip())
      except IOError:
         print "Error opening input file '%s'" % args.input

   source = fileSource.FileSource(unicode(args.src), others)

   # ...then prepare the destination handler object.
   mode = args.mode
   debug = False
   if 'debug' == mode:
      debug = True 
      mode = 'copy'



   dest = fileDestination.FileDestination(unicode(args.dest), mode, args.dupe, 
      args.rate, args.musiconly, args.cleanup, debug)


   toHandle = list(source)
   fileCount = sum(1 for item in toHandle if item[0] == fileSource.kMusic)

   if fileCount:
      print "{0} {1} files.".format("copying" if "copy" == mode else "moving", fileCount)
      # and finally perform the move/copy:
      mp3FileNum = 0
      for (fileType, fName) in toHandle:
         try:
            dest.HandleFile(fileType, fName)
         except fileDestination.MetadataException as e:
            print "ERROR: {0}".format(str(e))
         if fileSource.kMusic == fileType:
            mp3FileNum += 1
            print "{0:.2%}% complete".format(float(mp3FileNum) / fileCount)
      print "Done."         
   else:
      print "Nothing to do."






