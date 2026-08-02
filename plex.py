from plexapi.server import PlexServer
import os
from dotenv import load_dotenv

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



def get_unwatched_movies():
    # Connect to Plex server
    plex = PlexServer(PLEX_SERVER_URL,PLEX_TOKEN)

    # Get movie library
    Movielibrary = plex.library.section("Movies")  # or whatever your library is named
    movies=[]
    # Get all movies
    for movie in Movielibrary.all():
        if not movie.lastViewedAt:
            ids = organise_content_ids(movie.guid,movie.guids)
            movies.append({'title':movie.title,
                           'tmdb':ids['tmdb'],
                           'tvdb':ids['tvdb']})
            print (f"Title: {movie.title}")

    return movies


def get_unwatched_tvshows():
    # Connect to Plex server
    plex = PlexServer(PLEX_SERVER_URL,PLEX_TOKEN)

    # Get TV shows library
    TVlibrary = plex.library.section("TV Shows")
    tvshows = []
    # Get all TV shows that are not fully watched
    for show in TVlibrary.all():
        if show.viewedLeafCount != show.leafCount:
            ids = organise_content_ids(show.guid, show.guids)
            tvshows.append({'title': show.title,
                            'tmdb': ids['tmdb'],
                            'tvdb': ids['tvdb']})

    return tvshows







