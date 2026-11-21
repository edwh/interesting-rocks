[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
node["place"~"^(city|town|village|hamlet|suburb)$"]["name"](area.gb);
out;
