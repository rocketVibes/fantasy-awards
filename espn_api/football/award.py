from espn_api.football import FantasyPlayer
from espn_api.football import FantasyAward
import os.path
import json
from operator import attrgetter
from collections import defaultdict

if os.path.exists('values.json'):
    with open('values.json') as f:
        values = json.load(f)

POSITIONS = values['positions']
HEALTHY = ['ACTIVE', 'NORMAL']
BENCHED = ['BE', 'IR']
awards = defaultdict(dict)
MAGIC_ASCII_OFFSET = 66


def award_blunder(team_name, benched_player, starter, diff):
    # +++ AWARD teams for starting the wrong player by a margin =< the amount they lost by
    if benched_player.points >= abs(diff) + starter.points:
        award(team_name,
              f'BLUNDER - Started {starter.name} ({starter.points}) over {benched_player.name} '
              f'({benched_player.points}) (lost by {round(abs(diff), 2)})', 'IND_LOW',
              (benched_player.points - starter.points) * 10)


def award_start_sit(team_name, benched_player, starter):
    # +++ AWARD teams for starting the wrong player by a significant amount
    if (starter.injuryStatus in HEALTHY and benched_player.points >= starter.points * 2
            and benched_player.points >= starter.points + 5):
        award(team_name,
              f'START/SIT, GET HIT - Started {starter.name} ({starter.points}) over {benched_player.name} '
              f'({benched_player.points})', 'IND_LOW', benched_player.points - starter.points)


def award_cripple_fight(team_name, vs_owner, score):
    if score < 150:
        award(team_name, f'CRIPPLE FIGHT - Matchup totaled {score} against {vs_owner}', 'CRIPPLE')


def award_sub_100(team_name, score):
    # +++ AWARD teams who didn't make it to 100 points
    if score < 100:
        award(team_name, f'SUB-100 CLUB ({score})', 'SUB_100')


def award_madden_rookie(team_name, vs_owner, diff):
    # +++ AWARD teams who beat their opponent by 100
    if diff >= 100:
        award(team_name, f'MADDEN ROOKIE MODE (beat {vs_owner} by {diff})', 'MADDEN')


def award_burgers(team_name, player):
    # +++ AWARD players who scored over 50
    for burger in [100, 90, 80, 70, 60, 50, 40]:
        if player.points >= burger:
            award(team_name, f'{burger} BURGER ({player.name}, {player.points})', player.lineupSlot + '_HIGH',
                  player.points * 1000)


def award_injury_insult(team_name, player, diff):
    if diff < 0 and player.lineupSlot not in BENCHED:
        # +++ AWARD players who were injured in-game
        if player.injuryStatus not in HEALTHY:
            award(team_name, f'INJURY TO INSULT - ({player.name}, {player.points})', 'INJURY')


def award_daily_double(team_name, player):
    # +++ AWARD players who scored 2x projected
    if player.points > 0 and player.injuryStatus in HEALTHY and player.points >= 2 * player.projected_points:
        award(team_name, f'DAILY DOUBLE - {player.name} scored >2x projected ({player.points}, '
                         f'{player.projected_points} projected)', player.lineupSlot + '_HIGH', player.points)


def award_out_of_office(team_name, player):
    # +++ AWARD players who didn't get hurt but scored nothing
    if player.injuryStatus in HEALTHY and player.lineupSlot != 'TE' and player.points == 0:
        award(team_name, f'OUT OF OFFICE - ({player.name}, 0)', 'IND_LOW', 1)


def award_kick_rocks(team_name, player):
    # +++ AWARD kickers who somehow didn't score any points
    if player.lineupSlot == 'K' and player.injuryStatus in HEALTHY and player.points == 0:
        award(team_name, f'GO KICK ROCKS - Kicker scored 0', 'K_LOW')


def award_best_defense(team_name, player):
    # +++ AWARD defenses who sucked
    if player.lineupSlot == 'D/ST' and player.points < 2:
        award(team_name, f'THE BEST DEFENSE IS A GOOD OFFENSE - ({player.name}, {player.points})', 'D_ST_LOW')


def award_lost_sauce(team_name, lost_in_the_sauce):
    # +++ AWARD team whose players didn't exceed projected amount by 3+
    if lost_in_the_sauce:
        award(team_name, 'LOST IN THE SAUCE - No non-special-teams starter scored 3+ more than projected',
              'TEAM_LOW')


