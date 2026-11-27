"""The web app: the walk chosen at / (pages/home_page.py), then its page, /walk/<walk> (pages/walk_page.py),
and its review, /walk/<walk>/review (pages/walk_review_page.py).

Each page registers its route with @ui.page when its module is imported: here, before ui.run.
"""

from pathlib import Path

from nicegui import ui

# imported for their @ui.page
from webapps.pages import home_page, walk_page, walk_review_page  # noqa: F401

# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # - show=False: there is no browser in the container to open
    # - the reload polls python/src only, not the whole repo (the working directory), so a save comes through at once
    # - *.js too: pens/one_pen.js is read when its module is imported
    ui.run(
        title="Web apps",
        show=False,
        uvicorn_reload_dirs=str(Path(__file__).parents[1]),
        uvicorn_reload_includes="*.py, *.js",
    )
