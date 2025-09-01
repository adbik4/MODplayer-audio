from core.file import ModFile
filepath = "remonitor.mod"

song = ModFile.open(filepath)
for note in song.patternlist[0]:
    print(note)
