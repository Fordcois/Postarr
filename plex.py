from plexapi.server import PlexServer
import os
from dotenv import load_dotenv
from typing import Literal

load_dotenv()

PLEX_SERVER_URL = os.environ["PLEX_SERVER_URL"]
PLEX_TOKEN = os.environ["PLEX_TOKEN"]

def organise_content_ids(guid, guids):
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
            ids = organise_content_ids(media.guid, media.guids)
            unwatched.append({'title': media.title,
                              'tmdb': ids['tmdb'],
                              'tvdb': ids['tvdb']})
    
    return unwatched

def get_unknown_ids(known_id: int, known_id_source: Literal['tvdb', 'tmdb']):
    """
    Find missing ID using TMDB's find-by-external-id endpoint.
    
    Args:
        known_id: TVDB or TMDB ID
        known_id_type: 'tvdb' or 'tmdb'
    
    Returns:
        {'tvdb': int, 'tmdb': int}
    
    Reference:
        https://developer.themoviedb.org/reference/find-by-external-id
    """
    # TODO: Query TMDB endpoint with known_id_type
    pass





