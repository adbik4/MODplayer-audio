from modformat import ModFile
filepath = "examples/70hz_refresh_chip.mod"

song = ModFile.open(filepath)
print(song)