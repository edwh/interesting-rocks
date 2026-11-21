import json,sys,time
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common import api,RAW
t=json.load(open(RAW+'tree.json'))
fs=list(t['files']);info={}
for i in range(0,len(fs),50):
    r=api(action='query',titles='|'.join(fs[i:i+50]),prop='coordinates|imageinfo',coprimary='all',colimit=500,iiprop='url|extmetadata',iiurlwidth=1280,iiextmetadatafilter='LicenseShortName|Artist|ImageDescription|ObjectName|DateTimeOriginal')
    for p in r['query']['pages'].values():
        info[p['title']]=p
    time.sleep(.3)
json.dump(info,open(RAW+'info.json','w'))
n=sum(1 for p in info.values() if p.get('coordinates'))
print(len(info),n)
