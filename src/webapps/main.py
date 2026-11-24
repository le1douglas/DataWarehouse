from fastapi.responses import RedirectResponse
from nicegui import ui

from webapps.ui import drip_drain


@ui.page("/")
def index() -> RedirectResponse:
    # the only web app for now
    return RedirectResponse(drip_drain.PATH)


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Web apps", show=False)
