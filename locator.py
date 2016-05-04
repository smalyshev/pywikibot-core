import pywikibot
from pywikibot.data.sparql import SparqlQuery
from pywikibot.exceptions import CoordinateGlobeUnknownException

TEST = False

ENTITY_PREFIX = 'http://www.wikidata.org/entity/'
if TEST:
    site = pywikibot.Site("test", "wikidata")
    BODY = 'P734'
    LOCATION = 'P125'
else:
    site = pywikibot.Site("wikidata", "wikidata")
    BODY = 'P376'
    LOCATION = 'P625'

QUERY = """
SELECT ?item ?body ?globe
WHERE {
?item wdt:P376 ?body .
?item p:P625/psv:P625/wikibase:geoGlobe ?globe .
filter (?globe != ?body) .
} LIMIT 30
"""

sparql_query = SparqlQuery()
repo = site.data_repository()
globes = set(site.globes().values())

def log_item(itemID, message):
    print("[%s] %s" % (itemID, message))

if TEST:
    items = ['Q487']
else:
    items = sparql_query.get_items(QUERY, item_name='item')

print(items)
for itemID in items:
    item = pywikibot.ItemPage(repo, itemID)
    item.get()

    if LOCATION not in item.claims:
        log_item(itemID, "Location gone?")
        continue

    if BODY not in item.claims:
        log_item(itemID, "Hmm, no body claim, weird...")
        continue

    if len(item.claims[BODY]) > 1:
        log_item(itemID, "More than one body!")
        continue

    body = item.claims[BODY][0]
    if body.getSnakType() != 'value':
        log_item(itemID, "Body type is not value!")
        continue

    body_id = ENTITY_PREFIX + body.getTarget().title()
    if not TEST and body_id not in globes:
        log_item(itemID, "Unknown globe %s" % body_id)
        continue


    for coord in item.claims[LOCATION]:
        if coord.getSnakType() != 'value':
            log_item(itemID, "Location not a value")
            continue
        coordValue = coord.getTarget()
        if coordValue.entity != body_id:
            # got mislabeled coordinate
            print("Changing globe for coordinate on %s to %s" % (itemID, body_id))
            try:
                wb = coordValue.toWikibase()
            except CoordinateGlobeUnknownException:
                # does not matter, since we're going to replace it anyway
                coordValue.globe = 'earth'
                wb = coordValue.toWikibase()
            wb['globe'] = body_id
            newCoord = pywikibot.Coordinate.fromWikibase(wb, site)
            coord.changeTarget(newCoord)
