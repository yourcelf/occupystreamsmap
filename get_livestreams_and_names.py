import os
import re
import json
import codecs
import requests
import urllib
from BeautifulSoup import BeautifulSoup

root = "http://occupystreams.org"

def get_cached_page(url):
    name = os.path.join(
        os.path.dirname(__file__),
        "cache", 
        url.split("://")[1].replace("/", "---")
    )
    if not os.path.exists(name):
        content = requests.get(url).content
        try:
            os.makedirs(os.path.dirname(name))
        except OSError:
            pass
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
        match = re.match(r'^.*ustream.tv/(?:embed|socialstream)/(.*)$', iframe['src'])
        if match:
            item = match.group(1)
            provider = "ustream"

        # justin.tv
        match = re.match(r'^.*justin\.tv/chat/embed\?channel=([^\&]*)\&.*$', iframe['src'])
        if match:
            item = match.group(1)
            provider = "justintv"

        assert provider is not None, "Source not recognized: '%s'" % iframe['src']

        sources.append({
            'provider': provider,
            'id': item,
            'location': where,
            'url': "".join((root, link['href'])),
        })

for source in sources:
    # Special case non-geocodable locations
    locname = source['location']
    if locname.startswith("Wall Street") and "San Diego" not in locname:
        locname = "Wall Street, NY"
    elif locname.startswith("Wall Sreet"): # [sic]
        locname = "Wall Street, NY"
    elif "London" in locname:
        locname = "London"
    elif "Denver" in locname:
        locname = "Denver"
    elif "Phoenix" in locname:
        locname = "Phoenix, AZ"
    elif "Los Angeles" in locname:
        locname = "Los Angeles"
    elif "Boston" in locname:
        locname = "Boston"
    elif "Harvard" in locname:
        locname = "Harvard, Cambridge, MA"

    latlng = json.loads(get_cached_page(
        "https://maps.googleapis.com/maps/api/geocode/json?sensor=false&address=%s" % urllib.quote_plus(locname.encode('utf8'))
    ))
    assert latlng['status'] != 'ZERO_RESULTS', "Geocode not found for %s" % locname
    source['point'] = latlng['results'][0]['geometry']['location']

print "var data = %s" % json.dumps({'sources': sources})
