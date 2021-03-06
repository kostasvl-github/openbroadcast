var ImportfileApp = function () {

    var self = this;
    this.importer;
    this.api_url;
    this.container;
    this.local_data = false;
    this.ac;
    this.api_lock = false;

    this.update_callback = false;


    this.init = function (use_local_data) {
        debug.debug('ImportfileApp - init');

        self.ac = new ImportfileAcApp();

        self.bindings();

        self.load(use_local_data);
        pushy.subscribe(self.api_url, function () {
            debug.debug('pushy callback');
            self.load()
        });

    };


    this.bindings = function () {

        $('.result-set', self.container).live('click', function (e) {
            var el = $(this);
            var import_tag;


            if (el.hasClass('musicbrainz-tag')) {
                debug.debug('mb set selected:', el.index());
                var mb_tag = self.local_data.results_musicbrainz[el.index()]
                import_tag = self.parse_mb_tag(mb_tag);
            }


            if (el.hasClass('provider-tag')) {
                debug.debug('provider set selected');

                var results_tag = self.local_data.results_tag;

                var import_tag = self.local_data.import_tag;

                // unset mb tags
                delete import_tag['mb_track_id'];
                delete import_tag['mb_artist_id'];
                delete import_tag['mb_release_id'];
                delete import_tag['mb_label_id'];

                // unset links
                delete import_tag['alibrary_release_id'];

                import_tag['name'] = results_tag['media_name']
                import_tag['artist'] = results_tag['artist_name']
                import_tag['release'] = results_tag['release_name']
                import_tag['label'] = results_tag['label_name']

            }


            debug.debug(import_tag);

            self.set_import_tag(import_tag);

        });

        $('a.toggle-advanced', self.container).live('click', function (e) {

            $('.advanced-fields', self.container).toggle();

        });

        // autocomplete (input)
        $("input.autocomplete", self.container).live('keyup focus', function (e) {

            var q = $(this).val();
            var ct = $(this).attr('data-ct');
            var target = $('.ac-result', $(this).parent());


            if (e.keyCode == 13 || e.keyCode == 9) {
                return false;
            } else {

                debug.debug(q, ct, target)
                self.ac.search(q, ct, target);
            }

        });
        $("input.autocomplete", self.container).live('blur', function (e) {

            var q = $(this).val();
            var ct = $(this).attr('data-ct');
            var target = $('.ac-result', $(this).parent());

            target.fadeOut(200);
            setTimeout(function () {
                target.html('');
            }, 200);
            target.fadeIn(1);


            // apply to local data first (to allow tabbing)
            // TODO: implementation


            setTimeout(function () {
                if (!self.api_lock) {

                    var import_tag = self.local_data.import_tag;

                    /**/
                    if (ct == 'release') {
                        import_tag['release'] = q;
                        delete import_tag['alibrary_release_id'];
                    }

                    if (ct == 'artist') {
                        import_tag['artist'] = q;
                        delete import_tag['alibrary_artist_id'];
                    }


                    debug.debug('blur', name, ct);

                    self.set_import_tag(import_tag);
                }
            }, 200);

        });
        $("input.autoupdate", self.container).live('blur', function (e) {

            var value = $(this).val();
            var ct = $(this).attr('data-ct');

            if (ct == 'media') {
                self.local_data.import_tag['name'] = value
            }

            setTimeout(function () {
                if (!self.api_lock) {

                    var import_tag = self.local_data.import_tag;
                    self.set_import_tag(import_tag);

                }
            }, 200);

        });

        // autocomplete (result)
        $(".ac-result .item", self.container).live('click', function (e) {
            var el = $(this);
            self.ac_select(el);
        });

        // force creation
        $("input.force-creation", self.container).live('change', function (e) {
            var el = $(this);
            var val = false;
            if (el.attr('checked')) {
                val = true;
            }

            var import_tag = self.local_data.import_tag;

            var ct;

            if (el.parents('.base').hasClass('release')) {
                ct = 'release';
            }
            ;

            if (el.parents('.base').hasClass('artist')) {
                ct = 'artist';
            }
            ;


            if (val) {
                import_tag['force_' + ct] = true;
            } else {
                delete import_tag['force_' + ct];
            }

            self.set_import_tag(import_tag);

        });


        $('.start-import', self.container).live('click', function (e) {

            var data = {
                status: 6
            };

            $.ajax({
                type: "PUT",
                url: self.api_url,
                dataType: "application/json",
                contentType: 'application/json',
                processData: false,
                data: JSON.stringify(data),
                success: function (data) {
                    debug.debug(data);
                }
            });

        });


        $('.rescan', self.container).live('click', function (e) {

            e.preventDefault();

            var settings = {
                skip_tracknumber: false
            };
            var extra_settings = $(this).data('settings');

            if (extra_settings) {
                extra_settings = extra_settings.replace(/\s+/g, '').split(',');
                $.each(extra_settings, function (i, key) {
                    if (key == 'skip_tracknumber') {
                        settings.skip_tracknumber = true;
                    }
                });
            }


            var data = {
                status: 0,
                settings: settings
            };

            debug.debug(data);

            /**/
            $.ajax({
                type: "PUT",
                url: self.api_url,
                dataType: "application/json",
                contentType: 'application/json',
                processData: false,
                data: JSON.stringify(data),
                success: function (data) {
                    debug.debug(data);
                }
            });


        });


        $('.delete-importfile', self.container).live('click', function (e) {

            $.ajax({
                type: "DELETE",
                url: self.api_url,
                dataType: "application/json",
                contentType: 'application/json',
                processData: false,
                complete: function (data) {
                    self.container.fadeOut(200);
                }
            });

        });


        $('.apply-to-all', self.container).live('click', function (e) {

            e.preventDefault();
            var url = self.importer.api_url + 'apply-to-all/';
            var data = {
                item_id: self.local_data.id,
                ct: $(this).attr('data-ct'),
            }

            // data = JSON.stringify(data);

            /**/
            $.ajax({
                type: "POST",
                url: url,
                dataType: "application/json",
                contentType: 'application/json',
                processData: true,
                data: data,
                success: function (data) {
                    debug.debug(data);
                }
            });


        });


    };

    this.ac_select = function (el) {

        var id = el.data('id');
        var name = el.data('name');
        var ct = el.data('ct');

        var import_tag = self.local_data.import_tag;

        if (ct == 'release') {
            import_tag['release'] = name;
            import_tag['alibrary_release_id'] = id;
            delete import_tag['force_release'];
        }

        if (ct == 'artist') {
            import_tag['artist'] = name;
            import_tag['alibrary_artist_id'] = id;
            delete import_tag['force_artist'];
        }

        debug.debug('ac', id, name, ct);

        self.set_import_tag(import_tag);
    }

    this.rebind = function () {
        // $('.tooltip-inline').tooltip({ html: true });

        $('.tooltipable', self.container).tooltip();


        $('.tooltip-inline', self.container).each(function (index) {

            var el = $(this);
            /*
             $.get(el.data('resource_uri'), function (data) {

             data.ct = el.data('ct');

             var d = { item: data }

             var html = nj.render('importer/nj/popover.html', d);

             el.popover({content: html, title: data.name, trigger: 'hover', placement: 'top', html: true});
             });
             */


        });


    }

    this.load = function (use_local_data) {

        debug.debug('ImportfileApp - load');

        self.container.addClass('loading');

        if (use_local_data) {
            debug.debug('ImportfileApp - load: using local data');
            self.display(self.local_data);
        } else {
            debug.debug('ImportfileApp - load: using remote data');
            var url = self.api_url;

            /*
            $.get(url, function (data) {
                console.log(data);

                try {
                    data.results_tag = JSON.parse(data.results_tag);
                    data.results_acoustid = JSON.parse(data.results_acoustid);
                    data.results_musicbrainz = JSON.parse(data.results_musicbrainz);
                    data.import_tag = JSON.parse(data.import_tag);
                    data.messages = JSON.parse(data.messages);
                } catch (err) {
                    data.results_tag = false;
                    console.log(err);
                }


                self.local_data = data;
                self.display(data);
            })
            */


            jQuery.ajaxQueue({
                url: url,
                dataType: "json"
            }).done(function (data) {

                    try {
                        data.results_tag = JSON.parse(data.results_tag);
                        data.results_acoustid = JSON.parse(data.results_acoustid);
                        data.results_musicbrainz = JSON.parse(data.results_musicbrainz);
                        data.import_tag = JSON.parse(data.import_tag);
                        data.messages = JSON.parse(data.messages);
                    } catch (err) {
                        data.results_tag = false;
                        console.log(err);
                    }


                    self.local_data = data;
                    self.display(data);
                });


        }
    };

    this.display = function (data) {

        // TODO: make more nice!!!

        if(self.update_callback) {
            self.update_callback(data);
        }


        var d = {
            object: data,
        };

        var html = nj.render('importer/nj/importfile.html', d);
        self.container.html(html);

        // try to set states
        var selected_mb_id = data.import_tag.mb_release_id;
        console.log('selected_mb_id', selected_mb_id);
        if (selected_mb_id) {
            $('.mb_id-' + selected_mb_id, self.container).addClass('selected');
        }
        self.container.removeClass('loading');

        self.rebind();
        self.api_lock = false;

        // update importer app
        try {
            self.importer.update_summary();
        } catch (e) {
            // pass
        }



    };


    // api methods
    this.set_import_tag = function (import_tag) {

        debug.debug('ImportfileApp - set_import_tag');
        // debug.debug(import_tag)

        self.api_lock = true;

        self.container.addClass('loading');

        // prepare the data
        var data = {
            // status: 6,
            import_tag: import_tag
        };

        $.ajax({
            type: "PUT",
            url: self.api_url,
            dataType: "application/json",
            contentType: 'application/json',
            processData: false,
            data: JSON.stringify(data),
            success: function (data) {
                debug.debug(data);
                // form_result.hide();
                self.api_lock = false;
            }
        });

    }


    // provider tag parsers
    this.parse_mb_tag = function (mb_tag) {

        debug.debug('mb_tag:', mb_tag);

        var import_tag = {

            name: mb_tag.media.name,
            release: mb_tag.name,
            releasedate: mb_tag.releasedate,
            artist: mb_tag.artist.name,
            label: mb_tag.label.name,

            mb_track_id: mb_tag.media.mb_id,
            mb_release_id: mb_tag.mb_id,
            mb_artist_id: mb_tag.artist.mb_id,
            mb_label_id: mb_tag.label.mb_id,

            /*
             release: $('input.release', form_result).val(),
             releasedate: $('input.releasedate', form_result).val(),
             artist: $('input.artist', form_result).val(),
             tracknumber: $('input.tracknumber', form_result).val(),

             mb_track_id: $('input.mb-track-id', form_result).val(),
             mb_artist_id: $('input.mb-artist-id', form_result).val(),
             mb_release_id: $('input.mb-release-id', form_result).val(),
             */
        }

        debug.debug('import_tag:', import_tag);


        return import_tag;
    }

}


ImportfileAcApp = function () {

    var self = this;
    this.template = 'importer/nj/autocomplete.html';
    this.q_min = 2;

    this.search = function (q, ct, target) {

        console.log('AutocompleteApp - search', q, ct, target);

        var url = '/api/v1/' + ct + '/autocomplete-name/?q=' + q + '&';

        if (q.length >= this.q_min) {
            $.get(url, function (data) {
                self.display(target, data);
            });
        } else {
            target.html('');
            // a bit hackish..
        }

    };

    this.display = function (target, data) {
        console.log(data);
        html = nj.render(self.template, data);
        target.html(html);
    };


};