def award_dynamite(scores):
    # Score-based awards
    # +++ AWARD the highest score of the week
    highest = max(scores, key=attrgetter('score'))
    award(highest.team_name, f'BOOM GOES THE DYNAMITE - Highest weekly score ({highest.score})', 'HIGHEST')


def award_assume_position(scores):
    # +++ AWARD the lowest score of the week
    lowest = min(scores, key=attrgetter('score'))
    # Concatenate the lowest score award with sub-100 club if both apply
    if lowest.score < 100:
        awards[lowest.team_name].pop('SUB_100', None)
        lowest_award_string = f'ASSUME THE POSITION/SUB-100 CLUB - Lowest weekly score ({lowest.score})'
    else:
        lowest_award_string = f'ASSUME THE POSITION - Lowest weekly score ({lowest.score})'
    award(lowest.team_name, lowest_award_string, 'LOWEST')


def award_fortunate_son(scores):
    # +++ AWARD the lowest scoring winner
    fort_son = min([x for x in scores if x.diff > 0], key=attrgetter('score'))
    if fort_son.score < 100:
        awards[fort_son.team_name].pop('SUB_100', None)
        fort_son_award_string = f'FORTUNATE SON/SUB-100 CLUB - Lowest scoring winner ({fort_son.score})'
    else:
        fort_son_award_string = f'FORTUNATE SON - Lowest scoring winner ({fort_son.score})'
    award(fort_son.team_name, fort_son_award_string, 'FORT_SON')


def award_tough_luck(scores):
    # +++ AWARD the highest scoring loser
    tough_luck = max([x for x in scores if x.diff < 0], key=attrgetter('score'))
    award(tough_luck.team_name, f'TOUGH LUCK - Highest scoring loser ({tough_luck.score})', 'TOUGH_LUCK')


def award_total_domination(scores):
    # +++ AWARD the largest margin of victory
    big_margin = max(scores, key=attrgetter('diff'))
    award(big_margin.team_name,
          f'TOTAL DOMINATION - Beat opponent by largest margin ({big_margin.vs_owner} '
          f'by {round(big_margin.diff, 2)})',
          'BIG_MARGIN')


def award_second_banana(scores):
    # +++ AWARD team that lost with the smallest margin of victory
    small_margin = min([x for x in scores if x.diff > 0], key=attrgetter('diff'))
    award(small_margin.vs_team_name,
          f'SECOND BANANA - Beaten by slimmest margin '
          f'({get_first_name(small_margin.owner)} by {round(small_margin.diff, 2)})',
          'SMALL_MARGIN_LOSER')
    # +++ AWARD team that won with the smallest margin of victory
    award(small_margin.team_name,
          f'GEEKED FOR THE EKE - Beat opponent by slimmest margin ({small_margin.vs_owner} '
          f'by {round(small_margin.diff, 2)})',
          'SMALL_MARGIN')


def award_minority_report(scores):
    # +++ AWARD the best manager who scored most of available points from roster
    potential_high = max(scores, key=attrgetter('potential_used'))
    award(potential_high.team_name, f'MINORITY REPORT - Scored {potential_high.get_potential_used()} '
                                    f'of possible {potential_high.potential_high} points', 'POTENTIAL_HIGH')


def award_none_crystal(scores):
    # +++ AWARD the worst manager who scored least of available points from roster
    potential_low = min(scores, key=attrgetter('potential_used'))
    award(potential_low.team_name, f'GOT BALLS - NONE CRYSTAL - Scored {potential_low.get_potential_used()} '
                                   f'of possible {potential_low.potential_high} points', 'POTENTIAL_LOW')


def award_caller_baller(teams, quarterbacks):
    # +++ AWARD QB high
    qb_high = compute_top_scorer(teams, quarterbacks)
    award(qb_high.team_name, f'PLAY CALLER BALLER - QB high ({qb_high.get_last_name()}, {qb_high.score})',
          'QB_HIGH', qb_high.score * 10)


def award_tightest_end(teams, tight_ends):
    # +++ AWARD TE high
    te_high = compute_top_scorer(teams, tight_ends)
    award(te_high.team_name, f'TIGHTEST END - TE high ({te_high.get_last_name()}, {te_high.score})', 'TE_HIGH',
          te_high.score * 10)


