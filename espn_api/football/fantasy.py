from espn_api.football import League
from espn_api.football import GoogleSheetService
from espn_api.football.award import *

if os.path.exists('values.json'):
    with open('values.json') as f:
        values = json.load(f)

LEAGUE_ID = values['league_id']
WEEK = values['week']
SPREADSHEET_ID = values['spreadsheet_id']
YEAR = values['year']
HEALTHY = ['ACTIVE', 'NORMAL']
BENCHED = ['BE', 'IR']
MAGIC_ASCII_OFFSET = 66


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


class FantasyService:
    # 0) tues morning: change week number to current week
    # 1) tues morning: run generate awards, copy to keep
    # 2) tues morning: run update_weekly_column, update_weekly_scores, update_wins

    # 3) wednesday morning: run get_weekly_roster_rankings, get_ros_roster_rankings
    # 4) wednesday morning: run do_sheet_awards via generate_awards, update_comments
    # 5) wednesday morning: run update_previous_week
    def __init__(self):
        self.teams = None
        self.sheets = None
        self.league = League(LEAGUE_ID, YEAR)
        self.players = defaultdict(list)
        self.scores, self.mistakes, self.crashes, self.rookies = [], [], [], []

    # Iterate over scores and teams to generate awards for each team
    def generate_awards(self):
        print('Generating awards for WEEK: ' + str(WEEK) + '\n')
        # Process matchups
        for matchup in self.league.box_scores(week=WEEK):
            home = matchup.home_team
            away = matchup.away_team
            home_owner = home.owners[0]['firstName'] + ' ' + home.owners[0]['lastName']
            away_owner = away.owners[0]['firstName'] + ' ' + away.owners[0]['lastName']
            self.process_matchup(matchup.home_lineup, home.team_name, matchup.home_score, matchup.away_score,
                                 home_owner, away.team_name, get_first_name(away_owner), [home.outcomes.count('W')])
            self.process_matchup(matchup.away_lineup, away.team_name, matchup.away_score, matchup.home_score,
                                 away_owner, home.team_name, get_first_name(home_owner), [away.outcomes.count('W')])
        self.initialize_sheets()
        award_dynamite(self.scores)
        award_assume_position(self.scores)
        award_fortunate_son(self.scores)
        award_tough_luck(self.scores)
        award_total_domination(self.scores)
        award_second_banana(self.scores)
        award_minority_report(self.scores)
        award_none_crystal(self.scores)
        # Individual player awards
        award_caller_baller(self.teams, self.players['QB'])
        award_tightest_end(self.teams, self.players['TE'])
        award_fort_knox(self.teams, self.players['D/ST'])
        award_kick_fast(self.teams, self.players['K'])
        award_ground_delivery(self.teams, self.players['RB'])
        award_air_delivery(self.teams, self.players['WR'])
        award_deep_threat(self.teams, self.players['WR'])
        award_on_his_backs(self.teams, self.players['RB'])
        award_big_bench(self.scores)
        award_biggest_mistake(self.mistakes)
        award_crash_burn(self.crashes)
        award_rookie_cookie(self.rookies)
        self.evaluate_streaks()
        award_streaks(self.league.teams, WEEK)
        # self.sheets.wed_morn(True)
        # self.sheets.final(True, self.awards)
        print_awards(self.teams)

    # Process team performances to be iterable
    def process_matchup(self, lineup, team_name, score, opp_score, owner_name, vs_team_name, vs_owner, wins):
        # Calculate the difference between home and away scores
        diff = score - opp_score
        total = score + opp_score
        mistake = evaluate_start_decisions(team_name, lineup, diff)
        self.mistakes.append(mistake) if mistake is not None else None
        award_cripple_fight(team_name, vs_owner, total)
        award_sub_100(team_name, score)
        award_madden_rookie(team_name, vs_owner, diff)
        lost_in_the_sauce = True
        lowest_ind_player = None
        bench_total = 0
        lowest_ind = 50
        for player in lineup:
            # Make pile of all players to iterate over
            new_player = FantasyPlayer(player.name, team_name, player.points)
            if player.lineupSlot not in BENCHED and 'Rookie' in player.eligibleSlots:
                self.rookies.append(new_player)
            if (player.lineupSlot not in ['D/ST', 'K'] and player.injuryStatus in HEALTHY
                    and player.lineupSlot not in BENCHED and player.points < lowest_ind):
                lowest_ind = player.points
                lowest_ind_player = new_player
            award_burgers(team_name, player)
            if player.lineupSlot in BENCHED:
                bench_total += player.points
            if player.lineupSlot not in ['K', 'BE', 'D/ST', 'IR']:
                # If any players scored 3+ more than projected, the team is not lost in the sauce
                if player.points >= player.projected_points + 3:
                    lost_in_the_sauce = False
                award_daily_double(team_name, player)
                award_out_of_office(team_name, player)
                award_injury_insult(team_name, player, diff)
            # Compile lists of players at each position
            self.players[player.position].append(new_player)
            award_kick_rocks(team_name, player)
            award_best_defense(team_name, player)
        award_lost_sauce(team_name, lost_in_the_sauce)
        self.crashes.append(lowest_ind_player) if lowest_ind_player is not None else None
        self.scores.append(
            FantasyTeamPerformance(team_name, owner_name, score, diff, vs_team_name, vs_owner, lineup, bench_total,
                                   wins))

    def initialize_sheets(self):
        self.sheets = GoogleSheetService(self.scores, WEEK, SPREADSHEET_ID)
        # We want to do things in the order of teams from the spreadsheet, not the order from ESPN
        self.teams, wins = [], []
        for team in self.sheets.teams:
            # Append team name to list in the Google Sheet order
            self.teams.append(team[0])
            wins.append(next((score for score in self.scores if score.team_name == team[0])).wins)
        # self.sheets.tues_morn(True, wins)

    def evaluate_streaks(self):
        # Get last week's rankings to calculate any upsets
        old_rank_col = chr(MAGIC_ASCII_OFFSET + WEEK)
        values_old_rank = self.sheets.get_sheet_values('HISTORY!' + old_rank_col + '2:' + old_rank_col + '13')
        if not values_old_rank:
            print('Last week\'s rankings don\'t exist for some reason?')
        else:
            dict_of_old_ranks = award_upsets(self.teams, self.scores, values_old_rank)
            # Get this week's forecasted rankings to see if there is a new leader or a new bitch, or if rank changed 3+
            new_rank_col = chr(MAGIC_ASCII_OFFSET + WEEK + 1)
            values_new_rank = self.sheets.get_sheet_values('HISTORY!' + new_rank_col + '2:' + new_rank_col + '13')
            if not values_new_rank:
                print('This week\'s rankings haven\'t been calculated yet.')
            else:
                award_new_top_bottom(self.teams, self.scores, values_new_rank, dict_of_old_ranks)


service = FantasyService()

service.generate_awards()
