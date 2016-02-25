import os
import random

import fileSource
import fileDestination
import trackHistory

kTargetBasePath = '/media/usb1/'

kGenres = "Jazz,Rock,R&B,House,Electronica.Electronic,Funk,Blues,Latin,Alternative Rock,Pop"
kGenres = tuple(kGenres.split(','))

# we can store at most 5000 files for the player to read.
kMaxFiles = 5000
# each time we run, we cycle in this many new files.
kRefreshCount = 500



def DeleteTrack(trackFile):
   ''' trackFile is the full path to the track we want to delete. Delete the file 
      (if it exists) and also remove it from a history file if it's there. 

      If deleting this file leaves empty album and artist directories, remove them 
      as we exit.
   '''
   print "deleting file {0}".format(destFile.encode('utf-8'))
   path, track = os.path.split(trackFile)
   history = trackHistory.History(path)
   os.remove(trackFile)
   history.RemoveTrack(track)
   history.Save()

   # see if we need to trim empty directories
   # peel off the file name first.
   pth1, pth2 = os.path.split(destFile)
   print "checking {0} for deletion...".format(pth1.encode('utf-8'))
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



def FilterTrack(trackFile):
   ''' Decide whether this track should be copied over or not, based 
      on criteria like duration, genre, etc. If anyone but me ever used this
      code it should be parameterized.

      Returns bool, true = use this file, false = skip it.
   '''
   retval = False

   mp3 = fileDestination.Mp3File(trackFile)
   if mp3.length < (9 * 60):
      if mp3.genre in kGenres:
         retval = True
   return retval


def GetMusicFiles(fSource):
   ''' fSource is a fileSource.FileSource object. Returns a list of all the Mp3
      files contained in that source.
   '''
   return [f for (t, f) in fSource if t == fileSource.kMusic]


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
   parser.add_argument("-r", "--rate", action="store", nargs="?",
      default="0", help="Transcode bitrate (copy only). Use V[0..9] for VBR")
   parser.add_argument("-m", "--max", action="store", nargs="?", type=int, 
      default=kMaxFiles, help="Maximum number of files on the destination")
   parser.add_argument('-n', "--new", action="store", nargs="?", type=int, 
      default=kRefreshCount, help="Number of new files to shuffle in")
   parser.add_argument('-a', '--add', action="store", nargs="?",
       help="path to directory holding files to add")
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

   # get an inventory of all the files that are already on the destination
   destSource = fileSource.FileSource(args.dest)
   print "Getting list of files at destination {0}".format(args.dest)
   destInventory = GetMusicFiles(destSource) 

   # get a list of the files that we want to have pinned on the dest
   if args.pinned:
      pinnedSrc = fileSource.FileSource(args.src, args.pinned)
      print "Getting list of files to pin onto destination"
      pinnedFiles = GetMusicFiles(pinnedSrc) 
   else:
      pinnedFiles = []
   # get a list of all of the source files that aren't pinned.
   src = fileSource.FileSource(args.src)
   print "Getting list of all source files on {0}".format(args.src)
   srcFiles = GetMusicFiles(src)
   


   toCopy = []
   doNotDelete = []
   dest = fileDestination.FileDestination(args.dest, "copy", "skip", args.rate, True)

   for f in pinnedFiles:
      # we add each pinned file to one of two lists -- either we need to copy 
      # this file to the destination (list toCopy), or it's already pinned there,
      # so we need to add it to the list of files that shouldn't be deleted
      # (list doNotDelete). The fileDestination::MusicLocation() method
      # figures out where the source file is supposed to live, and we check to see 
      # if it's already there or not.  
      destPath = dest.MusicLocation(f)
      if not os.path.exists(destPath):
         toCopy.append(f)
      else:
         doNotDelete.append(destPath)

   # If we're adding files that aren't pinned and aren't shuffled, get that list now.
   addFiles = []
   if args.add:
      addSrc = fileSource.FileSource(args.add)
      addFiles = GetMusicFiles(addSrc)

   toCopy.extend(addFiles)

   # for each of the files that should be pinned to the destination, there's 
   # an entry either in toCopy (because it's not there yet) or doNotDelete
   # (because it's already there, and we need to know to not delete it below.)
   
   doNotDelete = set(doNotDelete)
   destFileCount = len(destInventory)
   pinnedCopyFileCount = len(toCopy)
   availableRoom = args.max - destFileCount


   # we want to copy at least this many files over to the dest.
   newFileCount = pinnedCopyFileCount + args.new

   print "Pinned/Added file count: {0}".format(pinnedCopyFileCount)
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
      deleteFiles = destInventory[:deleteCount]
      deleteFiles.sort()
      for destFile in deleteFiles:
         if destFile not in doNotDelete:
            DeleteTrack(destFile)
   # okay, now we do the opposite -- we need to
   # 1. Copy up any pinned files that aren't up there yet
   # 2. Shuffle the source files and start copying files up that aren't already
   #    at the destination.

   print "About to copy files to {0}".format(args.dest)

   toCopy.sort()
   for f in toCopy:
      print "Copying pinned/added file {0} ({1} to go...)".format(f.encode('utf-8'), newFileCount)
      dest.HandleMusic(f)
      newFileCount -= 1

   random.shuffle(srcFiles)
   index = 0
   shuffled = []
   while newFileCount > 0:
      nextFile = srcFiles[index]
      index += 1
      destPath = dest.MusicLocation(nextFile)
      if not os.path.exists(destPath):
         if FilterTrack(nextFile):
            shuffled.append(nextFile)
            newFileCount -= 1

   shuffled.sort()
   shuffleCount = len(shuffled)
   for (i, nextFile) in enumerate(shuffled):

      print "Copying {0} ({1} to go)".format(nextFile.encode('utf-8'), shuffleCount-i)
      dest.HandleMusic(nextFile)









   






