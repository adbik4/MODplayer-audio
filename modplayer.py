import pyaudio
import time
import numpy as np
import modformat

CHUNK = 1024
filepath = "examples/remonitor.mod"

# Initialize pyAudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt8, channels=1, rate=16574, input=False, output=True)

# Load song
song = modformat.ModFile.open(filepath)
print(song)

# Play all of its samples
for sample in song.samplelist:
    audio_data = sample.data
    stream.write(bytes(audio_data))

# Close the stream and terminate pyAudio
stream.stop_stream()
stream.close()
p.terminate()