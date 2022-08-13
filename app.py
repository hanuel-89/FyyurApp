#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from email.utils import format_datetime
from datetime import date
import itertools
import operator
from re import RegexFlag
from xml.dom import ValidationErr
import dateutil.parser
import babel
from flask import render_template, request, flash, redirect, url_for

import logging
from logging import Formatter, FileHandler
from sqlalchemy import select
from forms import *

import models as appmod
import helper_functions as controller_funcs

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
#----------------------------------------------------------------------------#

@app.route('/venues')
def venues():
    """Venue controller. It shows the list of registered venues"""
    venue_list = controller_funcs.get_venues_by_city_and_state(
        db=db, app_model=appmod)
    return render_template('pages/venues.html', areas=venue_list)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # TODO: implement search on venues with partial string search. Ensure it is case-insensitive.
    try:
        search_term = request.form.get('search_term', '')
        response = controller_funcs.search_venue(
            db=db, app_model=appmod, search_term=search_term)
        return render_template('pages/search_venues.html', results=response[0], search_term=search_term)
    except Exception as e:
        print(e)
        flash("Venue " + str(search_term).upper() +
              " not found.\nBelow is the list of all available venues.")
    return venues()


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # Get the details of the venue and regroup the dictionary
    regrouped_data_list = controller_funcs.show_venue_OR_artist_details(
        db=db, app_model=appmod, for_venue_id=True)

    print(regrouped_data_list)

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
    # Get the venue field from the forms

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

    # Convert form response into boolean field acceptable by the db
    if seeking_talent == 'y':
        seeking_talent = True
    else:
        seeking_talent = False

    form = VenueForm(request.form)
    if request.method == 'POST' and form.validate():
        venue_form_input = appmod.Venue(
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
    else:
       flash('An error occured. ' + request.form['name'] + ' could not be listed. Please make sure you fill all the required fields correctly.')
       return render_template('forms/new_venue.html', form=form)
    try:
        db.session.add(venue_form_input)
        db.session.commit()
        flash('Venue: ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        flash('An error occured. Venue: ' + request.form['name'] + ' could not be listed')
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['GET', 'DELETE'])
def delete_venue(venue_id):
    error = False
    try:
        venue_id_to_delete = appmod.Venue.query.get(venue_id)
        db.session.delete(venue_id_to_delete)
        db.session.commit()
        flash("Successfully deleted Venue with ID = " + venue_id)
    except:
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('There was an error with your delete request')
        return index()
    else:
        return index()
#  Artists
# ----------------------------------------------------------------


@app.route('/artists')
def artists():

    artist_query = db.session.query(appmod.Artist.id, appmod.Artist.name)
    artist_list = []
    for row in artist_query:
        artist_list.append(row._asdict())

    return render_template('pages/artists.html', artists=artist_list)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    try:
        search_term = request.form.get('search_term', '')
        response = controller_funcs.search_artist(
            db=db, app_model=appmod, search_term=search_term)
        return render_template('pages/search_artists.html', results=response[0], search_term=search_term)
    except Exception as e:
        print(e)
        flash("Artist " + str(search_term).upper() +
              " not found.\nBelow is the list of all available artists.")
    return artists()


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    regrouped_data_list = controller_funcs.show_venue_OR_artist_details(
        db=db, app_model=appmod, for_artist_id=True)

    artist_data = list(filter(lambda d: d['id'] ==
                              artist_id, regrouped_data_list))[0]
    return render_template('pages/show_artist.html', artist=artist_data)

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
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
    edited_artist = db.session.query(appmod.Artist).get(artist_id)

    edited_artist.name = request.form['name']
    edited_artist.city = request.form['city']
    edited_artist.state = request.form['state']
    edited_artist.phone = request.form['phone']
    edited_artist.genres = request.form.getlist('genres')
    edited_artist.facebook_link = request.form['facebook_link']
    edited_artist.image_link = request.form['image_link']
    if request.form.get('seeking_venue') == 'y':
        edited_artist.seeking_venue = True
    else:
        edited_artist.seeking_venue = False
    edited_artist.website = request.form['website_link']

    edited_artist.seeking_description = request.form['seeking_description']

    db.session.commit()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/artists/<artist_id>/delete', methods=['GET', 'DELETE'])
def delete_artist(artist_id):

    error = False
    try:
        artist_id_to_delete = appmod.Artist.query.get(artist_id)
        db.session.delete(artist_id_to_delete)
        db.session.commit()
        flash("Successfully deleted Artist with ID = " + artist_id)
    except:
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('There was an error with your delete request')
        return index()
    else:
        return index()


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
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
        seeking_venue = True
    else:
        seeking_venue = False

    form = ArtistForm(request.form)
    if request.method == 'POST' and form.validate():
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
    else:
        flash('An error occured. ' + request.form['name'] + ' could not be listed. Please make sure you fill all the required fields correctly.')
        return render_template('forms/new_artist.html', form=form)
    try:
        db.session.add(form_artist_input)
        db.session.commit()
        flash('Artist: ' + request.form['name'] + ' was successfully listed!')
    except Exception as e:
        flash('An error occured. Artist: ' + request.form['name'] + ' could not be listed')
    return render_template('pages/home.html')


#  Show
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    data = controller_funcs.get_shows(db=db, app_model=appmod)
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # Render show forms
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    if request.method == 'POST' and form.validate():
        show = appmod.Show(
            venue_id=request.form.get('venue_id'),
            artist_id=request.form.get('artist_id'),
            start_time=request.form.get('start_time')
        )
    else:
        flash("Ensure that you use the correct data format")
        return render_template('forms/new_show.html', form=form)
    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully created')
    except Exception as e:
        flash('An error occured. "SHOW" could not be listed. Ensure that both "Artist" and "Venue" IDs are registered')

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
