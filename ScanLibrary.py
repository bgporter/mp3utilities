#! /usr/bin/env python
#


'''   
   ScanLibrary -- utility to traverse a collection of MP3 files in our layout
   and collect data to save in a JSON file with useful details.

   We read and write the results as JSON text files, and manipulate them 
   internally as plain old dicts that reflect the hierarchy of 
   Artist
      album
         track 1
            track details
         track 2
            track details
      album 2
         track 1
            track details

   Anything that we need to store inside these dicts that's for our internal use
   should be named with two leading underscores (and by the same token, we need to 
      disallow naming artists, albums, or tracks with that convention to avoid them 
      disappearing)


'''



import json
import os
import stat
import time


import fileSource
import fileDestination
import trackHistory


kLastModified = "__mtime"

class NoFilenameError(Exception):
   pass

class Scanner(object):
   def __init__(self, libPath, filePath=None):
      ''' libPath -- path to the top of the library (e.g. the directory that 
         contains the artist directories)
         filePath -- path to a file to load for updating.
      '''

      self.libPath = libPath
      self.library = {}
      self.filePath = filePath
      if filePath:
         self.LoadFile(filePath)


   def LoadFile(self, filePath):
      self.filePath = filePath
      with open(filePath, "rt") as f:
         self.library = json.loads(f.read())

   def SaveFile(self, filePath=None):
      if not (filePath or self.filePath):
         raise NoFilenameError

      if filePath:
         # replace the existing filePath with this new one.
         self.filePath = filePath

      with open(self.filePath, "wt") as f:
         f.write(json.dumps(self.library, sort_keys=True, 
            indent=4, separators=(',', ': ')))


   def Scan(self, forceScan=False):
      source = fileSource.FileSource(self.libPath)

      currentArtist = None
      currentAlbum = None
      history = None
      depth = 0
      now = time.time()

      for (t, f) in source:
         print t, f
         _, itemName = os.path.split(f)
         if fileSource.kDirectory == t:
            if 0 == depth:
               # top level of the hierarchy -- at this point we know nothing.
               assert currentArtist is None
               assert currentAlbum is None
            elif 1 == depth:
               # Just entered an Artist directory. 
               assert currentArtist is None
               assert currentAlbum is None
               currentArtist = self.library.setdefault(itemName, {})
            elif 2 == depth:
               # just entered an album directory
               assert currentArtist is not None
               assert currentAlbum is None
               assert history is None
               currentAlbum = currentArtist.setdefault(itemName, {})
               history = trackHistory.History(f)
            else: 
               # deeper? Shouldn't happen. We should handle this more elegantly
               # than throwing an assertion error, though.
               assert False, "Hierarchy goes too deep!"
            depth += 1
            pass
         elif fileSource.kMusic == t:
            assert currentAlbum is not None
            assert history is not None
            trackName, _ = os.path.splitext(itemName)
            trackInfo = currentAlbum.setdefault(trackName, {})
            if history.fileExists:
               acq, move = history.GetTrack(itemName)
               trackInfo['acquired'] = acq
               trackInfo['moved'] = move
               mp3 = fileDestination.Mp3File(f)
               trackInfo['genre'] = mp3.genre


         elif fileSource.kOtherFile == t:
            pass
         elif fileSource.kExitDirectory == t:
            depth -= 1
            if 2 == depth:
               # leaving an album directory. 
               assert currentAlbum is not None
               assert currentArtist is not None
               assert history is not None 
               currentAlbum = None
               history = None
            elif 1 == depth:
               # leaving an artist directory.
               assert currentAlbum is None
               assert currentArtist is not None
               currentArtist = None
            elif 0 == depth:
               # leaving the top level directory, which should only happen as 
               # the very last thing we do here.
               assert currentAlbum is None
               assert currentArtist is  None
            else:
               assert False, "Hierarchy error!"






if __name__ == "__main__":
   import doctest
   doctest.testmod()