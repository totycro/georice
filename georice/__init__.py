#!/usr/bin/env python

from .imagery import GetSentinel, Geometry
from .ricemap import Ricemap
from .utils import load_config, show_config, save_config, set_sh, show_sh, Dir, mosaic
import os

class Georice:

    def __init__(self):
        self.config = load_config()
        self._imagery = GetSentinel()
        self._ricemap = Ricemap()

        self._get_tile_attr()

    def _get_tile_attr(self):
        for file in os.scandir(self.config['output']):
            if file.is_dir():
                setattr(self, file.name, Dir(file.path))

    def tiles(self):
        """Return list of tiles"""
        return [file.name for file in os.scandir(self.config['output']) if file.is_dir()]

    @staticmethod
    def set_credentials(**kwargs):
        """
        Save sentinel hub credentials into SHConfig. Credentials are:
        sh_client_id
        sh_client_secret
        instance_id
        More information about Sentinel-Hub credential at https://www.sentinel-hub.com/
        """
        for key in kwargs.keys():
            if key in ['sh_client_id', 'sh_client_secret', 'instance_id']:
                set_sh(key, kwargs[key])
            else:
                raise Exception(f'Key: {key} was not in expected keys  (sh_client_id, sh_client_secret, instance_id)')

    @staticmethod
    def show_credentials():
        """Show actual settingo of Sentinel Hub Credentials"""
        show_sh()

    def set_config(self, **kwargs):
        """Save setting of config file

        Parameters:
        polar - polarization; type: list; values VV, VH; default = ['VV','VH']; - used for filtering scenes
        orbit_path - orbit path; type: list; values ASC - ascending, DES - descending; default =['ASC','DES]; - used for filtering scenes
        scn_output - path to folder were scenes will be downloaded; type: str; required;
        rice_output - path to folder were will be saved generated rice maps; type: str; required;
        nodata - no data value; type: int; default = -999;
        timerange - used for filtering a merging S1B scenes which were acquired withing the time range; type: inf; default = 3600 s
        wsf_verison - type: str; default = '1.0.0'
        img_height - height of img in pixels; type: int; defualt = 1000;
        img_width - width of img in pixels; type: int; defualt = 1000;
        resx - resolution in x axis; type: int; default = 10;
        resy - resolution in y axis; type: int; default = 10;
        """
        save_config(kwargs)
        self.config = load_config()

    @staticmethod
    def show_config():
        """Save setting of config file

        Parameters:
        polar - polarization; type: list; values VV, VH; default = ['VV','VH']; - used for filtering scenes
        orbit_path - orbit path; type: list; values ASC - ascending, DES - descending; default =['ASC','DES]; - used for filtering scenes
        scn_output - path to folder were scenes will be downloaded; type: str; required;
        rice_output - path to folder were will be saved generated rice maps; type: str; required;
        nodata - no data value; type: int; default = -999;
        timerange - used for filtering a merging S1B scenes which were acquired withing the time range; type: inf; default = 3600 s
        wsf_verison - type: str; default = '1.0.0'
        img_height - height of img in pixels; type: int; defualt = 1000;
        img_width - width of img in pixels; type: int; defualt = 1000;
        resx - resolution in x axis; type: int; default = 10;
        resy - resolution in y axis; type: int; default = 10;
        """
        show_config()

    def find_scenes(self, bbox=None, epsg=None, period=None, info=True):
        """
        Find Sentinel 1 scenes from Sentinel Hub and return their list
        :param bbox: list of coordinates representing bbox
        :param epsg: int or str
        :param period: tuple (str, str). date format YYYYMMDD
        :param info: bool, turn off/on writing down list of found scenes
        """
        self._imagery.search(bbox, epsg, period)
        if info:
            self.scenes()

    def scenes(self):
        """Show found scenes"""
        self._imagery.scenes()

    def filter(self, inplace=False, **kwargs):
        """
        Provide filtering of found scenes according to given keyword arguments. Return the result of filtering, if
        inplace (default: False) is True, fond scenes are overwrite by filter result
        :param inplace: bool, default False, Overwrite scenes by filter result
        :param kwargs: keyword filtering arguments
        :return:
        """
        return self._imagery.filter(inplace, **kwargs)

    def get_scenes(self, name):
        self._imagery.download(name)
        print(f'Scenes were downloaded into {self.config["output"]}/{name}/scenes')
        self._get_tile_attr()

    def get_ricemap(self, name, period, orbit_path=None, orbit_number=None, inter=False, lzw=False, mask=False, nr=False):
        """
         Georice - generation of classified rice map
        "no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4

        Generete rice maps for given parameters of orbit number, orbit path and period and save them
        into rice_output path defined.
        orbit_number - orbit number; type: str; - three digits string representation i.e. '018'
        period - starting_date / ending_date => YYYYMMDD, type: tuple('str','str')
        orbit_path - orbit direction; type: str; values ASC - ascending, DES - descending; default = 'DES'
        inter - save intermediate products (min/max/mean/max_increase); type: bool; default = False
        lzv - use LZW compression; type: bool; default = False i.e. DEFLATE
        mask - generate and write rice, trees, water, other and nodata masks; type: bool; default = False
        nr - diable automatic reprojection to EPSG:4326, type: bool; default = True
        """
        self.filter(inplace=True, rel_orbit_num=orbit_number, orbit_path=orbit_path)

        if self._imagery.aoi.geometry.area >= load_config().get('max_area'):
            geom = Geometry(self._imagery.aoi.geometry, self._imagery.aoi.crs, grid_leght=(10000, 10000))
            copy = self._imagery.__copy__()
            for id, sub_aoi in enumerate(iter(geom)):
                part = f'part{id}-'
                grid = Geometry(sub_aoi[0], self._imagery.aoi.crs)
                copy.aoi = grid
                copy.download(tile_name=name, part=part)
                self._ricemap.ricemap_get(name, orbit_number, period, orbit_path, inter, lzw, mask, nr, part=part)
                self._get_tile_attr()
                self.__getattribute__(name).scenes.delete()
            mosaic(self.__getattribute__(name).ricemaps.file_paths())

        else:
            self._imagery.download(tile_name=name)
            self._ricemap.ricemap_get(name, orbit_number, period, orbit_path, inter, lzw, mask, nr)
            self._get_tile_attr()
            self.__getattribute__(name).scenes.delete()

        print(f'Rice maps were downloaded into {self.config["output"]}/{name}/ricemaps')



















