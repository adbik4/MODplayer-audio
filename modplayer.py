import threading

from managers import *
from settings import FILEPATH, CHANNELS, START_PATTERN, START_NOTE
from modformat import ModFile
from audioprocessing import interpolate
from typelib import ClockState, BUFFER_SIZE


def main():
    stop_flag = threading.Event()                          # For graceful shutdown
    channel_locks = [threading.Lock() for _ in range(4)]   # signal to the mixer when the channels finish writing
    output_lock = threading.Lock()                         # signals to the player when the mixer finishes writing

    # Load song
    song = ModFile.open(FILEPATH)

    # upscale the samplelist
    hires_samplelist = []
    for sample in song.samplelist:
        hires_samplelist.append(interpolate(sample))
    song.setSampleList(hires_samplelist)

    # Initialize and start the clock
    # TODO: refactor the thread flags into a dataclass
    clk_state = ClockState(tick_event=threading.Event(),
                           length=song.length,
                           repeat_idx=song.repeat_idx,
                           pattern_idx=START_PATTERN,
                           note_idx=START_NOTE)
    clock_thread = threading.Thread(target=clock, args=(clk_state, stop_flag,))
    clock_thread.start()

    # Prepare the channels output buffer
    channel_buffer = np.zeros((4, BUFFER_SIZE), dtype=np.int8)

    # Start the channel threads and store them
    channel_threads = []
    for i in CHANNELS:
        if 0 <= i <= 3:
            t = threading.Thread(target=channel, args=(i, clk_state, song, channel_buffer, channel_locks, stop_flag,))
            t.start()
            channel_threads.append(t)

    # Start the mixer
    output_buffer = np.zeros(BUFFER_SIZE, dtype=np.int8)
    mixer_thread = threading.Thread(target=mixer, args=(channel_buffer, output_buffer, channel_locks, clk_state, output_lock, stop_flag,))
    mixer_thread.start()

    # Start the player
    player_thread = threading.Thread(target=player, args=(output_buffer, output_lock, stop_flag,))
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
    for t in channel_threads:
        t.join()


if __name__ == "__main__":
    main()
