from multiprocessing import Manager
import time

from settings import FILEPATH
from core.setup import process_init, process_deinit
from core.file import ModFile

# TODO: THE EFFECTS RENDERER
# TODO: fix discontinuities
# TODO: a note counter in the visualiser
# TODO: artists description in the visualiser
# TODO: add download functionality?
# TODO: Discrete Cosine Transform mixer


def main():
    with Manager() as manager:
        song = ModFile.open(FILEPATH)
        process_info = process_init(manager, song)

        try:
            print("NOW PLAYING: ", song.name)
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("Exiting program...")

        finally:
            process_deinit(process_info)


if __name__ == "__main__":
    main()
