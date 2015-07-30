

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
   ("album",      "Album",        unicode, AlwaysValidates),
   ("performer",  "Album Artist", unicode, AlwaysValidates),
   ("artist",     "Track Artist", unicode, AlwaysValidates),
   ("title",      "Title",        unicode, AlwaysValidates),
   ("tracknumber", "Track #",     int, AlwaysValidates),
   ("date",       "Year",         int, AlwaysValidates),
   ("discnumber",  "Disc #",      int, AlwaysValidates),
   ("genre",      "Genre",        unicode, AlwaysValidates)
]

kRememberAttributes = ["album", "performer", "artist", "date", "discnumber", "genre"]

# use the field data above to dynamically build the format string 
# used to display a track's metadata.
metadataFormat = []
for i, (attr, label, t, val) in enumerate(kFields):
   metadataFormat.append(u"{0}. {1:<16} {{0.{2}}}".format(i+1, label, attr))

metadataFormat = u"\n".join(metadataFormat)


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
   def __init__(self, args):
      self.meta = None
      self.args = args

      # For fields that might recur across an album, remember the last 
      # value entered. See kRememberAttributes above.
      self.lastField = {}


   def Remember(self, attr, val):
      # if this is an attribute that we're supposed to remember, 
      # remember it.
      if attr in kRememberAttributes:
         self.lastField[attr] = val

   def Remembered(self, attr):
      # See if we have a human-entered value that we should have
      # remembered for this attribute.
      return self.lastField.get(attr, "")

   def EditFile(self, mp3File, force=False):
      ''' return true to process the next file, False to quit. '''
      self.meta = fileDestination.Metadata(EasyID3(mp3File))

      # if self.args is not empty, pass along any settings that we 
      # were given from the command line:
      for attr, val in self.args.items():
         self.meta[attr] = val

      if force:
         self.meta.Save()
         return True

      while 1:
         print "\n"
         # print as much of the path & file as we can without wrapping. 
         print mp3File[-80:]
         print metadataFormat.format(self.meta)
         choice = GetInput("Enter item to edit [0 = next, q = quit]: ", str, "0")
         if "0" == choice:
            self.meta.Save()
            return True
         elif "q" == choice.lower():
            self.meta.Save()
            return False
         else:
            # reset to zero-based so we can index into the list of attributes.
            try:
               choice = int(choice) - 1
               field = kFields[choice]
               self.EditAttribute(*field)
            except (IndexError, ValueError):
               continue

   def EditAttribute(self, attr, label, t, validate):
      print "\n{0}\nCurrent: {1}".format(label, getattr(self.meta, attr))
      lastVal = self.Remembered(attr)
      if lastVal:
         lvString = "[blank = '{0}']: ".format(lastVal)
      else: 
         lvString = ': '
      promptString = "New value {0}".format(lvString)
      newVal = GetInput(promptString, t, None)
      if newVal or lastVal:
         if not newVal:
            newVal = lastVal
         if validate(attr, newVal):
            self.meta[attr] = newVal
            self.Remember(attr, newVal)
         else:
            # if validation fails, we call ourselves recursively instead
            # of looping. We may want to change this. 
            self.EditAttribute(attr, label, t, val)





if __name__ == "__main__":
   import argparse
   import os

   parser = argparse.ArgumentParser(description='Edit MP3 file metadata')
   parser.add_argument("--src", action="store", nargs="?", default = os.getcwd(), 
      help="Directory containing MP3 files to edit.")
   parser.add_argument("--album", action="store", nargs="?", help="Album name to set")
   parser.add_argument("--performer", action="store", nargs="?", help="Album artist name to set")
   parser.add_argument("--artist", action="store", nargs="?", help="Track artist name to set")
   parser.add_argument("--date", action="store", nargs="?", help="Album year to set")
   parser.add_argument("--discnumber", action="store", nargs="?", help="Album year to set")
   parser.add_argument("--genre", action="store", nargs="?", help="Genre to set")
   parser.add_argument('-f', '--force', action="store_true", 
      help="Don't edit, just update all fields as passed on command line")


   args = parser.parse_args()

   args = vars(args)

   path = args.pop('src')
   force = args.pop('force')

   # get rid of any items in the dict with a value of None.
   for (k, v) in args.items():
      if v is None:
         args.pop(k)
      fs = fileSource.FileSource(path)

   editor = None

   for (fileType, filePath) in fs:
      if fileType == fileSource.kDirectory:
         # create a new editor for each directory, resetting all the 
         # remembered values.
         editor = MetadataEditor(args)
         print "Entering {0}".format(filePath)
      elif fileType == fileSource.kMusic:
         retval = editor.EditFile(filePath, force)
         if not retval:
            break

   print "Done."
