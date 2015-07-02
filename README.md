
## MP3 Utilities

A bunch of small Python utilities that I use to maintain my music collection. I doubt that these are in any way directly usable by anyone else directly as is, or are actually interesting to anyone. 

These run locally on my MacBook Pro running 10.7.5 and my jukebox machine that's running Ubuntu 12-something.

### Dependencies

- Python, obviously. I'm using 2.6 locally. 
- LAME - http://lame.sourceforge.net/ -- the `mover.py` utility has an option to copy files, and you can transcode to a different bitrate if LAME is available. 
- mutagen - http://code.google.com/p/mutagen/ Python library for working with metadata tagging

### Files

#### `mover.py`

This is the workhorse of these files. This does the following things for me:

- Move or copy one or more directories of MP3 files to a different location.
- If desired, copy files at a different bitrate than the source
- Rename directories and files into a uniform pattern

Renaming rules are:

- All illegal filesystem characters are replaced with '-'
- Whitespace characters replaced with '-'
- Multiple dashes elided to a single dash
- File metadata read to generate (if needed) a directory for the artist and album in the format `Artist-Name/YYYY_Album-Name`
- For now, the names used are encode in UTF-8, which isn't always right, e.g., I think that the flash drive I use in the car is actually formatted such that it's expecting an ISO-8859-1 encoding, but there's also the possibility that odd characters there are actually remnants of bugs in earlier versions of this code.


#### 'editMetadata.py'

Quick utility to walk through mp3 files in a directory tree and verify metadata settings (and make changes if needed.)

#### `dirlist.py`

The `mover.py` utility has an option to move/copy files based on a list of directory names
provided in a file. Run this to generate a list of directories in `artist/album` format like 
we use. This list is printed to stdout; redirect into a file. 
I use this when e.g. updating the flash drive I keep in the car -- generate a list of my entire 
collection, then delete albums that I *don't* want copied there, then use mover.py to copy (and 
usually transcode to a lower bitrate) files onto the drive.


#### `echonest.py`

#### `meta.py`


#### `splitter.py`

#### `updateMeta.py`
