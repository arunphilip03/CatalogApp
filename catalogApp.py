from flask import Flask, render_template, request, redirect, jsonify, url_for,\
 flash
from functools import wraps
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from database_setup import Category, Item, Base, User
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"


# Connect to database and create database session
#engine = create_engine('sqlite:///itemcatalog.db')
engine = create_engine('postgresql://vagrant:vagrant@localhost:5432/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

categories = session.query(Category).order_by(asc(Category.name))


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected\
        	.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = 'success'
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        return "you have been logged out"

    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.10/me"

    '''
        Due to the formatting for the result from the server token exchange we
        have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then we
        split it on colons to pull out the actual token value and replace the
        remaining quotes with nothing so that it can be used directly in the
        graph api calls.
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.10/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.10/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = 'success'

    flash("Logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# JSON API to fetch all Items in a Category
@app.route('/category/<string:category_name>/items/JSON')
def categoryItemsJSON(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_id=category.id).all()
    return jsonify(Items=[i.serialize for i in items])

# JSON API to fetch information about an item under a category


@app.route('/category/<string:category_name>/item/<string:item_name>/JSON')
def itemJSON(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(
        category_id=category.id, name=item_name).one()
    return jsonify(Item=item.serialize)

# JSON API to fetch all Categories


@app.route('/category/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[r.serialize for r in categories])


# Show all categories
@app.route('/')
@app.route('/catalog')
def showCatalog():
    latestItems = session.query(Item).order_by(
        desc(Item.created_date)).limit(10).all()
    if 'username' not in login_session:
        return render_template('publicCatalog.html', categories=categories,
                               latestItems=latestItems)
    else:
        return render_template('catalog.html', categories=categories,
                               latestItems=latestItems)


# Show items in a category
@app.route('/category/<string:category_name>')
@app.route('/category/<string:category_name>/items')
def showAllItems(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_id=category.id).all()
    countItems = session.query(Item).filter_by(category_id=category.id).count()

    if 'username' not in login_session:
        return render_template('publicItems.html', categories=categories,
                               category=category, items=items, count=countItems)
    else:
        return render_template('items.html', categories=categories,
                               category=category, items=items, count=countItems)


# Show an item
@app.route('/category/<string:category_name>/item/<string:item_name>')
def showItem(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    item = session.query(Item).filter_by(category_id=category.id, name=item_name).one()
    creator = getUserInfo(item.user_id)

    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicViewItem.html', category=category, item=item)
    else:
        return render_template('viewItem.html', category=category, item=item)


# Add new item under a category
@app.route('/category/<string:category_name>/item/new',
           methods=['GET', 'POST'])
@login_required
def addCategoryItem(category_name):

    if request.method == 'POST':
        category = session.query(Category).filter_by(name=category_name).one()
        newItem = Item(name=request.form['itemName'], description=request.form[
                       'description'], category_id=request.form['category'],
                       user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('New Item "%s" created successfully' % newItem.name)
        return redirect(url_for('showAllItems', category_name=category_name))

    else:
        return render_template('newItem.html', categories=categories,
                               category_name=category_name)


# Add new item
@app.route('/category/item/new', methods=['GET', 'POST'])
@login_required
def addItem():

    if request.method == 'POST':
        newItem = Item(name=request.form['itemName'], description=request.form[
                       'description'], category_id=request.form['category'],
                       user_id=login_session['user_id'])
        try:
            session.add(newItem)
            session.commit()
            flash('New Item %s created successfully' % newItem.name)
            return redirect(url_for('showCatalog'))
        except IntegrityError:
            print 'Caught error'
            session.rollback()
            flash('Item with name %s already exists in selected category %s' %
                  request.form['itemName'])
            return redirect(url_for('showCatalog'))

    else:
        return render_template('newItem.html', categories=categories)


# Edit Item
@app.route('/category/<string:category_name>/item/<string:item_name>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(category_name, item_name):

    category = session.query(Category).filter_by(name=category_name).one()
    editedItem = session.query(Item).filter_by(
        category_id=category.id, name=item_name).one()

    if editedItem.user_id != login_session['user_id']:
        flash('You are not authorized to edit item  "%s"' % item_name)
        return redirect(url_for('showItem', category_name=category_name,
                                item_name=item_name))

    if request.method == 'POST':
        if request.form['itemName']:
            editedItem.name = request.form['itemName']

        if request.form['description']:
            editedItem.description = request.form['description']

        if request.form['category']:
            editedItem.category_id = request.form['category']

        session.add(editedItem)
        session.commit()
        flash('Changes to Item %s saved successfully' % editedItem.name)

        return redirect(url_for('showAllItems', category_name=category_name))

    else:
        return render_template('editItem.html', categories=categories,
                               category_name=category_name,
                               item_name=item_name, item=editedItem)


# Delete Item
@app.route('/category/<string:category_name>/item/<string:item_name>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_name, item_name):

    category = session.query(Category).filter_by(name=category_name).one()
    deleteItem = session.query(Item).filter_by(
        category_id=category.id, name=item_name).one()

    if deleteItem.user_id != login_session['user_id']:
        flash('You are not authorized to delete %s' % item_name)
        return redirect(url_for('showItem', category_name=category_name,
                                item_name=item_name))

    if request.method == 'POST':
        session.delete(deleteItem)
        session.commit()
        flash('Item %s deleted successfully' % item_name)

        return redirect(url_for('showAllItems', category_name=category_name))

    else:
        return render_template('deleteItem.html', category_name=category_name,
                               item=deleteItem)


# Disconnect based on provider (Google or Facebook)
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        del login_session['access_token']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalog'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalog'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
