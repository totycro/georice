#!/usr/bin/env python

import click
import json
import os
import subprocess

from georice.utils import set_sh, show_sh, load_config, show_config


@click.group()
@click.version_option()
def main():
    """
    Georice - generation of classified rice map
    "no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4
    """
    pass


@main.group('sentinel', invoke_without_command=True)
@click.option('--show', '-s', 'show', is_flag=True,
              help='Show actual Sentinel-hub credentials (client_id, client_secret, instance_id)')
def sentinel(show):
    """Configuration of Sentinel Hub credentials"""
    if show:
        show_sh()

@sentinel.command('client_id')
@click.argument('value')
def client(value):
    """Set Sentinel hub client id"""
    set_sh('sh_client_id', value)
    click.echo(f'Client id: {value} was set')


@sentinel.command('client_secret')
@click.argument('value')
def client(value):
    """Set Sentinel hub client secret"""
    set_sh('sh_client_secret', value)
    click.echo(f'Client secret: {value} was set')


@sentinel.command('instance_id')
@click.argument('value')
def client(value):
    """Set Sentinel hub instance id"""
    set_sh('instance_id', value)
    click.echo(f'Instance id: {value} was set')


@main.group('config', invoke_without_command=True)
@click.option('--show', '-s', 'show', is_flag=True,
              help='Show actual setting georice config file')
def config(show):
    """Configuration of georice configuration file"""
    if show:
        show_config()


@config.command('set')
@click.argument('key')
@click.argument('value')
def set_config(key, value):
    """Save selected parameters of georice config file"""
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    config = load_config()
    config.update({key: type(config[key])(value)})
    with open(config_file, 'w') as cfg_file:
        json.dump(config, cfg_file, indent=2)


@main.group(name="imagery", invoke_without_command=True)
@click.option('--bbox', '-b', 'bbox', type=float, required=False, nargs=4, help='AOI bbox as minx miny maxx maxy')
@click.option('--geopath', '-g', 'geopath', default='', required=False, type=str,
              help='Path to geofile with AOI. Geofile have to be opened via geopandas')
@click.option('--epsg', '-e','epsg', type=str, default=None, required=False,
              help='Epsg code of bbox projection')
@click.option('--period', '-p', 'period', type=(str, str), default=None, required=True,
              help='Time period in format YYYYMMDD. e.g. 20180101 20180101')
@click.option('--tile', '-t', 'tile', type=str, default='Tile', required=False, help='Tile name')
def imagery(bbox, geopath, epsg, period, tile):
    """Download Sentinel 1A/1B scenes from Sentinel Hub"""
    from .imagery import GetSentinel
    import geopandas

    if len(bbox) == 0 and len(geopath) == 0:
        click.echo('Command aborted. Is required to provide AOI as bbox or path to geofile')
        quit()
    elif len(bbox) == 0:
        task = GetSentinel()
        geofile = geopandas.read_file(geopath)
        task.search(bbox=geofile, epsg=epsg, period=period, tile_name=tile)
        click.echo(f'For given parameters: {len(task._scenes)} scenes was found\n')
    elif len(geopath) == 0:
        task = GetSentinel()
        task.search(bbox=bbox, epsg=epsg, period=period, tile_name=tile)
        click.echo(f'For given parameters: {len(task._scenes)} scenes were found')

    if len(task._scenes) > 0:
        task.dump()
        click.echo(f'Scenes were downloaded in folder {task.config["output"]}/{tile}/scenes')


@main.group('ricemap', invoke_without_command=True)
@click.option('--tile', '-t', 'tile', type=str, default='Tile', required=False, help='Tile name')
@click.option('--all', '-a', 'a', is_flag=True, required=False,
              help='Generate rice maps for all combinations of orbit number, '
                   'direction a period found at scene directory')
def ricemap(tile, a):
    """
    Generate rice map from Sentinel imagery
    Tile - tile name used for downolad of scenes
    """
    if a:
        scene_path = os.path.join(load_config()['output'], tile, 'scenes')
        period, orb_num, orbit_path = set(), set(), set()
        with os.scandir(scene_path) as files:
            for file in files:
                if file.is_file():
                    parsed = file.name.split('_')
                    period.add(parsed[5])
                    orb_num.add(parsed[4])
                    orbit_path.add(parsed[3])
        for orbit in orbit_path:
            for num in orb_num:
                command = ['ricemap.py', scene_path, num, min(period), max(period),
                           config['output'], '-d', orbit]
                subprocess.run(' '.join(command), shell=True)
                click.echo(f'Ricemap for orbit path/orbit number/period: {orbit}/{num}/{min(period)}/{max(period)} '
                           f'saved at folder: {os.path.join(load_config()["output"], tile)}')


@ricemap.command('get')
@click.argument('orbit_number')
@click.argument('starting_date')
@click.argument('ending_date')
@click.option('--tile', '-t', 'tile', type=str, default='Tile', required=False, help='Tile name')
@click.option('--orbit_path', '-o', 'orbit_path', default='DES', required=False, type=str,
              help='Orbit direction. default DES, velues (ASC / DES)')
@click.option('--intermediate', '-i', 'inter', is_flag=True, required=False,
              help='write intermediate products (min/max/mean/max_increase)')
@click.option('-lzw', 'lzw', is_flag=True, required=False,
              help='write output tiff products using LZW compression instead of DEFLATE (compatibility with ENVI/IDL)')
@click.option('--mask', '-m', 'mask', is_flag=True, required=False,
              help='generate and write rice, trees, water, other and nodata masks')
@click.option('--noreproject', '-nr', 'nr', is_flag=True, required=False,
              help='diable automatic reprojection to EPSG:4326')
def get(orbit_number, starting_date, ending_date, tile, orbit_path, inter, lzw, mask, nr):
    """
    Generate rice map for specyfic parameters.
    NOTE: starting_date / ending_date => YYYYMMDD, inclusive
    """
    scene_path = os.path.join(load_config()['output'], tile, 'scenes')
    command = ['ricemap.py', scene_path, orbit_number, starting_date, ending_date, load_config()['output']]
    if orbit_path:
        command.append('-d ' + orbit_path)
    if inter:
        command.append('-i')
    if lzw:
        command.append('-lzw')
    if mask:
        command.append('-m')
    if nr:
        command.append('-nr')
    subprocess.run(' '.join(command), shell=True)
    click.echo(f'Rice map saved into folder: {os.path.join(load_config()["output"], tile)}')
