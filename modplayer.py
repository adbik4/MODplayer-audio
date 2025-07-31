from modformat import Loader
filepath = "examples/the_objttze.mod"

loader = Loader()
song = loader.loadSong(filepath)
print(song)