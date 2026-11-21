[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["natural"="spring"]["name"~"Holy Well|Holywell|Lady.?s Well|St\\.? .* Well|Saint .* Well|Wishing Well|Well of |Ffynnon|Tobar|Chad.?s Well|Blessed Well|Healing Well|Our Lady"](area.gb);
nwr["historic"="holy_well"](area.gb);
nwr["amenity"="holy_well"](area.gb);
nwr["man_made"="water_well"]["name"~"Holy Well|St\\.? .* Well|Saint .* Well|Lady.?s Well|Wishing Well|Ffynnon"](area.gb);
)
;out center tags;
