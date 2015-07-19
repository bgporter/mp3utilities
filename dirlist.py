import os

'''
   Output a file that contains a line per directory relative to the top-level directory
   as follows:

   If we start at /Volumes/zappa_files/music there's a level of directories 
   beneath that (artist level), and within each artist directory, there are one 
   or more album directories. This will only output album directories.

'''

import sys
import os

import fileSource

if __name__ =="__main__":
   import argparse
   parser = argparse.ArgumentParser("List subdirectories with MP3 files.")
   parser.add_argument("-s", "--src", action="store", nargs="?",
      default=os.getcwd(), help="Source directory containing mp3 files")  

   args = parser.parse_args()

   srcPath = os.path.normpath(args.src)


   paths = []

   fs = fileSource.FileSource(srcPath)
   for (fileType, filePath) in fs:
      if fileSource.kDirectory == fileType:
         relative = os.path.relpath(filePath, srcPath)
         pathComponents = relative.split(os.sep)
         if 2 == len(pathComponents):
            paths.append(relative)

   for p in sorted(paths, key=unicode.lower):
      print p.encode("utf-8")


