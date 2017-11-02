#!/usr/bin/python3
import pywikibot
from pywikibot.data.sparql import SparqlQuery
import requests
import datetime
import re
import jdcal
import sys
from optparse import OptionParser

# Are we testing or are we for real?
TEST = False
COMMIT = True
"""
This bot does the following:
for the specified set of items, for properties that
have start/end time qualifiers, and only one current (start time, no end time)
claim that claim is made preferred
"""
if TEST:
    site = pywikibot.Site("test", "wikidata")
    START_TIME = 'P355'
    END_TIME = 'P356'
    DEATH_DATE = 'P570'
    ABOLISHED = 'P576'
    start_end_props = ['P141']
    point_props = ['P1082']
else:
    START_TIME = 'P580'
    END_TIME = 'P582'
    DEATH_DATE = 'P570'
    ABOLISHED = 'P576'
    POINT_IN_TIME = 'P585'
    site = pywikibot.Site("wikidata", "wikidata")

STANDARD_CALENDAR = 'http://www.wikidata.org/entity/Q1985727'
JULIAN_CALENDAR = 'http://www.wikidata.org/entity/Q1985786'

LOGPAGE = "User:PreferentialBot/Log/"
qregex = re.compile('{{Q|(Q\d+)}}')
repo = site.data_repository()

parser = OptionParser()
parser.add_option("-p", "--prop", dest="prop",
                  help="Only work on this property", metavar="P123")
parser.add_option("-l", "--limit", dest="limit",
                  help="LIMIT in SPARQL query", default=10, type="int", metavar="NUM")
parser.add_option("-f", "--force", dest="force", action="store_true",
                  help="Force run even if there are too many bad ones. Will not record errors to log.")
parser.add_option("-w", "--wait", dest="wait",
                  help="Bot wait period", type="int", metavar="NUM")
parser.add_option("-b", "--bad", dest="bad",
                  help="How many bad items to allow?", default=30, type="int", metavar="NUM")

(options, args) = parser.parse_args()

if options.wait:
    site.throttle.setDelays(writedelay=options.wait)

START_END_QUERY = """
PREFIX q: <http://www.wikidata.org/prop/qualifier/>
SELECT DISTINCT ?s WHERE {
  BIND (p:%s as ?prop)
  ?s ?prop ?st .
# One claim with start time
  ?st q:P580 ?t .
# and no end time
  OPTIONAL { ?st q:P582 ?t2 }
  FILTER(!bound(?t2))
  ?st wikibase:rank wikibase:NormalRank.
# it's best rank, i.e. no preferred
  ?st a wikibase:BestRank .
# Another claim
  ?s ?prop ?st2 .
  FILTER(?st2 != ?st)
# with an end time
  ?st2 q:P582 ?t3 .
# and it's not a dead person
  OPTIONAL { ?s wdt:P570 ?d }
  FILTER(!bound(?d))
# and not abolished
  OPTIONAL { ?s wdt:P576 ?ab }
  FILTER(!bound(?ab))
# and no end time
  OPTIONAL { ?s wdt:P582 ?et }
  FILTER(!bound(?et))
# st2 is normal rank
  ?st2 wikibase:rank wikibase:NormalRank.
  %s
} LIMIT %d
"""

POINT_QUERY = """
PREFIX q: <http://www.wikidata.org/prop/qualifier/>
SELECT DISTINCT ?s WHERE {
  BIND (p:%s as ?prop)
  ?s ?prop ?st .
# One claim with point-in-time
  ?st q:P585 ?t .
# Normal rank
  ?st wikibase:rank wikibase:NormalRank.
  ?st a wikibase:BestRank .
# Another claim
  ?s ?prop ?st2 .
  FILTER(?st2 != ?st)
# with an end time
  ?st2 q:P585 ?t3 .
# and it's not a dead person
  OPTIONAL { ?s wdt:P570 ?d }
  FILTER(!bound(?d))
# and not abolished
  OPTIONAL { ?s wdt:P576 ?ab }
  FILTER(!bound(?ab))
# st2 is normal rank and normal is best
  ?st2 wikibase:rank wikibase:NormalRank.
  ?st2 a wikibase:BestRank .
  %s
} LIMIT %d
"""

sparql_query = SparqlQuery()

def get_items(query, prop, bad_ids=[]):
# Query asks for items with normal-ranked statement with start date
# and no end date, more than one statement on the same property
# and not date of death for this item
    if len(bad_ids) > 0:
        id_filter = "MINUS { VALUES ?s { %s } }" % ' '.join(["wd:"+q for q in bad_ids if q ])
    else:
        id_filter = ''

    dquery = query % (prop, id_filter, options.limit)
#    print(dquery)

    return sparql_query.get_items(dquery, item_name="s")

def load_page(page):
    page.modifiedByBot = False
    return set(qregex.findall(page.text))

