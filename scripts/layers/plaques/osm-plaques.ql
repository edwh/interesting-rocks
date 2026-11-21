[out:json][timeout:60];
nwr["historic"="memorial"]["memorial"~"^(plaque|blue_plaque)$"]({{bbox}});
out tags center;
