# Persist team name from box score to player instead of current team (which can change)
class FantasyPlayer:
    def __init__(self, name, team_name, score, second_score=0):
        self.name = name
        self.team_name = team_name
        self.score = score
        # Special use of the Fantasy_Player class -- only to find the biggest mistake across the league
        self.second_score = second_score
        self.diff = self.score - self.second_score

    def get_last_name(self):
        return self.name.split(None, 1)[1]

    def get_first_name(self):
        return self.name.split(None, 1)[0]

    # Special use of the Fantasy_Player class -- only to find the biggest mistake across the league
    def get_mistake_first(self):
        return self.name.split('.', 1)[0]

    # Special use of the Fantasy_Player class -- only to find the biggest mistake across the league
    def get_mistake_second(self):
        return self.name.split('.', 1)[1]


class FantasyAward:
    def __init__(self, award_string, team_name, magnitude=None):
        self.award_string = award_string
        self.team_name = team_name
        self.magnitude = magnitude
