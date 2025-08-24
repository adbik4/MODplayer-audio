from multiprocessing import shared_memory
import matplotlib.animation as animation
import matplotlib.style as mplstyle
import matplotlib.pyplot as plt
import numpy as np

from core.constants import BUFFER_SIZE, VIEW_WIDTH, TICK_RATE
from core.file import CHANNEL_COUNT
from core.utilities import profile


@profile
def visualizer(shm_names: str, song_name: str):
    # Create a numpy array view on the shared memory buffer
    shm_buffer = []
    for name in shm_names:
        shm = shared_memory.SharedMemory(name=name)
        shm_buffer.append(shm)

    # Persistent NumPy views for each channel
    shm_array = []
    for i in range(CHANNEL_COUNT):
        shm_array.append(np.ndarray((BUFFER_SIZE,), dtype=np.float32, buffer=shm_buffer[i].buf))

    try:
        # Create 4 subplots in a 2x2 grid
        fig, ax = plt.subplots(2, 2, figsize=(5, 5))
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
            begin = ((VIEW_WIDTH + 1) * frame) % BUFFER_SIZE
            end = ((VIEW_WIDTH + 1) * (frame + 1) - 1) % BUFFER_SIZE

            if begin > end:
                return artists

            for i in range(CHANNEL_COUNT):
                artists[i].set_ydata(shm_array[i][begin:end])
            return artists

        # Do the animation
        interv = TICK_RATE * 1000 * (VIEW_WIDTH / BUFFER_SIZE)
        ani = animation.FuncAnimation(fig=fig, func=update, interval=interv, save_count=10)
        plt.show()

    except KeyboardInterrupt:
        print("exiting visualiser")

    finally:
        # Cleanup
        for shm in shm_buffer:
            shm.close()
