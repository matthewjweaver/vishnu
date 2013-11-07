#!/usr/bin/env python
# vim:ts=4 sw=4 et:

import VishnuBrowser
from bs4 import BeautifulSoup
import re
import sys

names = {
    "BUF" : "Bills",
    "MIA" : "Dolphins",
    "NE"  : "Patriots",
    "NYJ" : "Jets",
    "BAL" : "Ravens",
    "CIN" : "Bengals",
    "CLE" : "Browns",
    "PIT" : "Steelers",
    "HOU" : "Texans",
    "IND" : "Colts",
    "JAX" : "Jaguars",
    "TEN" : "Titans",
    "DEN" : "Broncos",
    "KC"  : "Chiefs",
    "OAK" : "Raiders",
    "SD"  : "Chargers",
    "DAL" : "Cowboys",
    "NYG" : "Giants",
    "PHI" : "Eagles",
    "WAS" : "Redskins",
    "CHI" : "Bears",
    "DET" : "Lions",
    "GB"  : "Packers",
    "MIN" : "Vikings",
    "ATL" : "Falcons",
    "CAR" : "Panthers",
    "NO"  : "Saints",
    "TB"  : "Buccaneers",
    "ARI" : "Cardinals",
    "STL" : "Rams",
    "SF"  : "49ers",
    "SEA" : "Seahawks",
}

class NFLStandings:
    def __init__(self, source):
        self.conferences = []
        self.standings = { 'by-conf' : {}, 'by-team' : {} }

        s = BeautifulSoup(source)

        p = s.find('div', "yom-sports-phase-nav")
        for h in p.find_all("h4"):
            conf = h['class'][0].upper()
            self.conferences.append(conf)
            self.standings['by-conf'][conf] = {}

        cindex = 0
        last_division = None
        for t in p.find_all("table"):
            conf = self.conferences[cindex]
            division = t['summary']
            if division in self.standings['by-conf'][conf]:
                cindex += 1
            conf = self.conferences[cindex]

            for b in t.find_all("tbody"):
                for row in b.find_all('tr'):
                    team = {}
                    team['conference'] = conf
                    team['division'] = division

                    if division != last_division:
                        team['place'] = 1
                    else:
                        team['place'] = last_place + 1
                    last_place = team['place']

                    last_division = division
                    h = row.find("th")
                    sp = h.find("span")
                    team['abbrev'] = sp['class'][1].upper()
                    team['city'] = h.find('a').contents[1]
                    team['wins'] = 0
                    team['losses'] = 0

                    for col in row.find_all('td'):
                        if 'wins' in col['class']:
                            team['wins'] = int(col.contents[0])
                        if 'losses' in col['class']:
                            team['losses'] = int(col.contents[0])
                        if 'ties' in col['class']:
                            team['ties'] = int(col.contents[0])
                        if 'last-5-record' in col['class']:
                            team['l5'] = col.contents[0]
                        if 'streak' in col['class']:
                            team['streak'] = col.contents[0].replace('-', '')
                        if 'win-percentage' in col['class']:
                            team['pct'] = col.contents[0]

                    if team['pct'] == 'N/A':
                        team['pct'] = 0

                    team['name'] = names[team['abbrev']]

                    self.add_team(team)
                    del team


    def add_team(self, team):
        conf = team['conference']
        division = team['division']
        city = team['abbrev']
        place = team['place']

        self.standings['by-team'][city] = team
        if not division in self.standings['by-conf'][conf]:
            self.standings['by-conf'][conf][division] = {
                'by-team' : {},
                'by-place' : {}
            }
        self.standings['by-conf'][conf][division]['by-team'][city] = team
        self.standings['by-conf'][conf][division]['by-place'][place] = team

    def get_team(self, city):
        return self.standings['by-team'][city]

    def get_games_back(self, city):
        team = self.standings['by-team'][city]

        if team['place'] == 1:
            return 0

        conference = team['conference']
        division = team['division']

        leader = self.standings['by-conf'][conference][division]['by-place'][1]

        wins = leader['wins'] - team['wins']
        losses = leader['losses'] - team['losses']
        if 'ties' in leader:
            wins += leader['ties']/2
            losses += leader['ties']/2
        if 'ties' in team:
            wins -= team['ties']/2
            losses -= team['ties']/2

        return float(wins - losses) / 2 

class NFLTicker:
    url = "http://sports.yahoo.com/nfl/standings/"
    def __init__(self, browser):
        self.browser = browser

    def get_ticker(self, name):
        f = self.browser.open(self.url)
        html = f.read()

        st = NFLStandings(html)
        try:
            team = st.get_team(name)
            gb = st.get_games_back(name)
        except Exception, e:
            return "ERROR: %s" % str(e)

        if float(team['pct']) > 0.5:
            color = '\\\\g'
        else:
            color = '\\\\r'

        place = team['place']
        if place == 1:
            place = "1st"
        elif place == 2:
            place = "2nd"
        elif place == 3:
            place = "3rd"
        else:
            place = "%gth" % team['place']

        division = "%s %s" % (team['conference'], team['division'])

        record = "%g-%g" % (team['wins'], team['losses'])
        if 'ties' in team:
            record += "-%g" % team['ties']

        ret = "%s%s %s: %s, %s %s (L5: %s Streak: %s" % \
               (color, team['city'], team['name'], record, place, division, \
                team['l5'], team['streak'])
        if gb:
            ret += ", %g GB" % gb
        ret += ")"

        return ret

if __name__ == '__main__':
    browser = VishnuBrowser.VishnuBrowser()
    nfl = NFLTicker(browser)

    teams = ["NE"]
    if len(sys.argv) > 1:
        teams = sys.argv[1:]

    for team in teams:
        print nfl.get_ticker(team)
