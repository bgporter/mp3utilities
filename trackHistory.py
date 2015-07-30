

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


class RemoveTrackError(Exception):
   def __init__(self, trackFile):
      self.trackFile = trackFile

   def __str__(self):
      return "Trying to remove missing file {0}".format(self.trackFile.encode('utf-8'))


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
      # we always use the last path component as our file name
      artistPath, self.albumName = os.path.split(path)
      _, self.artistName = os.path.split(artistPath)
      filename = MakeHistoryFilename(self.albumName)

      self.filePath = os.path.join(path, filename)
      self.isDirty = False
      self.fileExists = False

      self.mostRecent = None

      try:
         with open(self.filePath, "rt") as f:
            self.history = json.loads(f.read())
            self.fileExists = True
      except IOError:
         # the file may not exist. That's okay. 
         self.history = {}

   def Save(self):
      ''' if we've been changed since we were created, we need to either:
         1. Save the current state of the history into our backing file. 
         2. If the user deleted the last track in this file, we instead
            *delete* that backing file if it exists.
      '''
      if self.isDirty:
         if self.history:
            with open(self.filePath, "wt") as f:
               output = json.dumps(self.history, indent=3, separators=[',', ': '])
               f.write(output)
         else:
            # we have an empty history dict -- delete the file if it exists.
            try:
               os.remove(self.filePath)
            except OSError:
               # that file isn't there, which is probably (?) not an error?
               print "***** ERROR trying to delete {0}".format(self.filePath.encode('utf-8'))
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

   def RemoveTrack(self, trackFile):
      try:
         self.history.pop(trackFile)
      except KeyError:
         raise RemoveTrackError(trackFile)

      self.isDirty = True




   def PrepRecent(self):
      ''' look through our contents to find the most recent acq/move amongst our 
         contents.
      '''
      if not self.mostRecent:
         mostRecentAcq = 0
         mostRecentMove = 0
         for (track, dates) in self.history.items():
            mostRecentAcq = max(mostRecentAcq, dates[kAcqDate])
            mostRecentMove = max(mostRecentMove, dates[kMoveDate])
         self.mostRecent = [mostRecentAcq, mostRecentMove]

   def RecentTracks(self, after, dateType=kAcqDate):
      ''' Return a list of tracks that were qcquired/moved after the specified 
         date stamp (in the same format that we use for our history)
      '''
      if dateType not in (kAcqDate, kMoveDate):
         raise ValueError("datetype must be in (kAcqDate, kMoveDate)")

      self.PrepRecent()
      retval = []

      # check to see if there are any tracks in this directory that are after
      # the requested date. If not, we won't bother looking.
      if self.mostRecent[dateType] >= after:
         for (track, dates) in self.history.items():
            if dates[dateType] >= after:
               retval.append(os.path.join(self.artistName, self.albumName, track))

      return retval












