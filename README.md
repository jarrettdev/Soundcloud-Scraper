# Soundcloud-Scraper
Pull Artists From SoundCloud!
![](https://github.com/jarrettdev/Soundcloud-Scraper/blob/main/resources/soundcloud_data.gif)

# Install

```sh
git clone https://github.com/jarrettdev/Soundcloud-Scraper
cd Soundcloud-Scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# Usage

1. Grab a client ID from SoundCloud using your browser's network tools.
2. Place the client ID in client_id.txt.
3. Choose an artist to start the scraper from. All the artists in the CSV will be somewhat related to the artist you choose.
4. Modifiy the ARTIST_NAME variable inside relative_artist_scraper.py.
5. Change the filter variables to narrow down your scrape (MIN_FOLLOWERS, MIN_TRACK_COUNT, and MIN_FOLLOWING_TO_FOLLOWERS).
6. Run the following commands on after the other : 
    - python relative_artist_scraper.py 1 (stop this command manually or it will keep pulling links)
    - python relative_artist_scraper.py 2
    - python relative_artist_scraper.py 3
    - python relative_artist_scraper.py 4

# Video Tutorial
[![Tutorial](https://github.com/jarrettdev/Soundcloud-Scraper/blob/main/resources/soundcloud_how.jpg)](https://www.youtube.com/watch?v=wY4aBlMZMhI)
