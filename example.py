from modformat import ModFile
filepath = "examples/_yes.mod"

song = ModFile.open(filepath)
print(song)