from nicegui import ui


@ui.page("/")
def index():
    ui.label("No programs yet")


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Web apps", show=False)
