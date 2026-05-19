"""
survey_state.py — In-memory кеш состояния опроса.
"""


class SurveyState:
    def __init__(self):
        self.active = False
        self.index = 0
        self.answers = {}

    def start(self):
        self.active = True
        self.index = 0
        self.answers = {}

    def answer(self, relapsed: bool):
        self.answers[self.index] = relapsed
        self.index += 1

    def is_complete(self, total: int) -> bool:
        return self.index >= total

    def reset(self):
        self.active = False
        self.index = 0
        self.answers = {}


survey_state = SurveyState()
