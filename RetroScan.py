import sys
from pathlib import Path, PosixPath, WindowsPath
import argparse
import re
import zlib
import configparser

platformExtensions = {
    "Switch" : "_libnx.nro",
    "Windows" : ".dll",
    "Linux" : ".so"
}


BuildPlatform = "Switch"

parser = argparse.ArgumentParser(description="A playlist builder for RetroArch.")
parser.add_argument("-crc", action="store_true")
parser.add_argument("-p", "--platform", action="store", nargs=1)
parser.add_argument("path", metavar = "PATH TO FOLDER", type=str, nargs="?")
args = parser.parse_args()


if args.platform:
    BuildPlatform = args.platform[0]
    try:
        platformExtensions[BuildPlatform]
    except KeyError:
        print("Platform {} is not available please use one of {}".format(BuildPlatform, tuple(platformExtensions.keys()) ) )
        exit(-1)

WPath = None
if args.path == None:
    WPath = Path.cwd()
else:
    WPath = Path(args.path)
    if WPath.is_file():
        raise ValueError("Input is a file not a folder")

DriveLetter = WPath.drive
retroPath = Path(WPath.drive) / "/retroarch"
corePath = Path("/retroarch/cores")
playlistPath = retroPath / "playlists"

def folderParse(currentPath, folderTags = [], playlistDictionary = {}, root=True):
    romsPresent = False
    entries = list(currentPath.iterdir())
    entries.sort()
    for entry in entries:
        if entry.is_file():
            try:
                rom = ROM.factory (entry, folderTags)
                print(rom.sysName, rom.getROMName(), rom.crc)
                playlistName = rom.getPlaylistName()

                if not playlistName in playlistDictionary.keys():
                    playlistDictionary[playlistName] = open(playlistPath / playlistName, "w")

                playlistDictionary[playlistName].write(rom.getPlaylistEntry())
                romsPresent = True
            except ROMError:
                pass

    for entry in currentPath.iterdir():
        if entry.is_dir():
            folderParse(currentPath / entry, folderTags + [entry.name] if romsPresent else folderTags, playlistDictionary, False)
    if root:
        for playlistFile in playlistDictionary.values():
            playlistFile.close()


class ROMError(TypeError):
    def __init__(self):
        TypeError.__init__(self, "File is not a ROM")




class ROM(object):
    core = None
    sysName = None
    extension = []
    lookupTable = {}
    def __init__(self, filePath, folderTags = []):
        self.filePath = filePath
        if type(self.filePath) is WindowsPath and self.filePath.drive != '':
            self.filePath = Path('/', *(filePath.parts[1:]))

        self.romName = self.filePath.stem
        self.fileExtension = self.filePath.suffix
        self.folderTags = folderTags
        self.crc = self.calcCRC()


    def calcCRC(self):
        if args.crc:
            buffersize = 65536
            self.crc = 0
            with open (self.filePath, 'rb') as f:
                buffer = f.read(buffersize)
                while len(buffer) > 0:
                    self.crc = zlib.crc32(buffer, self.crc)
                    buffer = f.read(buffersize)
                return format (self.crc & 0xFFFFFFFF, "08x") + "|crc"
        else:
            return "DETECT"

    def getROMName(self):
        return self.romName + ( "" if len(self.folderTags) == 0 else " [" + ", ".join(self.folderTags) +"]" )

    def getROMFile(self):
        return self.filePath.as_posix()

    def __lt__(self,other):
        return self.romName < other.romName

    def getPlaylistName(self):
        return str(self.sysName + ".lpl")

    def getCorePath(self):
        return (corePath / (self.core + platformExtensions[BuildPlatform] ) ).as_posix()

    def getCRC(self):
        return self.crc

    def getCoreTitle(self):
        return "DETECT"

    def getPlaylistEntry(self):
        entry = self.getROMFile() + '\n'
        entry += self.getROMName() + '\n'
        entry += self.getCorePath() + '\n'
        entry += self.getCoreTitle() + '\n'
        entry += self.getCRC() + '\n'
        entry += self.getPlaylistName() + '\n'
        return entry

    @staticmethod
    def factory(filePath, folderTags):
        extension = filePath.suffix.lower()
        try:
            return ROM.lookupTable[extension](filePath, folderTags)
        except KeyError:
            raise ROMError()

class ROMMeta(type):
    def __new__(cls, name, bases, dct):
        if dct.get("__metaclass__") is not ROMMeta:
            subClass = super(ROMMeta, cls).__new__(cls, name, bases, dct)
            for extension in dct["extensions"]:
                ROM.lookupTable[extension] = subClass
        return subClass

# Playlist Naming Convention
# https://github.com/libretro/docs/blob/master/docs/guides/roms-playlists-thumbnails.md

# Example for potential external file loading
def makeROMClass(coreIn, sysNameIn, extensionsIn = []):
    class SubROM(ROM, metaclass=ROMMeta):
        core = coreIn
        sysName = sysNameIn
        extensions = extensionsIn

    return SubROM

config = configparser.RawConfigParser()
config.read(Path.cwd() / "retroscan.cfg")

for section in config.sections():
    name = config.get(section, "name")
    core = config.get(section, "core")
    extensions = config.get(section, "extensions").split()
    makeROMClass(core, name, extensions)

#makeROMClass("mgba_libretro", "Nintendo - Game Boy Advance", [".gba"])

#makeROMClass("mupen64plus_libretro", "Nintendo - Nintendo 64", [".n64"])

#makeROMClass("nestopia_libretro", "Nintendo - Nintendo Entertainment System", [".nes"])

#makeROMClass("snes9x2010_libretro", "Nintendo - Super Nintendo Entertainment System", [".smc", ".sfc"])

#makeROMClass("pcsx_rearmed_libretro", "Sony - PlayStation", [".pbp"])

# Old system example
"""class GBAROM(ROM):
    core = "mgba_libretro"
    sysName = "Nintendo - Game Boy Advance"
    extensions = [".gba"]
"""


folderParse(WPath)
print("Playlist Building Complete\n")