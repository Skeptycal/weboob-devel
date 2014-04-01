# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


from weboob.tools.test import BackendTest
from weboob.tools.misc import html2text


__all__ = ['LeFigaroTest']


class LeFigaroTest(BackendTest):
    BACKEND = 'lefigaro'

    def test_lefigaro(self):
        l = list(self.backend.iter_threads())
        assert len(l)
        thread = self.backend.get_thread(l[0].id)
        assert len(thread.root.content)
        assert len(html2text(thread.root.content))
