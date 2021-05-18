import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
import json
import re
from tqdm import tqdm
import requests
import argparse
from bs4 import BeautifulSoup
import traceback
import os
import csv
import time
import logging

class SoundcloudScraper(scrapy.Spider):

    ARTIST_NAME = 'bigsean-1'
    MIN_FOLLOWERS = 300
    MIN_TRACK_COUNT = 3
    MIN_FOLLOWERS_TO_FOLLOWING = .80

    client_id = ''
    step = ''
    def to_csv(self, item):
        file_exists = os.path.isfile(f'Soundcloud_Artists_from_{self.ARTIST_NAME}.csv')
        # Append data to CSV file
        with open(f'Soundcloud_Artists_from_{self.ARTIST_NAME}.csv', 'a') as csv_file:
            # Init dictionary writer
            writer = csv.DictWriter(csv_file, fieldnames=item.keys())
            # Write header only ones
            if not file_exists:
                writer.writeheader()
            # Write entry to CSV file
            writer.writerow(item)

    def init_argparse(self) -> argparse.ArgumentParser:

        parser = argparse.ArgumentParser(
            usage="%(prog)s [OPTION] [FILE]...",
            description="Soundcloud relative followers extraction"
        )
        parser.add_argument(
            "-v", "--version", action="version",
            version = f"{parser.prog} version 1.2.0"
        )
        parser.add_argument('step', nargs=1)

        return parser

    name = 'soundcloud'
    headers = {
    "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0"
    }
    #change this to current artist's followers api link (we are going to branch out from this artist's related artists),
    artist_home = f'https://soundcloud.com/{ARTIST_NAME}'

    related_artist_list = []

    # custom settings
    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'Soundcloud Artists.csv',
        'CONCURRENT_REQUESTS' : 64,
        'CONCURRENT_REQUESTS_PER_DOMAIN' : 64,
        'LOG_ENABLED' : 'False'
        #'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        #'DOWNLOAD_DELAY': 1
    }


    # crawler's entry point
    def start_requests(self):
        # Setup logging
        ################################################

        logger = logging.getLogger('mylogger')

        handler = logging.FileHandler(f'run_{self.ARTIST_NAME}.log')

        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        ################################################

        # Initialize command line arguments
        ##################################################################

        parser = self.init_argparse()
        args = parser.parse_args()
        if not args.step:
            logger.error('no step provided')
            return

        logger.info(f' step : {str(args.step)}')
        with open('client_id.txt', 'r') as id_file:
            self.client_id = id_file.read().strip()
        self.step = int(str(args.step).replace('[','').replace(']','').replace("'",''))
        logger.info(f'self.step : {self.step}')

        ##################################################################

        # make HTTP GET request to parent Soundcloud artist

        if self.step == 1:
            #***THIS PART MUST BE MANUALLY STOPPED***
            yield scrapy.Request(url=self.artist_home, headers=self.headers, callback=self.get_related_artists)
        elif self.step == 2:
            relative_list = []
            with open('relative_list.txt', 'r', encoding = 'utf-8') as api_file:
                relative_list = list(set(api_file.read().split('\n')))
            logger.info(f'{len(relative_list)} items in relative_list')
            for link in tqdm(relative_list):

                if link != '':
                    logger.info(f'Parsing {link} (step 2)...')
                    yield scrapy.Request(url=link, headers=self.headers, callback=self.get_followers_link)
        elif self.step == 3:
            with open('relative_followers_list.txt', 'r', encoding = 'utf-8') as api_file:
                link_list = list(set(api_file.read().split('\n')))
            for link in tqdm(link_list[1:]):

                if link != '':
                    logger.info(f'Parsing {link} (step 3)...')
                    yield scrapy.Request(url=link, headers=self.headers, callback=self.collect_links)

        elif self.step == 4:
            link_list = []
            with open('soundcloud_api.txt', 'r', encoding = 'utf-8') as api_file:
                link_list = list(set(api_file.read().split('\n')))
            for link in tqdm(link_list):

                if link != '':
                    logger.info(f'Parsing {link} (step 4)...')
                    yield scrapy.Request(url=link, headers=self.headers, callback=self.parse_api_page)
        else:
            return


    def get_followers_link(self, response):
        #get artist id_number
        id_number = str(response.css('meta[property="twitter:app:url:googleplay"]::attr(content)')[0]).split('://')[1].split('users:')[1].split("'>")[0]
        follower_link = f'https://api-v2.soundcloud.com/users/{id_number}/followers?client_id={self.client_id}&limit=200'
        with open('relative_followers_list.txt', 'a', encoding = 'utf-8') as link_file:
            link_file.write(f'{follower_link}\n')

    def get_related_artists(self, response):
        #called on one artist at a time.
        #goes from one artists to many.
        id_number = str(response.css('meta[property="twitter:app:url:googleplay"]::attr(content)')[0]).split('://')[1].split('users:')[1].split("'>")[0]
        related_link = f'https://api-v2.soundcloud.com/users/{id_number}/relatedartists?client_id={self.client_id}&limit=12'
        yield response.follow(url=related_link, headers=self.headers, callback=self.parse_relatives)

    def parse_relatives(self, response):
        json_data = response.json()
        collection = json_data['collection']
        for user in collection:
            user_followers = user['followers_count']
            user_following = user['followings_count']
            user_track_count = user['track_count']
            user_link = user['permalink_url']
            user_follow_data = {"followers" : user_followers, "following" : user_following}
            self.related_artist_list.append(user_link)
            with open('relative_list.txt', 'a', encoding = 'utf-8') as artist_file:
                artist_file.write(f'{user_link}\n')
            yield response.follow(url=user_link, headers=self.headers, callback=self.get_related_artists)

    def parse_api_page(self, response):
        try:
            json_data = json.loads(response.text)
        except ValueError:
            logger.error('ValueError decoding JSON')
            json_data = {}
        try:
            collection = json_data['collection']
            for user in collection:
                user_followers = user['followers_count']
                user_following = user['followings_count']
                user_track_count = user['track_count']
                if int(user_followers) >= self.MIN_FOLLOWERS and int(user_track_count) >= self.MIN_TRACK_COUNT:
                    follower_ratio = float(user_following)/float(user_followers)
                    if follower_ratio <= self.MIN_FOLLOWERS_TO_FOLLOWING:
                        user_link = user['permalink_url']
                        user_name = user['username']
                        user_location = user['city'].strip()
                        user_description = user['description']
                        user_full_name = user['full_name']
                        user_first_name = user['first_name']
                        with open('artist_list.txt', 'a', encoding = 'utf-8') as artist_file:
                            artist_file.write(f'{user_link}\n')
                        potential_emails = []
                        if user_description:
                            potential_emails = re.findall('\w+@\w+\.{1}\w+', user_description)
                        #1. go to artist homepage and collect id
                        res = requests.get(user_link, timeout=6)
                        content = BeautifulSoup(res.text, 'lxml')
                        #first step of collecting id
                        init_meta = content.find("meta", {"property" : "twitter:app:url:googleplay"})
                        init_meta = str(init_meta)
                        id_number = init_meta.split('meta content="soundcloud://users:')[1].split(' ')[0].split('"')[0]
                        artist_social_link = f'https://api-v2.soundcloud.com/users/soundcloud:users:{id_number}/web-profiles?client_id={self.client_id}&app_version={int(time.time())}&app_locale=en'
                        #Might want to scrapify this part
                        #================================================
                        res = requests.get(artist_social_link, timeout=4)
                        json_data = res.json()
                        social_links = []
                        if json_data:
                            for social in json_data:
                                if social['network']:
                                    social_links.append(social['url'])
                        #================================================
                        if potential_emails or social_links:
                            items = {
                                "username" : user_name,
                                "followers" : user_followers,
                                "following" : user_following,
                                "social_links" : ' '.join(social_links),
                                "emails" : ' '.join(potential_emails),
                                "full_name" : user_full_name,
                                "user_id" : id_number,
                                "url" : user_link
                            }
                            tracklist_url = f'https://api-v2.soundcloud.com/users/{id_number}/toptracks?client_id={self.client_id}&limit=10&offset=0&linked_partitioning=1&app_version={int(time.time())}&app_locale=en'
                            res = requests.get(tracklist_url, headers=self.headers)
                            try:
                                json_data = res.json()
                            except ValueError:
                                logger.error('Error decoding JSON')
                                json_data = {}
                            try:
                                collection = json_data['collection']
                                genre_list = []
                                playcount_list = []
                                url_list = []
                                likecount_list = []
                                createdat_list = []
                                commentcount_list = []
                                for track in collection[0:3]:
                                    title = track['title']
                                    comment_count = track['comment_count']
                                    created_at = track['created_at']
                                    download_count = track['download_count']
                                    duration = track['duration']
                                    genre = track['genre']
                                    last_modified = track['last_modified']
                                    license = track['license']
                                    likes_count = track['likes_count']
                                    permalink_url = track['permalink_url']
                                    playback_count = track['playback_count']

                                    genre_list.append(genre)
                                    playcount_list.append(playback_count)
                                    likecount_list.append(likes_count)
                                    commentcount_list.append(comment_count)
                                    createdat_list.append(created_at)
                                    url_list.append(permalink_url)

                                genre_list = list(set(genre_list))

                                artist = {
                                    "Username" : user_name,
                                    "Followers" : user_followers,
                                    "Following" : user_following,
                                    "Genres" : " ".join(genre_list),
                                    "Location" : user_location,
                                    "# of Plays" : " ".join(list(map(str,playcount_list))),
                                    "# of Likes" : " ".join(list(map(str,likecount_list))),
                                    "# of Comments" : " ".join(list(map(str,commentcount_list))),
                                    "Dates Created" : " ".join(list(map(str,createdat_list))),
                                    "Track URLs" : " ".join(url_list),
                                    "Social Links" : " ".join(social_links),
                                    "Emails" : " ".join(potential_emails),
                                    "Full Name" : user_full_name,
                                    "URL" : user_link
                                }
                                self.to_csv(artist)
                                yield artist
                            except:
                                logger.error('problem getting tracks')
                                traceback.print_exc()
        except KeyError:
            logger.error('no "collection" in JSON (parseApiPage)')

    #grab api links
    def collect_links(self, response):
        try:
            json_data = json.loads(response.text)
        except ValueError:
            logger.error('Error decoding JSON')
            json_data = {}
        try:
            collection = json_data['collection']
            next_href = json_data['next_href']
            try:
                offset = next_href.split('offset=')[1].split('&')[0]
            except:
                return
            if '&offset' not in response.url:
                mutated_url = response.url + f'&offset={offset}'
            else:
                mutated_url = response.url.split('&offset=')[0] + f'&offset={offset}'
            with open('soundcloud_api.txt', 'a', encoding = 'utf-8') as link_file:
                link_file.write(f'{mutated_url}\n')
            yield response.follow(url = mutated_url, headers = self.headers, callback = self.collect_links)
        except KeyError:
            logger.error('no "collection" in JSON')

# main driver
if __name__ == '__main__':
    # run scraper
    process = CrawlerProcess()
    process.crawl(SoundcloudScraper)
    process.start()
