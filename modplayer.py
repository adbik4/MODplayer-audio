import threading

from managers import *
from settings import FILEPATH, CHANNELS, START_PATTERN, START_NOTE
from modformat import ModFile
from audioprocessing import interpolate
from typelib import BUFFER_SIZE, ChannelThreadInfo, MixerThreadInfo, PlayerThreadInfo


def main():
    stop_flag = threading.Event()                         # For graceful shutdown, signals to everyone when to stop
    channel_locks = [threading.Lock() for _ in range(4)]  # signals to the mixer when the channels finish writing

    # Initialize the song state
    song = ModFile.open(FILEPATH)
    beat_ptr = BeatPtr(length=song.length,
                       repeat_idx=song.repeat_idx,
                       pattern_idx=START_PATTERN,
                       note_idx=START_NOTE)
    # Load song

    # upscale the samplelist
    hires_samplelist = []
    for sample in song.samplelist:
        hires_samplelist.append(interpolate(sample))
    song.setSampleList(hires_samplelist)

    # Prepare the channels output buffer and output queue
    channel_buffer = np.zeros((4, BUFFER_SIZE), dtype=np.int8)
    output_queue = queue.Queue()

    # Start the channel threads and store them
    ch_threads = []
    ch_thread_info = ChannelThreadInfo(beat_ptr, channel_buffer, channel_locks, stop_flag)

    for i in CHANNELS:
        if 0 <= i <= 3:
            t = threading.Thread(target=channel, args=(i, song, ch_thread_info,))
            t.start()
            ch_threads.append(t)

    # Start the mixer
    mixer_thread_info = MixerThreadInfo(beat_ptr, channel_buffer, channel_locks, stop_flag)
    mixer_thread = threading.Thread(target=mixer, args=(output_queue, mixer_thread_info,))
    mixer_thread.start()

    # Start the player
    player_thread_info = PlayerThreadInfo(stop_flag)
    player_thread = threading.Thread(target=player, args=(output_queue, player_thread_info,))
    player_thread.start()

    # Wait until interrupt
    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Exiting program...")
        stop_flag.set()  # tell threads to exit

    # Wait for all the threads to finish
    mixer_thread.join()
    player_thread.join()
    for t in ch_threads:
        t.join()


if __name__ == "__main__":
    main()
