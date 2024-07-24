#!/usr/bin/env python
# encoding: utf-8
"""
This module maintains runtime configurations.
"""
import os

Base_Directory = os.path.dirname(__file__)
FileStore_Directory = os.path.join(Base_Directory, 'stores')
FileCache_Directory = os.path.join(Base_Directory, 'cache')
FileImport_Directory = os.path.join(Base_Directory, 'import')
