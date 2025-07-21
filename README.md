![](https://github.com/cwendt94/espn-api/workflows/Espn%20API/badge.svg)
![](https://github.com/cwendt94/espn-api/workflows/Espn%20API%20Integration%20Test/badge.svg) [![codecov](https://codecov.io/gh/cwendt94/espn-api/branch/master/graphs/badge.svg)](https://codecov.io/gh/cwendt94/espn-api) [![Join the chat at https://gitter.im/ff-espn-api/community](https://badges.gitter.im/ff-espn-api/community.svg)](https://gitter.im/ff-espn-api/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) [![PyPI version](https://badge.fury.io/py/espn-api.svg)](https://badge.fury.io/py/espn-api)<a target="_blank" href="https://www.python.org/downloads/" title="Python version"><img src="https://img.shields.io/badge/python-%3E=_3.8-teal.svg"></a>

## espn-api
This project is forked from [cwendt94/espn-api](https://github.com/cwendt94/espn-api).

## Award Descriptions
### Team Score Awards
- **Cripple Fight** - If both teams' scores total to less than 150
- **Sub-100 Club** - If a team scores less than 100
- **Madden Rookie Mode** - Team beat opponent by 100+
- **Assume The Position** - Lowest team score of the week
- **Fortunate Son** - Lowest scoring winner
- **Tough Luck** - Highest scoring loser
- **Total Domination** - Won by largest margin
- **Second Banana** - Lost by slimmest margin
- **Geeked For The Eke** - Won by slimmest margin
- **Minority Report** - Scored highest percentage of possible points
- **Got Balls, None Crystal** - Scored lowest percentage of possible points

### Individual Player Highs
- **40 Burger** - If individual player scored 40+
- **Daily Double** - Individual player scores over 2x projected
- **Rookie Gets A Cookie** - Highest scoring rookie
- **Play Caller Baller** - Highest scoring QB
- **Fort Knox** - Highest scoring D/ST
- **Tightest End** - Highest Scoring TE
- **Kick Fast, Eat Ass** - Highest scoring K
- **Special Delivery: Ground** - Highest scoring individual RB
- **Special Delivery: Air** - Highest scoring individual WR

### Individual Player Lows
- **Injury To Insult** - If starting player has non-healthy status after games
- **Out Of Office** - Healthy player scored 0
- **Go Kick Rocks** - Kicker scored 0
- **The Best Defense is a Good Offense** - D/ST scored < 2
- **Lost In The Sauce** - No non-special teams player scored 3+ more than projected

### Player Group Highs
- **Deep Threat** - Highest scoring WR corps
- **Put The Team On His BACKS** - Highest scoring RB corps
- **Bigly Bench** - Highest bench total

### Individual player lows compared to benched
- **Blunder** - A benched player scored more than a starter + the difference the team lost by
- **Start/Sit, Get Hit** - A benched player scored more than 5 + 2*starter score
- **Biggest Mistake** - The biggest difference between benched player score and starter score
- **Crash And Burn** - Lowest scoring non-special-teams starter

### Ranking Awards
- **Punching Above Your Weight** - Winning team was ranked at least 3 places worse
- **I, For One, Welcome Our New [NAME] Overlord** - New top-ranked team
- **Bitch Of The Week** - New lowest-ranked team
- **Free Fallin'** - Dropped 3+ places in the rankings
- **To The Moon!** - Rose 3+ places in the rankings

### Streaks
- **It Has Happened Before** - 3+ game winning streak
- **Can't Get Much Worse Than This** - 3+ game losing streak
- **Nobody Beats Me [STREAK_LENGTH+1] Times In A Row** - Snapped 3+ game losing streak
- **Pobody's Nerfect** - Snapped 3+ game winning streak

## ESPN API
This package uses ESPN's Fantasy API to extract data from any public or private league for **Fantasy Football**.  
Please feel free to make suggestions, bug reports, and pull request for features or fixes!

This base of this project was inspired and based off of [rbarton65/espnff](https://github.com/rbarton65/espnff).

## Installing
With Git:
```
git clone https://github.com/ladyskynet/espn-api
cd espn-api
python3 setup.py install
```
With pip:
```
pip install espn_api
```

## Usage
### [For Getting Started and API details head over to the Wiki!](https://github.com/cwendt94/espn-api/wiki)
```python
# Football API
from espn_api.football import League
# Init
league = League(league_id=222, year=2024)
```

### Run Tests
```
python3 setup.py nosetests
```