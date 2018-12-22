from pywikibot.data.sparql import SparqlQuery
import sys

HELP = """
This script produces candidates for START-END properties for PreferentialBot.
Use: st-candidates.py FROM-ID TO-ID
"""

if len(sys.argv) < 3:
    print(HELP)
    exit()

BATCH_SIZE=20
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
# has more than one statement  
  FILTER(?st != ?st2)
# with start/end qualifiers  
  ?st (q:P580|q:P582) [] .
  ?st2 (q:P580|q:P582) [] .
}
"""
START_END_QUERY = """
PREFIX q: <http://www.wikidata.org/prop/qualifier/>
SELECT DISTINCT ?s WHERE {
  BIND (<%s> as ?prop)
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
#    print(sparql)
    items = sparql_query.select(sparql)
#    print(items)
    for item in items:
        results = sparql_query.select(START_END_QUERY % item['p'])
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
