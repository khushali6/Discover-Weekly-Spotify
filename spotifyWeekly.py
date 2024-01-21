import spotipy
import time
import os
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect


# initialize Flask app
app = Flask(__name__)

# set the name of the session cookie
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

# set a random secret key to sign the cookie
app.secret_key = 'YOUR_SECRET_KEY'

# set the key for the token info in the session dictionary
TOKEN_INFO = 'token_info'

@app.route('/')
def login():
    # create a SpotifyOAuth instance and get the authorization URL
    auth_url = create_spotify_oauth().get_authorize_url()
    # redirect the user to the authorization URL
    return redirect(auth_url)


@app.route('/redirect')
def redirect_page():
    # clear the session
    session.clear()
    # get the authorization code from the request parameters
    code = request.args.get('code')
    # exchange the authorization code for an access token and refresh token
    token_info = create_spotify_oauth().get_access_token(code)
    # save the token info in the session
    session[TOKEN_INFO] = token_info
    # redirect the user to the save_discover_weekly route
    return redirect(url_for('save_discover_weekly',_external=True))

@app.route('/saveDiscoverWeekly')
def save_discover_weekly():
    try:
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")

    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # get the user's playlists
    current_playlists = sp.current_user_playlists()['items']
    discover_weekly_playlist_id = None
    saved_weekly_playlist_id = None
    user_id = sp.current_user()['id']

    # find the Discover Weekly and Saved Weekly playlists
    for playlist in current_playlists:
        print("Playlist Name:", playlist['name'])
        if playlist['name'] == 'Discover Weekly':
            discover_weekly_playlist_id = playlist['id']
        elif playlist['name'] == 'Saved Weekly':
            saved_weekly_playlist_id = playlist['id']

    # if the Discover Weekly playlist is not found, return an error message
    if not discover_weekly_playlist_id:
        return 'Discover Weekly not found.'

    # Check if the Saved Weekly playlist already exists
    if not saved_weekly_playlist_id:
        # Create a new playlist only if it doesn't exist
        playlists = sp.user_playlists(user_id)
        for playlist in playlists['items']:
            if playlist['name'] == 'Saved Weekly':
                saved_weekly_playlist_id = playlist['id']
                break

        if not saved_weekly_playlist_id:
            new_playlist = sp.user_playlist_create(user_id, 'Saved Weekly', True)
            saved_weekly_playlist_id = new_playlist['id']

    # get the tracks from the Discover Weekly playlist
    discover_weekly_playlist = sp.playlist_items(discover_weekly_playlist_id)
    song_uris = [song['track']['uri'] for song in discover_weekly_playlist['items']]

    # add the tracks to the Saved Weekly playlist
    sp.user_playlist_add_tracks(user_id, saved_weekly_playlist_id, song_uris, None)

    # return a success message
    return 'Discover Weekly songs added successfully'



# function to get the token info from the session
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # if the token info is not found, redirect the user to the login route
        redirect(url_for('login', _external=False))
    
    # check if the token is expired and refresh it if necessary
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id =os.environ.get('SPOTIPY_CLIENT_ID'),
        client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET'),
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private'
    )


app.run(debug=True)