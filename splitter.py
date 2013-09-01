kInput = "AllFiles.csv"


kMiscKey = chr(ord('z') + 1)

alphaLists = {}

# create a bunch of empty lists to write CSV data into by first letter
# of the line.lower(). The last one is for any line with a first letter
# that's not in the range a..z (numbers, punctuation, etc.)
for letter in range(ord('a'), ord('z')+2):
   alphaLists[chr(letter)] = []


def IsLetter(ch):
   return 'a' <= ch <= 'z'

with open(kInput, "rt") as f:
   for line in f:
      letter = line[0].lower()
      if IsLetter(letter):
         alphaLists[letter].append(line)
      else:
         alphaLists[kMiscKey].append(line)


for k, v in alphaLists.items():
   if kMiscKey == k:
      fName = "misc"
   else:
      fName = (k)

   print "Creating '{0}' file. ".format(fName)
   with open("{0}.csv".format(fName), "wt") as f:
      for line in v:
         f.write(line)


