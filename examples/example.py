from core.file import ModFile
filepath = "the_objttze.mod"

song = ModFile.open(filepath)
sample_idx = 0
for sample in song.samplelist:
    print(sample.name, sample.length, sample.loopstart, sample.looplength)
    if sample_idx == 4:
        print(sample.data)
    sample_idx += 1
