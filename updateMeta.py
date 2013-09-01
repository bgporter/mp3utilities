#! /usr/bin/env python

'''
   Using the CSV files that we've already created, update file metadata where it's been edited, 
   and move any 'deleted' files into a special quarantine location until we feel confident
   actually deleting them.
'''

import csv
import errno
import os
import shutil

from mutagen.easyid3 import EasyID3

import meta


kMp3FileRoot = '/Volumes/zappa_files/music'
kQuarantineRoot = '/Volumes/zappa_files/quarantine'
kCsvFileRoot = os.path.expanduser('~/personal/utilities/mp3/mover')

kOriginalPath = os.path.join(kCsvFileRoot, 'original')
kEditPath = os.path.join(kCsvFileRoot, 'edit')


def LoadCsvFile(filePath):
   '''
      load a CSV file and return a dict where each item is
      mp3filepath: ["artist", "title", "album", "tracknumber", "genre", "date", "bitrate",  "length"]
   '''
   d = {}
   with open(filePath, "rb") as f:
      reader = csv.reader(f)
      for row in reader:
         k = row[-1]
         v = [v.decode("utf-8") for v in row[:-1]]
         # print k, v
         d[k] = v
   return d


def EditFile(mp3file, originalData, editData):
   '''
      Update the id3 data according to the edits.
   '''
   fileMeta = EasyID3(os.path.join(kMp3FileRoot, mp3file))
   for i in range(6):
      print "   {0} - '{1}' -> '{2}'".format(meta.kMetadataFields[i], 
         originalData[i].encode("utf-8"), 
         editData[i].encode("utf-8"))
      
      fileMeta[meta.kMetadataFields[i]] = editData[i]
   fileMeta.save()

def DeleteFile(mp3File):
   '''
      move move mp3File frpm kMp3FileRoot to kQuarantineRoot

   '''
   src = os.path.join(kMp3FileRoot, mp3File)
   if os.path.exists(src):
      dest = os.path.join(kQuarantineRoot, mp3File)

      # before we move, we need to make sure that the directory tree we need 
      # exists. If the makedirs() call fails, it will probably be because the 
      # directory we need is already there, and it's not really a failure.
      targetPath = os.path.split(dest)[0]
      try:
         os.makedirs(targetPath)
      except OSError, e:
         if e.errno != errno.EEXIST:
            raise
      shutil.move(src, dest)


def CompareFiles(fileName):
   '''
      load two files, each named 'fileName', one from the original dir, one from the edit dir.
   '''


   originalData = LoadCsvFile(os.path.join(kOriginalPath, fileName))
   editData = LoadCsvFile(os.path.join(kEditPath, fileName))
   for mp3file in sorted(originalData.keys()):
      try:
         original = originalData[mp3file]
         edit = editData[mp3file]
         if edit != original:
            print "EDITED: '{0}'".format(mp3file)
            EditFile(mp3file, original, edit)
      except KeyError:
         print "Delete  '{0}'".format(mp3file)
         DeleteFile(mp3file)


if __name__ == "__main__":
   import sys
   fileName = "{0}.csv".format(sys.argv[1])
   CompareFiles(fileName)