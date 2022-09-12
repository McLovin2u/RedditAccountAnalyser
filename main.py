import json
import praw
import requests
from hashlib import blake2b
from bottle import route, run, template, static_file, post, request
from prawcore import NotFound
from operator import itemgetter

REDDIT_KEYS = 'keys.json' #Path to json containing credentials for PRAW

def getRedditUsingKeys(file):
    with open(file, 'r') as file:
        keys = json.loads(file.read())
        return praw.Reddit(
            client_id=keys['client_id'],
            client_secret=keys['client_secret'],
            user_agent=keys['user_agent'],
        )

def getImageBytes(url):
    with requests.get(url) as r:
        r.raise_for_status()
        return r.content


def getHash(imgBytes):
    h = blake2b(digest_size=20)
    h.update(imgBytes)
    return h.digest()


def user_exists(name):
    try:
        reddit.redditor(name).id
    except NotFound:
        return False
    return True


def getPosts(user, num_posts):
    if user == "" or not user_exists(user):
        return False
    redditor = reddit.redditor(user)
    submissions = redditor.submissions
    posts = {}
    for submission in submissions.new(limit=num_posts):
        posts[submission.id] = submission
    return posts


def getUniquePosts(user, num_posts):
    posts = getPosts(user, num_posts)
    if not posts:
        return False
    unique_posts = {}
    for submission in posts.values():
        if 'https' in submission.thumbnail:
            image_url = submission.thumbnail
            ident = getImageBytes(image_url)
        else:
            ident = submission.title
        unique_posts[ident] = {
            'post_url': f'https://reddit.com/{submission.permalink}',
            'out_url': submission.url,
            'title': submission.title,
            'sub': submission.subreddit.display_name,
            'upvotes': submission.ups,
            'thumbnail': submission.thumbnail
        }

    repost_rate = ((len(posts) - len(unique_posts)) / len(posts)) * 100
    return {
        'list': list(unique_posts.values()),
        'accountName': user,
        'repostRate': repost_rate,
        'numPosts': len(posts),
        'numUnique': len(unique_posts)
    }


@route('/')
def home():
    return static_file(filename='home.html', root='./static')


@post('/lookup')
def lookup():
    username = request.forms.get('username')
    num_posts = request.forms.get('num_posts')
    sort_by = request.forms.get('sort_by')
    if num_posts != "":
        num_posts = int(num_posts)
    else:
        num_posts = 50
    unique_posts = getUniquePosts(username, num_posts)
    if not unique_posts:
        return "USER DOES NOT EXIST"
    unique_posts['list'] = sorted(unique_posts['list'], key=itemgetter(sort_by))
    response = unique_posts
    return template('./static/results', response=response)


reddit = getRedditUsingKeys(REDDIT_KEYS)
run(host='localhost', port=8080)
