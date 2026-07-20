# Postarr

Generate Netflix-style screensavers and wallpapers from your Plex library for Nvidia Shield and other home media devices.

Fetches media artwork from FanartTV and TMDB APIs to create dynamic video screensavers with zoom effects and animated logos, or static wallpapers with composited artwork.

## TODO
- Build orchestrator task to coordinate workflow
- Integrate Plex API to fetch media library and watch data
- Implement content tracking (database/JSON log of generated files)
- Implement cleanup logic to delete old generated content
- Add scheduling/cron support for automated generation
## Future Roadmap

- Integrate Letterboxd API to show watched movies and ratings

## Changelog

### v0.1.0 (Initial Release)
- FanartTV and TMDB artwork fetching
- Static wallpaper generation
- Video screensaver generation with zoom and logo drift effects
