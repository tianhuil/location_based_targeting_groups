# Usage:
# mkvirtualenv demo_fb_location_targeting -p python3
# workon demo_fb_location_targeting # use this when you work on the project in a new Terminal window
# pip install -r requirements.txt
#
# Variables:
#.env file stories Google Maps, Google Sheets ID, Clearbit API Token, Facebook Access Token, Facebook Campaign ID

import sys, time, os, json, datetime
from random import randint
from collections import namedtuple

import requests
from sys import argv
from requests.auth import HTTPBasicAuth

# settings.py
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), verbose=True)

# Define a point object
Point = namedtuple('Point', ['lat', 'lng'])
# Define an exclusion transform, that moves points to create a zone around an inital point
# (usually given a 1km radius)
ExclusionTransform = namedtuple('ExclusionTransform', ['lat_transform', 'lng_transform'])

# These variables define the exclusion radius. Play with these to adjust how close or far you want to be from the building itself.
# This is approximately one block
BLOCK_EXCLUSION = ExclusionTransform(0.0099, 0.01391)

def query_google_maps(address):
  url = "https://maps.googleapis.com/maps/api/place/textsearch/json?query=" + address + "&region=&key=" + os.getenv('GOOGLE_MAPS_API_KEY')
  response = requests.get(url)
  if response.status_code == 200:
    data = json.loads(response.text)
    return data
    log (f'Status code: {response.status_code}')

def get_fb_targeting(addresses, location_interests):

  def transform_lat(p, delta):
    return Point(p.lat + delta, p.lng)

  def transform_lng(p, delta):
    return Point(p.lat, p.lng + delta)

  def get_zone(p, radius):
    return {
      "latitude": p.lat,
      "longitude": p.lng,
      "radius": str(radius),
      "distance_unit": "kilometer"
    }

  excluded_locations = []
  for address in addresses:
    excluded_locations.append(
      get_zone(transform_lat(address, BLOCK_EXCLUSION.lat_transform), 1))
    excluded_locations.append(
      get_zone(transform_lat(address, -1 * BLOCK_EXCLUSION.lat_transform), 1))
    excluded_locations.append(
      get_zone(transform_lng(address, BLOCK_EXCLUSION.lng_transform), 1))
    excluded_locations.append(
      get_zone(transform_lng(address, -1 * BLOCK_EXCLUSION.lng_transform), 1))
  return json.dumps({
    "excluded_geo_locations": {
      "custom_locations": excluded_locations,
    },
    "geo_locations": {
      "custom_locations": [get_zone(p, 1) for p in addresses],
      "location_types": ["recent"]
    },
    'publisher_platforms':['facebook','instagram'],
    'facebook_positions':['feed'],
    'instagram_positions':['stream'],
  }, indent=None)

  #'interests': get_interest_array(location_interests),

def build_geo_from_domain_via_clearbit(domain):

  # This function simply takes a web address and finds the physical location of the company via Clearbit.
  data = []

  url = 'https://company.clearbit.com/v2/companies/find'
  params = {
      'domain':domain
  }
  auth = os.getenv('CLEARBIT_ACCESS_TOKEN')
  response = requests.get(url=url, params=params, auth=HTTPBasicAuth(auth, ''))
  if response.status_code == 200:
    data = response.json()
    return data
  else:
    print(data)
    return None

def search_fb_employer(location_interests):

  # This function queries the Facebook Marketing API to get a list of interests based on a keyword.

  url = 'https://graph.facebook.com/v2.11/search'
  params = {
      'type':'adworkemployer',
      'q':'Smartsheet',
      'access_token': os.getenv('FACEBOOK_ACCESS_TOKEN'),
  }
  response = requests.get(url=url, params=params)
  print(response)
  if response.status_code == 200:
    data = response.json()
    return data

def build_fb_interests(location_interests):

  # This function queries the Facebook Marketing API to get a list of interests based on a keyword.

  url = 'https://graph.facebook.com/v2.11/search'
  params = {
      'type':'adinterest',
      'q':location_interests,
      'access_token': os.getenv('FACEBOOK_ACCESS_TOKEN'),
  }
  response = requests.get(url=url, params=params)
  print(response)
  if response.status_code == 200:
    data = response.json()
    return data

def get_insights_by_adset_id():

  # This function queries the Facebook Marketing API to get a list of interests based on a keyword.

  url = 'https://graph.facebook.com/v2.11/'+os.getenv('FACEBOOK_CAMPAIGN_ID')+'/insights'
  params = {
      'level':'ad',
      'fields':['impressions'],
      'access_token': os.getenv('FACEBOOK_ACCESS_TOKEN'),
  }
  response = requests.get(url=url, params=params)
  print(response)
  if response.status_code == 200:
    data = response.json()
    return data

