from threading import Thread
from multiprocessing import Process, shared_memory, Manager, Lock, Event

import time
import queue
from modules import channel, mixer, player, plotter
from settings import FILEPATH, CHANNELS, START_PATTERN, START_NOTE
from modformat import ModFile, CHANNEL_COUNT
from typelib import BUFFER_SIZE, MixerThreadInfo, PlayerThreadInfo, BeatPtr
from dataclasses import asdict


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
    output_queue = queue.Queue(10)

    # Start processes and Threads and manage their shared data
    with Manager() as manager:
        shrd_beat_ptr = manager.dict(asdict(beat_ptr))
        stop_flag = Event()                           # For graceful shutdown, signals to everyone when to stop
        shared_ch_locks = [Lock() for _ in range(CHANNEL_COUNT)] # signals to the mixer when the channels finish writing

        # Start the channel processes and store them
        ch_processes = []
        for i in CHANNELS:
            if 0 <= i <= 3:
                t = Process(target=channel, args=(i, song, shm_names[i], shrd_beat_ptr, shared_ch_locks,))
                t.start()
                ch_processes.append(t)

        # Start the plotter
        plotter_proc = Process(target=plotter, args=(shm_names, song.name, shared_ch_locks))
        plotter_proc.start()

        # Start the mixer
        mixer_thread_info = MixerThreadInfo(shared_ch_locks, stop_flag)
        mixer_thread = Thread(target=mixer, args=(shm_names, output_queue, shrd_beat_ptr, mixer_thread_info))
        mixer_thread.start()

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
        mixer_thread.join()
        player_thread.join()
        for t in ch_processes:
            t.join()

        # release shared memory
        for shm in shm_list:
            shm.unlink()


if __name__ == "__main__":
    main()
