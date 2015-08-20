#!/usr/bin/env python
# vim: ts=4 sw=4 et

import json
import VishnuBrowser
import datetime
import sys
import re

url = r"http://mlb.mlb.com/lookup/json/named.standings_schedule_date.bam?season=2014&schedule_game_date.game_date='%s'&sit_code='h0'&league_id=103&league_id=104&all_star_sw='N'&version=2"

class MLBTicker:
    def __init__(self, browser):
        self.browser = browser

    def get_standings(self, name="BOS"):
        today = datetime.date.today().strftime("%Y/%m/%d")
        thisurl = url % today

        f = self.browser.open(thisurl)
        mlb = json.loads(f.read())

        standings = mlb['standings_schedule_date']['standings_all_date_rptr']['standings_all_date']

        for league in standings:
            league = league['queryResults']['row']
            for team in league:
                if team['team_abbrev'] == name.upper():
                    return {
                        'record' : "%s-%s" % (team['w'], team['l']),
                        'pct' :  team['pct'],
                        'streak' : team['streak'],
                        'place' : team['place'],
                        'name' : team['team_full'],
                        'l10' : team['last_ten'],
                        'division' : team['division'],
                        'gb' : team['gb'],
                        'gb_wildcard' : team['gb_wildcard'],
                    }

    def get_ticker(self, name):
        st = self.get_standings(name)

        if not st:
            return "%s: No such team abbreviation" % name

        if float(st['pct']) > 0.5:
            color = '\\\\g'
        else:
            color = '\\\\r'

        place = st['place']
        gb = None
        if 'gb' in st:
            gb = st['gb']
        if place != "":
            if int(place) != 1:
                gb = st['gb']
            if place == "1":
                place = "1st"
            elif place == "2":
                place = "2nd"
            elif place == "3":
                place = "3rd"
            else:
                place += "th"
        else:
            place = "??"

        division = st['division']
        division = division.replace("American League", "AL")
        division = division.replace("National League", "NL")

        ret = "%s%s: %s, %s %s (L10: %s Streak: %s" % \
               (color, st['name'], st['record'], place, division, \
                st['l10'], st['streak'])
        if gb:
            ret += " %s/%s GB" % (gb, st['gb_wildcard'])
        ret += ")"

        return ret



if __name__ == '__main__':
    browser = VishnuBrowser.VishnuBrowser()
    mlb = MLBTicker(browser)

    for team in sys.argv[1:]:
        print mlb.get_ticker(team)
