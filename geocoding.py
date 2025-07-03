"""
This file helps to connect multiple geocoding/reverse-geocoding providers

As of today, Dated: 18-01-2025
This app heavily relies on free service providers
and might change to Paid service providers in future
"""
from functools import wraps

# import geocoder  # geocoder is not working as expected
from geopy.geocoders import Nominatim
import geopy.location

# from jnius_helper import autoclass
from tools import Constants

_ = """
Some available geocoding APIs from geocoder

without API key:
      provider        usage        optimal    support reverse-geocoding
    * ArcGIS                                   {Yes}
    * OpenStreetMap (Policy)                   {Yes}  <- OSM powered
    * Komoot                                   {Yes}  <- OSM powered
    * GecodeFarm    (Policy)                   {Yes}
    * USCensus                     [US]        {Yes}
    * Yandex                       [Russia]    {Yes}
    * GeoNames      (Username)
    * MaxMind
    * Yahoo
    * GeoOttawa                    [Ottawa]
    * TGOS                         [Taiwan]
    * IPInfo        (Rate limit)                      <- Has Plans
    * Geocoder.ca   (Rate limit)   [CA & US]


With API key:
    * Google                   {Yes}
    * Bing                     {Yes}
    * Gisgraphy                {Yes}
    * HERE                     {Yes}
    * LocationIQ               {Yes}
    * Mapbox                   {Yes}
    * MapQuest                 {Yes}
    * OpenCage                 {Yes}
    * What3Words               {Yes}
    * Gaode        [China]     {Yes}
    * TomTom
    * Tamu         [US]
    * Baidu        [China]
    * CanadaPost   [Canada]

"""

__reverse_geocode_cache: dict[tuple[float: 4], geopy.location.Location] = {}
__geocode_cache: dict[str, geopy.location.Location | None] = {}


def __cache_it(lat: tuple[float: 2] | str, lng: tuple[float, float] = None, *, data: geopy.location.Location | None):
    """
    Caching service, automatically switches between geocoding and reverse
    :param lat:
    :param lng:
    :param data:
    :return:
    """
    global __reverse_geocode_cache
    if lng is not None:
        assert isinstance(lat, tuple)
        lat: tuple[float, float] = lat
        cords = lat + lng
        __reverse_geocode_cache[cords] = data
    else:
        assert isinstance(lat, str)
        loc: str = lat.strip()
        loc = loc.lower()
        __geocode_cache[loc] = data

        # below code is already written in caching function

        # b_box: list[str] = data._raw.get(['boundingbox'], None)  # noqa
        # if b_box is None:
        #     return
        # b_box: list[float] = list(map(float, b_box))
        # a = b_box[0], b_box[1]
        # b = b_box[2], b_box[3]
        # __cache_it(a, b, data=data)  # caching cords


def __get_cached(lat: float | str, lng: float = None) -> tuple[geopy.location.Location, bool] | None:
    """
    Used to get cached data.
    :param lat:
    :param lng:
    :return: Sometime may return None if the location name is actually not available at the server
    """
    is_cached_data = True
    if lng is not None:
        assert isinstance(lat, float | int)
        for cords in __reverse_geocode_cache.keys():
            if cords[0] <= lat <= cords[1] and cords[2] <= lng <= cords[3]:
                out = __reverse_geocode_cache[cords]
                break
        else:
            is_cached_data = False
            out = None

    else:
        if lat not in __geocode_cache:
            is_cached_data = False
        out = __geocode_cache.get(lat, None)
    return out, is_cached_data


def _cached_geocoding(func):
    """
    As mentioned here https://operations.osmfoundation.org/policies/nominatim/
    it says that "Results must be cached on your side. Clients sending repeatedly the same query may be
    classified as faulty and blocked."
    This function helps us to cache the result

    In this version (2.1.0), caching is limited to storing it in a variable
    in future it will be changed to file type cache
    due to security issue this is not done
    :param func: function name
    :return:
    """
    @wraps(func)
    def wrapper(*args) -> tuple[geopy.location.Location | None, bool]:
        if len(args) > 2:  # reverse geocoding
            is_reverse_mode = True
            _self, lat, lng = args
            cached_data, is_cached_data = __get_cached(lat, lng)
            # required 2 variables, cuz somtimes cached_data can be None intentionally
            # this happens when the co-ordinates/location name is not available on the server
        else:
            is_reverse_mode = False
            _self, loc = args
            loc = loc.lower()
            cached_data, is_cached_data = __get_cached(loc)
        print(f'Cache state is {__geocode_cache} and \n {__reverse_geocode_cache}')
        if is_cached_data:  # returns even if it is None, cuz unknown location is referred as None
            return cached_data, True
        out: geopy.location.Location = func(*args)
        if not is_reverse_mode:
            _, loc = args
            __cache_it(loc, data=out)  # cache even if it is None
        if out is None:
            return None, False

        raw_data: dict = out.raw

        bounding_box: list[str] = raw_data.get('boundingbox', None)
        if bounding_box is None:
            return out, False
        # Bounding box details is as follows:
        # src: https://wiki.openstreetmap.org/wiki/Bounding_box
        #    A bounding box (Usually shortened to bbox) is an area defined by two longitudes and two latitudes,
        #    where:
        #        * Latitude is a decimal number between -90.0 and 90.0
        #        * Longitude is a decimal number between -180.0 and 180.0,
        #    They usually follow the standard format of:
        #       -> bbox = left, bottom,  right, top
        #       -> min Longitude, min Latitude, max Longitude, max Latitude (I don't think so)

        bounding_box: list[float] = list(map(float, bounding_box))
        x1, x2, y1, y2 = bounding_box
        lat = (x1, x2) if x1 < x2 else (x2, x1)  # sorting values
        lng = (y1, y2) if y1 < y2 else (y2, y1)  # may not be needed but doing it anyway
        __cache_it(lat, lng, data=out)
        return out, False
    return wrapper


class GeocoderClient:
    # service_providers = {'osm': geocoder.osm,
    #                      'ArcGIS': geocoder.arcgis,
    #                      'Komoot': geocoder.komoot}
    selected_provider = Nominatim

    # On geopy this is set to False, making android app not able to use the internet

    def __init__(self, ssl_context):
        self.provider = self.selected_provider(user_agent=Constants.PACKAGE_NAME, ssl_context=ssl_context)
        # self.__enable_trust()

    def __enable_trust(self):
        self.provider.adapter.session.trust_env = True

    def change_provider(self):
        # Not implemented yet
        pass

    @_cached_geocoding
    def geocode(self, location: str) -> geopy.location.Location:
        """
        Gets the coordinates using the location name of form str
        :param location: Location name
        :return:
        """
        out = self.provider.geocode(location)
        print(out)
        print(type(out))
        return out

    @_cached_geocoding
    def reverse_geocode(self, lat: float, lng: float) -> geopy.location.Location:
        """
        Converts gps coordinates to location and name
        :param lat:
        :param lng:
        :return:
        """
        return self.provider.reverse(f'{lat}, {lng}')


if __name__ == '__main__':
    client = GeocoderClient(ssl_context=None)
    # add = client.geocode('Bengaluru')
    add = client.geocode("belagavi")
    client.reverse_geocode(13.0004527, 76.9895111)
    print(f'Location is: {add}')

    box = add._raw['boundingbox']
    print(box)
    print(type(box))

    # ['13.0004527', '13.0043886', '76.9895111', '77.0145693']
    # <class 'list'>

    print(add._raw)
