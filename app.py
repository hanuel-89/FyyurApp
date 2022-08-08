#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import itertools
from datetime import date
import operator
import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy import JSON, inspect, select
import sqlalchemy
from forms import *
from flask_migrate import Migrate
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    website = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, default=True)
    seeking_description = db.Column(db.String(500))
    artists = db.relationship('Shows', back_populates='venue')

    # TODO: implement any missing fields, as a database migration using Flask-Migrate


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean, default=True)
    seeking_description = db.Column(db.String(500))
    venues = db.relationship('Shows', back_populates='artist')

    # TODO: implement any missing fields, as a database migration using Flask-Migrate


class Shows(db.Model):
    __tablename__ = 'Shows'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'))
    start_time = db.Column(db.Date, nullable=False)
    artist = db.relationship('Artist', back_populates='venues')
    venue = db.relationship('Venue', back_populates='artists')

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    # TODO: replace with real venues data.
    #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.

    # Query the Shows table to get the number of upcoming shows for each venue
    shows_alias_table = select([Shows.venue_id.label("venue_id"), db.func.count(Shows.venue_id).label(
        "num_upcoming_shows")]).where(Shows.start_time > db.func.now()).group_by(Shows.venue_id).alias()

    # Combine both shows_alias_table and Venue table to retrieve venue data
    data = db.session.query(Venue.id, Venue.city, Venue.state, Venue.name, shows_alias_table.c.num_upcoming_shows).outerjoin(
        shows_alias_table, shows_alias_table.c.venue_id == Venue.id).all()

    venue_list = []  # Create an empty list to append the regrouped query result

    for i, g in itertools.groupby(sorted(data, key=operator.itemgetter("city"), reverse=True), key=operator.itemgetter("city")):
        sub_object = list(g)
        venues = [{'id': obj['id'], 'name': obj['name'],
                   'num_upcoming_shows': obj['num_upcoming_shows']} for obj in sub_object]
        adict = {
            'city': i,
            'state': sub_object[0]['state'],
            'venues': venues
        }
        venue_list.append(adict)

    return render_template('pages/venues.html', areas=venue_list)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # TODO: implement search on venues with partial string search. Ensure it is case-insensitive.

    search_term = request.form.get('search_term', '')
    try:
      all_Venues = db.session.query(Venue.city, Venue.id, Venue.name).filter(
          Venue.name.ilike("%"+search_term+"%")).all()

      response = []
      for _, g in itertools.groupby(sorted(all_Venues, key=operator.itemgetter("city"), reverse=True), key=operator.itemgetter("city")):
            count = len(all_Venues)
            sub_object = list(g)
            data = [{'id': obj['id'], 'name': obj['name']}
                for obj in sub_object]
            adict = {
                'count': count,
                'data': data
            }
            response.append(adict)

      return render_template('pages/search_venues.html', results=response[0], search_term=request.form.get('search_term', ''))
    except Exception as e:
      print(e)
      flash("Venue " + str(search_term).upper() +
            " not found.\nBelow is the list of all available venues.")
    return venues()


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

    alias_query = db.session.query(Venue).cte()
    data_query_result = db.session.query(alias_query, Shows.artist_id, Artist.name.label("artist_name"), Artist.image_link.label(
        "artist_image_link"), Shows.start_time).join(alias_query, alias_query.c.id == Shows.venue_id, full=True).join(Artist, Artist.id == Shows.artist_id, full=True)

    data_list = []
    for data in data_query_result:
        data_list.append(data._asdict())

    data_list[:] = [delete_none_id for delete_none_id in data_list if delete_none_id.get(
        'id') != None]  # Delete ID's that are None based on the result of a full join query

    regrouped_data_list = []
    today = date.today()

    for _, g in itertools.groupby(
            sorted(data_list, key=operator.itemgetter("id"), reverse=False),
            key=operator.itemgetter("id")
    ):

        sub_object = list(g)

        upcoming_shows = []
        past_shows = []
        past_shows_count = 0
        upcoming_shows_count = 0
        for obj in sub_object:
            _, start_time = obj['id'], obj['start_time']
            if start_time is None:
                upcoming_shows = []
                past_shows = []

            elif start_time < today:
                past_shows.append(
                    {'artist_id': obj['artist_id'], 'artist_name': obj['artist_name'],
                     'artist_image_link': obj['artist_image_link'],
                     'start_time': start_time.strftime('%m/%d/%Y')}
                )
                past_shows_count += 1

            else:
                upcoming_shows.append(
                    {'artist_id': obj['artist_id'], 'artist_name': obj['artist_name'],
                     'artist_image_link': obj['artist_image_link'],
                     'start_time': start_time.strftime('%m/%d/%Y')}
                )
                upcoming_shows_count += 1

        adict = {
            **sub_object[0],
            'past_shows': past_shows,
            'upcoming_shows': upcoming_shows,
            'past_shows_count': past_shows_count,
            'upcoming_shows_count': upcoming_shows_count
        }
        regrouped_data_list.append(adict)


    venue_data = list(
        filter(lambda d: d['id'] == venue_id, regrouped_data_list))[0]
    return render_template('pages/show_venue.html', venue=venue_data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # TODO: insert form data as a new Venue record in the db, instead
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    address = request.form.get('address')
    phone = request.form.get('phone')
    genres = request.form.get('genres')
    facebook_link = request.form.get('facebook_link')
    image_link = request.form.get('image_link')
    website = request.form.get('website_link')
    seeking_talent = request.form.get('seeking_talent')
    seeking_description = request.form.get('seeking_description')

    if seeking_talent == 'y':
      seeking_talent = True
    else:
      seeking_talent = False
    form_venue_input = Venue(
        name=name,
        city=city,
        state=state,
        address=address,
        phone=phone,
        genres=genres,
        facebook_link=facebook_link,
        image_link=image_link,
        website=website,
        seeking_talent=seeking_talent,
        seeking_description=seeking_description
    )

    # TODO: modify data to be the data object returned from db insertion

    # on successful db insert, flash success
    try:
        db.session.add(form_venue_input)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        flash('An error occured. Venue' +
              request.form['name'] + 'could not be listed')
        print(e)

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # TODO: Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    try:
        venue_id_to_delete = Venue.query.get(venue_id)
        db.session.delete(venue_id_to_delete)
        db.session.commit()
        flash("Deletion completed")
    except Exception as e:
        flash('There was an error with your request')

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    # TODO: replace with real data returned from querying the database
    artist_query = db.session.query(Artist.id, Artist.name)
    artist_list = []
    for row in artist_query:
        artist_list.append(row._asdict())

    return render_template('pages/artists.html', artists=artist_list)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".

    search_term = request.form.get('search_term', '')
    try:
      artist_search = db.session.query(Artist.id, Artist.name).filter(
          Artist.name.ilike("%"+search_term+"%"))

      search_list = []
      for artist in artist_search:
          search_list.append(artist._asdict)


      response = []
      for _, g in itertools.groupby(sorted(artist_search, key=operator.itemgetter("id"), reverse=True)):
          count = len(search_list)
          sub_object = list(g)
          data = [{'id': obj['id'], 'name': obj['name']} for obj in sub_object]
          artist_search_dict = {
              **sub_object[0],
              'count': count,
              'data': data
          }
          response.append(artist_search_dict)
      return render_template('pages/search_artists.html', results=response[0], search_term=request.form.get('search_term', ''))
    except Exception as e:
      print(e)
      flash("Artist " + str(search_term).upper() + " not found.\nBelow is the list of all available artists.")
    return artists()


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    # TODO: replace with real artist data from the artist table, using artist_id

    artist_cte = db.session.query(Artist).cte()
    artist_query_result = db.session.query(artist_cte, Shows.venue_id, Venue.name.label("venue_name"),
                                           Venue.image_link.label("venue_image_link"), Shows.start_time).join(artist_cte, artist_cte.c.id == Shows.artist_id, full=True).join(Venue, Venue.id == Shows.venue_id, full=True)

    artist_data_list = []
    for data in artist_query_result:
        artist_data_list.append(data._asdict())

    artist_data_list[:] = [delete_none_id for delete_none_id in artist_data_list if delete_none_id.get('id') != None] # Delete ID's that are None based on the result of a full join query

    artist_regrouped_data_list = []
    today = date.today()

    for _, g in itertools.groupby(
            sorted(artist_data_list, key=operator.itemgetter(
                "id"), reverse=False),
            key=operator.itemgetter("id")
    ):

        sub_object = list(g)

        upcoming_shows = []
        past_shows = []
        past_shows_count = 0
        upcoming_shows_count = 0
        for obj in sub_object:
            _, start_time = obj['id'], obj['start_time']

            if start_time is None:
                upcoming_shows = []
                past_shows = []

            elif start_time < today:
                past_shows.append(
                    {'venue_id': obj['venue_id'], 'venue_name': obj['venue_name'],
                     'venue_image_link': obj['venue_image_link'],
                     'start_time': start_time.strftime('%m/%d/%Y')}
                )
                past_shows_count += 1

            else:
                upcoming_shows.append(
                    {'venue_id': obj['venue_id'], 'venue_name': obj['venue_name'],
                     'venue_image_link': obj['venue_image_link'],
                     'start_time': start_time.strftime('%m/%d/%Y')}
                )
                upcoming_shows_count += 1

        adict = {
            **sub_object[0],
            'past_shows': past_shows,
            'upcoming_shows': upcoming_shows,
            'past_shows_count': past_shows_count,
            'upcoming_shows_count': upcoming_shows_count
        }
        artist_regrouped_data_list.append(adict)

    artist_data = list(filter(lambda d: d['id'] ==
                              artist_id, artist_regrouped_data_list))[0]
    return render_template('pages/show_artist.html', artist=artist_data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = db.session.query(Artist).filter_by(id=artist_id).first()

    # TODO: populate form with fields from artist with ID <artist_id>
    form.name.data = artist.name
    form.city.data = artist.city
    form.state.data = artist.state
    form.phone.data = artist.phone
    form.genres.data = artist.genres
    form.facebook_link.data = artist.facebook_link
    form.image_link.data = artist.image_link
    form.website_link.data = artist.website
    form.seeking_venue.data = artist.seeking_venue
    form.seeking_description.data = artist.seeking_description

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes
    edited_artist = db.session.query(Artist).get(artist_id)

    edited_artist.name = request.form['name']
    edited_artist.city = request.form['city']
    edited_artist.state = request.form['state']
    edited_artist.phone = request.form['phone']
    edited_artist.genres = request.form.getlist('genres')
    edited_artist.facebook_link = request.form['facebook_link']
    edited_artist.image_link = request.form['image_link']
    if request.form['seeking_venue'] == 'y':
        edited_artist.seeking_venue = True
    else:
        edited_artist.seeking_venue = False
    edited_artist.website = request.form['website_link']

    edited_artist.seeking_description = request.form['seeking_description']

    db.session.commit()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = db.session.query(Venue).filter_by(id=venue_id).one()
    print(venue)
    # venues = []
    # for row in venue:
    #   venues.append(row._asdict())


    # TODO: populate form with fields from artist with ID <artist_id>
    form.name.data = venue.name
    form.city.data = venue.city
    form.state.data = venue.state
    form.phone.data = venue.phone
    form.genres.data = venue.genres
    form.address.data = venue.address
    form.facebook_link.data = venue.facebook_link
    form.image_link.data = venue.image_link
    form.website_link.data = venue.website
    form.seeking_talent.data = venue.seeking_talent
    form.seeking_description.data = venue.seeking_description
    print("--------------1------------------")
    print(venue.genres)

    # TODO: populate form with values from venue with ID <venue_id>
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # TODO: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes

    edited_venue = db.session.query(Venue).get(venue_id)

    edited_venue.name = request.form['name']
    edited_venue.city = request.form['city']
    edited_venue.state = request.form['state']
    edited_venue.phone = request.form['phone']
    edited_venue.genres = request.form.getlist('genres')
    edited_venue.address = request.form['address']
    print("----------------2--------------------")
    print(request.form.get('genres'))
    edited_venue.facebook_link = request.form['facebook_link']
    edited_venue.image_link = request.form['image_link']
    if request.form.get('seeking_talent') == 'y':
        edited_venue.seeking_talent = True
    else:
        edited_venue.seeking_talent = False
    edited_venue.website = request.form['website_link']

    edited_venue.seeking_description = request.form['seeking_description']

    db.session.commit()

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    # TODO: insert form data as a new Venue record in the db, instead
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    phone = request.form.get('phone')
    genres = request.form.get('genres')
    facebook_link = request.form.get('facebook_link')
    image_link = request.form.get('image_link')
    website = request.form.get('website_link')
    seeking_venue = request.form.get('seeking_venue')
    seeking_description = request.form.get('seeking_description')


    if seeking_venue == 'y':
        seeking_venue=True
    else:
        seeking_venue=False

    form_artist_input = Artist(
        name=name,
        city=city,
        state=state,
        phone=phone,
        genres=genres,
        facebook_link=facebook_link,
        image_link=image_link,
        website=website,
        seeking_venue=seeking_venue,
        seeking_description=seeking_description
    )

    try:
      db.session.add(form_artist_input)
      db.session.commit()
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        flash('An error occured. Artist ' +
              request.form['name'] + 'could not be listed')
        print(e)

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    # Query the Shows table to get the number of upcoming shows for each venue
    query = db.session.query(Shows.venue_id, Venue.name.label("venue_name"), Shows.artist_id, Artist.name.label("artist_name"), Artist.image_link.label(
        "artist_image_link"), Shows.start_time).join(Venue, Venue.id == Shows.venue_id).join(Artist, Artist.id == Shows.artist_id)

    data = []
    for show in query:
        data.append(show._asdict())

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    # TODO: insert form data as a new Show record in the db, instead
    show = Shows(
        venue_id=request.form.get('venue_id'),
        artist_id=request.form.get('artist_id'),
        start_time=request.form.get('start_time')
    )

    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully created')
    except sqlalchemy.exc.IntegrityError:
        flash('An error occured. Show could not be listed')

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
