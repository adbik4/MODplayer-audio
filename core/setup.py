from settings import CHANNELS, START_PATTERN, START_NOTE, SHOW_VISUALIZER
from multiprocessing import Process, shared_memory, Manager, Barrier, Queue
from core.types import BeatPtr, ProcessInfo
from core.file import CHANNEL_COUNT, ModFile
from core.constants import BUFFER_SIZE
from audio.channel import channel
from audio.mixer import mix
from audio.player import player
from graphics.visualizer import visualizer
from dataclasses import asdict
from functools import partial
from threading import Thread


def process_init(manager: Manager, song: ModFile) -> ProcessInfo:
    beat_ptr = BeatPtr(pattern_idx=START_PATTERN, note_idx=START_NOTE)

    # Create the channels shared memory output buffer
    shm_list = []
    shm_names = []
    for _ in range(CHANNEL_COUNT):
        shm = shared_memory.SharedMemory(create=True, size=BUFFER_SIZE*4)
        shm_list.append(shm)
        shm_names.append(shm.name)

    # Prepare the output queue
    output_queue = Queue(2)     # increase if you experience stuttering

    # Process safety and synchronization
    beat_ptr_proxy = manager.dict(asdict(beat_ptr))
    mix_action = partial(mix, shm_names, output_queue, beat_ptr_proxy, song.length, song.repeat_idx)
    sync_barrier = Barrier(len(CHANNELS), action=mix_action)

    # Initialise the channel processes and store them
    process_list = [Process(target=channel, args=(i, song, shm_names[i], beat_ptr_proxy, sync_barrier))
                    for i in CHANNELS if 0 <= i <= 3]

    # Initialise the plotter
    if SHOW_VISUALIZER:
        plotter_proc = Process(target=visualizer, args=(shm_names, song.name))
        process_list.append(plotter_proc)

    # Initialise the player
    player_thread = Thread(target=player, args=(output_queue,))
    process_list.append(player_thread)

    # Start all the processes
    for p in process_list:
        p.start()

    return ProcessInfo(process_list, shm_list, beat_ptr_proxy, output_queue)


def process_deinit(info: ProcessInfo):
    # wait for threads to finish
    for p in info.process_list:
        p.join()

    # release shared memory
    for shm in info.shm_list:
        shm.unlink()
