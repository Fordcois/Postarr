import sqlite3


DB_NAME = "mediaStatus.db"


def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mediaStatus (
        id INTEGER PRIMARY KEY,

        plex_id INTEGER UNIQUE NOT NULL,
        tmdb_id INTEGER,
        tvdb_id INTEGER,

        media_name TEXT NOT NULL,
        category TEXT NOT NULL,

        logo_artwork_location TEXT,
        background_artwork_location TEXT,

        screensaver_location TEXT,
        screensaver_active BOOLEAN DEFAULT FALSE,

        artwork_fetched TIMESTAMP,
        screensaver_made TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()


def insert_record(
    plex_id,
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO mediaStatus (
        plex_id,
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
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plex_id,
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


def update_record(plex_id, **kwargs):
    """
    Update any fields for a media record.

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

    values.append(plex_id)

    query = f"""
    UPDATE mediaStatus
    SET {", ".join(fields)}
    WHERE plex_id = ?
    """

    cursor.execute(query, values)

    conn.commit()
    conn.close()