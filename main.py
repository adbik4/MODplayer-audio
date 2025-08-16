from multiprocessing import Process, shared_memory, Manager, Barrier, Queue
from dataclasses import asdict
from functools import partial
from threading import Thread
import time

from settings import FILEPATH, CHANNELS, START_PATTERN, START_NOTE, SHOW_VISUALIZER
from core.types import BeatPtr
from core.file import CHANNEL_COUNT, ModFile
from core.constants import BUFFER_SIZE
from audio.channel import channel
from audio.mixer import mix
from audio.player import player
from graphics.visualizer import visualizer

# TODO: fix discontinuities
# TODO: a note counter in the visualiser
# TODO: artists description in the visualiser
# TODO: THE EFFECTS RENDERER
# TODO: add web functionality?


def main():
    song = ModFile.open(FILEPATH)
    beat_ptr = BeatPtr(pattern_idx=START_PATTERN, note_idx=START_NOTE)

    # Create the channels shared memory output buffer
    shm_list = []
    shm_names = []
    for _ in range(CHANNEL_COUNT):
        shm = shared_memory.SharedMemory(create=True, size=BUFFER_SIZE*4)
        shm_list.append(shm)
        shm_names.append(shm.name)

    # Prepare the output queue
    output_queue = Queue(1)

    with Manager() as manager:
        # process safety and synchronization
        beat_ptr_proxy = manager.dict(asdict(beat_ptr))
        mix_action = partial(mix, shm_names, output_queue, beat_ptr_proxy, song.length, song.repeat_idx)
        sync_barrier = Barrier(len(CHANNELS), action=mix_action)


        # Start the channel processes and store them
        ch_processes = [Process(target=channel, args=(i, song, shm_names[i], beat_ptr_proxy, sync_barrier))
                        for i in CHANNELS if 0 <= i <= 3]
        for p in ch_processes:
            p.start()


        # Start the plotter
        if SHOW_VISUALIZER:
            plotter_proc = Process(target=visualizer, args=(shm_names, song.name))
            plotter_proc.start()


        # Start the player
        player_thread = Thread(target=player, args=(output_queue,))
        player_thread.start()


        print("NOW PLAYING: ", song.name)
        try:
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("Exiting program...")

        finally:
            # Wait for all the threads to finish
            for t in ch_processes:
                t.join()
            player_thread.join()

            # release shared memory
            for shm in shm_list:
                shm.unlink()


if __name__ == "__main__":
    main()
