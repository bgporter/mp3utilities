import os
import random

import fileSource
import fileDestination

kTargetBasePath = '/media/usb1/'


class Shuffler(object):
   def __init__(self, source, dest, pinned=None):
      self.source = source
      self.dest = dest
      self.pinned = pinned










if __name__ == "__main__":
   import sys
   import argparse

   parser = argparse.ArgumentParser("Shuffle tracks onto USB drive for the car.")
   parser.add_argument("-t", "--test", action='store_true', 
      help ="run unit tests (other options ignored)")
   parser.add_argument("-u", "--dupe", action='store', nargs='?',
      default="skip", choices=["force", "skip", "ask"], 
      help="on dupe files: force move, skip file, ask user?")
   parser.add_argument("-s", "--src", action="store", nargs="?",
      default=os.getcwd(), help="Source directory containing mp3 files")
   parser.add_argument("-d", "--dest", action="store", nargs="?",
      default=kTargetBasePath, help="Destination directory for mp3 files")
   parser.add_argument("-p", "--pinned", action="store", nargs="?",
      default="", 
      help="Input file containing directores to force onto the drive (1 per line, relative to `src')" )   

   args = parser.parse_args()

   if args.test:
      import doctest
      print "running module tests..."
      doctest.testmod()
      print "done."
      sys.exit(0)


   # we can store at most 5000 files for the player to read.
   maxFiles = 5000
   # each time we run, we cycle in this many new files.
   refreshCount = 500



   # get an inventory of all the files that are already on the destination
   destSource = fileSource.FileSource(args.dest)
   print "Getting list of files at destination {0}".format(args.dest)
   destInventory = [f for (t, f) in destSource if t == fileSource.kMusic]

   # get a list of the files that we want to have pinned on the dest
   pinnedSrc = fileSource.FileSource(args.src, args.pinned)
   print "Getting list of files to pin onto destination"
   pinnedFiles = [f for (t,f) in pinnedSrc if t == fileSource.kMusic]
   # get a list of all of the source files that aren't pinned.
   src = fileSource.FileSource(args.src)
   print "Getting list of all source files on {0}".format(args.src)
   srcFiles = [f for (t,f) in src if t == fileSource.kMusic]
   

   toCopy = []
   doNotDelete = []
   dest = fileDestination.FileDestination(args.dest, "copy", "skip", "0", True)

   for f in pinnedFiles:
      destPath = dest.MusicLocation(f)
      if not os.path.exists(destPath):
         toCopy.append(f)
      else:
         doNotDelete.append(destPath)

   # for each of the files that should be pinned to the destination, there's 
   # an entry either in toCopy (because it's not there yet) or doNotDelete
   # (because it's already there, and we need to know to not delete it below.)
   
   doNotDelete = set(doNotDelete)
   destFileCount = len(destInventory)
   pinnedCopyFileCount = len(toCopy)
   availableRoom = maxFiles - destFileCount

   assert len(pinnedFiles) == pinnedCopyFileCount + len(doNotDelete)

   # we want to copy at least this many files over to the dest.
   newFileCount = pinnedCopyFileCount + refreshCount

   print "Pinned file count: {0}".format(pinnedCopyFileCount)
   print "Available Room: {0}".format(availableRoom)
   print "new file count: {0}".format(newFileCount)


   # We may need to delete some files from the destination before we can do 
   # anything here. NO matter what, we want to bring in at least 'refreshCount' new
   # files. At the end, we want there to be 'maxFiles' files on the destination, which 
   # will consist of 
   # 1. All of the pinned files
   # 2. At least refreshCount new files.
   # 3. Some files that were already at the destination. 
   # 
   # If we need to delete some files to make room for the 500 new ones, we need 
   # to make sure that we don't accidentally delete any of the pinned files.
   deleteCount = 0
   if newFileCount > availableRoom:
      deleteCount = newFileCount - availableRoom
   else:
      # there's more room than we need -- use it all up.
      newFileCount = availableRoom

   print "About to delete {0} files from {1}".format(deleteCount, args.dest)
   response = raw_input("Enter to continue or q to quit. ")
   if 'q' == response.lower():
      sys.exit(0)

   # get the files at the destination all mixed up and start randomly deleting files
   # that aren't protected by being pinned.
   if deleteCount > 0:
      random.shuffle(destInventory)
      for (i, destFile) in enumerate(destInventory):
         if destFile not in doNotDelete:
            print "deleting file {0}".format(destFile.encode('utf-8'))
            os.remove(destFile)
            # see if we need to trim empty directories
            # peel off the file name first.
            pth1, pth2 = os.path.split(destFile)
            if not os.listdir(pth1):
               # empty, so delete the album directory.
               print 'Deleting empty directory {0}'.format(pth1.encode('utf-8'))
               os.rmdir(pth1)
               # see if we can also delete the artist directory
               pth1, pth2 = os.path.split(pth1)
               if not os.listdir(pth1):
                  # yep, the artist dir is empty. Get rid of it.
                  print 'Deleting empty directory {0}'.format(pth1.encode('utf-8'))
                  os.rmdir(pth1)

            destInventory[i] = ''
            deleteCount -= 1
            if 0 == deleteCount:
               break
   # okay, now we do the opposite -- we need to
   # 1. Copy up any pinned files that aren't up there yet
   # 2. Shuffle the source files and start copying files up that aren't already
   #    at the destination.

   print "About to copy files to {0}".format(args.dest)

   for f in toCopy:
      print "Copying pinned file {0} ({1} to go...)".format(f, newFileCount)
      dest.HandleMusic(f)
      newFileCount -= 1

   random.shuffle(srcFiles)
   index = 0
   while newFileCount > 0:
      nextFile = srcFiles[index]
      index += 1
      destPath = dest.MusicLocation(nextFile)
      if not os.path.exists(destPath):
         # !!! do any additional tests here, check genre, length, etc.
         print "Copying {0} ({1} to go)".format(nextFile, newFileCount)
         dest.HandleMusic(nextFile)
         newFileCount -= 1









   






