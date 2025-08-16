from core.file import ModFile
filepath = "remonitor.mod"

song = ModFile.open(filepath)
sample_idx = 0
for sample in song.samplelist:
    print(sample.length, sample.looplength, len(sample.data))
