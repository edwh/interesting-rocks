[out:json][timeout:250];
area["ISO3166-1"="GB"]->.gb;
(
nwr["historic"="memorial"]["memorial"="war_memorial"](area.gb);
nwr["historic"="memorial"]["name"~"war memorial|cenotaph|roll of hono(u)?r",i](area.gb);
);
out center tags;
