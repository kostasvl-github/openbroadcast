import os
import string
import unicodedata
import pprint
import re
import time
import shutil

import json

import datetime

import locale

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.validators import email_re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from django.utils.html import strip_tags, strip_entities
from html2text import html2text

from filer.models.filemodels import File
from filer.models.audiomodels import Audio
from filer.models.imagemodels import Image

from audiotools import AudioFile, MP3Audio, M4AAudio, FlacAudio, WaveAudio, MetaData
import audiotools

from settings import MEDIA_ROOT

from tagging.models import Tag
#from alibrary.models import Relation, Release, Artist, Media, Label, MediaExtraartists, Profession, ArtistMembership
from obp_legacy.models import *

from lib.util import filer_extra

from l10n.models import Country

from settings import MEDIA_ROOT
from settings import LEGACY_STORAGE_ROOT

import logging

log = logging.getLogger(__name__)

validate_url = URLValidator(verify_exists=False)


class Migrator(object):
    pass


class ReleaseMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from alibrary.models import Release, Relation

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate release: %s' % legacy_obj.name)

        obj, created = Release.objects.get_or_create(legacy_id=legacy_obj.id)

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object found by legacy_id: %s' % obj.pk)

        if created:
            """
            Mapping data
            1-to-1 fields
            """
            obj.name = legacy_obj.name[:190]
            obj.created = legacy_obj.created
            obj.updated = legacy_obj.updated

            if legacy_obj.catalognumber:
                log.debug('catalognumber: %s' % legacy_obj.catalognumber)
                obj.catalognumber = legacy_obj.catalognumber

            if legacy_obj.releasetype:
                log.debug('releasetype: %s' % legacy_obj.releasetype)
                obj.releasetype = legacy_obj.releasetype

            if legacy_obj.releasestatus:
                obj.releasestatus = legacy_obj.releasestatus

            if legacy_obj.published:
                obj.publish_date = legacy_obj.published

            if legacy_obj.notes:
                obj.description = legacy_obj.notes

            if legacy_obj.totaltracks:
                obj.totaltracks = legacy_obj.totaltracks

            if legacy_obj.releasecountry and len(legacy_obj.releasecountry) == 2:
                obj.release_country = legacy_obj.releasecountry

            if legacy_obj.releasedate:
                log.debug('legacy-date: %s' % legacy_obj.releasedate)
                date = legacy_obj.releasedate
                if len(date) == 4:
                    date = '%s-00-00' % (date)
                elif len(date) == 7:
                    date = '%s-00' % (date)
                elif len(date) == 10:
                    date = '%s' % (date)

                re_date = re.compile('^\d{4}-\d{2}-\d{2}$')
                if re_date.match(date) and date != '0000-00-00':
                    try:
                        import time

                        valid_date = time.strptime('%s' % date, '%Y-%m-%d')
                        obj.releasedate_approx = '%s' % date
                    except Exception, e:
                        print 'Invalid date!'
                        print e

            """
            Relation mapping
            """
            if legacy_obj.discogs_releaseid and legacy_obj.discogs_releaseid != 'nf':
                url = 'http://www.discogs.com/release/%s' % legacy_obj.discogs_releaseid
                log.debug('discogs_url: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.mb_releaseid and legacy_obj.mb_releaseid != 'nf':
                url = 'http://musicbrainz.org/release/%s' % legacy_obj.mb_releaseid
                log.debug('mb_releaseid: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.myspace_url and legacy_obj.myspace_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.myspace_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.wikipedia_url and legacy_obj.wikipedia_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.wikipedia_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.facebook_url and legacy_obj.facebook_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.facebook_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.lastfm_url and legacy_obj.lastfm_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.lastfm_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.release_url and legacy_obj.release_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.release_url, service='official')
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.various_links and len(legacy_obj.various_links) > 10:
                for entry in legacy_obj.various_links.splitlines():
                    try:
                        validate_url(entry)
                        rel = Relation(content_object=obj, url=entry)
                        log.debug('url (from various): %s' % rel.url)
                        rel.save()

                    except ValidationError, e:
                        print e

            """
            Label Mapping
            """
            legacy_items = LabelsReleases.objects.using('legacy').filter(release=legacy_obj)
            # r.tags.clear()
            for legacy_item in legacy_items:
                log.debug('mapping label')
                item, s = get_label_by_legacy_object(legacy_item.label)
                obj.label = item

            """
            User mapping
            """
            try:
                legacy_user = Users.objects.using('legacy').get(id=legacy_obj.user_id)
                log.debug('mapping user')
                item, s = get_user_by_legacy_object(legacy_user)
                if item:
                    obj.creator = item
            except:
                pass

            """
            Tag Mapping
            """
            nts = NtagsReleases.objects.using('legacy').filter(release_id=legacy_obj.id)
            # r.tags.clear()
            for nt in nts:
                try:
                    t = Ntags.objects.using('legacy').get(id=nt.ntag_id)
                    log.debug('tag for object: %s' % t.name)
                    Tag.objects.add_tag(obj, u'"%s"' % t.name[:30])
                except Exception, e:
                    print e

            """
            Get image
            """
            try:
                img_url = 'http://openbroadcast.ch/static/images/release/%s/original.jpg' % id_to_location(
                    obj.legacy_id)
                log.debug('download image: %s' % img_url)
                img = filer_extra.url_to_file(img_url, obj.folder)
                obj.main_image = img
            except:
                pass

            """
            Finishing up
            """
            obj.save()

        return obj, status


class MediaMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj, force=False):

        from alibrary.models import Media, Relation

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate media: %s' % legacy_obj.name)

        obj, created = Media.objects.get_or_create(legacy_id=legacy_obj.id)

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object %s found by legacy_id: %s' % (obj.pk, obj.legacy_id))

        if created or force:
            """
            Mapping data
            1-to-1 fields
            """
            obj.name = legacy_obj.name
            obj.created = legacy_obj.created
            obj.updated = legacy_obj.updated
            if legacy_obj.published:
                obj.publish_date = legacy_obj.published

            if legacy_obj.tracknumber:
                log.debug('tracknumber: %s' % legacy_obj.tracknumber)
                try:
                    obj.tracknumber = int(legacy_obj.tracknumber)
                except:
                    pass

            """
            Relation mapping
            """

            if legacy_obj.mb_trackid and legacy_obj.mb_trackid != 'nf':
                url = 'http://musicbrainz.org/recording/%s' % legacy_obj.mb_trackid
                log.debug('mb_trackid: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.soundcloud_url and legacy_obj.soundcloud_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.soundcloud_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.youtube_url and legacy_obj.youtube_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.youtube_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            """
            Release Mapping
            """
            legacy_items = MediasReleases.objects.using('legacy').filter(media=legacy_obj)
            # r.tags.clear()
            for legacy_item in legacy_items:
                log.debug('mapping release')
                item, s = get_release_by_legacy_object(legacy_item.release)
                obj.release = item

            """
            Artist Mapping
            """
            legacy_items = ArtistsMedias.objects.using('legacy').filter(media=legacy_obj)
            # r.tags.clear()
            for legacy_item in legacy_items:
                log.debug('mapping artist')
                item, s = get_artist_by_legacy_object(legacy_item.artist)
                obj.artist = item

            """
            User mapping
            """
            try:
                legacy_user = Users.objects.using('legacy').get(id=legacy_obj.user_id)
                log.debug('mapping user')
                item, s = get_user_by_legacy_object(legacy_user)
                if item:
                    obj.creator = item
            except:
                pass

            """
            Tag Mapping
            """
            nts = NtagsMedias.objects.using('legacy').filter(media_id=legacy_obj.id)
            for nt in nts:
                try:
                    t = Ntags.objects.using('legacy').get(id=nt.ntag_id)
                    log.debug('tag for object: %s' % t.name)
                    Tag.objects.add_tag(obj, u'"%s"' % t.name[:30])
                except Exception, e:
                    print e

            """
            Get path to file
            """
            try:

                base_path = '%s%s' % (LEGACY_STORAGE_ROOT, 'media/')

                media_dir = '%s%s/' % (base_path, id_to_location(obj.legacy_id))

                if legacy_obj.has_flac_default == 1:
                    print 'FLAC'
                    media_path = '%sdefault.flac' % (media_dir)
                else:
                    print 'MP3'
                    media_path = '%sdefault.mp3' % (media_dir)

                print '******************************************************'
                print media_dir
                print media_path

                if os.path.isfile(media_path):
                    print 'file exists!'

                    """"""
                    folder = "private/%s/" % (obj.uuid.replace('-', '/'))

                    filename, extension = os.path.splitext(media_path)
                    dst = os.path.join(folder, "master%s" % extension.lower())

                    print dst

                    try:

                        os.makedirs("%s/%s" % (MEDIA_ROOT, folder))
                        shutil.copy(media_path, "%s/%s" % (MEDIA_ROOT, dst))
                        obj.master = dst
                        obj.save()

                    except Exception, e:
                        print e


                else:
                    print 'unable to get file'


            except:
                pass

            """
            Finishing up
            """
            obj.save()

        return obj, status


class ArtistMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from alibrary.models import Artist, Relation

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate artist: %s' % legacy_obj.name)

        obj, created = Artist.objects.get_or_create(legacy_id=legacy_obj.id)

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object found by legacy_id: %s' % obj.pk)

        if created:
            """
            Mapping data
            1-to-1 fields
            """
            obj.name = legacy_obj.name
            obj.created = legacy_obj.created
            obj.updated = legacy_obj.updated
            obj.published = legacy_obj.published

            if legacy_obj.profile:
                obj.description = legacy_obj.profile

            if legacy_obj.artisttype:
                obj.type = legacy_obj.artisttype

            if legacy_obj.realname:
                obj.real_name = legacy_obj.realname

            if legacy_obj.country:
                log.debug('country: %s' % legacy_obj.country)
                country = None
                if len(legacy_obj.country) == 2:
                    try:
                        country = Country.objects.get(iso2_code=legacy_obj.country)
                    except Exception, e:
                        pass

                else:
                    try:
                        country = Country.objects.get(printable_name=legacy_obj.country)
                    except Exception, e:
                        pass

                if country:
                    log.debug('got country: %s' % country.name)
                    obj.country = country

            if legacy_obj.aliases:
                log.debug('aliases: %s' % legacy_obj.aliases)
                for alias in legacy_obj.aliases.split(','):
                    log.debug('alias: %s' % alias)
                    try:
                        a, c = Artist.objects.get_or_create(name=alias.rstrip(' ').lstrip(' '))
                        obj.aliases.add(a)
                    except:
                        try:
                            a = Artist.objects.filter(name=alias.rstrip(' ').lstrip(' '))[0]
                            obj.aliases.add(a)
                        except:
                            pass

            """
            Relation mapping
            """
            if legacy_obj.discogs_artistid and legacy_obj.discogs_artistid != 'nf':
                url = 'http://www.discogs.com/artist/%s' % legacy_obj.discogs_artistid
                log.debug('discogs_url: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.mb_artistid and legacy_obj.mb_artistid != 'nf':
                url = 'http://musicbrainz.org/artist/%s' % legacy_obj.mb_artistid
                log.debug('mb_artistid: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.myspace_url and legacy_obj.myspace_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.myspace_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.wikipedia_url and legacy_obj.wikipedia_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.wikipedia_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.facebook_url and legacy_obj.facebook_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.facebook_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.lastfm_url and legacy_obj.lastfm_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.lastfm_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.soundcloud_url and legacy_obj.soundcloud_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.soundcloud_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.website and legacy_obj.website != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.website, service='official')
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.various_links and len(legacy_obj.various_links) > 10:
                for entry in legacy_obj.various_links.splitlines():
                    try:
                        validate_url(entry)
                        rel = Relation(content_object=obj, url=entry)
                        log.debug('url (from various): %s' % rel.url)
                        rel.save()

                    except ValidationError, e:
                        print e

            """
            User mapping
            """
            try:
                legacy_user = Users.objects.using('legacy').get(id=legacy_obj.user_id)
                log.debug('mapping user')
                item, s = get_user_by_legacy_object(legacy_user)
                if item:
                    obj.creator = item
            except:
                pass

            """
            Tag Mapping
            """
            nts = NtagsArtists.objects.using('legacy').filter(artist_id=legacy_obj.id)
            # r.tags.clear()
            for nt in nts:
                try:
                    t = Ntags.objects.using('legacy').get(id=nt.ntag_id)
                    log.debug('tag for object: %s' % t.name)
                    Tag.objects.add_tag(obj, u'"%s"' % t.name[:30])
                except Exception, e:
                    print e

            """
            Get image
            """
            try:
                img_url = 'http://openbroadcast.ch/static/images/artist/%s/original.jpg' % id_to_location(obj.legacy_id)
                log.debug('download image: %s' % img_url)
                img = filer_extra.url_to_file(img_url, obj.folder)
                obj.main_image = img
            except:
                pass

            """
            Finishing up
            """
            obj.save()

        return obj, status


class LabelMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from alibrary.models import Label, Relation, Distributor, DistributorLabel

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate release: %s' % legacy_obj.name)

        obj, created = Label.objects.get_or_create(legacy_id=legacy_obj.id)

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object found by legacy_id: %s' % obj.pk)

        if created:
            """
            Mapping data
            1-to-1 fields
            """
            obj.name = legacy_obj.name
            obj.created = legacy_obj.created
            obj.updated = legacy_obj.updated

            if legacy_obj.published:
                obj.published = legacy_obj.published

            if legacy_obj.label_type:
                obj.type = legacy_obj.label_type

            if legacy_obj.label_code:
                log.debug('label_code: %s' % legacy_obj.label_code)
                obj.labelcode = legacy_obj.label_code[:200]

            if legacy_obj.profile:
                if legacy_obj.notes:
                    obj.description = "%s\n\n%s" % (legacy_obj.profile, legacy_obj.notes)
                else:
                    obj.description = legacy_obj.profile

            if legacy_obj.address:
                obj.address = legacy_obj.address

            if legacy_obj.contact:
                log.debug('contact: %s' % legacy_obj.contact)
                if email_re.match(legacy_obj.contact):
                    obj.email = legacy_obj.contact

            if legacy_obj.country:
                log.debug('country: %s' % legacy_obj.country)
                country = None
                if len(legacy_obj.country) == 2:
                    try:
                        country = Country.objects.get(iso2_code=legacy_obj.country)
                    except Exception, e:
                        pass

                else:
                    try:
                        country = Country.objects.get(printable_name=legacy_obj.country)
                    except Exception, e:
                        pass

                if country:
                    log.debug('got country: %s' % country.name)
                    obj.country = country

            if legacy_obj.distributor:
                log.debug('distributor: %s' % legacy_obj.distributor)
                d, c = Distributor.objects.get_or_create(name=legacy_obj.distributor)
                dl = DistributorLabel(distributor=d, label=obj)
                dl.save()

            """
            Relation mapping
            """
            if legacy_obj.discogs_labelid and legacy_obj.discogs_labelid != 'nf':
                url = 'http://www.discogs.com/label/%s' % legacy_obj.discogs_labelid
                log.debug('discogs_url: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.mb_labelid and legacy_obj.mb_labelid != 'nf':
                url = 'http://musicbrainz.org/label/%s' % legacy_obj.mb_labelid
                log.debug('mb_labelid: %s' % url)
                rel = Relation(content_object=obj, url=url)
                rel.save()

            if legacy_obj.facebook_url and legacy_obj.facebook_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.facebook_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.wikipedia_url and legacy_obj.wikipedia_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.wikipedia_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.soundcloud_url and legacy_obj.soundcloud_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.soundcloud_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.lastfm_url and legacy_obj.lastfm_url != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.lastfm_url)
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.website and legacy_obj.website != 'nf':
                rel = Relation(content_object=obj, url=legacy_obj.website, service='official')
                log.debug('url: %s' % rel.url)
                rel.save()

            if legacy_obj.various_links and len(legacy_obj.various_links) > 10:
                for entry in legacy_obj.various_links.splitlines():

                    try:
                        validate_url(entry)
                        rel = Relation(content_object=obj, url=entry)
                        log.debug('url (from various): %s' % rel.url)
                        rel.save()

                    except ValidationError, e:
                        print e

            """
            User mapping
            """
            try:
                legacy_user = Users.objects.using('legacy').get(id=legacy_obj.user_id)
                log.debug('mapping user')
                item, s = get_user_by_legacy_object(legacy_user)
                if item:
                    obj.creator = item
            except:
                pass

            """
            Tag Mapping
            """
            nts = NtagsLabels.objects.using('legacy').filter(label_id=legacy_obj.id)
            # r.tags.clear()
            for nt in nts:
                try:
                    t = Ntags.objects.using('legacy').get(id=nt.ntag_id)
                    log.debug('tag for object: %s' % t.name)
                    Tag.objects.add_tag(obj, u'"%s"' % t.name[:30])
                except Exception, e:
                    print e

            """
            Get image
            """
            try:
                img_url = 'http://openbroadcast.ch/static/images/label/%s/original.jpg' % id_to_location(obj.legacy_id)
                log.debug('download image: %s' % img_url)
                img = filer_extra.url_to_file(img_url, obj.folder)
                obj.main_image = img
            except:
                pass

            """
            Finishing up
            """
            obj.save()

        return obj, status


class UserMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from profiles.models import Profile
        from django.contrib.auth.models import User, Group
        #from obp_legacy.models_legacy import *

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate user: %s' % legacy_obj.username)

        try:
            obj = Profile.objects.get(legacy_id=legacy_obj.id).user
        except:
            obj = None

        return obj, status


class LegacyUserMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from profiles.models import Profile
        from django.contrib.auth.models import User, Group
        from obp_legacy.models_legacy import *

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate user: %s' % legacy_obj.username)

        user, created = User.objects.get_or_create(username=legacy_obj.username)

        user.email = legacy_obj.email


        # add user to 'member' group
        mg, c = Group.objects.get_or_create(name='Member')
        user.groups.add(mg)

        obj = user.profile

        #obj.legacy_id = legacy_obj.id
        obj.legacy_legacy_id = legacy_obj.ident

        """
        Try to get legacy id (not legacy_legacy_id)
        """
        obj.legacy_id = Users.objects.using('legacy').get(legacy_id=legacy_obj.ident).id

        print '***'
        print obj.legacy_id
        print '***'

        print 'last_action: %s' % legacy_obj.last_action
        print 'join_date: %s' % legacy_obj.join_date

        if legacy_obj.last_action and legacy_obj.last_action > 0:
            user.last_login = datetime.datetime.fromtimestamp(int(legacy_obj.last_action)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            #user.last_login = datetime.datetime.strftime('2008-01-01 12:00:00')
            pass

        if legacy_obj.join_date and legacy_obj.join_date > 0:
            user.date_joined = datetime.datetime.fromtimestamp(int(legacy_obj.join_date)).strftime('%Y-%m-%d %H:%M:%S')

        """
        Get image
        """
        try:
            icon = int(legacy_obj.icon)
            if icon > 0:
                img_url = 'https://www.openbroadcast.ch/_icon/user/%s/h/300/w/300/302' % icon
                log.debug('download image: %s' % img_url)
            #img = filer_extra.url_to_file(img_url, obj.folder)
            #obj.image = img
        except Exception, e:
            print e
            pass

        """
        user.last_login = legacy_obj.created
        user.date_joined = legacy_obj.updated
        """
        if legacy_obj.name:
            name = legacy_obj.name.split(' ')

            if len(name) == 1:
                user.last_name = name[0][:29]

            if len(name) == 2:
                user.first_name = name[0][:29]
                user.last_name = name[1][:29]

            if len(name) > 2:
                user.first_name = name[0][:29]
                user.last_name = ', '.join(name[1:])[:29]

            print name
            print user.first_name
            print user.last_name

        user.save()

        #obj, created = Profile.objects.get_or_create(legacy_id=legacy_obj.id, user=user)

        """
        Gathering profile data
        """
        p_data = ElggProfileData.objects.using('legacy_legacy').filter(owner=legacy_obj.ident)
        """"""
        for item in p_data:
            """
            print 'access: %s' % item.access
            print 'name: %s' % item.name
            print 'value: %s' % item.value
            """

            # Mapping profile data

            if item.name == 'interests':
                tags = item.value.split(',')
                for tag in tags:
                    tag = tag.rstrip(' ').lstrip(' ')
                    if len(tag) > 2:
                        try:
                            Tag.objects.add_tag(obj, u'"%s"' % tag[:30])
                        except Exception, e:
                            print e

            if item.name == 'formats':
                tags = item.value.split(',')
                for tag in tags:
                    tag = tag.rstrip(' ').lstrip(' ')
                    if len(tag) > 2:
                        try:
                            Tag.objects.add_tag(obj, u'"%s"' % tag[:30])
                        except Exception, e:
                            print e

            if item.name == 'homecountry':
                country = None
                if len(item.value) == 2:
                    try:
                        country = Country.objects.get(iso2_code=item.value)
                    except Exception, e:
                        pass

                else:
                    try:
                        country = Country.objects.get(printable_name=item.value)
                    except Exception, e:
                        pass

                if country:
                    log.debug('got country: %s' % country.name)
                    obj.country = country

            if item.name == 'birth_date':
                try:
                    import time

                    valid_date = time.strptime('%s' % obj.birth_date, '%Y-%m-%d')
                    obj.birth_date = item.value
                except Exception, e:
                    print 'Invalid date!'
                    print e

            if item.name == 'streetaddress':
                obj.address1 = item.value

            if item.name == 'postcode':
                obj.zip = item.value

            if item.name == 'town':
                obj.city = item.value

            if item.name == 'workphone':
                obj.phone = item.value

            if item.name == 'minibio':
                obj.description = item.value

            if item.name == 'emailaddress':
                obj.email = item.value

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object found by legacy_id: %s' % obj.pk)

        if created:
            """
            Mapping data
            1-to-1 fields
            """

        obj.save()

        return obj, status


class CommunityMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from profiles.models import Profile, Community
        from django.contrib.auth.models import User, Group
        from obp_legacy.models_legacy import *

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('migrate user: %s' % legacy_obj.username)

        obj, created = Community.objects.get_or_create(name=legacy_obj.name)

        """
        Get image
        """
        try:
            icon = int(legacy_obj.icon)
            if icon > 0:
                img_url = 'https://www.openbroadcast.ch/_icon/user/%s/h/300/w/300/302' % icon
                log.debug('download image: %s' % img_url)
            #img = filer_extra.url_to_file(img_url, obj.folder)
            #obj.image = img
        except Exception, e:
            print e
            pass



        #obj, created = Profile.objects.get_or_create(legacy_id=legacy_obj.id, user=user)

        """
        Gathering profile data
        """
        p_data = ElggProfileData.objects.using('legacy_legacy').filter(owner=legacy_obj.ident)
        """"""
        for item in p_data:
            print 'access: %s' % item.access
            print 'name: %s' % item.name
            print 'value: %s' % item.value


            # Mapping profile data

            if item.name == 'interests':
                tags = item.value.split(',')
                for tag in tags:
                    tag = tag.rstrip(' ').lstrip(' ')
                    if len(tag) > 2:
                        try:
                            Tag.objects.add_tag(obj, u'"%s"' % tag[:30])
                        except Exception, e:
                            print e

            if item.name == 'country':
                country = None
                if len(item.value) == 2:
                    try:
                        country = Country.objects.get(iso2_code=item.value)
                    except Exception, e:
                        pass

                else:
                    try:
                        country = Country.objects.get(printable_name=item.value)
                    except Exception, e:
                        pass

                if country:
                    log.debug('got country: %s' % country.name)
                    obj.country = country

            if item.name == 'streetaddress':
                obj.address1 = item.value

            if item.name == 'postcode':
                obj.zip = item.value

            if item.name == 'town':
                obj.city = item.value

            if item.name == 'workphone':
                obj.phone = item.value

            if item.name == 'minibio':
                obj.description = item.value

            if item.name == 'emailaddress':
                obj.email = item.value



        #obj.legacy_id = legacy_obj.id
        obj.legacy_legacy_id = legacy_obj.ident

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object found by legacy_id: %s' % obj.pk)

        if created:
            """
            Mapping data
            1-to-1 fields
            """

        obj.save()

        return obj, status


class PlaylistMigrator(Migrator):
    def __init__(self):
        log = logging.getLogger('util.migrator.__init__')


    def run(self, legacy_obj):

        from alibrary.models import Playlist, PlaylistItem, PlaylistItemPlaylist
        from obp_legacy.models_legacy import *

        status = 1

        log = logging.getLogger('util.migrator.run')
        log.info('playlist: %s' % legacy_obj.title)

        obj, created = Playlist.objects.get_or_create(legacy_id=legacy_obj.ident)

        if created:
            log.info('object created: %s' % obj.pk)
        else:
            log.info('object found by legacy_id: %s' % obj.pk)

        """
        Mapping data
        """
        obj.name = legacy_obj.title

        print '#######################################################'
        print 'name: %s' % obj.name

        """
        legacy status
        1: work in progress
        2: ready to schedule
        3: scheduled (not possible to go back)
        4: un-scheduled ?
        """
        print 'status: %s' % legacy_obj.status

        if legacy_obj.status == 1:
            obj.status = 2
        if legacy_obj.status == 2:
            obj.status = 1
        if legacy_obj.status == 3:
            obj.status = 3
        if legacy_obj.status == 4:
            obj.status = 4

        """
        Type mapping
        """
        if legacy_obj.status in (2, 3, 4):
            obj.type = 'broadcast'
        if legacy_obj.status in (0, 1):
            # maybe exclude '0'
            obj.type = 'playlist'

        """
        Tag Mapping
        """
        nts = ElggTags.objects.using('legacy_legacy').filter(ref=legacy_obj.ident)
        for nt in nts:
            try:
                log.debug('tag for object: %s' % nt.tag)
                Tag.objects.add_tag(obj, u'"%s"' % nt.tag[:30])
            except Exception, e:
                print e

        if legacy_obj.intro:
            print legacy_obj.intro
            obj.description = legacy_obj.intro

        # date mappings
        if legacy_obj.posted:
            obj.created = datetime.datetime.fromtimestamp(int(legacy_obj.posted)).strftime('%Y-%m-%d %H:%M:%S')

        if legacy_obj.lastupdate:
            obj.updated = datetime.datetime.fromtimestamp(int(legacy_obj.lastupdate)).strftime('%Y-%m-%d %H:%M:%S')

        # TODO: status mapping
        if legacy_obj.status:
            print 'status id: %s' % legacy_obj.status

        """
        User mapping
        """
        try:
            legacy_user = Users.objects.using('legacy').get(legacy_id=legacy_obj.owner)
            log.debug('mapping user')
            item, s = get_user_by_legacy_object(legacy_user)
            if item:
                obj.user = item
        except Exception, e:
            print e
            pass

        """
        Getting this f**ing hell stupd content-container thing...
        """
        cts = ElggCmContainer.objects.using('legacy_legacy').filter(x_ident=legacy_obj.ident, container_type="Playlist")

        if cts.count() > 0:
            container = cts[0]
        else:
            container = None

        if container:

            print '***********************************************'
            print container.body
            print
            print html2text(container.body)
            print
            obj.description = html2text(container.body.replace('&nbsp;', ''))

            print 'target_duration: %s' % container.target_duration
            """
            target duration, calculation
            """
            print 'calculated:      %s' % (int(container.target_duration) * 15 * 60 * 1000)

            print 'duration:        %s' % container.duration
            print 'sub_type:        %s' % container.sub_type
            print 'best_broadcast_segment: %s' % container.best_broadcast_segment
            print 'rotation_include: %s' % container.rotation_include

            obj.target_duration = (int(container.target_duration) * 15 * 60)

            # TODO: Broadcast segment mapping
            bcs = json.loads(container.best_broadcast_segment)
            for bc in bcs:
                if bc[0] == 1:
                    print 'Mo:',
                    print bc[1]

            PlaylistItemPlaylist.objects.filter(playlist=obj).delete()
            """"""
            legacy_media = json.loads(container.content_list)
            position = 0
            for lm in legacy_media:
                print lm
                if 'source' in lm and lm['source'] == 'ml':
                    tm = Medias.objects.using('legacy').get(id=int(lm['ident']))
                    print tm.name
                    print 'pos: %s' % position

                    media, s = get_media_by_legacy_object(tm)
                    print media.pk

                    #pi = PlaylistItem()

                    # map timing
                    timing = {
                        'fade_in': lm['fade_in'],
                        'fade_out': lm['fade_out'],
                        'cue_in': lm['offset_in'],
                        'cue_out': lm['offset_out'],
                    }

                    obj.add_items_by_ids(ids=[media.pk,], ct='media', timing=timing)

                    position += 1

        obj.save()

        return obj, status


def get_release_by_legacy_object(legacy_obj):
    migrator = ReleaseMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


def get_media_by_legacy_object(legacy_obj, force=False):
    migrator = MediaMigrator()
    obj, status = migrator.run(legacy_obj, force)

    return obj, status


def get_artist_by_legacy_object(legacy_obj):
    migrator = ArtistMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


def get_label_by_legacy_object(legacy_obj):
    migrator = LabelMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


def get_user_by_legacy_object(legacy_obj):
    migrator = UserMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


def get_playlist_by_legacy_object(legacy_obj):
    migrator = PlaylistMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


"""
Double legacy shortcuts
"""


def get_user_by_legacy_legacy_object(legacy_obj):
    migrator = LegacyUserMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


def get_community_by_legacy_legacy_object(legacy_obj):
    migrator = CommunityMigrator()
    obj, status = migrator.run(legacy_obj)

    return obj, status


"""
helper
"""


def id_to_location(id):
    l = "%012d" % id
    return '%d/%d/%d' % (int(l[0:4]), int(l[4:8]), int(l[8:12]))
    
    



