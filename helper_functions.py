from datetime import date
from flask import flash
from sqlalchemy import select
import itertools
import operator


def get_venues_by_city_and_state(db, app_model):
    """
        Gets the list of venues grouped by city and state
        ----
        Args
        ----
            db (SQLAlchemy): The ORM postgres object
            app_model (flask_alchemy_model): The app_model object references the tables in the database.
        -------
        Returns
        -------
            venue_list (dict): A list of all venues grouped by city and state.
    """
    shows_table_query = select([app_model.Shows.venue_id.label("venue_id"), db.func.count(app_model.Shows.venue_id).label(
        "num_upcoming_shows")]).where(app_model.Shows.start_time > db.func.now()).group_by(app_model.Shows.venue_id).alias()

    # Combine both shows_table_query and venue table to retrieve venue data
    query_result = db.session.query(app_model.Venue.id, app_model.Venue.city, app_model.Venue.state, app_model.Venue.name, shows_table_query.c.num_upcoming_shows).outerjoin(
        shows_table_query, shows_table_query.c.venue_id == app_model.Venue.id).all()

    venue_list = []  # Create an empty list to append the regrouped query result

    for i, g in itertools.groupby(sorted(query_result, key=operator.itemgetter("city"), reverse=True), key=operator.itemgetter("city")):
        sub_object = list(g)
        venues = [{'id': obj['id'], 'name': obj['name'],
                   'num_upcoming_shows': obj['num_upcoming_shows']} for obj in sub_object]
        adict = {
            'city': i,
            'state': sub_object[0]['state'],
            'venues': venues
        }
        venue_list.append(adict)

    return venue_list


def search_venue(db, app_model, search_term):
    """Implements a search query for listed venues
        ----
        Args
        ----
            db (SQLAlchemy): The ORM postgres object
            app_model (flask_alchemy_model): The app_model references the venue table in the database
            search_term (string): The search keyword
        -------
        Returns
        -------
            search_result (dict): A dictionary of the search query
    """
    all_Venues = db.session.query(app_model.Venue.city, app_model.Venue.id, app_model.Venue.name).filter(
        app_model.Venue.name.ilike("%"+search_term+"%")).all()

    search_result = []

    for _, g in itertools.groupby(sorted(all_Venues, key=operator.itemgetter("city"), reverse=True), key=operator.itemgetter("city")):
        count = len(all_Venues)
        sub_object = list(g)
        data = [{'id': obj['id'], 'name': obj['name']}
                for obj in sub_object]
        adict = {
            'count': count,
            'data': data
        }
        search_result.append(adict)

    return search_result


def search_artist(db, app_model, search_term):
    """Implements a search query for listed artists
        ----
        Args
        ----
            db (SQLAlchemy): The ORM postgres object
            app_model (flask_alchemy_model): The Artist object references the artist table in the database
            search_term (string): The search keyword
        -------
        Returns
        -------
            search_result (dict): A dictionary of the search query
    """
    artist_search = db.session.query(app_model.Artist.id, app_model.Artist.name).filter(
        app_model.Artist.name.ilike("%"+search_term+"%")).all()

    search_list = []
    for artist in artist_search:
        search_list.append(artist._asdict)

    search_result = []
    for _, g in itertools.groupby(sorted(artist_search, key=operator.itemgetter("id"), reverse=True)):
        count = len(search_list)
        sub_object = list(g)
        data = [{'id': obj['id'], 'name': obj['name']} for obj in sub_object]
        artist_search_dict = {
            **sub_object[0],
            'count': count,
            'data': data
        }
        search_result.append(artist_search_dict)

    return search_result


def get_artist(db, app_model):
    """
       Gets the list of all registered artists
       ----
       Args
       ----
           db (SQLAlchemy): The ORM postgres object
           app_model (flask_alchemy_model): The app_model object references the tables in the database.
       -------
       Returns
       -------
           artist_list (list): A list of dictionaries of all artists.
   """
    artist_query = db.session.query(app_model.Artist.id, app_model.Artist.name)

    artist_list = []
    for row in artist_query:
        artist_list.append(row.asdict())

    return artist_list


def show_venue_OR_artist_details(db, app_model, for_venue_id=False, for_artist_id=False):
    """
       Gets the full details of each selected venue or artist from the db by filtering by ID.
       The details includes past shows, upcoming shows, and counts of both
       ----
       Args
       ----
           db (SQLAlchemy): The ORM postgres object
           app_model (flask_alchemy_model): The app_model object references the tables in the database.
           for_venue_id (boolean): Uses the venue syntax to get the venue details
           for_artist_id (boolean): Uses the artist syntax to get the artist details
       -------
       Returns
       -------
           regrouped_data_list (dict):  A dic
   """
    if for_venue_id:
        show_1_id = app_model.Shows.artist_id
        show_2_id = app_model.Shows.venue_id
        table_name_smallcase = 'artist'
        cte_tableName = app_model.Venue
        tableName = app_model.Artist

    if for_artist_id:
        show_1_id = app_model.Shows.venue_id
        show_2_id = app_model.Shows.artist_id
        table_name_smallcase = 'venue'
        cte_tableName = app_model.Artist
        tableName = app_model.Venue

    table_id = 'table_id'.replace('table', table_name_smallcase)
    table_name = 'table_name'.replace('table', table_name_smallcase)
    table_image_link = 'table_image_link'.replace(
        'table', table_name_smallcase)

    table_cte = db.session.query(cte_tableName).cte()

    query_result = db.session.query(
        table_cte, show_1_id,
        tableName.name.label(table_name),
        tableName.image_link.label(table_image_link), app_model.Shows.start_time).join(table_cte, table_cte.c.id == show_2_id, full=True).join(tableName, tableName.id == show_1_id, full=True)

    data_list = []
    for data in query_result:
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
                    {table_id: obj[table_id], table_name: obj[table_name],
                     table_image_link: obj[table_image_link],
                     'start_time': start_time.strftime('%m/%d/%Y')}
                )
                past_shows_count += 1

            else:
                upcoming_shows.append(
                    {table_id: obj[table_id], table_name: obj[table_name],
                     table_image_link: obj[table_image_link],
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
    print(regrouped_data_list)
    return regrouped_data_list


def get_shows(db, app_model):
    """
        Gets the list of scheduled shows across various venues        ----
        Args
        ----
            db (SQLAlchemy): The ORM postgres object
            app_model (flask_alchemy_model): The app_model object references the tables in the database.
        -------
        Returns
        -------
            venue_list (dict): A list of all venues grouped by city and state.
    """
    query = db.session.query(
        app_model.Shows.venue_id,
        app_model.Venue.name.label("venue_name"),
        app_model.Shows.artist_id,
        app_model.Artist.name.label("artist_name"),
        app_model.Artist.image_link.label(
            "artist_image_link"),
        app_model.Shows.start_time).join(app_model.Venue, app_model.Venue.id == app_model.Shows.venue_id).join(app_model.Artist, app_model.Artist.id == app_model.Shows.artist_id)

    data = []
    for show in query:
        data.append(show._asdict())
    return data
