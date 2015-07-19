import os

'''
   Output a file that contains a line per directory relative to the top-level directory
   as follows:

   If we start at /Volumes/zappa_files/music there's a level of directories 
   beneath that (artist level), and within each artist directory, there are one 
   or more album directories. This will only output album directories.

'''

# kTopDir = "/Volumes/zappa_files/music"

# # we ignore directories that don't split into this many parts
# kAlbumDirComponentCount = 2 + len(kTopDir.split(os.path.sep))

# print "looking for {0} parts".format(kAlbumDirComponentCount)
# output = []


# for dirname, dirlist, filenames in os.walk(kTopDir):
#    parts = dirname.split(os.path.sep)
#    if kAlbumDirComponentCount == len(parts):
#       output.append("{0}/{1}".format(parts[-2], parts[-1]))

# for line in sorted(output):
#    print line

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
      print p


