from django import forms
from django.conf import settings

from django.forms import ModelForm, Form

from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.contrib.contenttypes.generic import BaseGenericInlineFormSet, generic_inlineformset_factory


from django.utils.translation import ugettext as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import *
from crispy_forms.bootstrap import FormActions

from filer.models.imagemodels import Image

from django.contrib.admin import widgets as admin_widgets

import autocomplete_light

from alibrary.models import Media, Relation, Artist, MediaExtraartists

from pagedown.widgets import PagedownWidget

import selectable.forms as selectable
from alibrary.lookups import ReleaseNameLookup, ArtistLookup, LicenseLookup


import floppyforms as forms
from django_date_extensions.fields import ApproximateDateFormField

from ajax_select.fields import AutoCompleteSelectField
from ajax_select import make_ajax_field

    
from django.forms.widgets import FileInput, HiddenInput

#from floppyforms.widgets import DateInput
from tagging.forms import TagField
from ac_tagging.widgets import TagAutocompleteTagIt

from lib.widgets.widgets import ReadOnlyIconField



ACTION_LAYOUT =  action_layout = FormActions(
                HTML('<button type="submit" name="save" value="save" class="btn btn-primary pull-right ajax_submit" id="submit-id-save-i-classicon-arrow-upi"><i class="icon-save icon-white"></i> Save</button>'),            
                HTML('<button type="reset" name="reset" value="reset" class="reset resetButton btn btn-secondary pull-right" id="reset-id-reset"><i class="icon-trash"></i> Cancel</button>'),
        )
ACTION_LAYOUT_EXTENDED =  action_layout = FormActions(
                Field('publish', css_class='input-hidden' ),
                HTML('<button type="submit" name="save" value="save" class="btn btn-primary pull-right ajax_submit" id="submit-id-save-i-classicon-arrow-upi"><i class="icon-save icon-white"></i> Save</button>'),            
                HTML('<button type="submit" name="save-and-publish" value="save" class="btn pull-right ajax_submit save-and-publish" id="submit-id-save-i-classicon-arrow-upi"><i class="icon-bullhorn icon-white"></i> Save & Publish</button>'),            
                HTML('<button type="reset" name="reset" value="reset" class="reset resetButton btn btn-secondary pull-right" id="reset-id-reset"><i class="icon-trash"></i> Cancel</button>'),
        )


class MediaActionForm(Form):
    
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', False)        
        super(MediaActionForm, self).__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        
        
        self.helper.add_layout(ACTION_LAYOUT)
        """
        if self.instance and self.instance.publish_date:
            self.helper.add_layout(ACTION_LAYOUT)
        else:
            self.helper.add_layout(ACTION_LAYOUT_EXTENDED)
        """    
    publish = forms.BooleanField(required=False)


class MediaForm(ModelForm):

    class Meta:
        model = Media
        fields = ('name', 'description', 'artist', 'tracknumber', 'mediatype', 'license', 'release', 'd_tags', 'isrc', )


    def __init__(self, *args, **kwargs):

        self.user = kwargs['initial']['user']
        self.instance = kwargs['instance']
        
        print self.instance
        
        print self.user.has_perm("alibrary.edit_release")
        print self.user.has_perm("alibrary.admin_release", self.instance)

        
        self.label = kwargs.pop('label', None)
        

        super(MediaForm, self).__init__(*args, **kwargs)
        
        """
        Prototype function, set some fields to readonly depending on permissions
        """
        """
        if not self.user.has_perm("alibrary.admin_release", self.instance):
            self.fields['catalognumber'].widget.attrs['readonly'] = 'readonly'
        """

        self.helper = FormHelper()
        self.helper.form_id = "id_feedback_form_%s" % 'asd'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        self.helper.form_tag = False
        
        
        base_layout = Fieldset(
                               
                _('General'),
                LookupField('name', css_class='input-xlarge'),
                LookupField('release', css_class='input-xlarge'),
                LookupField('artist', css_class='input-xlarge'),
                LookupField('tracknumber', css_class='input-xlarge'),
                LookupField('mediatype', css_class='input-xlarge'),
        )
        
        license_layout = Fieldset(
                _('License/Source'),
                Field('license', css_class='input-xlarge'),   
        )
        
        catalog_layout = Fieldset(
                _('Label/Catalog'),
                LookupField('label', css_class='input-xlarge'),
                LookupField('catalognumber', css_class='input-xlarge'),
                LookupField('release_country', css_class='input-xlarge'),
                # LookupField('releasedate', css_class='input-xlarge'),
                LookupField('releasedate_approx', css_class='input-xlarge'),
        )
        

        meta_layout = Fieldset(
                'Meta',
                LookupField('description', css_class='input-xxlarge'),
        )
        
        tagging_layout = Fieldset(
                'Tags',
                LookupField('d_tags'),
        )

        identifiers_layout = Fieldset(
                _('Identifiers'),
                LookupField('isrc', css_class='input-xlarge'),
        )
            
        layout = Layout(
                        base_layout,
                        # artist_layout,
                        meta_layout,
                        license_layout,
                        tagging_layout,
                        identifiers_layout,
                        )

        self.helper.add_layout(layout)

        

    

    d_tags = TagField(widget=TagAutocompleteTagIt(max_tags=9), required=False, label=_('Tags'))
    release = selectable.AutoCompleteSelectField(ReleaseNameLookup, allow_new=True, required=True) 
    
    
    
    """
    extra_artists = forms.ModelChoiceField(Artist.objects.all(),
        widget=autocomplete_light.ChoiceWidget('ArtistAutocomplete'), required=False)
    """
    
    artist = selectable.AutoCompleteSelectField(ArtistLookup, allow_new=True, required=False)    
    
    
    
    
    description = forms.CharField(widget=PagedownWidget(), required=False, help_text="Markdown enabled text")   

    
    #license = selectable.AutoCompleteSelectField(LicenseLookup, widget=selectable.AutoComboboxSelectWidget(lookup_class=LicenseLookup), allow_new=False, required=False, label=_('License'))

    # aliases = selectable.AutoCompleteSelectMultipleField(ArtistLookup, required=False)
    # aliases  = make_ajax_field(Media,'aliases','aliases',help_text=None)
    
    #members = selectable.AutoCompleteSelectMultipleField(ArtistLookup, required=False)
    

    def clean(self, *args, **kwargs):
        
        cd = super(MediaForm, self).clean()

        print "*************************************"
        print cd
        print "*************************************"
        
            
        """
        
        if 'main_image' in cd and cd['main_image'] != None:
            try:
                ui = cd['main_image']
                dj_file = DjangoFile(open(ui.temporary_file_path()), name='cover.jpg')
                cd['main_image'], created = Image.objects.get_or_create(
                                    original_filename='cover_%s.jpg' % self.instance.pk,
                                    file=dj_file,
                                    folder=self.instance.folder,
                                    is_public=True)
            except Exception, e:
                print e
                pass
            
        else:
            cd['main_image'] = self.instance.main_image
        """

        return cd

    # TODO: take a look at save
    def save(self, *args, **kwargs):
        return super(MediaForm, self).save(*args, **kwargs)
   
    






