import pyaudio
import time
import numpy as np
import modformat

CHUNK = 1024
filepath = "examples/the_objttze.mod"

# Initialize pyAudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paUInt8, channels=1, rate=8287, input=False, output=True)

# Load song
loader = modformat.Loader()
song = loader.loadSong(filepath)
print(song)

# Play all of its samples
for sample in song.samplelist:
    audio_data = np.array(sample.data).view(np.int8)[::4]
    stream.write(audio_data.tobytes())

# Close the stream and terminate pyAudio
stream.stop_stream()
stream.close()
p.terminate()