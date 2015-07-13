#! /usr/bin/env python

'''
   Assumes a few things:

   1. We're using MPD (we are!)
   2. We have MP3 files in a tree where the leaf directories containing
      music also contain a file named YYYY_Album-Name.history that's 
      plain text and the first line of that file is a string/integer that's
      the int(time.time()) of when that directory was first moved into our
      system 
   3. We want to create a set of playlists that each contain all the files that 
      were acquired in the last (e.g.) Month, Quarter, Year.

   Docs on the requirements of the MPD playlist format are at
   http://mpd.wikia.com/wiki/Playlists

   2015/07/12: Rewritten to use the newer fileSource.FileSource object
   to handle walking the directories for us and the newer trackHistory.history 
   class that lets us track acruisition/move dates on a per-track basis instead
   of a per-directory basis.

'''

import os
import datetime
import glob
import time

import fileSource
import trackHistory
from trackHistory import History


## per-install things:
kMusicRoot = "/media/usb0/music/"
kRootLen = len(kMusicRoot)
kPlaylistDir = "/var/lib/mpd/playlists/"
kPlaylistExt = "m3u"


class Recent(object):
   def __init__(self, root, periods = None):
      if not periods:
         periods = [7, 30]
      self.root = root
      self.periods = periods
      # a place to accumulate the tracks that belong in each playlist file.
      # it will look something like:
      # { period: [list of tracks], period2: [list of tracks]}
      self.tracks = {}
      self.now = datetime.datetime.today()
      self.cutoffs = []
      for p in periods:
         self.cutoffs.append(self.now - datetime.timedelta(days=p))
         self.tracks[p] = []


   def CheckDir(self, path):
      # trim the trailing slash if it's there.
      if path.endswith(os.sep):
         path = path[:-1]
      try:
         _, historyFile = os.path.split(path)
         with open(os.path.join(path, "{0}.history".format(historyFile)), "rt") as f:
            lines = [l.strip() for l in f]
            try:
               createTime = float(lines[0])
               createDate = datetime.datetime.fromtimestamp(createTime)
               for period, cutoff in zip(self.periods, self.cutoffs):
                  if createDate > cutoff:
                     try:
                        tracks = glob.glob(os.path.join(path, "*.mp3"))
                        for track in tracks:
                           self.tracks[period].append(track[kRootLen:])
                     except Exception, e:
                        print "!!! on path ", path, str(e)
            except ValueError, e:
               print "Can't convert", str(e)
      except IOError:
         print "!!! HISTORY FILE NOT FOUND for {0}".format(path)

   def ScanForTracks(self):
      for (path, dirs, files) in os.walk(kMusicRoot):
         if not dirs:
            # e.g. we only look in leaf directories
            self.CheckDir(path)

   def WritePlaylists(self):
      for p in self.periods:
         fileName = "{0}-days.{1}".format(p, kPLaylistExt)
         with open(os.path.join(kPLaylistDir, fileName), "wt") as f:
            tracks = self.tracks[p]
            tracks.sort()
            f.write("\n".join(tracks))


def WritePlaylist(path, days, tracks):
   fileName = "{0}-days.{1}".format(days, kPlaylistExt)
   with open(os.path.join(path, fileName), "wt") as f:
      tracks.sort()
      f.write(u"\n".join(tracks).encode("utf-8"))


def DaysAgo(startTime, days):
   ''' Given the current time (as a datetime.datetime object) and a number
      of days, returns the integer timestamp that many days earlier.
   '''
   then = startTime - datetime.timedelta(days=days)
   return int(time.mktime(then.timetuple()))


if __name__ == "__main__":
   import argparse
   parser = argparse.ArgumentParser("Create playlist files from recent acquisitions.")

   parser.add_argument("-s", "--src", action="store", nargs="?", 
      default=kMusicRoot, help="root directory of music collection.")
   parser.add_argument("-d", "--dest", action="store", nargs="?",
      default=kPlaylistDir, help="output directory for playlist files.")
   parser.add_argument("-p", "--periods", action="store", nargs="?", 
      default="7,30,90,180", help="list of most recent 'n' days of files to gather")

   args = parser.parse_args()
   args = vars(args)

   # get the numbers from in between the commas and convert to integers.
   periods = [int(p.strip()) for p in args['periods'].split(',')]
   today = datetime.datetime.today()
   cutoffs = [DaysAgo(today, days) for days in periods]

   trackLists = [[] for p in periods]

   srcPath = args['src']

   fs = fileSource.FileSource(srcPath)

   for (t, p) in fs:
      if fileSource.kDirectory == t:
         try: # !!! delete this after testing...
            history = History(p)
         except: 
            continue
         if history.fileExists:
            print "dir - {0}".format(p)
            for i, cutoff in enumerate(cutoffs):
               tracks = history.RecentTracks(cutoff)
               if tracks:
                  trackLists[i].extend(tracks)

   for days, trackList in zip(periods, trackLists):
      print len(trackList)
      WritePlaylist(args['dest'], days, trackList)





   '''recent = Recent(kMusicRoot, [7, 30, 90, 180])
   recent.ScanForTracks()
   recent.WritePlaylists()'''
