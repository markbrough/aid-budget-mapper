#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  IATI Data Quality, tools for Data QA on IATI-formatted  publications
#  by Mark Brough, Martin Keegan, Ben Webb and Jennifer Smith
#
#  Copyright (C) 2013  Publish What You Fund
#
#  This programme is free software; you may redistribute and/or modify
#  it under the terms of the GNU Affero General Public License v3.0

from flask.ext.script import Manager
import abmapper

def run():
    manager = Manager(abmapper.app)
    manager.run()

if __name__ == "__main__":
    run()
