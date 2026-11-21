[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["name"~"Green Man"]["historic"](area.gb);
nwr["description"~"Green Man",i]["historic"](area.gb);
nwr["artwork_subject"~"green.?man",i](area.gb);
)
;out center tags;
