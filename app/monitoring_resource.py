class MonitoringResource:
    """Класс для репрезентации состояния сервера"""
    def __init__(self, name: str, url: str):
        self.name: str = name
        self.url: str = url
        self.__current_status_code: int = -1

    def update_status_code(self, status_code: int):
        self.__current_status_code = status_code

    @property
    def current_status_code(self):
        return self.__current_status_code

    @property
    def is_running(self):
        if self.__current_status_code in [200, 202]:
            return True

        return False

    def create_current_state_report(self):
        return f"{self.name}: status code {self.current_status_code} for {self.url}"