def log_item(page, item, reason):
    print("%s on %s" %(reason, item))
    if page.text.find(item+"}}") != -1:
        # already there
        return
    page.text = page.text.strip() + "\n* {{Q|%s}} %s" % (item, reason)
    page.modifiedByBot = True
    pass

"""
Test entities for P6:
wd:Q5870
wd:Q148
wd:Q5906
wd:Q6441
wd:Q10483
wd:Q1718
wd:Q826
wd:Q891
wd:Q2948
wd:Q3936
"""
"""
Too many bad entries:
P54: member of the sports team
P102: member of political party
P131: located in the administrative territorial entity
?P286: head coach?
P195: collection
P551: residence
P579: IMA status and/or rank
"""
"""
P6: head of government
P17: country
P26: spouse
P35: head of state
P36: capital
P41: flag image
P94: coat of arms image
P115: home venue
P118: league
P123: publisher
P126: maintained by
P138: named after
P154: logo image
P159: headquarters location
P169: chief executive officer
P176: manufacturer
P237: coat of arms
P286: head coach
P289: vessel class
P300: ISO 3166-2 code
P449: original network
P484: IMA Number, broad sense
P488: chairperson
P505: general manager
P579: IMA status and/or rank
P598: commander of
P605: NUTS code
P625: coordinate location
P708: diocese
P749: parent company
P879: pennant number
P964: Austrian municipality key
P969: located at street address
P1037: manager/director
P1075: rector
P1308: officeholder
P1435: heritage status
P1448: official name
P1454: legal form
P1476: title
P1705: native label
P1813: short name
P1998: UCI code
P2978: wheel arrangement
"""
"""
point in time:
P348: software version
P1082: population
P1114: quantity
P1538: number of households
P1539: female population
P1540: male population
P1831: electorate
P2046: area
P2124: member count
P2196: students count
P2403: total assets
P2139: total revenue
P2295: net profit
P3362: operating income
P4080: number of houses
"""

if not TEST:
    start_end_props = [
               'P131',
               'P41', 'P26', 'P6', 'P17', 'P35', 'P36', 'P94', 'P115', 'P118', 'P123', 'P126', 'P138', 'P154', 'P159', 'P169',
               'P176', 'P237', 'P289', 'P300', 'P449', 'P484', 'P488', 'P505', 'P598', 'P605', 'P625', 'P708', 'P749', 'P879',
               'P964', 'P969', 'P1037', 'P1075', 'P1308', 'P1435', 'P1448', 'P1454', 'P1476', 'P1705', 'P1813', 'P1998', 'P2978'
    ]
    point_props = [
               'P348', 'P1082', 'P1114', 'P1538', 'P1539', 'P1540', 'P1831', 'P2046', 'P1833',  'P2124', 'P2196', 'P2403',
               'P2139', 'P2295', 'P3362', 'P4080'
    ]

if options.prop:
    prop = options.prop
    if prop in start_end_props:
        start_end_props = [prop]
        point_props = []
    elif prop in point_props:
        start_end_props = []
        point_props = [prop]
    else:
        raise Exception("Unknown option " + prop)
    print("Doing only %s" % prop)

# Check if this item is ok to process
def check_item(prop, item, itemID):
    if prop not in item.claims:
        print("Hmm, no %s for %s" % (prop, itemID))
        return False

    if DEATH_DATE in item.claims:
        log_item(logpage, itemID, "Death date specified, skipping")
        return False
    if ABOLISHED in item.claims:
        log_item(logpage, itemID, "Abolished date specified, skipping")
        return False
    if END_TIME in item.claims:
        log_item(logpage, itemID, "End date specified, skipping")
        return False

    if len(item.claims[prop]) < 2:
        # if there are less than two, no reason to bother
        print("Sole %s for %s, don't bother" % (prop, itemID))
        return False
    foundPreferred = False
    for statement in item.claims[prop]:
        if statement.rank == 'preferred':
        # if there's already preferred statement here, we should not intervene
            foundPreferred = True
            break
    if foundPreferred:
        print("Already have preference for %s on %s, skip" % (prop, itemID))
        return False
    return True

def convert_calendar(value, to_cal):
    if value.calendarmodel == JULIAN_CALENDAR and to_cal == STANDARD_CALENDAR:
        if value.precision < 10:
            # No sense to convert for year-precision and lower
            value.calendarmodel = STANDARD_CALENDAR
            return value
        if value.year and value.month and value.day and value.precision >= 11:
    # Convert Julian to Standard
            jday = jdcal.gcal2jd(value.year, value.month, value.day)
            jdate = jdcal.jd2jcal(*jday)
            return pywikibot.WbTime(year=jdate[0], month=jdate[1], day=jdate[2], precision=value.precision, calendarmodel=STANDARD_CALENDAR)
    return value

