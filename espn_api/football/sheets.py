import os.path
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import requests

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

ROS_RANKING_URI = 'https://mpbnfl.fantasypros.com/api/getLeagueAnalysisJSON?key=nfl~021c6923-33f0-4763-a84a-6327f62fded2&period=ros'
WEEKLY_RANKING_URI = 'https://mpbnfl.fantasypros.com/api/getLeagueAnalysisJSON?key=nfl~021c6923-33f0-4763-a84a-6327f62fded2&period=week'

MAGIC_ASCII_OFFSET = 66

COMMENTS_RANGE_OUTPUT = 'COMMENTS!B1:B12'
POINTS_LETTER_OUTPUT = 'POINTS!B1'
WINS_RANGE_OUTPUT = 'POINTS!C18:C29'
WEEKLY_RANKINGS_RANGE_OUTPUT = 'POINTS!Q18:Q29'
ROS_RANKINGS_RANGE_OUTPUT = 'POINTS!P18:P29'
TEAM_NAMES_RANGE, TEAM_NAMES_RANGE_OUTPUT = 'TEAMS!B3:B14', 'TEAMS!B3:B14'
OWNER_NAMES_RANGE = 'TEAMS!C3:C14'
HISTORY_RANKINGS_RANGE = 'TEAMS!D3:D14'
WINS_RANGE = 'POINTS!B18:C29'


