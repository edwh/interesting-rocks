[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["historic"="standing_stone"]["name"](area.gb);
nwr["historic"="archaeological_site"]["site_type"~"stone_circle|megalith"]["name"](area.gb);
nwr["historic"="archaeological_site"]["archaeological_site"="megalith"]["name"](area.gb);
)
;out center tags;