########## Point in time

for prop in point_props:
    logpage = pywikibot.Page(site, LOGPAGE+prop)
    baditems = load_page(logpage)
    if not options.force and len(baditems) > options.bad:
        print("Too many bad items for %s (%d > %d), skipping" % (prop, len(baditems), options.bad))
        continue
    if TEST:
        items = ["Q10402"]
    else:
        items = get_items(POINT_QUERY, prop, baditems)
    print("Property %s items %s" % (prop, items))
    for itemID in items:
        if itemID in baditems:
            print("Known bad item %s, skip" % itemID)
            continue

        item = pywikibot.ItemPage(repo, itemID)
        item.get()

        if not check_item(prop, item, itemID):
            continue
        maxDate = datetime.date(datetime.MINYEAR, 1, 1)
        maxClaim = None
        for statement in item.claims[prop]:
            if POINT_IN_TIME not in statement.qualifiers:
                log_item(logpage, itemID, "Missing point-in-time qualifier")
                maxClaim = None
                break
            q = statement.qualifiers[POINT_IN_TIME][0]
            if q.getSnakType() != 'value':
                log_item(logpage, itemID, "Invalid point-in-time value type")
                maxClaim = None
                break
            value = q.getTarget()
            if value.calendarmodel != repo.calendarmodel():
            # Try to convert
                value = convert_calendar(value, repo.calendarmodel())
            if value.calendarmodel != repo.calendarmodel():
                log_item(logpage, itemID, "Non-standard calendar: %s" % value.calendarmodel)
                maxClaim = None
                break
            if not (datetime.MINYEAR <= value.year <= datetime.MAXYEAR):
                log_item(logpage, itemID, "Date out of range")
                maxClaim = None
                break
            #print(value)
            if value.month == 2 and value.day > 29:
                value.day = 29
            if value.month in [4, 6, 9, 11] and value.day > 30:
                value.day = 30
            vdate = datetime.date(value.year, value.month or 1, value.day or 1)
            if vdate > maxDate:
                maxDate = vdate
                maxClaim = statement
        if maxClaim:
            print("Marking %s on %s:%s as preferred " % (maxClaim.snak, itemID, prop))
            if COMMIT:
                result = maxClaim.changeRank('preferred')
    if not options.force and logpage.modifiedByBot:
        logpage.save("log for "+prop)

########### Start/end pairs

for prop in start_end_props:
    logpage = pywikibot.Page(site, LOGPAGE+prop)
    baditems = load_page(logpage)
    if not options.force and len(baditems) > options.bad:
        print("Too many bad items for %s (%d > %d), skipping" % (prop, len(baditems), options.bad))
        continue
    if TEST:
        items = ["Q826"]
    else:
        items = get_items(START_END_QUERY, prop, baditems)
    print("Property %s items %s" % (prop, items))
    for itemID in items:
        if itemID in baditems:
            print("Known bad item %s, skip" % itemID)
            continue

        item = pywikibot.ItemPage(repo, itemID)
        item.get()

        if not check_item(prop, item, itemID):
            continue

        bestRanked = []
        for statement in item.claims[prop]:
            if START_TIME not in statement.qualifiers:
                if END_TIME in statement.qualifiers and statement.qualifiers[END_TIME][0].getSnakType() != 'novalue':
                    # has end time, then allow not to have start time
                    continue
                # no start or more than one start - this one is weird
                log_item(logpage, itemID, "Missing start qualifier")
                bestRanked = []
                break
            if len(statement.qualifiers[START_TIME])>1:
                if END_TIME in statement.qualifiers and len(statement.qualifiers[START_TIME]) == len(statement.qualifiers[END_TIME]):
                    # multi matching start-ends are ok
                    continue
                log_item(logpage, itemID, "Multiple start qualifiers")
                bestRanked = []
                break
            if END_TIME in statement.qualifiers:
                if len(statement.qualifiers[END_TIME])>1:
                    log_item(logpage, itemID, "Multiple end qualifiers")
                    # more than one end - weird, skip it
                    bestRanked = []
                    break
                q = statement.qualifiers[END_TIME][0]
                if q.getSnakType() != 'novalue':
                    # skip those that have end values - these are not preferred ones
                    continue
            # has start but no end - that's what we're looking for
            if statement.rank == 'normal':
                bestRanked.append(statement)

        if(len(bestRanked) > 1):
            print("Multiple bests on %s:%s, skip for now" % (itemID, prop))
            log_item(logpage, itemID, "Multiple best statements")
            continue
        for statement in bestRanked:
            print("Marking %s on %s:%s as preferred " % (statement.snak, itemID, prop))
            if COMMIT:
                result = statement.changeRank('preferred')
    if logpage.modifiedByBot and not options.force:
        logpage.save("log for "+prop)

