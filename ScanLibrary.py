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


kMtime = "_MTIME"



def SplitMp3Info(filePath):
   '''
   Given the path to an MP3 file that's stored in our standard artist/album/trackFile
   hierarchy, return a tuple (artist, album, trackFile)

   >>> SplitMp3Info("Artist/Album/01_File.mp3")
   ('Artist', 'Album', '01_File.mp3')
   >>> SplitMp3Info("foo/bar/baz/Artist/Album/02_Another-File.mp3")
   ('Artist', 'Album', '02_Another-File.mp3')
   '''
   parts = filePath.split(os.sep)
   return tuple(parts[-3:])


def AddTrack(library, trackFile):
   #mp3 = fileDestination.Mp3File(trackFile)
   albumPath, f = os.path.split(trackFile)
   st = os.stat(albumPath)
   mTime = st.st_mtime


   artist, album, track = SplitMp3Info(trackFile)

   artistDict = library.setdefault(artist, {})
   albumDict = artistDict.setDefault(album, {})
   lastMtime = albumDict.get(kMtime, 0)
   if mTime > lastMtime:
      albumDict


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


   def Scan(self):
      source = fileSource.FileSource(self.libPath)

      currentArtist = None
      currentAlbum = None
      depth = 0

      for (t, f) in source:
         print t, f
         _, itemName = os.path.split(f)
         if fileSource.kDirectory == t:
            if 0 == depth:
               assert currentArtist is None
               assert currentAlbum is None
            elif 1 == depth:
               assert currentArtist is None
               assert currentAlbum is None
               currentArtist = self.library.setdefault(itemName, {})
            elif 2 == depth:
               assert currentArtist is not None
               assert currentAlbum is None
               currentAlbum = currentArtist.setdefault(itemName, {})
            else: 
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
            if 3 == depth:
               assert currentAlbum is not None
               assert currentArtist is not None
               currentAlbum = None
            elif 2 == depth:
               assert currentAlbum is None
               assert currentArtist is not None
               currentArtist = None
            elif 1 == depth:
               assert currentAlbum is None
               assert currentArtist is  None
            else:
               assert False, "Hierarchy error!"

            depth -= 1





if __name__ == "__main__":
   import doctest
   doctest.testmod()