class GoogleSheetService:
    def __init__(self, scores, week, spreadsheet_id):
        self.scores = scores
        self.week = week
        self.spreadsheet_id = spreadsheet_id

        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open("token.json", "w") as token:
                    token.write(creds.to_json())

        self.service = build("sheets", "v4", credentials=creds)
        # Call the Sheets API
        self.sheet = self.service.spreadsheets()

        # GET current owners and team names
        owners = self.get_sheet_values(OWNER_NAMES_RANGE)
        if not owners:
            print('No data found in while updating team names.')

        # Match up current owners with most recent team names from ESPN
        new_team_names = []
        for row in owners:
            team_name = next(score for score in scores if score.owner == row[0]).team_name
            new_team_names.append([team_name])

        # UPDATE team names in sheet
        print('Updating team names!')
        self.update_sheet_values(TEAM_NAMES_RANGE_OUTPUT, new_team_names)
        print()

        self.teams = self.get_sheet_values(TEAM_NAMES_RANGE_OUTPUT)

    # GET values from Google Sheet from given range
    def get_sheet_values(self, range_input):
        try:
            result = (self.sheet.values()
                      .get(spreadsheetId=self.spreadsheet_id, range=range_input).execute())
            return result.get("values", [])
        except HttpError as error:
            print(f'An error occurred: {error}')

    # UPDATE Google Sheet for given range with given values
    def update_sheet_values(self, range_output, values):
        try:
            body = {"values": values}
            result = (self.service.spreadsheets()
                      .values()
                      .update(
                spreadsheetId=self.spreadsheet_id,
                range=range_output,
                valueInputOption='USER_ENTERED',
                body=body).execute())
            print(f'{result.get('updatedCells')} cells updated.')

        except HttpError as err:
            print(f'An error occurred: {err}')

    def tues_morn(self, do_sheets_calls, wins):
        self.update_weekly_column(do_sheets_calls)
        self.update_weekly_scores(do_sheets_calls)
        self.update_wins(do_sheets_calls, wins)

    def wed_morn(self, do_sheets_calls):
        self.get_weekly_roster_rankings(do_sheets_calls)
        self.get_ros_roster_rankings(do_sheets_calls)
        self.update_previous_week(do_sheets_calls)

    def final(self, do_sheets_calls, awards):
        self.update_comments(do_sheets_calls, awards)

    # GET previous weeks rankings and UPDATE them in HISTORY of sheet
    def update_previous_week(self, do_sheets_calls):
        rankings = self.get_sheet_values(HISTORY_RANKINGS_RANGE)
        if not rankings:
            print('No data found.')
            return

        rankings_list = []
        for rank in rankings:
            rankings_list.append([rank[0]])

        if do_sheets_calls:
            print('Updating rankings from last week!')
            prev_rank_col = chr(MAGIC_ASCII_OFFSET + self.week + 1)
            prev_rank_output = 'HISTORY!' + prev_rank_col + '2:' + prev_rank_col + '13'
            self.update_sheet_values(prev_rank_output, rankings_list)
        else:
            print('No update sheets calls have been authorized: update_previous_week')

    # UPDATE new column letter in sheet
    def update_weekly_column(self, do_sheets_calls):
        if do_sheets_calls:
            print('Updating singular letter to represent column!')
            pts_char_col = chr(MAGIC_ASCII_OFFSET + self.week)
            self.update_sheet_values(POINTS_LETTER_OUTPUT, [[pts_char_col]])
        else:
            print('No update sheets calls have been authorized: update_weekly_column')

    # UPDATE weekly scores in new column for each team in sheet
    def update_weekly_scores(self, do_sheets_calls):
        pts_col = chr(MAGIC_ASCII_OFFSET + self.week)
        pts_output = 'POINTS!' + pts_col + '3:' + pts_col + '14'
        score_list = []
        for row in self.teams:
            team_score = next(score for score in self.scores if score.team_name == row[0]).score
            score_list.append([team_score])

        if do_sheets_calls:
            print('Updating this week\'s scores!')
            self.update_sheet_values(pts_output, score_list)
        else:
            print('No update sheets calls have been authorized: update_weekly_scores')

    # GET team order of win total and UPDATE win total for winning teams in sheet
    def update_wins(self, do_sheets_calls, wins):
        if do_sheets_calls:
            print('Updating the win counts!')
            self.update_sheet_values(WINS_RANGE_OUTPUT, wins)
        else:
            print('No update sheets calls have been authorized: update_wins')

    # GET weekly or RoS roster rankings from FantasyPros
    def get_fantasy_pros_rankings(self, uri):
        data = requests.get(uri)
        if not data.ok:
            print(f'An error occurred when fetching rankings from FantasyPros {uri}: ' + data.reason)
        else:
            rankings_list = []
            for row in self.teams:
                for team in data.json()['standings']:
                    if row[0] == team['teamName']:
                        num = round(float(team['percentAsNumber']) * 100)
                        rankings_list.append([num])
            return rankings_list

    # GET weekly roster ranking scores from FantasyPros and UPDATE weekly roster ranking scores in sheet
    def get_weekly_roster_rankings(self, do_sheets_calls):
        rankings_list = self.get_fantasy_pros_rankings(WEEKLY_RANKING_URI)
        if do_sheets_calls and rankings_list is not None:
            print('Updating weekly roster rankings from FantasyPros!')
            self.update_sheet_values(WEEKLY_RANKINGS_RANGE_OUTPUT, rankings_list)
        else:
            print('No update sheets calls have been authorized: get_weekly_roster_rankings')

    # GET RoS roster ranking scores from FantasyPros and UPDATE RoS roster rankings scores in sheet
    def get_ros_roster_rankings(self, do_sheets_calls):
        rankings_list = self.get_fantasy_pros_rankings(ROS_RANKING_URI)
        if do_sheets_calls and rankings_list is not None:
            print('Updating RoS roster rankings from FantasyPros!')
            self.update_sheet_values(ROS_RANKINGS_RANGE_OUTPUT, rankings_list)
        else:
            print('No update sheets calls have been authorized: get_weekly_roster_rankings')

    # UPDATE comment values in sheet
    def update_comments(self, do_sheets_calls, awards):
        award_list = []
        for row in self.teams:
            award_string = ''
            ctr = len(awards[row[0]].values()) - 1
            for award in awards[row[0]].values():
                ctr_string = '\n' if ctr > 0 else ''
                award_string += award.award_string + ctr_string
                ctr -= 1
            award_list.append([award_string])

        if do_sheets_calls:
            print('Updating comments!')
            self.update_sheet_values(COMMENTS_RANGE_OUTPUT, award_list)
        else:
            print('No update sheets calls have been authorized: update_comments')
