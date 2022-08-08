#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from email.utils import format_datetime
import itertools
from datetime import date
import operator
import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for

import logging
from logging import Formatter, FileHandler
from sqlalchemy import select
from forms import *

import models as appmod

from settings import app, db

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

    # Query the appmod.appmod.Shows table to get the number of upcoming shows for each venue
    shows_alias_table = select([appmod.Shows.venue_id.label("venue_id"), db.func.count(appmod.Shows.venue_id).label(
        "num_upcoming_shows")]).where(appmod.Shows.start_time > db.func.now()).group_by(appmod.Shows.venue_id).alias()

    # Combine both shows_alias_table and appmod.Venue table to retrieve venue data
    data = db.session.query(appmod.Venue.id, appmod.Venue.city, appmod.Venue.state, appmod.Venue.name, shows_alias_table.c.num_upcoming_shows).outerjoin(
        shows_alias_table, shows_alias_table.c.venue_id == appmod.Venue.id).all()

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
      all_Venues = db.session.query(appmod.Venue.city, appmod.Venue.id, appmod.Venue.name).filter(
          appmod.Venue.name.ilike("%"+search_term+"%")).all()

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
      flash("appmod.Venue " + str(search_term).upper() +
            " not found.\nBelow is the list of all available venues.")
    return venues()


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

    alias_query = db.session.query(appmod.Venue).cte()
    data_query_result = db.session.query(alias_query, appmod.Shows.artist_id, appmod.Artist.name.label("artist_name"), appmod.Artist.image_link.label(
        "artist_image_link"), appmod.Shows.start_time).join(alias_query, alias_query.c.id == appmod.Shows.venue_id, full=True).join(appmod.Artist, appmod.Artist.id == appmod.Shows.artist_id, full=True)

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

#  Create appmod.Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # TODO: insert form data as a new appmod.Venue record in the db, instead
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    address = request.form.get('address')
    phone = request.form.get('phone')
    genres = request.form.getlist('genres')
    facebook_link = request.form.get('facebook_link')
    image_link = request.form.get('image_link')
    website = request.form.get('website_link')
    seeking_talent = request.form.get('seeking_talent')
    seeking_description = request.form.get('seeking_description')

    if seeking_talent == 'y':
      seeking_talent = True
    else:
      seeking_talent = False
    form_venue_input = appmod.Venue(
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
        flash('appmod.Venue ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        flash('An error occured. appmod.Venue' +
              request.form['name'] + 'could not be listed')
        print(e)

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
    # TODO: Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    try:
        venue_id_to_delete = appmod.Venue.query.get(venue_id)
        db.session.delete(venue_id_to_delete)
        db.session.commit()
        flash("Successfully deleted appmod.Venue with ID = " + venue_id)
    except Exception as e:
        print(e)
        flash('There was an error with your delete request')
    return index()


    # BONUS CHALLENGE: Implement a button to delete a appmod.Venue on a appmod.Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage


#  appmod.Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    # TODO: replace with real data returned from querying the database
    artist_query = db.session.query(appmod.Artist.id, appmod.Artist.name)
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
      artist_search = db.session.query(appmod.Artist.id, appmod.Artist.name).filter(
          appmod.Artist.name.ilike("%"+search_term+"%"))

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
      flash("appmod.Artist " + str(search_term).upper() + " not found.\nBelow is the list of all available artists.")
    return artists()


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    # TODO: replace with real artist data from the artist table, using artist_id

    artist_cte = db.session.query(appmod.Artist).cte()
    artist_query_result = db.session.query(artist_cte, appmod.Shows.venue_id, appmod.Venue.name.label("venue_name"),
                                           appmod.Venue.image_link.label("venue_image_link"), appmod.Shows.start_time).join(artist_cte, artist_cte.c.id == appmod.Shows.artist_id, full=True).join(appmod.Venue, appmod.Venue.id == appmod.Shows.venue_id, full=True)

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
    form = appmod.ArtistForm()
    artist = db.session.query(appmod.Artist).filter_by(id=artist_id).first()

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
    edited_artist = db.session.query(appmod.Artist).get(artist_id)

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


@app.route('/artist/<artist_id>/delete', methods=['GET'])
def delete_artist(artist_id):
    # TODO: Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    try:
        artist_id_to_delete = appmod.Artist.query.get(artist_id)
        db.session.delete(artist_id_to_delete)
        db.session.commit()
        flash("Successfully deleted appmod.Artist with ID = " + artist_id)
    except Exception as e:
        print(e)
        flash('There was an error with your delete request')
    return index()


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = appmod.VenueForm()
    venue = db.session.query(appmod.Venue).filter_by(id=venue_id).one()

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

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):

    edited_venue = db.session.query(appmod.Venue).get(venue_id)

    edited_venue.name = request.form['name']
    edited_venue.city = request.form['city']
    edited_venue.state = request.form['state']
    edited_venue.phone = request.form['phone']
    edited_venue.genres = request.form.getlist('genres')
    edited_venue.address = request.form['address']
    edited_venue.facebook_link = request.form['facebook_link']
    edited_venue.image_link = request.form['image_link']
    edited_venue.website = request.form['website_link']
    edited_venue.seeking_description = request.form['seeking_description']
    if request.form.get('seeking_talent') == 'y':
        edited_venue.seeking_talent = True
    else:
        edited_venue.seeking_talent = False

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
    # TODO: insert form data as a new appmod.Venue record in the db, instead
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    phone = request.form.get('phone')
    genres = request.form.getlist('genres')
    facebook_link = request.form.get('facebook_link')
    image_link = request.form.get('image_link')
    website = request.form.get('website_link')
    seeking_venue = request.form.get('seeking_venue')
    seeking_description = request.form.get('seeking_description')


    if seeking_venue == 'y':
        seeking_venue=True
    else:
        seeking_venue=False

    form_artist_input = appmod.Artist(
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
      flash('appmod.Artist ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        flash('An error occured. appmod.Artist ' +
              request.form['name'] + 'could not be listed')
        print(e)

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    # Query the appmod.Shows table to get the number of upcoming shows for each venue
    query = db.session.query(appmod.Shows.venue_id, appmod.Venue.name.label("venue_name"), appmod.Shows.artist_id, appmod.Artist.name.label("artist_name"), appmod.Artist.image_link.label(
        "artist_image_link"), appmod.Shows.start_time).join(appmod.Venue, appmod.Venue.id == appmod.Shows.venue_id).join(appmod.Artist, appmod.Artist.id == appmod.Shows.artist_id)

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
    show = appmod.Shows(
        venue_id=request.form.get('venue_id'),
        artist_id=request.form.get('artist_id'),
        start_time=request.form.get('start_time')
    )

    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully created')
    except Exception as e:
        flash('An error occured. "SHOW appmod.Venue" could not be listed\n\n Ensure that both "appmod.Artist" and "appmod.Venue" IDs are registered')

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
