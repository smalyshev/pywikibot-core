import pwb
import pywikibot
import httplib2
import urllib
import json
import re

# Are we testing or are we for real?
TEST = False
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
    props = ['P141']
else:
    START_TIME = 'P580'
    END_TIME = 'P582'
    site = pywikibot.Site("wikidata", "wikidata")

LOGPAGE = "User:PreferentialBot/Log/"
qregex = re.compile('{{Q|(Q\d+)}}')
repo = site.data_repository()

def get_items(prop):
    SPARQL = "http://wdqs-beta.wmflabs.org/bigdata/namespace/wdq/sparql?query="
    QUERY = """
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX q: <http://www.wikidata.org/prop/qualifier/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?s WHERE {
  ?s p:%s ?st .
  ?st q:P580 ?t .
  OPTIONAL { ?st q:P582 ?t2 }
  ?st wikibase:rank wikibase:NormalRank.
  FILTER(!bound(?t2))
  ?s p:%s ?st2 .
  FILTER(?st2 != ?st)
  OPTIONAL { ?s wdt:P570 ?d }
  FILTER(!bound(?d))
} LIMIT 10
"""
# Query asks for items with normal-ranked statement with start date
# and no end date, more than one statement on the same property
# and not date of death for this item
    dquery = SPARQL + urllib.quote(QUERY % (prop, prop))

    h = httplib2.Http(".cache")
    (resp, content) = h.request(dquery,
                            "GET",
                            headers={'cache-control':'no-cache',
                                     'Accept': 'application/sparql-results+json'
                            } )
    # print resp
    if not content or resp['status'] != '200':
        print "Query on %s failed" % prop
        print resp
        return []
    data = json.loads(content)
    items = []
    if 'results' in data:
        for r in data['results']['bindings']:
            items.append(r['s']['value'][31:])
    return items

def load_page(page):
    return set(qregex.findall(page.text))

def log_item(page, item, reason):
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
P6: head of government
P35: head of state
P39: position held
P176: manufacturer
P488: chairperson
P598: commander of
"""
if not TEST:
    props = [ 'P6', 'P35', 'P39', 'P176',  'P488', 'P598']

for prop in props:
    if TEST:
        items = [u"Q826"]
    else:
        items = get_items(prop)
    logpage = pywikibot.Page(site, LOGPAGE+prop)
    logpage.modifiedByBot = False
    baditems = load_page(logpage)
    print "Property %s items %s" % (prop, items)
    for itemID in items:
        if itemID in baditems:
            print "Known bad item %s, skip" % itemID
            continue

        item = pywikibot.ItemPage(repo, itemID)
        item.get()

        if prop not in item.claims:
            print "Hmm, no %s for %s" % (prop, itemID)
            continue

        if len(item.claims[prop]) < 2:
            # if there are less than two, no reason to bother
            print "Sole %s for %s, don't bother" % (prop, itemID)
            continue
        foundPreferred = False
        for statement in item.claims[prop]:
            if statement.rank == 'preferred':
                # if there's already preferred statement here, we should not intervene
                foundPreferred = True
                break
        if foundPreferred:
            print "Already have preference for %s on %s, skip" % (prop, itemID)
            break

        bestRanked = []
        for statement in item.claims[prop]:
            if START_TIME not in statement.qualifiers:
                if END_TIME in statement.qualifiers and statement.qualifiers[END_TIME][0].getSnakType() != 'novalue':
                    # has end time, then allow not to have start time
                    continue
                # no start or more than one start - this one is weird
                log_item(logpage, itemID, "Missing start qualifier")
                break
            if len(statement.qualifiers[START_TIME])>1:
                log_item(logpage, itemID, "Multiple start qualifiers")
                break
            if END_TIME in statement.qualifiers:
                if len(statement.qualifiers[END_TIME])>1:
                    log_item(logpage, itemID, "Multiple end qualifiers")
                    # more than one end - weird, skip it
                    break
                q = statement.qualifiers[END_TIME][0]
                if q.getSnakType() != 'novalue':
                    # skip those that have end values - these are not preferred ones
                    continue
            # has start but no end - that's what we're looking for
            if statement.rank == 'normal':
                bestRanked.append(statement)

        if(len(bestRanked) > 1):
            print "Multiple bests on %s:%s, skip for now" % (itemID, prop)
            log_item(logpage, itemID, "Multiple best statements")
            continue
        for statement in bestRanked:
            print "Marking %s on %s:%s as preferred " % (statement.snak, itemID, prop)
            result = statement.changeRank('preferred')
    if logpage.modifiedByBot:
        logpage.save("log for "+prop)

