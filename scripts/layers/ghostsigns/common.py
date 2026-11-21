import json,urllib.request,urllib.parse,time,sys
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
import os; RAW=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','raw','ghostsigns')+'/'
def api(**p):
    p['format']='json'
    u='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(p)
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=60))
        except Exception as e: time.sleep(2)
    raise
def members(cat,typ):
    out=[];c={}
