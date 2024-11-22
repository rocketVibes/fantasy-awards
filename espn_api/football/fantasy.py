from espn_api.football import League
from espn_api.football import GoogleSheetService
from espn_api.football import FantasyTeamPerformance
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
IRRELEVANT = ['K', 'BE', 'D/ST', 'IR']
MAGIC_ASCII_OFFSET = 66


def get_first_name(name):
    if 'Aaron' in name:
        return 'Yates'
    elif 'Nathan' in name:
        return 'Nate'
    elif 'Dustin' in name:
        return 'Libby'
    elif 'Zachary' in name:
        return 'Zach'
    else:
        return name.split(' ', 1)[0]


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
        self.scores, self.crashes, self.rookies, self.mistakes = [], [], [], []

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
        award_biggest_mistake()
        award_crash_burn(self.crashes)
        award_rookie_cookie(self.rookies)
        self.evaluate_streaks()
        award_streaks(self.league.teams, WEEK)
        # self.sheets.wed_morn(True)
        # self.sheets.final(True, self.awards)
        self.print_awards()

    # Process team performances to be iterable
    def process_matchup(self, lineup, team_name, score, opp_score, owner_name, vs_team_name, vs_owner, wins):
        # Calculate the difference between home and away scores
        diff = score - opp_score
        total = score + opp_score

        self.evaluate_start_decisions(team_name, lineup, diff)

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

            if player.lineupSlot not in IRRELEVANT:
                if player.injuryStatus in HEALTHY and player.points < lowest_ind:
                    lowest_ind = player.points
                    lowest_ind_player = new_player

                # If any players scored 3+ more than projected, the team is not lost in the sauce
                if player.points >= player.projected_points + 3:
                    lost_in_the_sauce = False

                award_burgers(team_name, player)
                award_daily_double(team_name, player)
                award_out_of_office(team_name, player)
                award_injury_insult(team_name, player, diff)

            if player.lineupSlot in BENCHED:
                bench_total += player.points
            elif 'Rookie' in player.eligibleSlots:
                self.rookies.append(new_player)

            # Compile lists of players at each position
            self.players[player.lineupSlot].append(new_player) if player.lineupSlot != 'WR/TE' else (
                self.players[player.position].append(new_player))
            award_kick_rocks(team_name, player)
            award_best_defense(team_name, player)

        award_lost_sauce(team_name, lost_in_the_sauce)
        self.crashes.append(lowest_ind_player) if lowest_ind_player is not None else None
        self.scores.append(
            FantasyTeamPerformance(
                team_name,
                owner_name,
                score,
                diff,
                vs_team_name,
                vs_owner,
                lineup,
                bench_total,
                wins))

    def evaluate_start_decisions(self, team_name, lineup, diff):
        # Evaluate starters vs benched players at each position
        for pos in POSITIONS:
            lineup_slot = pos[0]
            if len(pos) > 1:
                lineup_slot = '/'.join(pos)

            starters = [player for player in lineup if player.lineupSlot == lineup_slot]
            benches = [player for player in lineup if player.lineupSlot in BENCHED and player.position in lineup_slot]
            # Find the worst starter vs the best benched player at a given position
            starter = min(starters, key=attrgetter('points'))
            benched_player = max(benches, key=attrgetter('points')) if len(benches) > 0 else None

            if benched_player is not None:
                # If there is a benched player who outperformed, and the team lost then evaluate awards
                if benched_player.points >= abs(diff) + starter.points:
                    award_blunder(team_name, benched_player, starter, diff)
                    self.mistakes.append(FantasyPlayer(benched_player.name + '.' + starter.name,
                                                       team_name,
                                                       benched_player.points,
                                                       starter.points))
                elif (starter.injuryStatus in HEALTHY and benched_player.points >= starter.points * 2
                      and benched_player.points >= starter.points + 5):
                    award_start_sit(team_name, benched_player, starter)
                    self.mistakes.append(FantasyPlayer(benched_player.name + '.' + starter.name,
                                                       team_name,
                                                       benched_player.points,
                                                       starter.points))

    def initialize_sheets(self):
        self.sheets = GoogleSheetService(self.scores, WEEK, SPREADSHEET_ID)
        # We want to do things in the order of teams from the spreadsheet, not the order from ESPN
        self.teams, wins = [], []
        for team in self.sheets.teams:
            # Append team name to list in the Google Sheet order
            self.teams.append(team[0])
            wins.append(next((score for score in self.scores if score.team_name == team[0])).wins)
        # self.sheets.tues_morn(True, wins)

    # Get last week's rankings to calculate any upsets
    def evaluate_streaks(self):
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

    # Print all awards
    def print_awards(self):
        i = 1
        for team_name in self.teams:
            print(f'{i}) {team_name}')
            award_values = awards[team_name].values()
            for award_value in award_values:
                if (len(awards) <= 4 or award_value.award_string !=
                        'LOST IN THE SAUCE - No non-special-teams starter scored 3+ more than projected'):
                    print(award_value.award_string)
            i += 1
            print()


service = FantasyService()

service.generate_awards()
