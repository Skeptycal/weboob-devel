# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from dateutil.parser import parse as parse_date

from weboob.tools.browser import BasePage
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.housing import Housing, HousingPhoto


__all__ = ['SearchResultsPage', 'HousingPage']


class SearchResultsPage(BasePage):
    def iter_housings(self):
        for a in self.document.getroot().xpath('//annonce'):
            housing = Housing(a.find('idannonce').text)
            housing.title = a.find('titre').text
            housing.date = parse_date(a.find('dtfraicheur').text)
            housing.cost = float(a.find('prix').text)
            housing.currency = u'€'
            housing.area = float(a.find('surface').text)
            housing.text = a.find('descriptif').text.strip()
            housing.location = a.find('ville').text
            try:
                housing.station = a.find('proximite').text
            except AttributeError:
                housing.station = NotAvailable

            housing.photos = []
            for photo in a.xpath('./photos/photo'):
                url = photo.find('stdurl').text
                housing.photos.append(HousingPhoto(url))

            yield housing

class HousingPage(BasePage):
    def get_housing(self, housing=None):
        if housing is None:
            housing = Housing(self.groups[0])

        details = self.document.getroot().xpath('//detailannonce')[0]
        if details.find('titre') is None:
            return None

        housing.title = details.find('titre').text
        housing.text = details.find('descriptif').text.strip()
        housing.cost = float(details.find('prix').text)
        housing.currency = u'€'
        housing.date = parse_date(details.find('dtfraicheur').text)
        housing.area = float(details.find('surface').text)
        housing.phone = details.find('contact').find('telephone').text

        try:
            housing.station = details.find('proximite').text
        except AttributeError:
            housing.station = NotAvailable

        housing.location = details.find('adresse').text
        if not housing.location and details.find('quartier') is not None:
            housing.location = details.find('quartier').text
        if not housing.location:
            housing.location = NotAvailable

        housing.photos = []
        for photo in details.xpath('./photos/photo'):
            if photo.find('bigurl').text:
                url = photo.find('bigurl').text
            else:
                url = photo.find('stdurl').text
            housing.photos.append(HousingPhoto(url))

        housing.details = {}
        for detail in details.xpath('./details/detail'):
            housing.details[detail.find('libelle').text.strip()] = detail.find('valeur').text or 'N/A'

        housing.details['Reference'] = details.find('reference').text

        return housing
