
import os

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
         yield os.path.join(self.base, subdir)

   def GetFiles(self, dirPath, files):
      '''
         Yield each of the files in this directory, using path/list
         as yielded by os.walk()

         >>> f = FileSource('a')
         >>> list(f.GetFiles('a/b/c', ['foo.mp3', 'bar.mp3', 'cover.jpg']))
         ['a/b/c/foo.mp3', 'a/b/c/bar.mp3', 'a/b/c/cover.jpg']
      '''
      for file in files:
         yield(os.path.join(dirPath, file))





if __name__ == "__main__":
   import doctest
   doctest.testmod()