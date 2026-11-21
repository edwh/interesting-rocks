[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["tourism"="museum"]["name"](area.gb);
nwr["tourism"="gallery"]["name"](area.gb);
);
out center tags;
