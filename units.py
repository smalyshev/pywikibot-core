import pywikibot
from pywikibot.data.sparql import SparqlQuery
from urllib.parse import quote

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
SELECT ?id WHERE {
    ?id p:%s/psv:%s [ wikibase:quantityUnit wd:%s ]
    FILTER(?id != wd:Q4115189 && ?id != wd:Q13406268 && ?id != wd:Q15397819)
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
mixed_units = set(['P1083', 'P1092', 'P1181', 'P1114', 'P1436', 'P2415', 'P2635'])

# report inconsistent properties
def found_inconsistent(prop, result):
    if prop in mixed_units:
        return
    print("Inconsistent units for %s" % prop)
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
    logpage.text = "\n\n".join([ "{{P|" + prop + "}} [[" + LOGPAGE+"/"+prop + "]]" for prop in sorted(badprops) ])
    logpage.save("log for units")
