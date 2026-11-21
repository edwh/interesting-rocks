[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["natural"="cave_entrance"]["name"]["wikidata"](area.gb);
nwr["natural"="cave_entrance"]["name"]["tourism"](area.gb);
nwr["natural"="cave_entrance"]["name"]["website"](area.gb);
nwr["tourism"~"attraction|museum"]["name"~"Cave|Cavern|Mine|Caverns"]["historic"~"mine"](area.gb);
nwr["historic"="mine"]["tourism"](area.gb);
)
;out center tags;
