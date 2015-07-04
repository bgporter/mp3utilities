

import os

kHistoryFileExt = ".history"

def MakeHistoryFilename(f):
   return "{0}{1}".format(f, kHistoryFileExt)

def IsHistoryFile(f):
   return kHistoryFileExt == os.path.splitext(f)[1] 

def HandleHistory(srcPath, targetPath):
   ''' if there's a history file in our src, we add a new line in the 
      copy at the destination after copying it there. Otherwise, we create
      a new empty file at the destination dir and put the current time
      into it.

      Executed at the time when we create the target directories.
   '''
   print "HandleHistory src = {0} dest = {1}".format(srcPath, targetPath)
   history = []
   srcAlbumName = os.path.split(srcPath)[1]
   srcHistory = MakeHistoryFilename(srcAlbumName)
   try:
      with open(os.path.join(srcPath, srcHistory), "rt") as f:
         history = [s.strip() for s in f]
   except IOError:
      # file doesn't exist, which is legit. ignore it.
      pass

   destAlbumName = os.path.split(targetPath)[1]
   destHistory = MakeHistoryFilename(destAlbumName)
   with open(os.path.join(targetPath, destHistory), "wt") as f:
      history.append("{0}".format(int(time.time())))
      f.write("\n".join(history))

import os
import time


class History(object):
   def __init__(self, srcPath):
      ''' attempt to open and load a history file from the given path. 
         If there's nothing there, that's okay; our history is empty.
      '''
      self.history = []
      srcAlbumName = os.path.split(srcPath)[1]
      srcHistory = "{0}.history".format(srcAlbumName)
      historyPath = os.path.join(srcPath, srcHistory)
      try:
         # see if there's a history file at the source path. There may not be.
         with open(historyPath, "rt") as f:
            self.history = [line.strip() for line in f]
      except IOError:
         # Nope, no history. That's okay. Leave the list blank.
         pass


   def Update(self, destPath):
      ''' add the current date/time to the end of the history and write 
         the resulting list out into a history file at a new location, 
         replacing any file that might already be there. 
      '''

      destAlbumName = os.path.split(destPath)[1]
      destHistory = "{0}.history".format(destAlbumName)
      with open(os.path.join(destPath, destHistory), "wt") as f:
         self.history.append("{0}".format(int(time.time())))
         f.write("\n".join(self.history))

   def Oldest(self):
      ''' return the timestamp of the first entry in the history file. '''
      retval = None
      if self.history:
         retval = self.history[0]
      return retval


   def Newest(self):
      ''' return the timestamp of the last entry in the history file. '''
      retval = None
      if self.history:
         retval = self.history[-1]
      return retval

