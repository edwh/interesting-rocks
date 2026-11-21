// Named settlements, used only to label "near X" for places with no admin area.
[out:json][timeout:240];
node["place"~"^(city|town|village|hamlet|suburb|island)$"]["name"]({BBOX});
out;
