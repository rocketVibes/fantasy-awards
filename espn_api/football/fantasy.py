from espn_api.football import League



from operator import attrgetter
from collections import defaultdict
from espn_api.football import Google_Sheet_Service

import google.auth
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
import requests

TREND_RANGE = 'A3:J25'

# Flatten list of team scores as they come in box_score format
class Fantasy_Team_Performance:
	def __init__(self, team_name, owner, score, point_differential, vs_team_name, vs_owner, lineup, bench_total):
		self.team_name = team_name
		self.owner = owner['firstName'] + ' ' + owner['lastName']
		self.score = score
		self.diff = point_differential
		self.vs_team_name = vs_team_name
		self.vs_owner = vs_owner
		self.lineup = lineup
		self.bench_total = bench_total

	def set_potential(self, potential_high):
		self.potential_high = potential_high
		self.potential_used = self.score / potential_high

	def get_first_name(self):
		return self.owner.split(' ', 1)[0]

	def get_potential_used(self):
		return '{:,.2%}'.format(self.potential_used)

class Fantasy_Player:
	def __init__(self, name, team_name, score, second_score=0):
		self.name = name
		self.team_name = team_name
		self.score = score
		self.second_score = second_score
		self.diff = self.score - self.second_score

	def get_last_name(self):
		return self.name.split(None, 1)[1]

	def get_first_name(self):
		return self.name.split(None, 1)[0]

	def get_mistake_first(self):
		return self.name.split('.', 1)[0]

	def get_mistake_second(self):
		return self.name.split('.', 1)[1]

class Fantasy_Award:
	def __init__(self, award_string, team_name, magnitude=None):
		self.award_string = award_string
		self.team_name = team_name
		self.magnitude = magnitude

