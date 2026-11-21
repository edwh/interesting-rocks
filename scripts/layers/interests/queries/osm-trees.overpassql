[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["natural"="tree"]["name"]["wikidata"](area.gb);
nwr["natural"="tree"]["name"]["denotation"~"natural_monument|landmark"](area.gb);
nwr["natural"="tree"]["name"]["historic"](area.gb);
nwr["natural"="tree"]["name"]["wikipedia"](area.gb);
nwr["natural"="tree"]["name"]["tourism"](area.gb);
)
;out center tags;
