from settings import USE_PROFILER
from pyinstrument.renderers import HTMLRenderer
import pyinstrument
import functools

# --- decorators
def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global profiler
        if USE_PROFILER:
            profiler = pyinstrument.Profiler()
            profiler.start()
        # ---- profiled code
        func(*args, **kwargs)
        # ---- end of profiled code
        if USE_PROFILER:
            profiler.stop()
            profiler.output(HTMLRenderer(show_all=True, timeline=True))
            profiler.open_in_browser(timeline=True)

    return wrapper