def award_fort_knox(teams, defenses):
    # +++ AWARD D/ST high
    d_st_high = compute_top_scorer(teams, defenses)
    award(d_st_high.team_name, f'FORT KNOX - D/ST high ({d_st_high.name}, {d_st_high.score})', 'D_ST_HIGH',
          d_st_high.score * 10)


def award_kick_fast(teams, kickers):
    # +++ AWARD Compute K high
    k_high = compute_top_scorer(teams, kickers)
    award(k_high.team_name, f'KICK FAST, EAT ASS - Kicker high ({k_high.get_last_name()}, {k_high.score})',
          'K_HIGH', k_high.score * 10)


def award_ground_delivery(teams, running_backs):
    # +++ AWARD individual RB high
    rb_high = compute_top_scorer(teams, running_backs)
    award(rb_high.team_name, f'SPECIAL DELIVERY: GROUND - RB high ({rb_high.get_last_name()}, '
                             f'{round(rb_high.score, 2)})', 'RB_HIGH', rb_high.score * 100)


def award_air_delivery(teams, wide_receivers):
    # +++ AWARD individual WR high
    wr_high = compute_top_scorer(teams, wide_receivers)
    award(wr_high.team_name, f'SPECIAL DELIVERY: AIR - WR high ({wr_high.get_last_name()}, '
                             f'{round(wr_high.score, 2)})', 'WR_HIGH', wr_high.score * 100)


def award_deep_threat(teams, wide_receivers):
    # +++ AWARD WR corps high
    wr_total_high = compute_top_scorer(teams, wide_receivers, True)
    award(wr_total_high.team_name, f'DEEP THREAT - WR corps high ({round(wr_total_high.score, 2)})',
          'WR_HIGH', wr_total_high.score)


def award_on_his_backs(teams, running_backs):
    # +++ AWARD RB corps high
    rb_total_high = compute_top_scorer(teams, running_backs, True)
    award(rb_total_high.team_name,
          f'PUT THE TEAM ON HIS BACKS - RB corps high ({round(rb_total_high.score, 2)})', 'RB_HIGH',
          rb_total_high.score)


def award_big_bench(scores):
    # +++ AWARD bench total high
    bench_total_high = max(scores, key=attrgetter('bench_total'))
    award(bench_total_high.team_name,
          f'BIGLY BENCH - Bench total high ({round(bench_total_high.bench_total, 2)})', 'BIG_BENCH')


def award_biggest_mistake(mistakes):
    # +++ AWARD worst start/sit mistake
    biggest_mistake = max(mistakes, key=attrgetter('diff'))
    award(biggest_mistake.team_name,
          f'BIGGEST MISTAKE - Starting {biggest_mistake.get_mistake_first()} ({biggest_mistake.score}) over '
          f'{biggest_mistake.get_mistake_second()} ({biggest_mistake.second_score})',
          'IND_LOW')


def award_crash_burn(healthy_starters_who_scored_zero):
    # +++ AWARD player who scored the least of projected
    crash_burn = min(healthy_starters_who_scored_zero, key=attrgetter('score'))
    award(crash_burn.team_name,
          f'CRASH AND BURN - Lowest scoring non-special-teams starter ({crash_burn.name}, {crash_burn.score})',
          'IND_LOW', 10)


def award_rookie_cookie(rookies):
    # +++ AWARD starting rookie who scored the most points
    rookie_cookie = max(rookies, key=attrgetter('score'))
    award(rookie_cookie.team_name, f'ROOKIE GETS A COOKIE - Highest scoring starting rookie '
                                   f'({rookie_cookie.name}, {rookie_cookie.score})', 'ROOKIE_COOKIE')


def award_upsets(teams, scores, values_old_rank):
    k = 0
    dict_of_old_ranks = {}
    for team_name in teams:
        dict_of_old_ranks[team_name] = int(values_old_rank[k][0])
        k += 1
    lowest_winner, low_rank, high_rank = None, None, None
    for score in scores:
        dif = dict_of_old_ranks[score.team_name] - dict_of_old_ranks[score.vs_team_name]
        if score.diff > 0 and dif >= 3:
            high_rank = dict_of_old_ranks[score.team_name]
            low_rank = dict_of_old_ranks[score.vs_team_name]
            lowest_winner = score
    if lowest_winner is not None:
        award(lowest_winner.team_name,
              f'PUNCHING ABOVE YOUR WEIGHT - {get_first_name(lowest_winner.owner)} ranked {high_rank} '
              f'beat {lowest_winner.vs_owner} ranked {low_rank}',
              'LOSS')
    return dict_of_old_ranks


