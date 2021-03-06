/*
 * IMPORTER SCRIPTS
 * probably split in importer.base.js and importer.ui.js later on
 */

/* core */
var importer = importer || {};
importer.base = importer.base || {};
importer.ui = importer.ui || {};

ImporterUi = function() {

	var self = this;

	this.lookup_prefix = 'lookup_id_';
	this.field_prefix = 'id_';
	this.interval = false;
	this.interval_loops = 0;
	this.interval_duration = 50000;
	this.api_url = false;

	// attach fu here
	this.fileupload_id = false;
	this.fileupload_options = false

	this.current_data = new Array;
	this.musicbrainz_data = new Array;

	this.is_ie6 = $.browser == 'msie' && $.browser.version < 7;

	this.init = function() {
		console.log('importer: init');
		console.log(self.api_url);
		self.iface();

		self.fileupload = $('#' + self.fileupload_id);
		self.fileupload.fileupload('option', self.fileupload_options);

		self.bindings();

		// set interval (now handled by pushy..)
		// self.set_interval(self.run_interval, self.interval_duration);
		pushy.subscribe(self.api_url, function() {
        	self.run_interval();
        });
		self.run_interval();
	};

	this.iface = function() {
		this.floating_sidebar('lookup_providers', 120)
	};

	this.bindings = function() {

		self.fileupload.bind('fileuploaddone', function(e, data) {
			// run update
			self.update_import_files();
		});
		
		// list items
		$('#result_holder .result-set').live('click', function(e){
			
			/*
			$('.result-set', $(this).parents('.importfile')).removeClass('selected');
			$(this).addClass('selected');
			*/
			$('.result-set', $(this).parents('.importfile')).removeClass('selected choosen');
			$(this).addClass('choosen');
			
			self.apply_best_match();
			
		});
		
		// item actions
		var actions = $('#result_holder .importfile.item .result-actions');
		
		
		$('.delete-importfile', actions).live('click', function(e){
			
			var parent = $(this).parents('.importfile');
			parent_id = parent.attr('id').split('_')[2];
			
			var item = self.current_data[parent_id];
			
			$.ajax({
				type: "DELETE",
				url: item.resource_uri,
				dataType: "application/json",
				contentType: 'application/json',
  				processData:  false,
				// data: JSON.stringify(data),
				success: function(data) {
					// console.log(data);
					// form_result.hide();
				},
				complete: function(jqXHR) {
					if(jqXHR.status == 204) {
						parent.hide(200);
					}

				}
			});
			
		});
		
		
		
		
		$('.start-import', actions).live('click', function(e){
			
			var parent = $(this).parents('.importfile');
			parent_id = parent.attr('id').split('_')[2];
			
			self.import_by_id(parent_id);

		});
		
		
		$('.start-import-all', $('#import_summary')).live('click', function(e){
			$('.importfile.ready').each(function(i, el) {
				id = $(this).attr('id').split('_')[2];			
				self.import_by_id(id);
			});
		});
		
		
		/* summary actions */
		var container = $('#import_summary');
		$(container).on('click', 'a.toggle', function(e){
			e.preventDefault();
			var cls = $(this).data('toggle');
			
			if($(this).data('toggle-active') == 0) {
				
				$('i', this).removeClass('icon-angle-down');
				$('i', this).addClass('icon-angle-up');
				
				$('.importfile.' + cls).show(100);
				$(this).data('toggle-active', 1);
			} else {
				
				$('i', this).removeClass('icon-angle-up');
				$('i', this).addClass('icon-angle-down');
				
				$('.importfile.' + cls).hide(300);
				$(this).data('toggle-active', 0);
			}
			
			
			
		});
	};



	this.import_by_id = function(id) {
		console.log('id: ' + id);
		
		var item = self.current_data[id];
		var el = $('#importfile_result_' + id)
		var form_result = $('.form-result', el);

		var import_tag = {
			name: $('input.name', form_result).val(), 
			release: $('input.release', form_result).val(), 
			releasedate: $('input.releasedate', form_result).val(), 
			artist: $('input.artist', form_result).val(), 
			tracknumber: $('input.tracknumber', form_result).val(), 
			
			mb_track_id: $('input.mb-track-id', form_result).val(), 
			mb_artist_id: $('input.mb-artist-id', form_result).val(), 
			mb_release_id: $('input.mb-release-id', form_result).val(), 
		}
		
		if(! (import_tag.name && import_tag.artist)) {
			alert('Missing fields!!');
			return;
		}
		
		var data = { 
			status: 6, 
			import_tag: import_tag 
			};
		

		el.removeClass('working');
		el.addClass('queued');
		
		$('.result-set', el).hide(100);
		$('.result-actions', el).hide(200);
		
		/**/
		$.ajax({
			type: "PUT",
			url: item.resource_uri,
			dataType: "application/json",
			contentType: 'application/json',
			processData:  false,
			data: JSON.stringify(data),
			success: function(data) {
				console.log(data);
				form_result.hide();
				
			}
		});
		
		
	};


	/*
	 * Methods for import editing
	 */
	this.set_interval = function(method, duration) {
		self.interval = setInterval(method, duration);
	};
	this.clear_interval = function(method) {
		self.interval = clearInterval(method);
	};

	this.run_interval = function() {
		//console.log('interval: ' + self.interval_loops);
		self.interval_loops += 1;

		// Put functions needed in interval here
		self.update_import_files();

	};

	this.update_import_files = function() {

		$.getJSON(self.api_url, function(data) {
			self.update_import_files_callback(data);
		});

	};
	this.update_import_files_callback = function(data) {
		self.update_list_display(data.files);
		self.update_summary_display(data.files);
		try {
			self.update_best_match(data.files);
			self.apply_best_match(data.files);
		} catch(err) {
			// console.log(err);
		}
		
		
	};
	
	this.update_summary_display = function(data) {
		var container = $('#import_summary');
		var status_map = new Array;
		status_map[0] = 'init';
		status_map[1] = 'done';
		status_map[2] = 'ready';
		status_map[3] = 'working';
		status_map[4] = 'warning';
		status_map[5] = 'duplicate';
		status_map[6] = 'queued';
		status_map[7] = 'importing';
		status_map[99] = 'error';

		var count_init = 0;
		var count_done = 0;
		var count_ready = 0;
		var count_working = 0;
		var count_warning = 0;
		var count_duplicate = 0;
		var count_error = 0;

		for (var i in data) {
			var item = data[i];

			if (item.status == 1) {
				count_done++;
			}
			if (item.status == 2) {
				count_ready++;
			}
			if (item.status == 3) {
				count_working++;
			}
			if (item.status == 4) {
				count_warning++;
			}
			if (item.status == 5) {
				count_duplicate++;
			}
			if (item.status == 99) {
				count_error++;
			}
		}
		$('.item.done .num-files', container).html(count_done);
		$('.item.ready .num-files', container).html(count_ready);
		$('.item.working .num-files', container).html(count_working);
		$('.item.warning .num-files', container).html(count_warning);
		$('.item.duplicate .num-files', container).html(count_duplicate);
		$('.item.error .num-files', container).html(count_error);
		//console.log('count_ready:', count_ready);
	
	};


	this.apply_best_match = function(data) {
	
		var holder = $('#result_holder');
		
		$('.importfile', holder).each(function(i, item) {
			
			//console.log(i);
			//console.log(item);
			
			var selected = $('.result-set.musicbrainz-tag.selected, .result-set.musicbrainz-tag.choosen', item)
			
			console.log('media-id', $('.media-id', selected).val());
			console.log('release-id', $('.release-id', selected).val());
			console.log('artist-id', $('.artist-id', selected).val());
			
			var result_form = $('.form-result', item);
			// ids
			$('.mb-track-id', result_form).val($('.media-id', selected).val())
			$('.mb-artist-id', result_form).val($('.artist-id', selected).val())
			$('.mb-release-id', result_form).val($('.release-id', selected).val())
			
			// other data
			$('.releasedate', result_form).val($('.releasedate', selected).val())
			$('.catalognumber', result_form).val($('.catalognumber', selected).val())
			$('.release', result_form).val($('.release', selected).val())
			$('.artist', result_form).val($('.artist', selected).val())
			$('.name', result_form).val($('.name', selected).val())
			
			// selected.hide(20000);

			
		});
	
	};

	this.update_best_match = function(data) {

		var active_releases = new Array;

		//console.log('update_best_match');

		// populate calculation array
		for (var i in data) {
			var item = data[i];
			var target_result = $('#importfile_result_' + item.id);

			if (item.status > 0) {

				try {
					item.results_musicbrainz = JSON.parse(item.results_musicbrainz);
				} catch(err) {
					//console.log(err);
				}

				if (item.id in self.current_data) {

					if (item.results_musicbrainz) {

						for (var k in item.results_musicbrainz) {
							var res = item.results_musicbrainz[k]
							//console.log(res);

							if (res['mb_id'] in active_releases) {
								active_releases[res['mb_id']] += 1;
							} else {
								active_releases[res['mb_id']] = 1;
							}

						}
					}
				}
			}
		}

		active_releases = sortObject(active_releases);

		// console.log(active_releases.reverse());
		
		var hits = active_releases.reverse().slice()
		var top_hit = active_releases[0]['key'];

		//console.log(hits);
		//console.log(top_hit);

		// set selection state
		
		for (var i in data) {
			var item = data[i];
			var target_result = $('#importfile_result_' + item.id);

			$('.result-set.musicbrainz-tag', target_result).removeClass('selected');
			
			// check if manually choosen
			if(!$('.result-set.musicbrainz-tag', target_result).hasClass('choosen')) {
			
			
				if (item.status > 0) {
					
					//console.log(item.results_musicbrainz);
	
					if (item.id in self.current_data) {
	
						if (item.results_musicbrainz) {
	
							//console.log('ok');	
							
							for (var k in item.results_musicbrainz) {
								var res = item.results_musicbrainz[k]
								//console.log(res['mb_id']);
	
								if (res['mb_id'] == top_hit) {
									// console.log('top-match');
									$('.result-set.musicbrainz-tag.mb_id-' + res['mb_id'], target_result).addClass('selected');
								} else {
									//console.log('NOOOOOOO-match');
								}
	
							}
						}
					}
	
				}
			
				
			}

			
			
			
			
			
			
		}

	};

	this.update_list_display = function(data) {

		// console.log(data)
		// console.log(self.current_data)

		var status_map = new Array;
		status_map[0] = 'init';
		status_map[1] = 'done';
		status_map[2] = 'ready';
		status_map[3] = 'working';
		status_map[4] = 'warning';
		status_map[5] = 'duplicate';
		status_map[6] = 'queued';
		status_map[99] = 'error';

		for (var i in data) {

			var item = data[i];
			var target_result = $('#importfile_result_' + item.id);

			if (item.status > -1) { // to check..

				// sorry for this... don't know how to directly provide json from JSONField
				try {
					item.results_tag = JSON.parse(item.results_tag);
					item.results_acoustid = JSON.parse(item.results_acoustid);
					item.results_musicbrainz = JSON.parse(item.results_musicbrainz);
					//item.messages = JSON.parse(item.messages);
				} catch(err) {
					item.results_tag = false;
					//console.log(err);
				}

				//console.log(item.results_musicbrainz);

				if (item.id in self.current_data) {
					self.current_data[item.id] = item;
					console.log('item already present');
				} else {

					var result = tmpl("template-import", item);

					$('#result_holder').append(result);

					self.current_data[item.id] = item;
				}
				
				var target_result = $('#importfile_result_' + item.id);

				// Applying gathered results
				if (item.results_tag) {
					
					//console.log(item.results_tag)

					// building the target
					target_set = $('.provider-tag', target_result);
					for (var k in item.results_tag) {
						var res = item.results_tag[k]
						// console.log(k, res);
						$('.holder-' + k + ' .value', target_set).html(res);
					}
				}

				if (item.results_acoustid) {

					// building the target
					target_set = $('.provider-tag', target_result);
					for (var k in item.results_acoustid) {
						var res = item.results_acoustid[k]
						//console.log(k, res);
						$('.holder-' + k + ' .value', target_set).html(res);
					}
				}

				if (item.media) {

					target_set = $('.status-imported', target_result);
					
					var res = tmpl("template-result-imported", item.media);
					target_set.html(res);
					
				}





				if (item.results_musicbrainz && item.results_musicbrainz.length > 0) {



					// building the target
					target_set = $('.musicbrainz-tag-holder', target_result);

					if (item.id in self.musicbrainz_data) {
						console.log('results_musicbrainz already present');
					} else {
						console.log('results_musicbrainz NOT present');
						self.musicbrainz_data[item.id] = item.results_musicbrainz;
						
						var res = tmpl("template-result-musicbrainz", item);
						target_set.html(res);
					}

					
					
					
					/*
					for (var k in item.results_musicbrainz) {
						console.log(k);
						var res = item.results_musicbrainz[k]
						$('.holder-' + k + ' .value', target_set).html(res);
					}
					*/						

				}

				// Done - Hide selection forms & co
				if (item.status == 1) {
					
					target_result.removeClass('queued');

					$('.result-set', target_result).hide();
					$('.result-actions', target_result).hide();

				}
				if (item.status == 6) {

					$('.result-set', target_result).hide();
					$('.result-actions', target_result).hide();

				}

				for (s in status_map) {
					if (s != item.status) {
						target_result.removeClass(status_map[s]);
					}
				}
				target_result.addClass(status_map[item.status]);

			}

		}

	};

	this.api_lookup = function(item_type, item_id, provider) {

		var data = {
			'item_type' : item_type,
			'item_id' : item_id,
			'provider' : provider
		}

		Dajaxice.alibrary.api_lookup(self.api_lookup_callback, data);
	};

	this.floating_sidebar = function(id, offset) {

		try {

		} catch(err) {
			console.log(error);
		}

	};

};

function sortObject(obj) {
	var arr = [];
	for (var prop in obj) {
		if (obj.hasOwnProperty(prop)) {
			arr.push({
				'key' : prop,
				'value' : obj[prop]
			});
		}
	}
	arr.sort(function(a, b) {
		return a.value - b.value;
	});
	return arr;
	// returns array
}