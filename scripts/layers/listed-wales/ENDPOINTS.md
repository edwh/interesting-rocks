# Scotland (fetch_listed_scotland.py OUT.json [RAW_DIR])
GET/POST https://inspire.hes.scot/arcgis/rest/services/HES/HES_Designations/MapServer/0/query
 step 1: where=CATEGORY in ('A','B') AND DES_TYPE='Listed Building' & returnIdsOnly=true & f=json  (40,974 ids)
 step 2: objectIds=<1000 ids> & outFields=* & outSR=4326 & returnGeometry=true & f=json
 (resultOffset/resultRecordCount NOT supported -> "Pagination is not supported"; native CRS is EPSG:27700, outSR handles conversion)
 Licence: OGL v3.0. Attribution: "Contains Historic Environment Scotland data (c) Crown copyright and database right <year>"
# Wales (fetch_listed_wales.py OUT.json [RAW_DIR])
GET https://datamap.gov.wales/geoserver/inspire-wg/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire-wg:Cadw_ListedBuildings&outputFormat=application/json&srsName=EPSG:4326&cql_filter=Grade IN ('I','II*')&sortBy=RecordNumber&startIndex=N&count=1000
 Licence: OGL v3.0. Attribution (DataMapWales metadata): "Designated Historic Asset GIS Data, The Welsh Historic Environment Service (Cadw), <date received>, licensed under the Open Government Licence http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