"""
Album Artists
"""
class BaseExtraartistFormSet(BaseInlineFormSet):


    def __init__(self, *args, **kwargs):

        self.instance = kwargs['instance']

        super(BaseExtraartistFormSet, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "id_artists_form_%s" % 'inline'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        self.helper.form_tag = False

        base_layout = Row(
                Column(
                       Field('artist', css_class='input-large'),
                       css_class='span5'
                       ),
                Column(
                       Field('profession', css_class='input-large'),
                       css_class='span5'
                       ),
                Column(
                       Field('DELETE', css_class='input-mini'),
                       css_class='span2'
                       ),
                css_class='albumartist-row row-fluid form-autogrow',
        )

        self.helper.add_layout(base_layout)




    def add_fields(self, form, index):
        # allow the super class to create the fields as usual
        super(BaseExtraartistFormSet, self).add_fields(form, index)

        # created the nested formset
        try:
            instance = self.get_queryset()[index]
            pk_value = instance.pk
        except IndexError:
            instance=None
            pk_value = hash(form.prefix)


class BaseExtraartistForm(ModelForm):

    class Meta:
        model = MediaExtraartists
        parent_model = Media
        fields = ('artist','profession',)

    def __init__(self, *args, **kwargs):
        super(BaseExtraartistForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

    artist = selectable.AutoCompleteSelectField(ArtistLookup, allow_new=True, required=False)









  
class BaseMediaReleationFormSet(BaseGenericInlineFormSet):

        
        
    def __init__(self, *args, **kwargs):

        self.instance = kwargs['instance']
        super(BaseMediaReleationFormSet, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "id_releasemediainline_form_%s" % 'asdfds'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.form_action = ''
        self.helper.form_tag = False
        
        base_layout = Row(
                Column(
                       Field('url', css_class='input-xlarge'),
                       css_class='span6 relation-url'
                       ),
                Column(
                       Field('service', css_class='input-mini'),
                       css_class='span4'
                       ),
                Column(
                       Field('DELETE', css_class='input-mini'),
                       css_class='span2'
                       ),
                css_class='row-fluid relation-row form-autogrow',
        )
 
        self.helper.add_layout(base_layout)
        


class BaseMediaReleationForm(ModelForm):

    class Meta:
        model = Relation
        parent_model = Media
        formset = BaseMediaReleationFormSet
        fields = ('url','service',)
        
    def __init__(self, *args, **kwargs):
        super(BaseMediaReleationForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.fields['service'].widget.instance = instance
        if instance and instance.id:
            self.fields['service'].widget.attrs['readonly'] = True
        
    def clean_service(self):
        return self.instance.service

    service = forms.CharField(label='', widget=ReadOnlyIconField(), required=False)
    url = forms.URLField(label=_('Website / URL'), required=False)



# Compose Formsets
MediaRelationFormSet = generic_inlineformset_factory(Relation,
                                                     form=BaseMediaReleationForm,
                                                     formset=BaseMediaReleationFormSet,
                                                     extra=10, exclude=('action',),
                                                     can_delete=True)

ExtraartistFormSet = inlineformset_factory(Media,
                                       MediaExtraartists,
                                       form=BaseExtraartistForm,
                                       formset=BaseExtraartistFormSet,
                                       fk_name = 'media',
                                       extra=10,
                                       #exclude=('position',),
                                       can_delete=True,
                                       can_order=False,)




    