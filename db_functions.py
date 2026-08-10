import sqlite3
from datetime import datetime

DB_NAME = "mediaStatus.db"


def insert_record(
    tmdb_id,
    tvdb_id,
    media_name,
    category,
    logo_artwork_location=None,
    background_artwork_location=None,
    screensaver_location=None,
    screensaver_active=False,
    artwork_fetched=None,
    screensaver_made=None
):
    """Insert a new media record."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO mediaStatus (
        tmdb_id,
        tvdb_id,
        media_name,
        category,
        logo_artwork_location,
        background_artwork_location,
        screensaver_location,
        screensaver_active,
        artwork_fetched,
        screensaver_made
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tmdb_id,
        tvdb_id,
        media_name,
        category,
        logo_artwork_location,
        background_artwork_location,
        screensaver_location,
        screensaver_active,
        artwork_fetched,
        screensaver_made
    ))

    conn.commit()
    conn.close()


def update_record(tmdb_id, **kwargs):
    """
    Update any fields for a media record by tmdb_id.

    Example:
    update_record(
        12345,
        screensaver_active=True,
        screensaver_location="/images/movie.jpg"
    )
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    fields = []
    values = []

    for key, value in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(value)

    values.append(tmdb_id)

    query = f"""
    UPDATE mediaStatus
    SET {", ".join(fields)}
    WHERE tmdb_id = ?
    """

    cursor.execute(query, values)
    conn.commit()
    conn.close()

def remove_record(tmdb_id):
    """Delete a media record by tmdb_id. Returns True if deleted, False if not found."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM mediaStatus WHERE tmdb_id = ?", (tmdb_id,))
    conn.commit()
    
    deleted = cursor.rowcount > 0
    conn.close()
    
    return deleted