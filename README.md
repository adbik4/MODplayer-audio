# MODplayer-audio
An audio player for .mod files - a classic module music format that originated on the Commodore Amiga in 1987. The format stores musical patterns together with digital samples (instruments) in a single file.

A .mod file works by including a collection of sampled instruments, a set of patterns that describe when and how each sample should be played, and an order list that defines the sequence of those patterns to form a song. Traditional modules typically use 4 audio channels, up to 31 samples, and patterns made of 64 rows.

## Demo
[![Watch the video](https://img.youtube.com/vi/y-e6WNMb_rQ/maxresdefault.jpg)](https://youtu.be/y-e6WNMb_rQ)

### [Watch this video on YouTube](https://youtu.be/y-e6WNMb_rQ)

## Dependencies
Install the required Python packages:

```bash
pip install numpy samplerate pyaudio matplotlib pyinstrument
```

### Debian/Ubuntu
```bash
sudo apt-get install portaudio19-dev python3-dev
pip install pyaudio
```

## Running the player
Edit settings.py to configure playback options, select channels, and choose which .MOD file to play.

```
python main.py
```