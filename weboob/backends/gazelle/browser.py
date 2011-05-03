# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.browser import BaseBrowser

from .pages.index import IndexPage, LoginPage
from .pages.torrents import TorrentsPage


__all__ = ['GazelleBrowser']


class GazelleBrowser(BaseBrowser):
    PAGES = {'https?://%s/?(index.php)?':  IndexPage,
             'https?://%s/login.php':      LoginPage,
             'https?://%s/torrents.php.*': TorrentsPage,
            }

    def __init__(self, protocol, domain, *args, **kwargs):
        self.DOMAIN = domain
        self.PROTOCOL = protocol
        self.PAGES = {}
        for key, value in GazelleBrowser.PAGES.iteritems():
            self.PAGES[key % domain] = value

        BaseBrowser.__init__(self, *args, **kwargs)

    def login(self):
        if not self.is_on_page(LoginPage):
            self.home()
        self.page.login(self.username, self.password)

    def is_logged(self):
        if not self.page or self.is_on_page(LoginPage):
            return False
        if self.is_on_page(IndexPage):
            return self.page.is_logged()
        return True

    def home(self):
        return self.location('%s://%s/login.php' % (self.PROTOCOL, self.DOMAIN))

    def iter_torrents(self, pattern):
        self.location(self.buildurl('/torrents.php', searchstr=pattern.encode('utf-8')))

        assert self.is_on_page(TorrentsPage)
        return self.page.iter_torrents()

    def get_torrent(self, id):
        self.location('/torrents.php?torrentid=%s' % id)

        assert self.is_on_page(TorrentsPage)
        return self.page.get_torrent(id)
