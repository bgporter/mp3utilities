
from mutagen.easyid3 import EasyID3
from pprint import pprint
import glob
import json
import mutagen
import time
import urllib
import urllib2


kApiKey = "DLTTSSYQQ9SL2CEIT"

kBaseUrl = "http://developer.echonest.com/api/v4/track"


def CheckFile(filePath):
   print "Processing %s" % filePath

   # grab the first 1MB from the MP3 file...
   fileData = open(filePath, "rb").read()[:1024*1024]


   parms = {   "api_key" : kApiKey,
               "format" : "json",
               "wait"   : "true",
               "filetype" : "mp3",
               "track" : fileData,
               }



   print "sending track data"
   f = urllib2.urlopen(kBaseUrl + "/upload", urllib.urlencode(parms))

   response = json.loads(f.read())

   pprint(response)

   if response['response']['status']['code'] == 0:
      try:
         f = EasyID3(filePath)
      except mutagen.id3.ID3NoHeaderError:
         f = mutagen.File(filePath, easy=True)
         f.add_tags()

      def GetAttribute(r, field):
         return r['response']['track'][field]

      title = GetAttribute(response, 'title')
      artist = GetAttribute(response, 'artist')
      album = GetAttribute(response, 'release')
      if title or artist or album:
         if title:
            f["title"] = title
         if artist:
            f["artist"] = artist
         if album:
            f["album"] = album
         f.save()


letters =[ "music" ]

for letter in letters:
   print "Processing '%s' files" % letter
   #for f in glob.glob("/Users/bgporter/temp/%s/*.mp3" % letter):
   for f in glob.glob("*.mp3"):
      try:
         CheckFile(f)
      except urllib2.HTTPError, e:
         print str(e)
         print "about to retry..."
         time.sleep(4)
         try:
            CheckFile(f)
         except urllib2.HTTPError, e:
            print "Error again (%s); giving up on this file." % e



