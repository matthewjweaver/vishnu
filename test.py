#!/usr/local/bin/python
import time
def timeAgo(then_tm, now_tm):
    ago = ""

    seconds = now_tm.tm_sec - then_tm.tm_sec
    minutes = now_tm.tm_min - then_tm.tm_min
    hours   = now_tm.tm_hour - then_tm.tm_hour
    days    = now_tm.tm_mday - then_tm.tm_mday
    months  = now_tm.tm_mon  - then_tm.tm_mon
    years   = now_tm.tm_year - then_tm.tm_year

    # We want all positives, so lets make it go
    if seconds < 0:
        seconds += 60
        minutes -= 1

    if minutes < 0:
        minutes += 60
        hours -= 1

    if hours < 0:
        hours += 24
        days -= 1

    if days < 0:
        if now_tm.tm_mon == 4 or now_tm.tm_mon == 6 or now_tm.tm_mon == 9 or now_tm.tm_mon == 11:
            days += 30
        elif now_tm.tm_mon == 2:
            if now_tm.tm_year % 4 == 0 and now_tm.tm_year % 100 != 0:
                days += 29
            else:
                days += 28
        else:
            days += 31
            months -= 1

    if months < 0:
        months += 12
        years -= 1

    if years > 0:
        hours = minutes = seconds = 0
        ago = str(years) + "y"

    if months > 0:
        hours = minutes = seconds = 0
        if ago != "":
            ago += ", "

        ago += str(months) + "m"

    if days > 0:
        minutes = seconds = 0
        if ago != "":
            ago += ", "

        ago += str(days) + "d"

    if hours > 0:
        seconds = 0
        if ago != "":
            ago += ", "

        ago += str(hours) + "h"

    if minutes > 0:
        if ago != "":
            ago += ", "

        ago += str(minutes) + "m"

    if seconds > 0:
        if ago != "":
            ago += ", "

        ago += str(seconds) + "s"
    else:
       	if ago == "":
          ago = "0s"

    ago += " ago"

    return ago


print timeAgo(time.localtime(time.time() - 8000), time.localtime(time.time()))
