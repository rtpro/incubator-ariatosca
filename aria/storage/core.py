# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Aria's storage Sub-Package
Path: aria.storage

Storage package is a generic abstraction over different storage types.
We define this abstraction with the following components:

1. storage: simple mapi to use
2. driver: implementation of the database client mapi.
3. model: defines the structure of the table/document.
4. field: defines a field/item in the model.

API:
    * application_storage_factory - function, default Aria storage factory.
    * Storage - class, simple storage mapi.
    * models - module, default Aria standard models.
    * structures - module, default Aria structures - holds the base model,
                   and different fields types.
    * Model - class, abstract model implementation.
    * Field - class, base field implementation.
    * IterField - class, base iterable field implementation.
    * drivers - module, a pool of Aria standard drivers.
    * StorageDriver - class, abstract model implementation.
"""

from aria.logger import LoggerMixin
from . import api as storage_api

__all__ = (
    'Storage',
    'ModelStorage',
    'ResourceStorage'
)


class Storage(LoggerMixin):
    """
    Represents the storage
    """
    def __init__(self, api_cls, driver_kwargs=None, items=(), **kwargs):
        super(Storage, self).__init__(**kwargs)
        self.api = api_cls
        self._driver_kwargs = driver_kwargs or {}
        self.registered = {}
        for item in items:
            self.register(item)
        self.logger.debug('{name} object is ready: {0!r}'.format(
            self, name=self.__class__.__name__))

    def __repr__(self):
        return '{name}(api={self.api})'.format(name=self.__class__.__name__, self=self)

    def __getattr__(self, item):
        try:
            return self.registered[item]
        except KeyError:
            return super(Storage, self).__getattribute__(item)

    def register(self, entry):
        """
        Register the entry to the storage
        :param name:
        :return:
        """
        raise NotImplementedError('Subclass must implement abstract register method')


class ResourceStorage(Storage):
    """
    Represents resource storage.
    """
    def register(self, name):
        """
        Register the resource type to resource storage.
        :param name:
        :return:
        """
        self.registered[name] = self.api(name=name, **self._driver_kwargs)
        self.registered[name].create()
        self.logger.debug('setup {name} in storage {self!r}'.format(name=name, self=self))


class ModelStorage(Storage):
    """
    Represents model storage.
    """
    def register(self, model_cls):
        """
        Register the model into the model storage.
        :param model_cls: the model to register.
        :return:
        """
        model_name = storage_api.generate_lower_name(model_cls)
        if model_name in self.registered:
            self.logger.debug('{name} in already storage {self!r}'.format(name=model_name,
                                                                          self=self))
            return
        self.registered[model_name] = self.api(name=model_name,
                                               model_cls=model_cls,
                                               **self._driver_kwargs)
        self.registered[model_name].create()
        self.logger.debug('setup {name} in storage {self!r}'.format(name=model_name, self=self))

    def drop(self):
        """
        Drop all the tables from the model.
        :return:
        """
        for mapi in self.registered.values():
            mapi.drop()
