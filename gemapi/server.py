from gemapi.applications import Application


class Server:
    def __init__(self, application: Application) -> None:
        self._application = application
