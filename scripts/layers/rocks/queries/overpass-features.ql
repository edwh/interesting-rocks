// Named rock/geology features in one bounding box ({BBOX} = south,west,north,east).
[out:json][timeout:240];
(
  nwr["natural"="arch"]["name"]({BBOX});
  nwr["natural"~"^(stack|sea_stack)$"]["name"]({BBOX});
  nwr["natural"~"^(stone|rock|bare_rock)$"]["name"]["geological"~"^(glacial_erratic|outcrop|limestone_pavement|hoodoo|giants_kettle|columnar_jointing|inselberg|volcanic_vent|dyke|geotope)$"]({BBOX});
  nwr["natural"~"^(stone|rock)$"]["name"]["rock"~"^(erratic|stack|tor|pinnacle|pillar|arch|spire|hoodoo|tower)$"]({BBOX});
  nwr["natural"~"^(stone|rock)$"]["name"]["wikidata"]({BBOX});
  nwr["natural"~"^(stone|rock)$"]["name"]["wikipedia"]({BBOX});
  nwr["natural"~"^(stone|rock)$"]["name"]["wikimedia_commons"]({BBOX});
  nwr["natural"~"^(stone|rock)$"]["name"~"(Erratic|Boulder|Stone|Rock|Crag|Tor|Arch|Stack|Stac|Pinnacle|Pillar|Needle|Pulpit|Pavement|Scar|Chair|Kettle|Cove|Gate|Tower)"]["historic"!~"."]["seamark:type"!~"."]({BBOX});
  nwr["geological"~"^(glacial_erratic|limestone_pavement|palaeontological_site|hoodoo|giants_kettle|columnar_jointing|geotope|outcrop|volcanic_vent|inselberg)$"]["name"]({BBOX});
);
out center tags;
