from threading import Thread
from multiprocessing import Process, shared_memory, Manager, Event, Barrier, Queue

import time
from functools import partial
from audioprocessing import mix
from modules import channel, player, plotter
from settings import FILEPATH, CHANNELS, START_PATTERN, START_NOTE, SHOW_VISUALIZER
from modformat import ModFile, CHANNEL_COUNT
from typelib import BUFFER_SIZE, PlayerThreadInfo, BeatPtr
from dataclasses import asdict

# TODO: large refactor
# TODO: fix discontinuities
# TODO: a note counter in the visualiser
# TODO: artists description in the visualiser
# TODO: THE EFFECTS RENDERER


def main():
    # Load the song
    song = ModFile.open(FILEPATH)

    # Initialise the beat pointer
    beat_ptr = BeatPtr(length=song.length,
                       repeat_idx=song.repeat_idx,
                       pattern_idx=START_PATTERN,
                       note_idx=START_NOTE)

    # Prepare the channels shared memory output buffer
    shm_list = []
    shm_names = []
    for _ in range(CHANNEL_COUNT):
        shm = shared_memory.SharedMemory(create=True, size=BUFFER_SIZE*4)
        shm_list.append(shm)
        shm_names.append(shm.name)

    # Prepare the output queue
    output_queue = Queue(1)

    # Start processes and Threads and manage their shared data
    with Manager() as manager:
        # Create the thread safety objects
        shared_beat_ptr = manager.dict(asdict(beat_ptr))  # Keeps track of the position in the song
        stop_flag = Event()             # For graceful shutdown, signals to everyone when to stop

        # enforces the 4 channels generate -> mix -> repeat rule
        mix_action = partial(mix, shm_names, output_queue, shared_beat_ptr)
        sync_barrier = Barrier(len(CHANNELS), action=mix_action)

        # Start the channel processes and store them
        ch_processes = []
        for i in CHANNELS:
            if 0 <= i <= 3:
                t = Process(target=channel, args=(i, song, shm_names[i], shared_beat_ptr, sync_barrier))
                t.start()
                ch_processes.append(t)

        # Start the plotter
        if SHOW_VISUALIZER:
            plotter_proc = Process(target=plotter, args=(shm_names, song.name))
            plotter_proc.start()

        # Start the player
        player_thread_info = PlayerThreadInfo(stop_flag)
        player_thread = Thread(target=player, args=(output_queue, player_thread_info,))
        player_thread.start()

        print("NOW PLAYING: ", song.name)

        # Wait until interrupt
        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("Exiting program...")
            stop_flag.set()  # tell threads to exit

        # Wait for all the threads to finish
        player_thread.join()
        for t in ch_processes:
            t.join()

        # release shared memory
        for shm in shm_list:
            shm.unlink()


if __name__ == "__main__":
    main()
