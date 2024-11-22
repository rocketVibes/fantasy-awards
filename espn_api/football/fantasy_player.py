from operator import attrgetter


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


# Flatten list of team scores as they come in box_score format
class FantasyTeamPerformance:
    def __init__(self, team_name, owner, score, score_diff, vs_team_name, vs_owner, lineup, bench_total, wins):
        self.team_name = team_name
        self.owner = owner
        self.score = score
        self.diff = score_diff
        self.vs_team_name = vs_team_name
        self.vs_owner = vs_owner
        self.lineup = lineup
        self.bench_total = bench_total
        self.wins = wins
        # Compute a team's potential highest score given perfect start/sit decisions
        roster = lineup.copy()
        total_potential = 0
        # Add individual contributors to the highest potential and remove them from the pool
        for pos in [['QB'], ['K'], ['D/ST'], ['RB'], ['RB'], ['TE'], ['WR'], ['WR'], ['WR', 'TE']]:
            best_player = max([player for player in roster if player.position in pos], key=attrgetter('points'))
            total_potential += best_player.points
            roster.remove(best_player)
        self.potential_high = round(total_potential, 2)
        self.potential_used = self.score / total_potential

    def get_potential_used(self):
        return '{:,.2%}'.format(self.potential_used)