import pywikibot
from pywikibot.data.sparql import SparqlQuery
from urllib.parse import quote

"""
Get the list of units with anomalies, such as props having
both united and unitless quantities.
"""

QUANT = """
SELECT ?p WHERE {
  ?p a wikibase:Property; wikibase:propertyType wikibase:Quantity .
}
"""
CHECKUNITS = """
SELECT ?unit (count(?x) as ?count) WHERE {
    ?x p:%s/psv:%s [ wikibase:quantityUnit ?unit ]
} GROUP BY ?unit
ORDER BY DESC(?count)
"""
GETUNITS = """
SELECT ?id ?idLabel ?type ?typeLabel WHERE {
    ?id p:%s/psv:%s [ wikibase:quantityUnit wd:%s ] .
    OPTIONAL { ?id wdt:P31 ?type }
    FILTER(?id != wd:Q4115189 && ?id != wd:Q13406268 && ?id != wd:Q15397819)
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
"""
SPARQL = """
[http://query.wikidata.org/#%s SPARQL]
"""
LOGPAGE = "User:Laboramus/Units"
ONE = 'http://www.wikidata.org/entity/Q199'
# Load properties
sparql_query = SparqlQuery()
site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

badprops = []
counts = {}
items = sparql_query.get_items(QUANT, item_name='p')

sandboxes = set(['Q13406268', 'Q15397819', 'Q4115189'])
# Mixed units - for these, mixing is OK
# maximum capacity (P1083)
# total produced (P1092)
# quantity (P1114)
# numeric value (P1181)
# collection or exhibition size (P1436)
# personal best (P2415)
# number of parts of a work of art (P2635)
# number of participants (P1132)
mixed_units = set(['P1083', 'P1092', 'P1181', 'P1114', 'P1132', 'P1436', 'P2415', 'P2635' ])
# Properties with known anomalous units
allowed_anomaly = {
    'P1110': set(['http://www.wikidata.org/entity/Q6256', 'http://www.wikidata.org/entity/Q7275']),
    'P1113': set(['http://www.wikidata.org/entity/Q1261214']),
    'P1122': set(['http://www.wikidata.org/entity/Q12503', 'http://www.wikidata.org/entity/Q743139']),
    'P1971': set(['http://www.wikidata.org/entity/Q177232', 'http://www.wikidata.org/entity/Q308194']),
    'P2103': set(['http://www.wikidata.org/entity/Q28997']),
    'P2124': set(['http://www.wikidata.org/entity/Q37226', 'http://www.wikidata.org/entity/Q43229', 'http://www.wikidata.org/entity/Q515']),
    'P2196': set(['http://www.wikidata.org/entity/Q21094885']),
}

# report inconsistent properties
def found_inconsistent(prop, result):
    if prop in mixed_units:
        return
    print("Inconsistent units for %s" % prop)
    if prop in allowed_anomaly:
        count = 1 # This is for Q199 itself
        for unit in result:
            if unit['unit'] in allowed_anomaly[prop]:
                count = count + 1
        if count == len(result):
        # All anomalies are accounted for
            print("All anomalies accounted for in %s" % prop)
            return
    badprops.append(prop)
    logpage = pywikibot.Page(site, LOGPAGE+"/"+prop)
    text = "{{P|" + prop + "}}\n\n{| class=\"wikitable\"\n"
    for unit in result:
        unitName = unit['unit'].replace('http://www.wikidata.org/entity/', '')
        if unitName in sandboxes:
            continue
        query = GETUNITS % (prop, prop, unitName)
        text = text + "|-\n" + \
            "|| {{Q|" + unitName + "}} || " + \
            unit['count'] + "||" + \
            SPARQL % quote(query) + "\n"
        if unitName == 'Q199':
            counts[prop] = unit['count']
    text = text + "|}\n"
    text = text + "[http://query.wikidata.org/#%s Try again]\n" % quote(CHECKUNITS % (prop, prop))
    logpage.text = text
    logpage.save("log for "+prop)

# Check property units
for item in items:
    query = CHECKUNITS % (item, item)
    try:
        result = sparql_query.select(query)
    except:
        print("Failed to query %s!" % item)
        continue
    if len(result) <= 1:
        continue
    for unit in result:
        if unit['unit'] == ONE:
            found_inconsistent(item, result)
#
if badprops:
    logpage = pywikibot.Page(site, LOGPAGE)
    logpage.text = "\n\n".join([ "{{P|" + prop + "}} [[" + LOGPAGE+"/"+prop + "]] (" + counts[prop] + ")" for prop in sorted(badprops) ])
    logpage.save("log for units")