class Fantasy_Service:
	def __init__(self):
		# Hardcode league ID and year
		self.league = League(306883, 2024)
		self.awards = defaultdict(dict)
		self.scores, self.qbs, self.tes, self.ks, self.wrs, self.rbs, self.dsts, self.mistakes = [], [], [], [], [], [], [], []
		self.week = 9

		# Iterating over matchups
		for matchup in self.league.box_scores(week=self.week):
			# Calculate the difference between home and away scores
			home = matchup.home_team
			away = matchup.away_team

			self.process_matchup(matchup.home_lineup, home.team_name, matchup.home_score, matchup.away_score, home.owners[0], away.team_name, away.owners[0]['firstName'])
			self.process_matchup(matchup.away_lineup, away.team_name, matchup.away_score, matchup.home_score, away.owners[0], home.team_name, home.owners[0]['firstName'])
		
		self.sheets = Google_Sheet_Service()
		self.teams = self.sheets.teams

		self.sheets.update_team_names(True, self.scores)

	# Process team performances to be iterable
	def process_matchup(self, lineup, team_name, score, opp_score, owner_name, vs_team_name, vs_owner):
		lost_in_the_sauce = True
		award_list, aw_list = [], []
		diff = score - opp_score

		# +++ AWARD teams who didn't make it to 100 points
		if score < 100:
			self.award(team_name, f'SUB-100 CLUB ({score})', 'SUB_100')
		for pos in [['QB'], ['K'], ['D/ST'], ['RB'], ['WR'], ['TE']]:
			start_sit = self.compute_start_sit(lineup, pos, pos, team_name, diff)
			if start_sit != '':
				self.award(team_name, start_sit[0], 'IND_LOW', start_sit[1])

		start_sit = self.compute_start_sit(lineup, ['WR', 'TE'], ['WR/TE'], team_name, diff)
		if start_sit != '':
			self.award(team_name, start_sit[0], 'IND_LOW', start_sit[1])

		bench_total = 0

		for player in lineup:
			# Make pile of all players to iterate over 	
			new_player = Fantasy_Player(player.name, team_name, player.points)
			if player.points >= 40:
				self.award(team_name, f'40 BURGER ({player.name}, {player.points})', player.lineupSlot + '_HIGH', player.points * 1000)
			if player.lineupSlot == 'BE' or player.lineupSlot == 'IR':
				bench_total += player.points
			if diff < 0 and player.lineupSlot not in ['BE', 'IR']:
				if player.injuryStatus not in ['ACTIVE', 'NORMAL']:
					self.award(team_name, f'INJURY TO INSULT - ({player.name}, {player.points})', 'INJURY')
			if player.lineupSlot not in ['K', 'BE', 'D/ST', 'IR']:
				# If any players scored 3+ more than projected, the team is not lost in the sauce
				if player.points >= player.projected_points + 3:
					lost_in_the_sauce = False

				# +++ AWARD players who scored 2x projected
				if player.points > 0 and player.injuryStatus in ['ACTIVE', 'NORMAL'] and player.points >= 2 * player.projected_points:
					self.award(team_name, f'DAILY DOUBLE - {player.name} scored >2x projected ({player.points}, {player.projected_points} projected)', player.lineupSlot + '_HIGH', player.points)

				# +++ AWARD players who didn't get hurt but scored nothing
				if player.injuryStatus in ['ACTIVE', 'NORMAL'] and player.points == 0:
					self.award(team_name, f'OUT OF OFFICE - ({player.name}, 0)', 'IND_LOW')

			# Compile lists of players at each position
			match player.lineupSlot:
				case 'QB':
					self.qbs.append(new_player)
					ints = 0 if player.stats[self.week]['breakdown'].get('passingInterceptions') == None else player.stats[self.week]['breakdown']['passingInterceptions']
					tds = 0 if player.stats[self.week]['breakdown'].get('passingTouchdowns') == None else player.stats[self.week]['breakdown']['passingTouchdowns']
				
					# +++ AWARD if any starting QBs had equal num of TDs and INTs
					if ints != 0 and tds == ints:
						plural = 's' if tds > 1 else ''
						self.award(team_name, f'PERFECTLY BALANCED - {player.name} threw {int(tds)} TD{plural} and {int(ints)} INT{plural}', 'QB_MID')
				case 'TE':
					self.tes.append(new_player)
				case 'K':
					self.ks.append(new_player)
					# +++ AWARD kickers who somehow didn't score any points
					if player.injuryStatus in ['ACTIVE', 'NORMAL'] and player.points == 0:
						self.award(team_name, f'GO KICK ROCKS - Kicker scored 0', 'K_LOW')
				case 'RB':
					self.rbs.append(new_player)
				case 'WR':
					self.wrs.append(new_player)
				case 'WR/TE':
					self.wrs.append(new_player)
				case 'D/ST':
					self.dsts.append(new_player)
					# +++ AWARD defenses who sucked
					if player.points < 2:
						self.award(team_name, f'THE BEST DEFENSE IS A GOOD OFFENSE - ({player.name}, {player.points})', 'D_ST_LOW')
		
		new_performance = Fantasy_Team_Performance(team_name, owner_name, score, diff, vs_team_name, vs_owner, lineup, bench_total)
		self.scores.append(new_performance)
		new_performance.set_potential(self.compute_potential(lineup, team_name, diff))

		# +++ AWARD team whose players didn't exceed projected amount by 3+
		if lost_in_the_sauce: 
			self.award(team_name, 'LOST IN THE SAUCE - No non-special-teams starter scored 3+ more than projected', 'TEAM_LOW')

	# Iterate over scores and teams to generate awards for each team
	def generate_awards(self):
		# Score-based awards
		# +++ AWARD highest score of the week
		highest = max(self.scores, key=attrgetter('score'))
		self.award(highest.team_name, f'BOOM GOES THE DYNAMITE - Highest weekly score ({highest.score})', 'HIGHEST')

		# +++ AWARD lowest score of the week 
		lowest = min(self.scores, key=attrgetter('score'))
		self.award(lowest.team_name, f'ASSUME THE POSITION - Lowest weekly score ({lowest.score})', 'LOWEST')
	
		# +++ AWARD lowest scoring winner
		fort_son = min([x for x in self.scores if x.diff > 0], key=attrgetter('score'))
		self.award(fort_son.team_name, f'FORTUNATE SON - Lowest scoring winner ({fort_son.score})', 'FORT_SON')

		# +++ AWARD highest scoring loser
		tough_luck = max([x for x in self.scores if x.diff < 0], key=attrgetter('score'))
		self.award(tough_luck.team_name, f'TOUGH LUCK - Highest scoring loser ({tough_luck.score})', 'TOUGH_LUCK')

		# +++ AWARD largest margin of victory
		big_margin = max(self.scores, key=attrgetter('diff'))
		self.award(big_margin.team_name, f'TOTAL DOMINATION - Beat opponent by largest margin ({big_margin.vs_owner} by {round(big_margin.diff, 2)})', 'BIG_MARGIN')

		# +++ AWARD team that lost with smallest margin of victory
		small_margin = min([x for x in self.scores if x.diff > 0], key=attrgetter('diff'))
		self.award(small_margin.vs_team_name, f'SECOND BANANA - Beaten by slimmest margin ({small_margin.get_first_name()} by {round(small_margin.diff, 2)})', 'SMALL_MARGIN_LOSER')
		
		# +++ AWARD team that won with smallest margin of victory
		self.award(small_margin.team_name, f'GEEKED FOR THE EKE - Beat opponent by slimmest margin ({small_margin.vs_owner} by {round(small_margin.diff, 2)})', 'SMALL_MARGIN')

		# +++ AWARD best manager who scored most of available points from roster
		potential_high = max(self.scores, key=attrgetter('potential_used'))
		self.award(potential_high.team_name, f'MINORITY REPORT - Scored highest percentage of possible points from roster ({potential_high.get_potential_used()} of {potential_high.potential_high})', 'POTENTIAL_HIGH')
		
		# +++ AWARD worst manager who scored least of available points from roster
		potential_low = min(self.scores, key=attrgetter('potential_used'))
		self.award(potential_low.team_name, f'GOT BALLS - NONE CRYSTAL - Scored lowest percentage of possible points from roster ({potential_low.get_potential_used()} of {potential_low.potential_high})', 'POTENTIAL_LOW')
		
		# Individual player awards
		# +++ AWARD QB high
		qb_high = self.compute_top_scorer(self.qbs)
		self.award(qb_high.team_name, f'PLAY CALLER BALLER - QB high ({qb_high.get_last_name()}, {qb_high.score})', 'QB_HIGH', qb_high.score * 10)

		# +++ AWARD TE high
		te_high = self.compute_top_scorer(self.tes)
		self.award(te_high.team_name, f'TIGHTEST END - TE high ({te_high.get_last_name()}, {te_high.score})', 'TE_HIGH', te_high.score * 10)

		# +++ AWARD D/ST high
		d_st_high = self.compute_top_scorer(self.dsts)
		self.award(d_st_high.team_name, f'FORT KNOX - D/ST high ({d_st_high.name}, {d_st_high.score})', 'D_ST_HIGH', d_st_high.score * 10)

		# +++ AWARD Compute K high
		k_high = self.compute_top_scorer(self.ks)
		self.award(k_high.team_name, f'KICK FAST, EAT ASS - Kicker high ({k_high.get_last_name()}, {k_high.score})', 'K_HIGH', k_high.score * 10)

		# +++ AWARD individual RB high
		rb_high = self.compute_top_scorer(self.rbs)
		self.award(rb_high.team_name, f'SPECIAL DELIVERY: GROUND - RB high ({rb_high.get_last_name()}, {round(rb_high.score, 2)})', 'RB_HIGH', rb_high.score * 100)
		
		# +++ AWARD individual WR high
		wr_high = self.compute_top_scorer(self.wrs)
		self.award(wr_high.team_name, f'SPECIAL DELIVERY: AIR - WR high ({wr_high.get_last_name()}, {round(wr_high.score, 2)})', 'WR_HIGH', wr_high.score * 100)

		# +++ AWARD WR corps high
		wr_total_high = self.compute_top_scorer(self.wrs, True)
		if wr_total_high.team_name != wr_high.team_name:
			self.award(wr_total_high.team_name, f'DEEP THREAT - WR corps high ({round(wr_total_high.score, 2)})', 'WR_HIGH')

		# +++ AWARD RB corps high
		rb_total_high = self.compute_top_scorer(self.rbs, True)
		if rb_total_high.team_name != rb_high.team_name:
			self.award(rb_total_high.team_name, f'PUT THE TEAM ON HIS BACKS - RB corps high ({round(rb_total_high.score, 2)})', 'RB_HIGH')

		# +++ AWARD RB corps high
		bench_total_high = max(self.scores, key=attrgetter('bench_total'))
		self.award(bench_total_high.team_name, f'BIGLY BENCH - Bench total high ({round(bench_total_high.bench_total, 2)})', 'BIG_BENCH')

		biggest_mistake = max(self.mistakes, key=attrgetter('diff'))
		self.award(biggest_mistake.team_name, f'BIGGEST MISTAKE - Starting {biggest_mistake.get_mistake_first()} ({biggest_mistake.score}) over {biggest_mistake.get_mistake_second()} ({biggest_mistake.second_score})', 'IND_LOW')

		self.do_sheet_awards()

		i = 1
		for team_name in self.teams:
			print(f'{i}) {team_name[0]}')
			awards = self.awards[team_name[0]].values()
			for award in awards:
				if len(awards) <= 4 or award.award_string != 'LOST IN THE SAUCE - No non-special-teams starter scored 3+ more than projected':
					print(award.award_string)
			i += 1
			print()

	# Add awards with proper weighting to global self.awards
	def award(self, team_name, award_string, award_type, magnitude=0):
		best = self.awards[team_name].get(award_type)
		if best == None:
			self.awards[team_name][award_type] = Fantasy_Award(award_string, team_name, magnitude)
		elif (magnitude > best.magnitude):
			self.awards[team_name][award_type] = Fantasy_Award(award_string, team_name, magnitude)

	# GET trends for each team generated by sheet for ranking-trend-based awards
	def do_sheet_awards(self):
		values = self.sheets.get_sheet_values(TREND_RANGE)
		if not values:
			print("No data found.")
			return
		
		i = 0
		for row in values:
			if i % 2 == 0:
				if len(row) > 0 and len(row[3]) == 2 and int(row[3][1]) > 2:
					if '▼' in row[3]:
						self.award(row[1].split('\n', 1)[0], 'FREE FALLIN\' - Dropped 3 spots in the rankings', 'FREE_FALL')
					else:
						self.award(row[1].split('\n', 1)[0], 'TO THE MOON! - Rose 3 spots in the rankings', 'TO_MOON')
			i += 1

	# Compute highest scorer for given list of players
	def compute_top_scorer(self, players, grouped_stat=False):
		filtered_dict = {}

		# Make a dictionary of team_name -> sum of scores from starters
		for team in self.league.teams:
			total = 0
			winner = max([player for player in players if player.team_name == team.team_name], key=attrgetter('score'))
			filtered_dict[team.team_name] = winner
			if grouped_stat:
				# Add up the scores of like positions
				total = sum(player.score for player in players if player.team_name == team.team_name)
				filtered_dict[team.team_name] = Fantasy_Player(winner.name, winner.team_name, total)
		
		# Return player(s) with highest score
		return max(filtered_dict.values(), key=attrgetter('score'))

	# Compute a team's potential highest score given perfect start/sit decisions
	def compute_potential(self, lineup, team_name, diff):
		roster = lineup.copy()
		total_potential = 0

		# Add individual contributors that don't need to be removed
		for pos in [['QB'], ['K'], ['D/ST'], ['RB'], ['RB'], ['TE'], ['WR'], ['WR'], ['WR', 'TE', 'WR/TE']]:
			best_player = max([player for player in roster if player.position in pos], key=attrgetter('points'))
			total_potential += best_player.points
			roster.remove(best_player)

		return round(total_potential, 2)

	# Compare starter's score at a given position to the top scorer at that position on the team and award if benched player scored significantly higher
	def compute_start_sit(self, roster, pos, lineup_slot, team_name, diff):
		starters = [player for player in roster if player.lineupSlot in lineup_slot]
		benched_players = [player for player in roster if player.lineupSlot in ['BE', 'IR'] and player.position in pos]
		award = ''
		play = max(benched_players, key=attrgetter('points')) if len(benched_players) > 0 else None
		starter = min(starters, key=attrgetter('points'))

		if play != None:
			if diff < 0 and play.points >= abs(diff) + starter.points:
				award = (f'BLUNDER - Starting {play.name} ({play.points}) over {starter.name} ({starter.points}) would have been enough to win (lost by {round(abs(diff), 2)})', (play.points - starter.points) * 10)
			elif diff < 0 and starter.injuryStatus in ['ACTIVE', 'NORMAL'] and play.points >= starter.points * 2 and play.points >= starter.points + 5:
				award = (f'START/SIT, GET HIT - Started {starter.name} ({starter.points}) over {play.name} ({play.points})', play.points - starter.points)
			if play.points > starter.points:
				self.mistakes.append(Fantasy_Player(play.name + '.' + starter.name, team_name, play.points, starter.points))
		return award
# _____________________________________________________________________________________________________________________________________________________________________________________________________________________
# _____________________________________________________________________________________________________________________________________________________________________________________________________________________
# _____________________________________________________________________________________________________________________________________________________________________________________________________________________
# _____________________________________________________________________________________________________________________________________________________________________________________________________________________

service = Fantasy_Service()
service.generate_awards()

# sheets.update_weekly_column(True)
# sheets.update_weekly_scores(True)
# sheets.update_wins(True)

# sheets.get_weekly_roster_rankings(True)
# sheets.get_ros_roster_rankings(True)
# sheets.update_comments(True)

# sheets.update_previous_week(True)

# 0) tues morning: change week number to current week 
# 1) tues morning: run generate awards, copy to keep 
# 2) tues morning: run update_weekly_column, update_weekly_scores, update_wins
# 3) thursday morning: run get_weekly_roster_rankings, get_ros_roster_rankings
# 4) thursday morning: run do_sheet_awards via generate_awards, update_comments
# 5) thursday morning: run update_previous_week
