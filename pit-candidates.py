from pywikibot.data.sparql import SparqlQuery
import sys

HELP = """
This script produces candidates for PIT properties for PreferentialBot.
Use: pit-candidates.py FROM-ID TO-ID
"""

if len(sys.argv) < 3:
    print(HELP)
    exit()

BATCH_SIZE=10
QUERY="""
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX q: <http://www.wikidata.org/prop/qualifier/>
# All properties with point-in-time qualifiers and more than one claims
SELECT DISTINCT ?p WHERE {
  VALUES ?p {
%s
  }
  ?s ?p ?st .
  ?s ?p ?st2 .
  FILTER(?st!=?st2)
  ?st q:P585 [] .
  ?st2 q:P585 [] .
}
"""
POINT_QUERY = """
PREFIX q: <http://www.wikidata.org/prop/qualifier/>
SELECT DISTINCT ?s WHERE {
  BIND (<%s> as ?prop)
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
} LIMIT 10
"""
LABELS = """
SELECT ?p ?pLabel {
  VALUES ?p {
%s
  }
  ?p rdfs:label ?pLabel
  FILTER(lang(?pLabel) = 'en')
}"""
sparql_query = SparqlQuery()

fromID=int(sys.argv[1])
toID=int(sys.argv[2])

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

for chunk in batch(range(fromID, toID), BATCH_SIZE):
    candidates = set()
    props = ' '.join(["p:P" + str(x) for x in chunk])
    sparql = QUERY % props
#    print(chunk)
#    print(sparql)
    items = sparql_query.select(sparql)
    for item in items:
#        print("Checking %s" % item['p'])
        results = sparql_query.select(POINT_QUERY % item['p'])
        if len(results) > 5:
            candidates.add(item['p'][len('http://www.wikidata.org/prop/'):])
    props = ' '.join(["wd:" + x['p'][len('http://www.wikidata.org/prop/'):] for x in items])
    results = sparql_query.select(LABELS % props)
    for res in results:
        propID = res['p'][len('http://www.wikidata.org/entity/'):]
        print("%s %s%s" % (
                    propID,
                    res['pLabel'],
                    "" if propID in candidates else " <-- no data"
        ))
