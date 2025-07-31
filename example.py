from modformat import Loader
filepath = "examples/70hz_refresh_chip.mod"

loader = Loader()
song = loader.loadSong(filepath)

for sample in song.samplelist:
    print(sample)