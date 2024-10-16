from espn_api.football import League
from operator import attrgetter
from collections import defaultdict

# Flatten list of team scores as they come in box_score format
class Score:
	def __init__(self, team_name, owner, score, point_differential, vs_team_name, vs_owner):
		self.team_name = team_name
		self.owner = owner
		self.score = score
		self.diff = point_differential
		self.vs = vs_team_name
		self.vs_owner = vs_owner

class Top_Scorer:
	def __init__(self, name, team_name, score, pos):
		self.name = name
		self.team_name = team_name
		self.score = score
		self.pos = pos

class Fantasy_Service:
	def __init__(self):
		# Hardcode league ID and year
		self.league = League(306883, 2024)
		self.awards = defaultdict(list)
		self.players = []
		self.scores = []
		self.week = 6

	def generateAwards(self):
		# Iterating over matchups
		for matchup in self.league.box_scores(week=self.week):

			# Make pile of all players to iterate over 
			self.players += matchup.away_lineup + matchup.home_lineup

			diff = max([matchup.home_score, matchup.away_score]) - min([matchup.home_score, matchup.away_score])
			
			# Make new list of matchups to iterate over
			self.scores.append(Score(matchup.home_team.team_name, matchup.home_team.owners[0]['firstName'], matchup.home_score, diff, matchup.away_team.team_name, matchup.away_team.owners[0]['firstName']))
			self.scores.append(Score(matchup.away_team.team_name, matchup.away_team.owners[0]['firstName'], matchup.away_score, (0-diff), matchup.home_team.team_name, matchup.home_team.owners[0]['firstName']))

		# 1) Compute highest score of the week
		highest = max(self.scores, key=attrgetter('score'))
		self.award(highest.team_name, f'BOOM GOES THE DYNAMITE - Highest weekly score ({highest.score})')

		# 2) Compute lowest score of the week 
		lowest = min(self.scores, key=attrgetter('score'))
		self.award(lowest.team_name, f'ASSUME THE POSITION - Lowest weekly score ({lowest.score})')
	
		# 3) Compute lowest scoring winner
		fort_son = min([x for x in self.scores if x.diff > 0], key=attrgetter('score'))
		self.award(fort_son.team_name, f'FORTUNATE SON - Lowest scoring winner ({fort_son.score})')

		# 4) Compute highest scoring loser
		tough_luck = max([x for x in self.scores if x.diff < 0], key=attrgetter('score'))
		self.award(tough_luck.team_name, f'TOUGH LUCK - Highest scoring loser ({tough_luck.score})')

		# 5) Compute largest margin of victory
		big_margin = max(self.scores, key=attrgetter('diff'))
		self.award(big_margin.team_name, f'TOTAL DOMINATION - Beat opponent by largest margin ({big_margin.vs_owner} by {round(big_margin.diff, 2)})')

		# 6) Compute team that lost with smallest margin of victory
		small_margin = min([x for x in self.scores if x.diff > 0], key=attrgetter('diff'))
		self.award(small_margin.vs, f'SECOND BANANA - Beaten by slimmest margin ({small_margin.owner} by {round(small_margin.diff, 2)})')
		
		# 7) Compute team that won with smallest margin of victory
		self.award(small_margin.team_name, f'GEEKED FOR THE EKE - Beat opponent by slimmest margin ({small_margin.vs_owner} by {round(small_margin.diff, 2)})')

		for team in self.scores:
			# 8) Award teams who didn't make it to 100 points
			if team.score < 100:
				self.award(team.team_name, 'SUB-100 CLUB')

		# 9) Compute if any QBs had equal num of TDs and INTs
		for qb in [x for x in self.players if x.lineupSlot == 'QB']:
			ints = 0 if qb.stats[self.week]['breakdown'].get('passingInterceptions') == None else qb.stats[self.week]['breakdown']['passingInterceptions']
			tds = 0 if qb.stats[self.week]['breakdown'].get('passingTouchdowns') == None else qb.stats[self.week]['breakdown']['passingTouchdowns']
			if ints != 0 and tds == ints:
				plural = 's' if tds > 1 else ''
				award_string = f'PERFECTLY BALANCED - {qb.name} threw {int(tds)} TD{plural} and {int(ints)} INT{plural}'
				self.award(self.get_team_name_from_id(qb.onTeamId), award_string)

		# 10) Compute QB high
		qb_high = self.compute_high('QB', True)
		self.award(qb_high.team_name, f'PLAY CALLER BALLER: QB high ({qb_high.name.split()[1]}, {qb_high.score})')

		# 11) Compute TE high
		te_high = self.compute_high(['TE'], True)
		self.award(te_high.team_name, f'TIGHTEST END - TE high ({te_high.name.split()[1]}, {te_high.score})')

		# 12) Compute D/ST high
		d_st_high = self.compute_high(['D/ST'], True)
		self.award(d_st_high.team_name, f'FORT KNOX - D/ST high ({d_st_high.name}, {d_st_high.score})')

		# 13) Compute kicker high
		k_high = self.compute_high(['K'], True)
		self.award(k_high.team_name, f'KICK FAST, EAT ASS - Kicker high ({k_high.name.split()[1]}, {k_high.score})')

		# 14) Compute WR corps high
		wr_high = self.compute_high(['WR', 'WR/TE'])
		self.award(wr_high.team_name, f'DEEP THREAT - WR corps high ({wr_high.score})')

		# 15) Compute RB corps high
		rb_high = self.compute_high(['RB'])
		self.award(rb_high.team_name, f'PUT THE TEAM ON HIS BACKS - RB corps high ({rb_high.score})')

		# 16) Award defenses who went negative
		defenses = [x for x in self.players if x.lineupSlot == 'D/ST']
		for defense in defenses:
			if defense.points < 0:
				self.award(self.get_team_name_from_id(defense.onTeamId), f'THE BEST DEFENSE IS A GOOD OFFENSE - ({defense.name}, {defense.points}')

		# 17) Award players who didn't get hurt but scored nothing
		for player in self.players:
			if player.lineupSlot not in ['IR', 'BE', 'D/ST'] and player.injuryStatus == 'ACTIVE' and player.points == 0:
				self.award(self.get_team_name_from_id(player.onTeamId), f'OUT OF OFFICE - ({player.name}, 0)')

		# 18) Compute players who scored 2x projected
		daily_doubles = filter(lambda x: x.lineupSlot not in ['IR', 'BE', 'D/ST', 'K'] and x.points >= 2 * x.projected_points, self.players)
		for player in daily_doubles:
			dbl_award_string = f'DAILY DOUBLE - {player.name} scored >2x projected ({player.points}, {player.projected_points} projected)'
			self.award(self.get_team_name_from_id(player.onTeamId), dbl_award_string)

		self.print_awards()

	# Add award to dict of teams
	def award(self, team_name, award_string):
		self.awards[team_name].append(award_string)

	# Print all awards for each team
	def print_awards(self):
		for team_name in self.awards:
			print(team_name)
			for award in self.awards[team_name]:
				print(award)
			print()

	# Compute highest value for given position(s)
	def compute_high(self, pos, seek_player=False):

		# Compile list of players at position(s) pos
		filtered_players = [x for x in self.players if x.lineupSlot in pos]
		filtered_dict = {}

		# Make a dictionary of team_name -> sum of players at that position
		for team in self.league.teams:
			total = sum(player.points for player in filtered_players if player.onTeamId == team.team_id)
			filtered_dict[team.team_name] = total
		
		# Compute team with highest score
		team_name = max(filtered_dict, key=filtered_dict.get)
		player_name = self.get_player_name_from_score(team_name, filtered_dict[team_name], filtered_players) if seek_player else ''
		return Top_Scorer(player_name, team_name, filtered_dict[team_name], pos)

	# Attempt to match what player did the thing 
	def get_player_name_from_score(self, team_name, score, filtered_players):
		team = self.get_team_from_name(team_name)
		for player in filtered_players:
			if player.points == score and player.onTeamId == team.team_id:
				return player.name
		return ''

	# Get team name from team_id
	def get_team_name_from_id(self, team_id):
		return next((y.team_name for y in self.league.teams if y.team_id == team_id), None)

	# Get team from team name
	def get_team_from_name(self, team_name):
		return next((y for y in self.league.teams if y.team_name == team_name), None)

Fantasy_Service().generateAwards()
