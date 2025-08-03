from modformat import ModFile
filepath = "examples/savedick.mod"

song = ModFile.open(filepath)
for sample in song.samplelist:
    print(sample.name, sample.length, sample.loopstart, sample.looplength)