def award_new_top_bottom(teams, scores, values_new_rank, dict_of_old_ranks):
    j = 0
    for team_name in teams:
        score = next(score for score in scores if score.team_name == team_name)
        # +++ AWARD newly top-ranked team
        if values_new_rank[j][0] == '1' and dict_of_old_ranks[team_name] != 1:
            award(team_name,
                  f'I, FOR ONE, WELCOME OUR NEW {get_first_name(score.owner).upper()} '
                  f'OVERLORD - New top ranked team ',
                  'RANK')
        elif values_new_rank[j][0] == '12' and dict_of_old_ranks[team_name] != 12:
            award(team_name,
                  f'BITCH OF THE WEEK - New lowest ranked team',
                  'RANK')
        # Calculate rank diff from last week to this week
        fid = dict_of_old_ranks[team_name] - int(values_new_rank[j][0])
        if abs(fid) > 2:
            # +++ AWARD teams who fell 3+ spots in the rankings
            if fid < 0:
                award(team_name, f'FREE FALLIN\' - Dropped {abs(fid)} spots in the rankings',
                      'FREE_FALL')
            # +++ AWARD teams who rose 3+ spots in the rankings
            else:
                award(team_name, f'TO THE MOON! - Rose {fid} spots in the rankings', 'TO_MOON')
        j += 1


def award_streaks(teams, week):
    # Calculate current streak and streak changes for each team
    for team in teams:
        # Use the current streak on the team class if we are at the current week, otherwise calculate
        if team.outcomes[week] != 'U':
            streak_type = team.outcomes[week - 1]
            streak_length = 1
            for i in range(week - 2, 1, -1):
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
        for i in range(week - streak_length - 2, 0, -1):
            if team.outcomes[i] == old_streak_type:
                old_streak_length += 1
            # If the previous streak has ended, break
            else:
                break
        # If the current streak is more than 2 games
        if streak_length > 2:
            if streak_type == 'W':
                award(team.team_name, f'IT HAS HAPPENED BEFORE - {streak_length} game winning streak',
                      'W_STREAK')
            else:
                award(team.team_name,
                      f'CAN\'T GET MUCH WORSE THAN THIS - {streak_length} game losing streak', 'L_STREAK')
        # If the current streak snapped a previously significant streak
        elif team.streak_length == 1:
            if old_streak_length > 2:
                if old_streak_type == 'L':
                    award(team.team_name, f'NOBODY BEATS ME {old_streak_length + 1} TIMES IN A ROW - '
                                          f'Snapped {old_streak_length} game losing streak', 'SNAP_L')
                else:
                    award(team.team_name,
                          f'POBODY\'S NERFECT - Broke {old_streak_length} game winning streak (finally)',
                          'SNAP_W')


# Compute the highest scorer for given list of players
def compute_top_scorer(teams, players, grouped_stat=False):
    filtered_dict = {}
    # Make a dictionary of team_name -> sum of scores from starters
    for team_name in teams:
        # Compute the highest scoring player on each team
        winner = max([player for player in players if player.team_name == team_name], key=attrgetter('score'))
        filtered_dict[team_name] = winner
        if grouped_stat:
            # If a stat that counts multiple players, reassign to the sum instead of a single player's score
            filtered_dict[team_name] = FantasyPlayer(winner.name, winner.team_name, sum(
                player.score for player in players if player.team_name == team_name))
    # Return player(s) with highest score
    return max(filtered_dict.values(), key=attrgetter('score'))


# Add awards with proper weighting to global self.awards
def award(team_name, award_string, award_type, magnitude=0):
    best = awards[team_name].get(award_type)
    # If there is no award of that type or if the new one exceeds the existing one, add the new one
    if best is None or magnitude > best.magnitude:
        awards[team_name][award_type] = FantasyAward(award_string, team_name, magnitude)
