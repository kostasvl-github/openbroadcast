#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import datetime
import re

from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic


from cms.models import CMSPlugin
from django_extensions.db.fields import *
from django_extensions.db.fields.json import JSONField

from django.core.urlresolvers import reverse

# filer
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField


# 
from lib.fields import extra

from alibrary.models import Artist, Playlist

from abcast.models import BaseModel, Station, Channel


from caching.base import CachingMixin, CachingManager



class Broadcast(BaseModel):
    
    # core fields
    name = models.CharField(max_length=200, db_index=True)
    slug = AutoSlugField(populate_from='name', editable=True, blank=True, overwrite=True)

    STATUS_CHOICES = (
        (0, _('Waiting')),
        (1, _('Done')),
        (2, _('Error')),
    )
    status = models.PositiveIntegerField(max_length=2, default=0, choices=STATUS_CHOICES)

    TYPE_CHOICES = (
        ('studio', _('Studio')),
        ('playlist', _('Playlist')),
        ('couchcast', _('Couchcast')),
    )
    type = models.CharField(verbose_name=_('Type'), max_length=12, default='jingle', choices=TYPE_CHOICES)
    
    description = models.TextField(verbose_name="Extra Description", blank=True, null=True)
    duration = models.PositiveIntegerField(verbose_name="Duration (in ms)", max_length=12, blank=True, null=True, editable=True)
    
    # relations
    user = models.ForeignKey(User, blank=True, null=True, related_name="scheduler_broadcasts", on_delete=models.SET_NULL)

    # REFACTORED: playlist not used, modeled via emission -> co
    playlist = models.ForeignKey(Playlist, blank=True, null=True, related_name="scheduler_broadcasts", on_delete=models.SET_NULL)

    # manager
    objects = models.Manager()

    class Meta:
        app_label = 'abcast'
        verbose_name = _('Broadcast')
        verbose_name_plural = _('Broadcasts')
        ordering = ('created', )
    
    
    def __unicode__(self):
        return u'%s' % self.name


class EmissionManager(CachingManager):

    def future(self):
        now = datetime.datetime.now()
        return self.get_query_set().filter(time_end__gte=now)

    def past(self):
        now = datetime.datetime.now()
        return self.get_query_set().filter(time_end__lt=now)




class Emission(BaseModel, CachingMixin):
    
    # core fields
    name = models.CharField(max_length=200, db_index=True)
    slug = AutoSlugField(populate_from='name', editable=True, blank=True, overwrite=True)

    STATUS_CHOICES = (
        (0, _('Waiting')),
        (1, _('Done')),
        (2, _('Error')),
    )
    status = models.PositiveIntegerField(max_length=2, default=0, choices=STATUS_CHOICES)
    
    COLOR_CHOICES = (
        (0, _('Theme 1')),
        (1, _('Theme 2')),
        (2, _('Theme 3')),
        (3, _('Theme 4')),
    )
    color = models.PositiveIntegerField(max_length=2, default=0, choices=COLOR_CHOICES)

    TYPE_CHOICES = (
        ('studio', _('Studio')),
        ('playlist', _('Playlist')),
        ('couchcast', _('Couchcast')),
    )
    type = models.CharField(verbose_name=_('Type'), max_length=12, default='playlist', choices=TYPE_CHOICES)

    SOURCE_CHOICES = (
        ('user', _('User')),
        ('autopilot', _('Autopilot')),
    )
    source = models.CharField(verbose_name=_('Source'), max_length=12, default='user', choices=SOURCE_CHOICES)
    
    
    time_start = models.DateTimeField(blank=True, null=True)
    time_end = models.DateTimeField(blank=True, null=True)
    
    # eventually use this
    duration = models.PositiveIntegerField(verbose_name="Duration (in ms)", max_length=12, blank=True, null=True, editable=False)
    
    
    # relations
    user = models.ForeignKey(User, blank=True, null=True, related_name="scheduler_emissions", on_delete=models.SET_NULL)
    channel = models.ForeignKey(Channel, blank=True, null=True, related_name="scheduler_emissions", on_delete=models.SET_NULL)
    
    
    """
    content
    content objects have to implement certain methosds/properties:
     - get_duration()
     - t.b.d.
    """
    ct_limit = models.Q(app_label = 'alibrary', model = 'playlist') | models.Q(app_label = 'alibrary', model = 'release')
    content_type = models.ForeignKey(ContentType, limit_choices_to = ct_limit)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    
    locked = models.BooleanField(default=False)
    
    
    # manager
    objects = EmissionManager()

    class Meta:
        app_label = 'abcast'
        verbose_name = _('Emission')
        verbose_name_plural = _('Emissions')
        ordering = ('created', )
    
    
    def __unicode__(self):
        return u'%s' % self.name
    
    
    @models.permalink
    def get_absolute_url(self):      
        return ('abcast-emission-detail', [self.pk])
    
    
    def get_api_url(self):
        return reverse('api_dispatch_detail', kwargs={  
            'api_name': 'v1',  
            'resource_name': 'abcast/emission',  
            'pk': self.pk  
        }) + ''



    @property
    def has_lock(self):
        if self.locked:
            return self.locked
        
        lock = False
        if self.time_start < datetime.datetime.now():
            lock = True
        return lock
    
    @property
    def is_playing(self):
        playing = False
        if self.time_start < datetime.datetime.now() and datetime.datetime.now() < self.time_end:
            playing = True
        return playing

    def save(self, *args, **kwargs):
        
        print 'save'
        print self.content_object
        
        if not self.name:
            self.name = self.content_object.name
        
        
        self.duration = self.content_object.get_duration()
        
        print 'duration: %s' % self.content_object.get_duration()
        
        if self.duration:
            self.time_end = self.time_start + datetime.timedelta(milliseconds=self.duration)
        
        
        super(Emission, self).save(*args, **kwargs)
        
        
        
        
        
        
