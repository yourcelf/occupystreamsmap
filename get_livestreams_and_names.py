import os
import re
import json
import codecs
import requests
import urllib
from BeautifulSoup import BeautifulSoup

root = "http://occupystreams.org"

def get_cached_page(url):
    name = os.path.join("cache", url.split("://")[1].replace("/", "---"))
    if not os.path.exists(name):
        content = requests.get(url).content
        with codecs.open(name, 'w', 'utf-8') as fh:
            fh.write(content)
    with codecs.open(name, 'r', 'utf-8') as fh:
        content = fh.read()
    return content

soup = BeautifulSoup(get_cached_page(root))
links = soup.findAll("a")
sources = []
for link in links:
    if link['href'].startswith("/item/occupy"):
        subpage = "".join((root, link['href']))
        subsoup = BeautifulSoup(get_cached_page(subpage))
        iframes = subsoup.findAll("iframe")
        if not iframes:
            continue
        where = link.text
        where = where.replace("Occupy ", "")
        where = where.replace(" - UStream", "")
        where = where.replace(" - Livestream", "")
        iframe = iframes[0]
        # Livestream
        match = re.match(r'^.*livestream.com/embed/([^\?]*)(\?.*)?$', iframe['src'])
        provider = None
        if match:
            item = match.group(1)
            provider = "livestream"

        # Ustream
        else:
            match = re.match(r'^.*ustream.tv/embed/(.*)$', iframe['src'])
            if match:
                item = match.group(1)
                provider = "ustream"
            else:
                continue
        sources.append({
            'provider': provider,
            'id': item,
            'location': where,
            'url': "".join((root, link['href'])),
        })

for source in sources:
    # Special case non-geocodable locations
    locname = source['location']
    if locname.startswith("Wall Street"):
        locname = "Wall Street, NY"
    elif locname.startswith("Wall Sreet"): # [sic]
        locname = "Wall Street, NY"
    elif "London" in locname:
        locname = "London"
    elif locname == "Denver - wired":
        locname = "Denver"
    elif locname == "OccupyPhoenix":
        locname = "Phoenix, AZ"

    latlng = json.loads(get_cached_page(
        "https://maps.googleapis.com/maps/api/geocode/json?sensor=false&address=%s" % urllib.quote_plus(locname.encode('utf8'))
    ))
    if latlng['status'] == 'ZERO_RESULTS':
        raise Exception("Geocode not found for %s" % locname)
    source['point'] = latlng['results'][0]['geometry']['location']

print json.dumps({'sources': sources})
