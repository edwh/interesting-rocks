[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["natural"="tree"]["name"~"Oak|Yew|Elm|Ash|Beech|Chestnut|Thorn|Tree|Pine|Lime|Sycamore|Hornbeam"](area.gb);
nwr["natural"="tree"]["species"~"Taxus"]["name"](area.gb);
)
;out center tags;