class DaypartSet(BaseModel):
    
    channel = models.ForeignKey(Channel, blank=False, null=True, related_name="daypartset_set", on_delete=models.SET_NULL)

    time_start = models.DateField(blank=False, null=True)
    time_end = models.DateField(blank=False, null=True)

    class Meta:
        app_label = 'abcast'
        verbose_name = _('Daypart set')
        verbose_name_plural = _('Daypart sets')
        ordering = ('created', )
    
    
    def __unicode__(self):
        return u'%s' % self.time_start
        



class Weekday(models.Model):

    DAY_CHOICES = (
        (1, _('Sun')),
        (2, _('Mon')),
        (3, _('Tue')),
        (4, _('Wed')),
        (5, _('Thu')),
        (6, _('Fri')),
        (7, _('Sat')),
    )
    day = models.PositiveIntegerField(max_length=1, default=1, null=False, choices=DAY_CHOICES)

    class Meta:
        app_label = 'abcast'
        verbose_name = _('Weekay')
        verbose_name_plural = _('Weekays')
        ordering = ('day', )
    
    
    def __unicode__(self):
        return u'%s' % self.get_day_display()
    

class Daypart(BaseModel):

    DAY_CHOICES = (
        (0, _('Mon')),
        (1, _('Tue')),
        (2, _('Wed')),
        (3, _('Thu')),
        (4, _('Fri')),
        (5, _('Sat')),
        (6, _('Sun')),
    )
    daypartset = models.ForeignKey(DaypartSet, blank=False, null=True, on_delete=models.SET_NULL)
    weekdays = models.ManyToManyField(Weekday, null=True, blank=True)
    
    time_start = models.TimeField()
    time_end = models.TimeField()
    
    name = models.CharField(max_length=128, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    mood = models.TextField(null=True, blank=True)
    sound = models.TextField(null=True, blank=True)
    talk = models.TextField(null=True, blank=True)
    
    @property
    def duration(self):
        duration = (self.time_end.hour - self.time_start.hour)
        if duration < 0:
            duration = 24 + duration
        return duration

    class Meta:
        app_label = 'abcast'
        verbose_name = _('Daypart')
        verbose_name_plural = _('Dayparts')
        ordering = ('created', )
    
    
    def __unicode__(self):
        return u'%s - %s' % (self.time_start, self.time_end)
        
        
    