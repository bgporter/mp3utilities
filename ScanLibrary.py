#! /usr/bin/env python
#


'''   
   ScanLibrary -- utility to traverse a collection of MP3 files in our layout
   and collect data to save in a JSON file with useful details.

   


'''



import json
import os
import stat


import fileSource
import fileDestination


class NoFilenameError(Exception):
   pass

class Scanner(object):
   def __init__(self, libPath, filePath=None):
      ''' libPath -- path to the top of the library (e.g. the directory that 
         contains the artist directories)
         filePath -- path to a file to load. 
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
         self.filePath = filePath

      with open(self.filePath, "wt") as f:
         f.write(json.dumps(self.library, sort_keys=True, 
            indent=4, separators=(',', ': ')))


   def Scan(self, forceScan=False):
      source = fileSource.FileSource(self.libPath)

      currentArtist = None
      currentAlbum = None
      depth = 0

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
               currentAlbum = currentArtist.setdefault(itemName, {})
            else: 
               # deeper? Shouldn't happen. We should handle this more elegantly
               # than throwing an assertion error, though.
               assert False, "Hierarchy goes too deep!"
            depth += 1
            pass
         elif fileSource.kMusic == t:
            assert currentAlbum is not None
            trackName, _ = os.path.splitext(itemName)
            trackInfo = currentAlbum.setdefault(trackName, {})

         elif fileSource.kOtherFile == t:
            pass
         elif fileSource.kExitDirectory == t:
            depth -= 1
            if 2 == depth:
               # leaving an album directory. 
               assert currentAlbum is not None
               assert currentArtist is not None
               currentAlbum = None
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