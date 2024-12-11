![](https://github.com/cwendt94/espn-api/workflows/Espn%20API/badge.svg)
![](https://github.com/cwendt94/espn-api/workflows/Espn%20API%20Integration%20Test/badge.svg) [![codecov](https://codecov.io/gh/cwendt94/espn-api/branch/master/graphs/badge.svg)](https://codecov.io/gh/cwendt94/espn-api) [![Join the chat at https://gitter.im/ff-espn-api/community](https://badges.gitter.im/ff-espn-api/community.svg)](https://gitter.im/ff-espn-api/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge) [![PyPI version](https://badge.fury.io/py/espn-api.svg)](https://badge.fury.io/py/espn-api)<a target="_blank" href="https://www.python.org/downloads/" title="Python version"><img src="https://img.shields.io/badge/python-%3E=_3.8-teal.svg"></a>

## espn-api
This project is forked from [cwendt94/espn-api](https://github.com/cwendt94/espn-api).

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