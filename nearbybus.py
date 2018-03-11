import urllib.request
import xml.etree.ElementTree as ET
import json
import math
import pickle
import os

def latlon_bbox(latlon, miles):
	lat, lon = latlon
	earth_radius = 3960.0 # miles
	dlat = math.degrees(miles / earth_radius)
	r = earth_radius * math.cos(math.radians(lat))
	dlon = math.degrees(miles / r)
	return (lat - dlat, lon - dlon), (lat + dlat, lon + dlon)

def change_in_longitude(latitude, miles):
    "Given a latitude and a distance west, return the change in longitude."
    # Find the radius of a circle around the earth at given latitude.
    r = earth_radius*math.cos(latitude*degrees_to_radians)
    return (miles/r)*radians_to_degrees

def get_latlon(address):
	# TODO proper quoting
	addr_escaped = address.replace(" ", "%20")
	req = "https://services.gisgraphy.com/geocoding/geocode?address=" + addr_escaped
	response = urllib.request.urlopen(req)
	xml = response.read().decode('utf8', 'ignore')
	root = ET.fromstring(xml)
	result = root.find('result')
	address_back = result.find('formatedFull').text
	lat = float(result.find('lat').text)
	lng = float(result.find('lng').text)
	return address_back, (lat, lng)

def get_routes(bbox):
	lo, hi = bbox
	req = "https://transit.land/api/v1/routes?bbox={},{},{},{}".format(*lo[::-1], *hi[::-1])
	response = urllib.request.urlopen(req)
	js = response.read().decode('utf8', 'ignore')
	return js

def prettyprint_route(r):
	s = "{} ({}), operated by {}".format(
		r["name"], r["vehicle_type"], r["operated_by_name"])
	return s

def query_route_stops(r):
	ids = [s["stop_onestop_id"] for s in r["stops_served_by_route"]]
	url = "https://transit.land/api/v1/stops?onestop_id=" + ",".join(ids)
	# TODO proper quoting
	url = url.replace("<", "%3C")
	response = urllib.request.urlopen(url)
	js = response.read().decode('utf8', 'ignore')
	return js

def query_yelp_near(latlon, radius_miles):
	radius_meters = int(1609 * radius_miles)
	url = "https://api.yelp.com/v3/businesses/search?latitude={}&longitude={}&radius={}".format(
		latlon[0], latlon[1], radius_meters)
	import private
	key = private.yelp_key
	req = urllib.request.Request(url, headers={'Authorization': 'Bearer %s' % key})
	response = urllib.request.urlopen(req)
	js = response.read().decode('utf8', 'ignore')
	return js

walk_radius = 0.5

def get_dev_routes():
	path = "dev_routes.json"
	if not os.path.exists(path):
		print("fetching dev routes from the internet")
		import private
		address_back, latlon = get_latlon(private.address)
		bbox = latlon_bbox(latlon, walk_radius)
		js = get_routes(bbox)
		with open(path, "w") as f:
			f.write(js)
	else:
		print("loading cached dev routes from disk")
		with open(path) as f:
			js = f.read()
	return js

def get_dev_stops():
	path = "dev_stops.json"
	if not os.path.exists(path):
		print("fetching dev stops from the internet")
		routes = json.loads(get_dev_routes())["routes"]
		for r in routes:
			if r["name"].startswith("Metro Expo"):
				js = query_route_stops(r)
				with open(path, "w") as f:
					f.write(js)
				return js
	else:
		print("loading cached dev stops from disk")
		with open(path) as f:
			return f.read()

def get_dev_pois():
	path = "dev_pois.json"
	if not os.path.exists(path):
		print("fetching dev POIs from the internet")
		stops = json.loads(get_dev_stops())["stops"]
		stop_pois = []
		for s in stops:
			lon, lat = s["geometry"]["coordinates"]
			latlon = (float(lat), float(lon))
			pois = query_yelp_near(latlon, walk_radius)
			pois = json.loads(pois)
			stop_pois.append({"stop": s, "pois": pois})
		js = json.dumps(stop_pois)
		with open(path, "w") as f:
			f.write(js)
		return js
	else:
		print("loading cached dev POIs from disk")
		with open(path) as f:
			js = f.read()
			return js

stop_pois = json.loads(get_dev_pois())
for stop in stop_pois:
	s = stop["stop"]
	pois = stop["pois"]
	print()
	print()
	print(s["name"])
	print("-----------")
	# TODO iterate thru everything in yelp request
	for b in pois["businesses"]:
		print(b["name"])
