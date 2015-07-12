

'''
   An updated history handling system. Instead of having a single file 
   that indicates when we first added something from an album, we'll instead 
   track the history of individual files -- helpful for something like TMBG's 
   2015 Dial a song project, where they release a new track each week that we 
   treat as all being part of the same album. 

   We'll keep track of each MP3 file as it's added to a directory, using a data structure 
   that's a dict of file names mapping to a list of timestamps (we'll continue using 
   int(time.time())). The history class can then grow some useful functionality like returning 
   a list of files that were put there within a certain number of days (see recent.py, for 
   code that maintains a set of MPD playlist files that are time)
   
   The list of timestamps for each file will be [date_acquired, date_copied_here] -- in most
   cases, I expect that date acquired is going to be the interesting one, but who knows. When 
   we copy/move files, that timestamp will be copied into the same index in the new history 
   file in the new directory, but the second one will reflect the date/time the file was 
   moved/copied.

'''
import os
import json
import time
import datetime

kHistoryExtension = ".tracks"
kOldHistoryExtension = ".history"

# index into the list.
kAcqDate, kMoveDate = (0, 1)


def MakeHistoryFilename(f):
   return u"{0}{1}".format(f, kHistoryExtension)

def IsHistoryFile(f):
   return os.path.splitext(f)[1] in (kHistoryExtension, kOldHistoryExtension)


class History(object):
   def __init__(self, path):
      '''
         We store our track history in text files storing JSON objects. 
         These files are always stored at the album level, and the name of a 
         history file will always be the name of its parent directory + the 
         history file extension.
      '''
      path = path
      # we always use the last path component as our file name
      albumName = os.path.split(path)[1]
      filename = MakeHistoryFilename(albumName)

      self.filePath = os.path.join(path, filename)
      self.isDirty = False

      try:
         with open(self.filePath, "rt") as f:
            self.history = json.loads(f.read())
      except IOError:
         # the file may not exist. That's okay. 
         self.history = {}

   def Save(self):
      if self.isDirty:
         with open(self.filePath, "wt") as f:
            output = json.dumps(self.history, indent=3, separators=[',', ': '])
            f.write(output)
            self.isDirty = False

   def GetTrack(self, trackFile):
      '''
         returns a list of two integers, [acquireDate, moveDate] or 
         [None, None] if we don't know this track yet.
      '''
      return self.history.get(trackFile, [None, None])

   def AddTrack(self, trackFile, acquireDate=None, moveDate=None):
      '''
         Add this track file to our history tracking. 
      '''

      now = int(time.time())
      acquireDate = acquireDate or now
      moveDate = moveDate or now

      oldAcq, oldMove = self.GetTrack(trackFile)
      self.history[trackFile] = [(oldAcq or acquireDate), moveDate]
      self.isDirty = True

   def TracksInHistory(self, dateType, days):
      if dateType not in (kAcqDate, kMoveDate):
         raise ValueError("datetype must be in (kAcqDate, kMoveDate)")

      today = datetime.date.today()
      retval = []

      for (track, dates) in self.history.items():
         trackDate = datetime.date.fromtimestamp(dates[dateType])
         if (today - trackDate).days <= days:
            retval.append(track)
      return retval











