from espn_api.football import League
from espn_api.football import Google_Sheet_Service

from operator import attrgetter
from collections import defaultdict
import os.path
import json

if os.path.exists('values.json'):
    with open('values.json') as f:
        values = json.load(f)

LEAGUE_ID = values['league_id']
WEEK = values['week']
SPREADSHEET_ID = values['spreadsheet_id']
YEAR = values['year']
POSITIONS = values['positions']
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
        self.awards = defaultdict(dict)
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
        self.award_dynamite()
        self.award_assume_position()
        self.award_fortunate_son()
        self.award_tough_luck()
        self.award_total_domination()
        self.award_second_banana()
        self.award_minority_report()
        self.award_none_crystal()
        self.award_caller_baller()
        self.award_tightest_end()
        self.award_fort_knox()
        self.award_kick_fast()
        self.award_ground_delivery()
        self.award_air_delivery()
        self.award_deep_threat()
        self.award_on_his_backs()
        self.award_big_bench()
        self.award_biggest_mistake()
        self.award_crash_burn()
        self.award_rookie_cookie()
        self.award_upsets()
        self.award_streaks()
        # self.sheets.wed_morn(True, self.awards)
        self.print_awards()

    def initialize_sheets(self):
        self.sheets = Google_Sheet_Service(self.scores, WEEK, SPREADSHEET_ID)
        # We want to do things in the order of teams from the spreadsheet, not the order from ESPN
        self.teams, wins = [], []
        for team in self.sheets.teams:
            # Append team name to list in the Google Sheet order
            self.teams.append(team[0])
            wins.append(next((score for score in self.scores if score.team_name == team[0])).wins)
        # self.sheets.tues_morn(True, wins)

    # Process team performances to be iterable
    def process_matchup(self, lineup, team_name, score, opp_score, owner_name, vs_team_name, vs_owner, wins):
        # Calculate the difference between home and away scores
        diff = score - opp_score
        self.award_sub_100(score, team_name)
        self.award_madden_rookie(diff, team_name, vs_owner)
        self.award_start_sit(lineup, team_name, diff)
        lost_in_the_sauce = True
        lowest_ind_player = None
        bench_total = 0
        lowest_ind = 50
        for player in lineup:
            # Make pile of all players to iterate over
            new_player = FantasyPlayer(player.name, team_name, player.points)
            if player.lineupSlot not in BENCHED and 'Rookie' in player.eligibleSlots:
                self.rookies.append(new_player)
            if (player.lineupSlot not in ['D/ST', 'K']
                    and player.injuryStatus in HEALTHY
                    and player.lineupSlot not in BENCHED
                    and player.points < lowest_ind):
                lowest_ind = player.points
                lowest_ind_player = new_player
            self.award_burgers(player, team_name)
            if player.lineupSlot in BENCHED:
                bench_total += player.points
            self.award_injury_insult(player, team_name, diff)
            if player.lineupSlot not in ['K', 'BE', 'D/ST', 'IR']:
                # If any players scored 3+ more than projected, the team is not lost in the sauce
                if player.points >= player.projected_points + 3:
                    lost_in_the_sauce = False
                self.award_daily_double(player, team_name)
                self.award_injury_insult(player, team_name, diff)
            # Compile lists of players at each position
            self.players[player.lineupSlot].append(new_player) if 'WR/' not in player.lineupSlot else (
                self.players['WR'].append(new_player))
            self.award_kick_rocks(player, team_name)
            self.award_best_defense(player, team_name)
        self.award_lost_sauce(lost_in_the_sauce, team_name)
        self.crashes.append(lowest_ind_player) if lowest_ind_player is not None else None
        self.scores.append(
            FantasyTeamPerformance(team_name, owner_name, score, diff, vs_team_name, vs_owner, lineup, bench_total,
                                   wins))

    def award_sub_100(self, score, team_name):
        # +++ AWARD teams who didn't make it to 100 points
        if score < 100:
            self.award(team_name, f'SUB-100 CLUB ({score})', 'SUB_100')

    def award_madden_rookie(self, diff, team_name, vs_owner):
        # +++ AWARD teams who beat their opponent by 100
        if diff >= 100:
            self.award(team_name, f'MADDEN ROOKIE MODE (beat {vs_owner} by {diff})', 'MADDEN')

    def award_start_sit(self, lineup, team_name, diff):
        # Evaluate starters vs benched players at each position
        for pos in POSITIONS:
            start_sit = self.compute_start_sit(lineup, pos, team_name, diff)
            if start_sit is not None:
                # +++ AWARD team if a benched player outperformed a starter at the same position (Non-FLEX)
                self.award(team_name, start_sit[0], 'IND_LOW', start_sit[1])

    def award_burgers(self, player, team_name):
        # +++ AWARD players who scored over 50
        for burger in [100, 90, 80, 70, 60, 50, 40]:
            if player.points >= burger:
                self.award(team_name, f'{burger} BURGER ({player.name}, {player.points})', player.lineupSlot + '_HIGH',
                           player.points * 1000)

    def award_injury_insult(self, player, team_name, diff):
        if diff < 0 and player.lineupSlot not in BENCHED:
            # +++ AWARD players who were injured in-game
            if player.injuryStatus not in HEALTHY:
                self.award(team_name, f'INJURY TO INSULT - ({player.name}, {player.points})', 'INJURY')

    def award_daily_double(self, player, team_name):
        # +++ AWARD players who scored 2x projected
        if (player.points > 0 and player.injuryStatus in HEALTHY
                and player.points >= 2 * player.projected_points):
            self.award(team_name,
                       f'DAILY DOUBLE - {player.name} scored >2x projected ({player.points}, '
                       f'{player.projected_points} projected)',
                       player.lineupSlot + '_HIGH', player.points)

    def award_out_of_office(self, player, team_name):
        # +++ AWARD players who didn't get hurt but scored nothing
        if player.injuryStatus in HEALTHY and player.points == 0:
            self.award(team_name, f'OUT OF OFFICE - ({player.name}, 0)', 'IND_LOW', 1)

    def award_kick_rocks(self, player, team_name):
        # +++ AWARD kickers who somehow didn't score any points
        if player.lineupSlot == 'K' and player.injuryStatus in HEALTHY and player.points == 0:
            self.award(team_name, f'GO KICK ROCKS - Kicker scored 0', 'K_LOW')

    def award_best_defense(self, player, team_name):
        # +++ AWARD defenses who sucked
        if player.lineupSlot == 'D/ST' and player.points < 2:
            self.award(team_name, f'THE BEST DEFENSE IS A GOOD OFFENSE - ({player.name}, {player.points})',
                       'D_ST_LOW')

    def award_lost_sauce(self, lost_in_the_sauce, team_name):
        # +++ AWARD team whose players didn't exceed projected amount by 3+
        if lost_in_the_sauce:
            self.award(team_name, 'LOST IN THE SAUCE - No non-special-teams starter scored 3+ more than projected',
                       'TEAM_LOW')

    def award_dynamite(self):
        # Score-based awards
        # +++ AWARD the highest score of the week
        highest = max(self.scores, key=attrgetter('score'))
        self.award(highest.team_name, f'BOOM GOES THE DYNAMITE - Highest weekly score ({highest.score})', 'HIGHEST')

    def award_assume_position(self):
        # +++ AWARD the lowest score of the week
        lowest = min(self.scores, key=attrgetter('score'))
        # Concatenate the lowest score award with sub-100 club if both apply
        if lowest.score < 100:
            self.awards[lowest.team_name].pop('SUB_100', None)
            lowest_award_string = f'ASSUME THE POSITION/SUB-100 CLUB - Lowest weekly score ({lowest.score})'
        else:
            lowest_award_string = f'ASSUME THE POSITION - Lowest weekly score ({lowest.score})'
        self.award(lowest.team_name, lowest_award_string, 'LOWEST')

    def award_fortunate_son(self):
        # +++ AWARD the lowest scoring winner
        fort_son = min([x for x in self.scores if x.diff > 0], key=attrgetter('score'))
        if fort_son.score < 100:
            self.awards[fort_son.team_name].pop('SUB_100', None)
            fort_son_award_string = f'FORTUNATE SON/SUB-100 CLUB - Lowest scoring winner ({fort_son.score})'
        else:
            fort_son_award_string = f'FORTUNATE SON - Lowest scoring winner ({fort_son.score})'
        self.award(fort_son.team_name, fort_son_award_string, 'FORT_SON')

    def award_tough_luck(self):
        # +++ AWARD the highest scoring loser
        tough_luck = max([x for x in self.scores if x.diff < 0], key=attrgetter('score'))
        self.award(tough_luck.team_name, f'TOUGH LUCK - Highest scoring loser ({tough_luck.score})', 'TOUGH_LUCK')

    def award_total_domination(self):
        # +++ AWARD the largest margin of victory
        big_margin = max(self.scores, key=attrgetter('diff'))
        self.award(big_margin.team_name,
                   f'TOTAL DOMINATION - Beat opponent by largest margin ({big_margin.vs_owner} '
                   f'by {round(big_margin.diff, 2)})',
                   'BIG_MARGIN')

    def award_second_banana(self):
        # +++ AWARD team that lost with the smallest margin of victory
        small_margin = min([x for x in self.scores if x.diff > 0], key=attrgetter('diff'))
        self.award(small_margin.vs_team_name,
                   f'SECOND BANANA - Beaten by slimmest margin ({get_first_name(small_margin.owner)} '
                   f'by {round(small_margin.diff, 2)})',
                   'SMALL_MARGIN_LOSER')
        # +++ AWARD team that won with the smallest margin of victory
        self.award(small_margin.team_name,
                   f'GEEKED FOR THE EKE - Beat opponent by slimmest margin ({small_margin.vs_owner} '
                   f'by {round(small_margin.diff, 2)})',
                   'SMALL_MARGIN')

    def award_minority_report(self):
        # +++ AWARD the best manager who scored most of available points from roster
        potential_high = max(self.scores, key=attrgetter('potential_used'))
        self.award(potential_high.team_name,
                   f'MINORITY REPORT - Scored {potential_high.get_potential_used()} '
                   f'of possible {potential_high.potential_high} points',
                   'POTENTIAL_HIGH')

    def award_none_crystal(self):
        # +++ AWARD the worst manager who scored least of available points from roster
        potential_low = min(self.scores, key=attrgetter('potential_used'))
        self.award(potential_low.team_name,
                   f'GOT BALLS - NONE CRYSTAL - Scored {potential_low.get_potential_used()} '
                   f'of possible {potential_low.potential_high} points',
                   'POTENTIAL_LOW')

    def award_caller_baller(self):
        # Individual player awards
        # +++ AWARD QB high
        qb_high = self.compute_top_scorer(self.players['QB'])
        self.award(qb_high.team_name, f'PLAY CALLER BALLER - QB high ({qb_high.get_last_name()}, {qb_high.score})',
                   'QB_HIGH', qb_high.score * 10)

    def award_tightest_end(self):
        # +++ AWARD TE high
        te_high = self.compute_top_scorer(self.players['TE'])
        self.award(te_high.team_name, f'TIGHTEST END - TE high ({te_high.get_last_name()}, {te_high.score})', 'TE_HIGH',
                   te_high.score * 10)

    def award_fort_knox(self):
        # +++ AWARD D/ST high
        d_st_high = self.compute_top_scorer(self.players['D/ST'])
        self.award(d_st_high.team_name, f'FORT KNOX - D/ST high ({d_st_high.name}, {d_st_high.score})', 'D_ST_HIGH',
                   d_st_high.score * 10)

    def award_kick_fast(self):
        # +++ AWARD Compute K high
        k_high = self.compute_top_scorer(self.players['K'])
        self.award(k_high.team_name, f'KICK FAST, EAT ASS - Kicker high ({k_high.get_last_name()}, {k_high.score})',
                   'K_HIGH', k_high.score * 10)

    def award_ground_delivery(self):
        # +++ AWARD individual RB high
        rb_high = self.compute_top_scorer(self.players['RB'])
        self.award(rb_high.team_name,
                   f'SPECIAL DELIVERY: GROUND - RB high ({rb_high.get_last_name()}, {round(rb_high.score, 2)})',
                   'RB_HIGH', rb_high.score * 100)

    def award_air_delivery(self):
        # +++ AWARD individual WR high
        wr_high = self.compute_top_scorer(self.players['WR'])
        self.award(wr_high.team_name,
                   f'SPECIAL DELIVERY: AIR - WR high ({wr_high.get_last_name()}, {round(wr_high.score, 2)})', 'WR_HIGH',
                   wr_high.score * 100)

    def award_deep_threat(self):
        # +++ AWARD WR corps high
        wr_total_high = self.compute_top_scorer(self.players['WR'], True)
        self.award(wr_total_high.team_name, f'DEEP THREAT - WR corps high ({round(wr_total_high.score, 2)})',
                   'WR_HIGH', wr_total_high.score)

    def award_on_his_backs(self):
        # +++ AWARD RB corps high
        rb_total_high = self.compute_top_scorer(self.players['RB'], True)
        self.award(rb_total_high.team_name,
                   f'PUT THE TEAM ON HIS BACKS - RB corps high ({round(rb_total_high.score, 2)})', 'RB_HIGH',
                   rb_total_high.score)

    def award_big_bench(self):
        # +++ AWARD bench total high
        bench_total_high = max(self.scores, key=attrgetter('bench_total'))
        self.award(bench_total_high.team_name,
                   f'BIGLY BENCH - Bench total high ({round(bench_total_high.bench_total, 2)})', 'BIG_BENCH')

    def award_biggest_mistake(self):
        # +++ AWARD worst start/sit mistake
        biggest_mistake = max(self.mistakes, key=attrgetter('diff'))
        self.award(biggest_mistake.team_name,
                   f'BIGGEST MISTAKE - Starting {biggest_mistake.get_mistake_first()} ({biggest_mistake.score}) over '
                   f'{biggest_mistake.get_mistake_second()} ({biggest_mistake.second_score})',
                   'IND_LOW')

    def award_crash_burn(self):
        # +++ AWARD player who scored the least of projected
        crash_burn = min(self.crashes, key=attrgetter('score'))
        self.award(crash_burn.team_name,
                   f'CRASH AND BURN - Lowest scoring non-special-teams starter ({crash_burn.name}, {crash_burn.score})',
                   'IND_LOW', 10)

    def award_rookie_cookie(self):
        # +++ AWARD starting rookie who scored the most points
        rookie_cookie = max(self.rookies, key=attrgetter('score'))
        self.award(rookie_cookie.team_name, f'ROOKIE GETS A COOKIE - Highest scoring starting rookie '
                                            f'({rookie_cookie.name}, {rookie_cookie.score})',
                   'ROOKIE_COOKIE')

    def award_upsets(self):
        # Get last week's rankings to calculate any upsets
        old_rank_col = chr(MAGIC_ASCII_OFFSET + WEEK)
        values_old_rank = self.sheets.get_sheet_values('HISTORY!' + old_rank_col + '2:' + old_rank_col + '13')
        if not values_old_rank:
            print('Last week\'s rankings don\'t exist for some reason?')
        else:
            k = 0
            dict_of_old_ranks = {}
            for team_name in self.teams:
                dict_of_old_ranks[team_name] = int(values_old_rank[k][0])
                k += 1

            lowest_winner, low_rank, high_rank = None, None, None
            for score in self.scores:
                dif = dict_of_old_ranks[score.team_name] - dict_of_old_ranks[score.vs_team_name]
                if score.diff > 0 and dif >= 3:
                    high_rank = dict_of_old_ranks[score.team_name]
                    low_rank = dict_of_old_ranks[score.vs_team_name]
                    lowest_winner = score
            if lowest_winner is not None:
                self.award(lowest_winner.team_name,
                           f'PUNCHING ABOVE YOUR WEIGHT - {get_first_name(lowest_winner.owner)} ranked {high_rank} '
                           f'beat {lowest_winner.vs_owner} ranked {low_rank}',
                           'LOSS')

            # Get this week's forecasted rankings to see if there is a new leader or a new bitch, or if rank changed 3+
            new_rank_col = chr(MAGIC_ASCII_OFFSET + WEEK + 1)
            values_new_rank = self.sheets.get_sheet_values('HISTORY!' + new_rank_col + '2:' + new_rank_col + '13')
            if not values_new_rank:
                print('This week\'s rankings haven\'t been calculated yet.')
            else:
                j = 0
                for team_name in self.teams:
                    score = next(score for score in self.scores if score.team_name == team_name)
                    # +++ AWARD newly top-ranked team
                    if values_new_rank[j][0] == '1' and dict_of_old_ranks[team_name] != 1:
                        self.award(team_name,
                                   f'I, FOR ONE, WELCOME OUR NEW {get_first_name(score.owner).upper()} '
                                   f'OVERLORD - New top ranked team ',
                                   'RANK')
                    elif values_new_rank[j][0] == '12' and dict_of_old_ranks[team_name] != 12:
                        self.award(team_name,
                                   f'BITCH OF THE WEEK - New lowest ranked team',
                                   'RANK')
                    # Calculate rank diff from last week to this week
                    fid = dict_of_old_ranks[team_name] - int(values_new_rank[j][0])
                    if abs(fid) > 2:
                        # +++ AWARD teams who fell 3+ spots in the rankings
                        if fid < 0:
                            self.award(team_name, f'FREE FALLIN\' - Dropped {fid} spots in the rankings',
                                       'FREE_FALL')
                        # +++ AWARD teams who rose 3+ spots in the rankings
                        else:
                            self.award(team_name, f'TO THE MOON! - Rose {fid} spots in the rankings', 'TO_MOON')
                    j += 1

    def award_streaks(self):
        # Calculate current streak and streak changes for each team
        for team in self.league.teams:
            # Use the current streak on the team class if we are at the current week, otherwise calculate
            if team.outcomes[WEEK] != 'U':
                streak_type = team.outcomes[WEEK - 1]
                streak_length = 1
                for i in range(WEEK - 2, 1, -1):
                    if team.outcomes[i] == streak_type:
                        streak_length += 1
                    else:
                        break
            else:
                streak_type = team.streak_type[0]
                streak_length = team.streak_length
            # Whatever the current streak type is, the one previously must have been the opposite
            old_streak_type = 'W' if streak_type == 'L' else 'L'
            old_streak_length = 1
            # Start from the week previous to the beginning of the current streak to compute the previous streak
            for i in range(WEEK - streak_length - 2, 0, -1):
                if team.outcomes[i] == old_streak_type:
                    old_streak_length += 1
                # If the previous streak has ended, break
                else:
                    break
            # If the current streak is more than 2 games
            if streak_length > 2:
                if streak_type == 'W':
                    self.award(team.team_name, f'IT HAS HAPPENED BEFORE - {streak_length} game winning streak',
                               'W_STREAK')
                else:
                    self.award(team.team_name,
                               f'CAN\'T GET MUCH WORSE THAN THIS - {streak_length} game losing streak', 'L_STREAK')
            # If the current streak snapped a previously significant streak
            elif team.streak_length == 1:
                if old_streak_length > 2:
                    if old_streak_type == 'L':
                        self.award(team.team_name, f'NOBODY BEATS ME {old_streak_length + 1} TIMES IN A ROW - '
                                                   f'Snapped {old_streak_length} game losing streak', 'SNAP_L')
                    else:
                        self.award(team.team_name,
                                   f'POBODY\'S NERFECT - Broke {old_streak_length} game winning streak (finally)',
                                   'SNAP_W')

    # Compute the highest scorer for given list of players
    def compute_top_scorer(self, players, grouped_stat=False):
        filtered_dict = {}
        # Make a dictionary of team_name -> sum of scores from starters
        for team_name in self.teams:
            # Compute the highest scoring player on each team
            winner = max([player for player in players if player.team_name == team_name], key=attrgetter('score'))
            filtered_dict[team_name] = winner
            if grouped_stat:
                # If a stat that counts multiple players, reassign to the sum instead of a single player's score
                filtered_dict[team_name] = FantasyPlayer(winner.name, winner.team_name, sum(
                    player.score for player in players if player.team_name == team_name))
        # Return player(s) with highest score
        return max(filtered_dict.values(), key=attrgetter('score'))

    # Compare starter's score to top scorer at that position and award if benched player outperformed starter
    def compute_start_sit(self, roster, pos, team_name, diff):
        lineup_slot = pos[0]
        if len(pos) > 1:
            lineup_slot = '/'.join(pos)
        # Make list of starting players at given position
        starters = [player for player in roster if player.lineupSlot == lineup_slot]
        # Make list of benched players at given position
        benched_players = [player for player in roster if player.lineupSlot in BENCHED and
                           player.position in lineup_slot]
        # Find the lowest scoring starter
        starter = min(starters, key=attrgetter('points'))
        # Find the highest scoring benched player
        benched_player = max(benched_players, key=attrgetter('points')) if len(benched_players) > 0 else None
        # If the team in question lost their matchup and benched player who scored better than the worst starter
        if benched_player is not None and diff < 0 and benched_player.points > starter.points:
            print(starter.name + ' ' + benched_player.name)
            self.mistakes.append(
                FantasyPlayer(benched_player.name + '.' + starter.name, team_name, benched_player.points,
                              starter.points))
            # +++ AWARD teams for starting the wrong player by a margin =< the amount they lost by
            if benched_player.points >= abs(diff) + starter.points:
                return (f'BLUNDER - Started {starter.name} ({starter.points}) over {benched_player.name} '
                        f'({benched_player.points}) (lost by {round(abs(diff), 2)})',
                        (benched_player.points - starter.points) * 10)
            # +++ AWARD teams for starting the wrong player by a significant amount
            elif (starter.injuryStatus in HEALTHY
                  and benched_player.points >= starter.points * 2
                  and benched_player.points >= starter.points + 5):
                return (f'START/SIT, GET HIT - Started {starter.name} ({starter.points}) over {benched_player.name} '
                        f'({benched_player.points})', benched_player.points - starter.points)

    # Add awards with proper weighting to global self.awards
    def award(self, team_name, award_string, award_type, magnitude=0):
        best = self.awards[team_name].get(award_type)
        # If there is no award of that type or if the new one exceeds the existing one, add the new one
        if best is None or magnitude > best.magnitude:
            self.awards[team_name][award_type] = FantasyAward(award_string, team_name, magnitude)

    # Print all awards
    def print_awards(self):
        i = 1
        for team_name in self.teams:
            print(f'{i}) {team_name}')
            awards = self.awards[team_name].values()
            for award in awards:
                if (len(awards) <= 4
                        or award.award_string != (
                                'LOST IN THE SAUCE - No non-special-teams starter scored 3+ more than projected')):
                    print(award.award_string)
            i += 1
            print()


service = FantasyService()

service.generate_awards()
