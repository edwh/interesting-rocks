# Exact requests (User-Agent: goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map))
Commons API https://commons.wikimedia.org/w/api.php (format=json):
1. tree.py: action=query&list=categorymembers&cmtitle=<cat>&cmtype=subcat|file&cmlimit=500, recursive from
   Category:Ghost signs in England / Scotland / Wales; files also from Category:Ghost signs in the United Kingdom.
   Resulting category list written to ../ghostsign-raw/categories.txt each run.
2. info.py: action=query&titles=<50 files>&prop=coordinates|imageinfo&coprimary=all&colimit=500
   &iiprop=url|extmetadata&iiurlwidth=1280&iiextmetadatafilter=LicenseShortName|Artist|ImageDescription|ObjectName|DateTimeOriginal
Geograph https://www.geograph.org.uk/syndicator.php (1.2 s between calls):
3. geo.py: q=ghost+sign and q=ghost+signs, format=KML&perpage=100; first call format=GeoRSS gives the saved-search id,
   then i=<id>&format=KML&perpage=100&page=N until a 400 (cap 1000 results/query).
4. geo2.py: same for extra queries (see list in the file).
postcodes.io: POST https://api.postcodes.io/postcodes {"geolocations":[{latitude,longitude,radius:500|2000,limit:1}]} (100/batch; cached in pc.json).
