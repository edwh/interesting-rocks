import urllib.request,urllib.parse,time,re,json,html
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
import os; RAW=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','raw','ghostsigns')+'/'
out={}
import os
out=json.load(open(RAW+'geo.json'))
for q in ['ghostsign','ghost advert','faded advert','painted advertisement wall ghost','old advertisement painted brick wall','ghost sign Scotland','ghost sign Wales','ghost sign London','ghost sign Yorkshire','ghost sign Lancashire','ghost sign Kent','ghost sign Devon']:
  qid=None
  for page in range(1,40):
    prm={'q':q,'format':'KML','perpage':100} if qid is None else {'i':qid,'format':'KML','perpage':100,'page':page}
    u='https://www.geograph.org.uk/syndicator.php?'+urllib.parse.urlencode(prm)
    try: x=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=60).read().decode('utf8','replace')
    except Exception as e:
        print('stop',q,page,e);break
    if qid is None:
        qid=1
        r2=urllib.request.urlopen(urllib.request.Request(u.replace('KML','GeoRSS'),headers={'User-Agent':UA}),timeout=60).read().decode('utf8','replace')
        qid=re.search(r'results/(\d+)',r2).group(1)
    pms=re.findall(r'<Placemark id="([^"]+)">(.*?)</Placemark>',x,re.S)
    if not pms:break
    for pid,b in pms:
        g=pid.rsplit('/',1)[1]
        name=html.unescape(re.search(r'<name>(.*?)</name>',b,re.S).group(1))
        c=re.search(r'<coordinates>([-\d.]+),([-\d.]+)',b)
        img=re.search(r'src="([^"]+_120x120\.jpg)"',b)
        cr=re.search(r'class="attribution">(.*?)</i>',b)
        sn=re.search(r'<Snippet[^>]*>(.*?)</Snippet>',b,re.S)
        out[g]={'id':g,'title':name,'lon':float(c.group(1)),'lat':float(c.group(2)),'thumb':img and img.group(1),'artist':cr and html.unescape(cr.group(1)),'desc':sn and html.unescape(html.unescape(sn.group(1)))[:600],'q':q}
    print(q,page,len(out),flush=True)
    time.sleep(1.2)
    if len(pms)<100:break
json.dump(out,open(RAW+'geo.json','w'))
