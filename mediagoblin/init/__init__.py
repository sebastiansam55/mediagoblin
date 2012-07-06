# GNU MediaGoblin -- federated, autonomous media hosting
# Copyright (C) 2011, 2012 MediaGoblin contributors.  See AUTHORS.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options
import jinja2

from mediagoblin.tools import staticdirect
from mediagoblin.init.config import (
    read_mediagoblin_config, generate_validation_report)
from mediagoblin import mg_globals
from mediagoblin.mg_globals import setup_globals
from mediagoblin.db.open import setup_connection_and_db_from_config, \
    check_db_migrations_current, load_models
from mediagoblin.workbench import WorkbenchManager
from mediagoblin.storage import storage_system_from_config


class Error(Exception):
    pass


class ImproperlyConfigured(Error):
    pass


def setup_global_and_app_config(config_path):
    global_config, validation_result = read_mediagoblin_config(config_path)
    app_config = global_config['mediagoblin']
    # report errors if necessary
    validation_report = generate_validation_report(
        global_config, validation_result)
    if validation_report:
        raise ImproperlyConfigured(validation_report)

    setup_globals(
        app_config=app_config,
        global_config=global_config)

    return global_config, app_config


def setup_database():
    app_config = mg_globals.app_config

    # Load all models for media types (plugins, ...)
    load_models(app_config)

    # Set up the database
    connection, db = setup_connection_and_db_from_config(app_config)

    check_db_migrations_current(db)

    setup_globals(
        db_connection=connection,
        database=db)

    return connection, db


def get_jinja_loader(user_template_path=None, current_theme=None):
    """
    Set up the Jinja template loaders, possibly allowing for user
    overridden templates.

    (In the future we may have another system for providing theming;
    for now this is good enough.)
    """
    if user_template_path or current_theme:
        loader_choices = []

        # user template overrides
        if user_template_path:
            loader_choices.append(jinja2.FileSystemLoader(user_template_path))

        # Any theme directories in the registry
        if current_theme and current_theme.get('templates_dir'):
            loader_choices.append(
                jinja2.FileSystemLoader(
                    current_theme['templates_dir']))

        # Add the main mediagoblin templates
        loader_choices.append(
            jinja2.PackageLoader('mediagoblin', 'templates'))

        return jinja2.ChoiceLoader(loader_choices)
    else:
        return jinja2.PackageLoader('mediagoblin', 'templates')


def get_staticdirector(app_config):
    if not 'direct_remote_path' in app_config:
        raise ImproperlyConfigured(
            "One of direct_remote_path or "
            "direct_remote_paths must be provided")

    return staticdirect.StaticDirect(
        {None: app_config['direct_remote_path'].strip()})


def setup_storage():
    global_config = mg_globals.global_config

    key_short = 'publicstore'
    key_long = "storage:" + key_short
    public_store = storage_system_from_config(global_config[key_long])

    key_short = 'queuestore'
    key_long = "storage:" + key_short
    queue_store = storage_system_from_config(global_config[key_long])

    setup_globals(
        public_store=public_store,
        queue_store=queue_store)

    return public_store, queue_store


def setup_workbench():
    app_config = mg_globals.app_config

    workbench_manager = WorkbenchManager(app_config['workbench_path'])

    setup_globals(workbench_manager=workbench_manager)


def setup_beaker_cache():
    """
    Setup the Beaker Cache manager.
    """
    cache_config = mg_globals.global_config['beaker.cache']
    cache_config = dict(
        [(u'cache.%s' % key, value)
         for key, value in cache_config.iteritems()])
    cache = CacheManager(**parse_cache_config_options(cache_config))
    setup_globals(cache=cache)
    return cache
