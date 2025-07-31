from sclib import SoundcloudAPI, Track, Playlist
import tqdm
from pathlib import Path
import pandas as pd
import re

# Create base downloads directory and subdirectories
downloads_dir = Path('/home/brett/Desktop/pers/soundbits/soundcloud/downloads')
songs_dir = downloads_dir / 'songs'
mixes_dir = downloads_dir / 'mixes'
songs_dir.mkdir(parents=True, exist_ok=True)
mixes_dir.mkdir(parents=True, exist_ok=True)

# CSV file paths
all_tracks_csv = downloads_dir / 'all_playlist_tracks.csv'
mixes_csv = downloads_dir / 'downloaded_mixes.csv'

# do not pass a Soundcloud client ID that did not come from this library, but you can save a client_id that this lib found and reuse it
api = SoundcloudAPI()  

def sanitize_filename(filename):
    """Removes characters that are invalid in Windows/macOS/Linux filenames."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

try: 
    playlist = api.resolve('https://soundcloud.com/brett-hockey/sets/jams')
    assert isinstance(playlist, Playlist)

    all_tracks_data = []
    downloaded_mixes_data = []

    print(f"Processing playlist: {playlist.title} ({len(playlist.tracks)} tracks)")

    with tqdm.tqdm(playlist.tracks, unit="track") as pbar:
        for track in pbar:
            assert isinstance(track, Track)

            clean_title = sanitize_filename(f'{track.artist} - {track.title}')
            pbar.set_description(f"Checking: {clean_title[:40]}")

            track_info = {slot: getattr(track, slot, None) for slot in track.__slots__}
            track_info['downloaded'] = False
            track_info['download_path'] = ''

            if track.downloadable:
                try:
                    is_mix = (track.duration / 1000) > 900  # duration is in ms
                    download_dir = mixes_dir if is_mix else songs_dir
                    path = download_dir / f'{clean_title}.mp3'
                    
                    pbar.set_description(f"Downloading: {clean_title[:35]}")
                    with open(path, 'wb+') as file:
                        track.write_mp3_to(file)

                    track_info['downloaded'] = True
                    track_info['download_path'] = str(path)
                    
                    if is_mix:
                        downloaded_mixes_data.append(track_info)

                except Exception as e:
                    print(f"\nFailed to download {clean_title}: {e}")
            
            all_tracks_data.append(track_info)

    if all_tracks_data:
        pd.DataFrame(all_tracks_data).to_csv(all_tracks_csv, index=False)
        print(f"\nSuccess: All track metadata saved to '{all_tracks_csv.name}'")

    if downloaded_mixes_data:
        pd.DataFrame(downloaded_mixes_data).to_csv(mixes_csv, index=False)
        print(f"Success: Downloaded mixes metadata saved to '{mixes_csv.name}'")
    else:
        print("No new mixes were downloaded in this run.")

except Exception as e:
    print(f"An error occurred: {e}")

print("Done")