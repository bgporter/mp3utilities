

import os

import fileDestination
import fileHistory
import fileSource
import trackHistory

fs = fileSource.FileSource(u"/Volumes/zappa_files/music/")

newHistory = None 


for (t, p) in fs:
   if t == fileSource.kDirectory:
      try:
         oldHistory = fileHistory.History(fileDestination.NormalizeFilename(p))
         if oldHistory.fileExists:
            lastTime = int(float(oldHistory.Oldest()))
            print u"{0}: {1}".format(lastTime, p).encode("utf-8")
            if newHistory:
               newHistory.Save()
            # create an empty new-style history file in the same location.   
            newHistory = trackHistory.History(p)
      except UnicodeDecodeError, e:
         print p.encode("utf-8")
         print str(e)

   elif (t == fileSource.kMusic):
      track = os.path.split(p)[1]
      print "   " + track.encode('utf-8')
      # add a track to the new history file using the same (old) timestamp 
      # for acquired and moved.
      newHistory.AddTrack(track, lastTime, lastTime)

# don't forget to save the last one we were writing to!
newHistory.Save()