def build_fb_job_interests(location_interests):

  # This function queries the Facebook Marketing API to get a list of interests based on a keyword.
  url = 'https://graph.facebook.com/v2.11/search'
  params = {
      'type':'adworkposition',
      'q':location_interests,
      'access_token': os.getenv('FACEBOOK_ACCESS_TOKEN'),
  }
  response = requests.get(url=url, params=params)
  if response.status_code == 200:
    data = response.json()
    return data

def get_interest_array(location_interests):
  interests = build_fb_interests(location_interests)
  field_list = interests['data']

  return [
    {
      'id': fields['id'],
      'name': fields['name']
    }
    for fields in field_list
  ]

def post_to_facebook(name, targeting, campaign_type):

  url = 'https://graph.facebook.com/v3.3/act_'+os.getenv('FACEBOOK_AD_ACCOUNT')+'/adsets'

  if(campaign_type == 'traffic'):

    params = {
        'name':name,
        'optimization_goal':'LINK_CLICKS',
        'billing_event':'IMPRESSIONS',
        'bid_strategy':'LOWEST_COST_WITHOUT_CAP',
        'bid_amount': '100',
        'status':'ACTIVE',
        'targeting': targeting,
        'campaign_id':os.getenv('FACEBOOK_CAMPAIGN_ID'),
        'access_token': os.getenv('FACEBOOK_ACCESS_TOKEN')
    }

  if(campaign_type == 'leads'):
    params = {
        'name':name,
        'objective': 'LEAD_GENERATION',
        'optimization_goal':'LEAD_GENERATION',
        'billing_event':'IMPRESSIONS',
        'TARGET_COST':'5000',
        'promoted_object': '{"page_id":109789313259125}',
        'status':'ACTIVE',
        'campaign_id':os.getenv('FACEBOOK_CAMPAIGN_ID'),
        'targeting': targeting,
        'access_token': os.getenv('FACEBOOK_ACCESS_TOKEN')
    }

  resp = requests.post(url=url, data=params)
  print(resp)
  data = resp.json()
  print(data)

def load_urls():
  f = open('urls.txt', 'r')
  roles = f.readlines()
  roles = [role.strip() for role in roles]
  f.close()
  return list(roles)

def load_addresses():
  f = open('addresses.txt', 'r')
  roles = f.readlines()
  roles = [role.strip() for role in roles]
  f.close()
  return list(roles)

def process_addresses(campaign_type,u_interests):
  #Get the list of the addresses you want to build locations for
  company_addresses = load_addresses()

  addresses = []
  for u_address in company_addresses:
    google_maps_response = query_google_maps(u_address)
    addresses.append(Point(google_maps_response['results'][0]['geometry']['location']['lat'], google_maps_response['results'][0]['geometry']['location']['lng']))

  targeting = get_fb_targeting(addresses, u_interests)
  post_to_facebook(f"multi-adset-{len(addresses)}", targeting, campaign_type)
  time.sleep(5)

def process_urls(campaign_type,u_interests):
  #Get the list of the URLs you want to build locations for
  company_urls = load_urls()
  addresses = []
  for u_url in company_urls:
    clear_bit_response = build_geo_from_domain_via_clearbit(u_url)
    if(clear_bit_response == None or clear_bit_response['geo']['lat'] == None or clear_bit_response['geo']['lng'] == None
      # Throwing out locations that are not in the U.S.
      or clear_bit_response['geo']['countryCode'] != 'US' ):
      continue

    addresses.append(Point(clear_bit_response['geo']['lat'], clear_bit_response['geo']['lng']))

  targeting = get_fb_targeting(addresses, u_interests)
  post_to_facebook(f"mkvirtualenvlti-adset-{len(addresses)}", targeting, campaign_type)
  time.sleep(5)

#Start
if __name__ == '__main__':

  # Define which type of adset you are trying to build for. In this script, the two options are traffic and leads.
  # Facebook forces that the attributes of the adset map to the campaign objective.
  campaign_type = 'traffic'

  # Define which interests you would like to layer into the targeting. This will show up in your adset as interests based targeting and becomes an AND on the geo location targeting.
  u_interests = 'Product Management'

  # This takes your list of URLs (urls.txt) and builds the adsets
  process_urls(campaign_type,u_interests)

  # This takes your list of addresses (addresses.txt) and builds the adsets
  # process_addresses(campaign_type,u_interests)

