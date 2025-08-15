import pyaudio
import numpy as np
import samplerate
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.style as mplstyle
from multiprocessing import shared_memory, Barrier, Queue
from typelib import ChannelState, PlayerThreadInfo
from typelib import profile, BUFFER_SIZE, PLAYBACK_RATE, TICK_RATE
from modformat import ModFile, CHANNEL_COUNT
from settings import INTERPOLATION
from audioprocessing import render_frame


# TODO: create custom thread decorator
# TODO: add visualizaton graph renderer

# ---- local constants
VIEW_WIDTH = min(max(2, 256), BUFFER_SIZE)


# ---- thread definitions
# Keeps track of the current note to play and calls the render_frame function
@profile
def channel(channel_no: int, song: ModFile, shm_name: str, beat_ptr: dict, sync_barrier: Barrier):
    # Initialise the channel state
    channel_state = ChannelState()

    # Create the samplerate converter
    converter = samplerate.Resampler(INTERPOLATION)

    #  Create a numpy array view on the shared memory buffer
    shm = shared_memory.SharedMemory(name=shm_name)
    buffer_np = np.ndarray((BUFFER_SIZE,), dtype=np.float32, buffer=shm.buf)

    try:
        while True:
            pattern_idx = beat_ptr["pattern_idx"]
            note_idx = beat_ptr["note_idx"]

            # Unpack the current pattern
            pattern = song.patternlist[song.pattern_order[pattern_idx]]

            # Reset the channel_state if there was a unique note
            new_note = pattern[channel_no][note_idx]
            if new_note.sample_idx == -1:
                # Continue last note
                channel_state.increment(new_note)
            else:
                # Trigger new note
                channel_state.trigger(new_note)

            # Render a new frame and pass it to the mixer
            audio_data = render_frame(channel_state, converter, song.samplelist)
            buffer_np[:] = audio_data
            sync_barrier.wait()     # wait for all the other threads and mixing to finish

    finally:
        # cleanup
        shm.close()


# Manages the sound settings, playback, creation and destruction of the audio stream
@profile
def player(output_queue: Queue, thread_info: PlayerThreadInfo):
    # Initialize pyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=PLAYBACK_RATE,
                    input=False,
                    output=True)

    # Wait for the beginning of new frame and playback the buffer
    while not thread_info.stop_flag.is_set():
        # Playback
        data = output_queue.get()
        stream.write(data)

    # Close the stream and terminate pyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()


@profile
def plotter(shm_names: str, song_name: str):
    # Create a numpy array view on the shared memory buffer
    shm_buffer = []
    for name in shm_names:
        shm = shared_memory.SharedMemory(name=name)
        shm_buffer.append(shm)

    # Persistent NumPy views for each channel
    shm_array = []
    for i in range(CHANNEL_COUNT):
        shm_array.append(np.ndarray((BUFFER_SIZE,), dtype=np.float32, buffer=shm_buffer[i].buf))

    # Create 4 subplots in a 2x2 grid
    fig, ax = plt.subplots(2, 2, figsize=(9, 9))
    ax = ax.flatten()

    # Theme setup
    plt.rcParams["font.family"] = "Consolas"
    mplstyle.use(['dark_background', 'fast'])
    fig.patch.set_facecolor("#111111")

    # Window setup
    manager = plt.get_current_fig_manager()
    manager.window.wm_title(song_name)
    screen_width = manager.window.winfo_screenwidth()
    screen_height = manager.window.winfo_screenheight()
    fig_width = int(fig.get_figwidth() * manager.window.winfo_fpixels('1i'))
    fig_height = int(fig.get_figheight() * manager.window.winfo_fpixels('1i'))
    x = (screen_width - fig_width) // 2
    y = (screen_height - fig_height) // 2
    manager.window.wm_geometry(f"{fig_width}x{fig_height}+{x}+{y}")

    # Plot title
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.suptitle(
        f"NOW PLAYING: {song_name}",
        fontsize=18,
    )

    # Create one Line2D per channel
    artists = [
        ax[i].plot(np.zeros(VIEW_WIDTH, dtype=np.float32), linewidth=1, color="#00e6b8")[0]
        for i in range(CHANNEL_COUNT)
    ]

    # Subplot configuration
    for i in range(CHANNEL_COUNT):
        ax[i].text(0.05, 0.03, f'CHANNEL {i + 1}', fontsize=12, color="white", transform=ax[i].transAxes)
        ax[i].set_ylim(-1.25, 1.25)
        ax[i].set_xticks([])  # Remove x ticks
        ax[i].set_yticks([])  # Remove y ticks
        ax[i].set_facecolor("#222222")

    def update(frame):
        begin = ((VIEW_WIDTH+1) * frame) % BUFFER_SIZE
        end = ((VIEW_WIDTH+1) * (frame+1) - 1) % BUFFER_SIZE

        if begin > end:
            return artists

        for i in range(CHANNEL_COUNT):
            artists[i].set_ydata(shm_array[i][begin:end])
        return artists

    try:
        # Do the animation
        interv = TICK_RATE * 1000 * (VIEW_WIDTH/BUFFER_SIZE)
        ani = animation.FuncAnimation(fig=fig, func=update, interval=interv)
        plt.show()

    except KeyboardInterrupt:
        # Cleanup
        for shm in shm_buffer:
            shm.close()
