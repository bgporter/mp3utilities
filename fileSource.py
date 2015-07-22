
import os

kDirectory = "DIR"
kExitDirectory = "RID"
kMusic = "MP3"
kOtherFile = "ETC"

class FileSource(object):
   def __init__(self, base, others=None):
      '''
      >>> f = FileSource('/a/b/c', ['d', ' e ', '   ', 'g '])
      >>> f.base
      '/a/b/c'
      >>> f.others
      ['d', 'e', 'g']

      '''
      self.base = base
      if others is None:
         self.others = ['']
      else:
         self.others = []
         # get list of subdirectories from 'others' -- maybe it's a filename, maybe
         # it's a list of strings..
         if hasattr(others, "lower"):
            # it's  a string, so treat it as a filename
            with open(others, "rt") as f:
               for line in f:
                  # get rid of anything after a '#' comment
                  line = line.partition("#")[0]
                  # ..and whitespace
                  line = line.strip()
                  # if there's anything left, add it to the list.
                  if line:
                     self.others.append(line)
         else:
            # add that line to the list if stripping it doesn't result 
            # in an empty string.
            self.others = [line.strip() for line in others if line.strip()]

   def GetDirectories(self):
      '''
      >>> f = FileSource('/a/b/c')
      >>> list(f.GetDirectories())
      ['/a/b/c/']

      >>> f = FileSource('a/b', ['aa', 'bb'])
      >>> list(f.GetDirectories())
      ['a/b/aa', 'a/b/bb']

      >>> f = FileSource('a/b', ['a  ', ' bb', 'c'])
      >>> list(f.GetDirectories())
      ['a/b/a', 'a/b/bb', 'a/b/c']


      '''
      for subdir in self.others:
         yield os.path.join(self.base, subdir.decode('utf-8'))



   def GetFiles(self):
      '''
         Walk through all of the directories that we should be looking at. if
         any of them contain files, yield those files back to whoever
         called us, one at a time.
      '''

      def Spelunk(d, visited):
         ''' generator that recursively walks down into directory paths and only 
            yields the ExitDirectory message when we're done processing all of 
            its children.

            We pass in a set that collects diretories that we've processed to avoid
            accidentally visiting the same directory more than once.
         '''
         assert os.path.isdir(d)
         dirs = []
         files = []
         # notify that we're entering a directory.
         yield (kDirectory, d)
         for item in os.listdir(d):
            fullpath = os.path.join(d, item)
            if os.path.isdir(fullpath):
               if fullpath not in visited:
                  dirs.append(fullpath)
                  visited.add(fullpath)
            else:
               files.append(fullpath)

         otherFiles = []
         files.sort()
         for f in files:
            base, ext = os.path.splitext(f)
            if ext.lower() in (u".mp3",):
               yield (kMusic, f)
            else:
               otherFiles.append(f)
         # we've yielded all the MP3 files, now yield back anything else.
         for f in otherFiles:
            yield (kOtherFile, f)

         # now spelunk into any subdiretories...
         dirs.sort()
         for sub in dirs:
            for t, f in Spelunk(sub, visited):
               yield (t,f)

         yield (kExitDirectory, d)



      visited = set()
      dirList = self.GetDirectories()
      for d in dirList:
         for (t, f) in Spelunk(d, visited):
            yield (t, f)


   def __iter__(self):
      return self.GetFiles()



if __name__ == "__main__":
   import doctest
   doctest.testmod()