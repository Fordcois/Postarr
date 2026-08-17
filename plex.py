from plexapi.server import PlexServer
import os
from dotenv import load_dotenv
from typing import Literal
import requests

load_dotenv()

PLEX_SERVER_URL = os.environ["PLEX_SERVER_URL"]
PLEX_TOKEN = os.environ["PLEX_TOKEN"]
TMDB_API_KEY = os.environ['TMDB_API_KEY']

def organise_content_ids(guid, guids,media_type):
    """Extract TMDB/TVDB/IMDB IDs from Plex guid/guids"""
    ids: dict[str, str | None] = {'tmdb': None, 'tvdb': None}
    
    # New format: guids list
    if guids:
        for guid_obj in guids:
            guid_str = str(guid_obj.id)
            if 'tmdb' in guid_str and '//' in guid_str:
                ids['tmdb'] = guid_str.split('//')[1]
            elif 'tvdb' in guid_str and '//' in guid_str:
                ids['tvdb'] = guid_str.split('//')[1]

    
    # Old format: single guid string
    if guid and not ids['tmdb'] and not ids['tvdb']:
        if 'themoviedb' in guid:
            ids['tmdb'] = guid.split('//')[1].split('?')[0]
        elif 'thetvdb' in guid:
            ids['tvdb'] = guid.split('//')[1].split('?')[0]
        # Find Missing id
    if ids['tmdb'] and not ids['tvdb']:
        # TODO: Remove this check - movies don't have TVDB IDs, only TV shows do
        ids['tvdb']=get_unknown_ids(ids['tmdb'],'tmdb',media_type)
    elif ids['tvdb'] and not ids['tmdb']:
        ids['tmdb']=get_unknown_ids(ids['tvdb'],'tvdb',media_type)

    return ids

def get_unwatched_media(library_name, content_type):
    plex = PlexServer(PLEX_SERVER_URL, PLEX_TOKEN)
    library = plex.library.section(library_name)
    unwatched = []
    
    def is_unwatched(media):
        if content_type == 'movie':
            return not media.lastViewedAt
        elif content_type == 'tvshow':
            return media.viewedLeafCount != media.leafCount
        return False
    
    for media in library.all():
        if is_unwatched(media):
            api_type = 'tv' if content_type == 'tvshow' else 'movie'
            ids = organise_content_ids(media.guid, media.guids, api_type)
            unwatched.append({'title': media.title,
                              'tmdb': ids['tmdb'],
                              'tvdb': ids['tvdb']})
    
    return unwatched

def get_unknown_ids(known_id: int, known_id_source: Literal['tvdb', 'tmdb'], media_type: Literal['tv', 'movie'])-> int | None:
    """
    Find missing ID using TMDB's find-by-external-id endpoint.
    
    Args:
        known_id: TVDB or TMDB ID (as integer)
        known_id_source: 'tvdb' or 'tmdb'
        media_type: 'tv' or 'movie'
    
    Returns:
        {'tvdb': int, 'tmdb': int} or None if not found
    """
    
    try:
        if known_id_source == 'tmdb':
            # You have TMDb ID, get TVDB ID
            url = f"https://api.themoviedb.org/3/{media_type}/{known_id}"
            params = {
                "api_key": TMDB_API_KEY,
                "append_to_response": "external_ids"
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            tvdb_id = data['external_ids'].get('tvdb_id')
            return tvdb_id
        
        elif known_id_source == 'tvdb':
            # You have TVDB ID, get TMDb ID
            url = f"https://api.themoviedb.org/3/find/{known_id}"
            params = {
                "api_key": TMDB_API_KEY,
                "external_source": "tvdb_id"
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check the appropriate results array based on media_type
            results_key = "tv_results" if media_type == "tv" else "movie_results"
            
            if data.get(results_key) and len(data[results_key]) > 0:
                tmdb_record = data[results_key][0]
                tmdb_id = tmdb_record["id"]
                return tmdb_id
            
            return None
            
    except requests.RequestException as e:
        print(f"Error fetching IDs: {e}")
        return None




