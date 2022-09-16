import json
import bottle
import praw
import redis
import requests
from hashlib import blake2b
from bottle import route, run, template, static_file, post, request
from prawcore import NotFound
import bottle_session
import bottle_redis
import io
import imagehash
from PIL import Image

REDDIT_KEYS = 'keys.json'  # Path to json containing credentials for PRAW


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
        image = Image.open(io.BytesIO(r.content))
        hash = imagehash.average_hash(image)
        return hash


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


def deleteDuplicatePosts(posts):
    unique_posts = {}
    for post in posts:
        if 'http' in post['thumbnail']:
            ident = getImageBytes(post['thumbnail'])
        else:
            ident = post['title']
        unique_posts[ident] = post
    return list(unique_posts.values())


def fetchPosts(username, num_posts, rdb: redis.Redis):
    redditor = reddit.redditor(username)
    submissions = redditor.submissions.new(limit=num_posts)
    if rdb.get(username + '_max_tried') is not None and int(rdb.get(username + '_max_tried')) >= num_posts:
        print("fetching from Redis")
        return
    print("fetching from API")
    rdb.set(username+'_max_tried', num_posts)
    for submission in submissions:
        rdb.hset(name=submission.id, key='post_id', value=submission.id)
        rdb.hset(name=submission.id, key='title', value=submission.title)
        rdb.hset(name=submission.id, key='thumbnail', value=submission.thumbnail)
        rdb.hset(name=submission.id, key='upvotes', value=int(submission.ups))
        rdb.hset(name=submission.id, key='post_url', value=f'https://reddit.com{submission.permalink}')
        rdb.hset(name=submission.id, key='out_url', value=submission.url)
        rdb.hset(name=submission.id, key='sub', value=submission.subreddit.display_name)

        rdb.sadd(username + 'subs', submission.subreddit.display_name)
        rdb.sadd(username + submission.subreddit.display_name, submission.id)
        rdb.sadd(username + 'ids', submission.id)


def createOverview(rdb: redis.Redis, session, sort_by='upvotes', unique=False):
    username = session['username']
    post_ids = rdb.smembers(username + 'ids')
    posts = []
    for id in post_ids:
        posts.append(rdb.hgetall(id))
    if unique:
        posts = deleteDuplicatePosts(posts)
    subs = []
    posts.sort(key=lambda x: int(x[sort_by]) if sort_by == 'upvotes' else x[sort_by], reverse=sort_by=='upvotes')
    for sub in rdb.smembers(username + 'subs'):
        subs.append({
            'name': sub,
            'size': rdb.scard(username + sub)
        })
    return {
        'username': username,
        'posts': posts,
        'subs': subs,
        'num_posts': len(posts)
    }


def createSubPage(rdb: redis.Redis, session, sub):
    username = session['username']
    post_ids = rdb.smembers(username + sub)
    posts = []
    for id in post_ids:
        posts.append(rdb.hgetall(id))
    posts.sort(key=lambda x: int(x['upvotes']), reverse=True)
    return ({
        'username': username,
        'subName': sub,
        'posts': posts,
        'num_posts': len(posts)
    })


def checkDefault(input, default):
    if input == "" or input is None:
        return default
    else:
        return int(input)


def checkParams(username, num_posts):
    if username == "":
        return False
    try:
        reddit.redditor(username).id
    except:
        return False
    return True


@route('/')
def home(session):
    return static_file(filename='home.html', root='./static')


@post('/overview')
def lookup(session, rdb):
    username = request.forms.get('username')
    session['username'] = username
    num_posts = checkDefault(request.forms.get('num_posts'), 50)
    session['num_posts'] = num_posts
    if checkParams(username, num_posts):
        fetchPosts(username, num_posts, rdb)
        response = createOverview(rdb, session)
        return template('./static/overview', response=response)
    else:
        return 'BAD INPUT'


@route('/overview')
def lookup(session, rdb):
    if session['username'] is None:
        return static_file(filename='redirect.html', root='./static')
    username = session['username']
    num_posts = int(session['num_posts'])
    unique = request.GET.get('unique', False)
    sort_by = request.GET.get('sort_by', 'upvotes')

    if checkParams(username, num_posts):
        fetchPosts(username, num_posts, rdb)
        response = createOverview(rdb, session, sort_by=sort_by, unique=unique)
        return template('./static/overview', response=response)
    else:
        return 'BAD INPUT'


@post('/singleSub')
def lookup(session, rdb):
    if session['username'] is None:
        return static_file(filename='redirect.html', root='./static')
    sub = request.forms.get('sub')
    response = createSubPage(rdb, session, sub)
    return template('./static/sub', response=response)


reddit = getRedditUsingKeys(REDDIT_KEYS)
app = bottle.default_app()
session_plugin = bottle_session.SessionPlugin(cookie_lifetime=300)
redis_plugin = bottle_redis.RedisPlugin(host='localhost', decode_responses=True)
app.install(session_plugin)
app.install(redis_plugin)
run(app=app, host='localhost', port=8080, debug=True)
