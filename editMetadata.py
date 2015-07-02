

import sys

import fileSource
import fileDestination
from mutagen.easyid3 import EasyID3


## Validator functions -- accept an attribute name and a value, returns 
# true/false whether we should accept that value for this attribute or not.
def AlwaysValidates(attr, value):
   return True

kFields = [
   # attribute, label, datatype, validation fn
   ("performer",  "Album Artist", str, AlwaysValidates),
   ("artist",     "Track Artist", str, AlwaysValidates),
   ("title",      "Title",        str, AlwaysValidates),
   ("tracknumber", "Track #",     int, AlwaysValidates),
   ("date",       "Year",         int, AlwaysValidates),
   ("discnumber",  "Disc #",      int, AlwaysValidates),
   ("genre",      "Genre",        str, AlwaysValidates)
]

metadataFormat = []
for i, (attr, label, t, val) in enumerate(kFields):
   metadataFormat.append("{0}. {1:<16} {{0.{2}}}".format(i+1, label, attr))

metadataFormat = "\n".join(metadataFormat)


def GetInput(prompt, datatype=str, defaultVal=None):
   if defaultVal is not None:
      try:
         defaultVal = datatype(defaultVal)
      except (TypeError, ValueError):
         defaultVal = None

   while 1:
      raw = raw_input(prompt)
      raw = raw.strip()
      #if (not raw) and defaultVal is not None:
      if (not raw):
         return defaultVal
      else:
         try:
            retval = datatype(raw)
            return retval
         except ValueError:
            # they entered a bogus value, try again.
            pass



class MetadataEditor(object):
   def __init__(self, mp3file):
      self.meta = fileDestination.Metadata(EasyID3(mp3file))

   def EditFile(self):
      while 1:
         print metadataFormat.format(self.meta)
         choice = abs(GetInput("Enter item to edit [0 = done]: ", int, 0))
         if 0 == choice:
            break
         else:
            # reset to zero-based so we can index into the list of attributes.
            choice -= 1
            try:
               field = kFields[choice]
               self.EditAttribute(*field)
            except IndexError:
               continue

   def EditAttribute(self, attr, label, t, val):
      print "\n{0}\n".format(label)



if __name__ == "__main__":
   if len(sys.argv) > 1:
      path = sys.argv[1]
   else:
      path = '.'

   fs = fileSource.FileSource(path)

   for (fileType, filePath) in fs:
      if fileType == fileSource.kMusic:
         editor = MetadataEditor(filePath)
         editor.EditFile()
