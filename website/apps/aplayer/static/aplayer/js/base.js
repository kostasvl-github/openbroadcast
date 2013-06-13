/*********************************************************************************
 * APLAYER BASE
 * Copyright 2012, Jonas Ohrstrom  - ohrstrom@gmail.com
 * See LICENSE.txt
 *********************************************************************************/



var loaded = true;

var aplayer = aplayer || {};
aplayer.base = aplayer.base || {};
aplayer.vars = aplayer.vars || {};

var local = local || {};
local.timer = local.timer || false;

aplayer.backend = aplayer.backend || 'jwp'; // could be extended

var initial_states = { current: 0, uuid: false, next: false, prev: false};
aplayer.states = aplayer.states || initial_states;
aplayer.states_last = aplayer.states_last || false;

// legacy!! TODO: remove after refactoring
aplayer.vars.states = { current: 0, next: false, prev: false};

// polling interval
aplayer.vars.len_interval = 500;

aplayer.vars.debug = true;
// aplayer.vars.stream_mode = 'rtmp';
aplayer.vars.stream_mode = 'html5';



/*********************************************************************************
 * global initialisation
 * 1st step
 * called from site, on domready
 *********************************************************************************/
aplayer.base.init = function() {
	
	if (aplayer.vars.mode === undefined) {
		aplayer.vars.mode = "replace";
	}
	if (aplayer.vars.playlist_api_url === undefined) {
		aplayer.vars.playlist_api_url = false;
	}
	
	if(aplayer.backend == 'jwp') {
		aplayer.player = aplayer.jwp('aplayer_container'); // loads player into #aplayer_container
	}
	
	// console.log(aplayer.jwp, 'jwp');
	
};



/*********************************************************************************
 * 2nd step 
 * (called by init, prepares the player and continues via 'onReady')
 * returns the jwp instance
 *********************************************************************************/
aplayer.jwp = function(container) {

	// kill instance
	try {
		jwplayer(container).remove();
	} catch(e) {};
	
	// player setup
	return jwplayer(container).setup({
		id: container,
        flashplayer: aplayer.vars.swf_url,
        height: 10,
        width: 610,
        repeat: false,
        events: {
            onReady: function() { aplayer.jwp.on_ready();},
            onPlaylist: function(event) { aplayer.jwp.on_playlist(event);}, 
            onComplete: function(event) { aplayer.jwp.on_complete(event);}
        },
	    modes: [
	        {type: 'flash', src: aplayer.vars.swf_url},
	        {type: 'html5'}
	    ],
    });

};
/*********************************************************************************
 * mapping jwp events to generic ones 
 *********************************************************************************/
aplayer.jwp.on_ready = function() {
	aplayer.base.debug('aplayer.jwp.on_ready()');
	aplayer.base.ready();
};
aplayer.jwp.on_playlist = function(event) {
	
	var uuid = event.playlist[0].mediaid;
	var index = parseFloat(event.playlist[0].index);
	
	aplayer.base.on_play(index, uuid);
};
aplayer.jwp.on_complete = function(event) {

	aplayer.base.on_complete();

};










/*********************************************************************************
 * 3rd step 
 * document is ready now and so is the selected player
 * - this sequence is only required for the initial page-load
 * - this refers to the window where the player lives!
 *********************************************************************************/
aplayer.base.ready = function() {
	
	// initial load, so we want a replace anyway
	aplayer.base.debug('initial load. calling remote window');
	
	parent_win.aplayer.base.remote_player_ready(aplayer);
	
	// register unload event
	$(window).unload(function() {
  		parent_win.aplayer.base.release_remote_player();
	});

};







/*********************************************************************************
 * Load wrapper
 *********************************************************************************/
aplayer.base.load = function(play) {
	
	aplayer.base.debug('aplayer.base.load - callback from remote window');
	
	if(aplayer.vars.debug) {
		console.log(play);
	}
	
	console.log('******************************')
	console.log(play);
	console.log('******************************')
	
	aplayer.vars.uri = play.uri;
	
	if (play.mode === undefined) {
		aplayer.vars.mode = "replace";
	} else {
		aplayer.vars.mode = play.mode;
	}
	if (play.offset === undefined) {
		aplayer.vars.offset = 0;
	} else {
		aplayer.vars.offset = play.offset;
	}
	if (play.force_seek === undefined) {
		aplayer.vars.force_seek = false;
	} else {
		aplayer.vars.force_seek = play.force_seek;
	}
	
	aplayer.vars.source = play.source;
	
	aplayer.base.debug('uri - ' + play.uri);
		
	aplayer.ui.hide_overlay();

	aplayer.base.load_playlist(play.uri);

};




/*********************************************************************************
 * Loads the (json) playlist from the API
 * (eg: /api/releases/142b60ba-41cf-11e1-bcff-d49a20be2cd0/ )
 *********************************************************************************/
aplayer.base.load_playlist = function(uri) {

	console.log('aplayer.base.load_playlist', uri);

	if(uri) {
		data = {};
		
		aplayer.base.debug('aplayer.base.load_playlist() - ' + uri);
		
		$.ajax( {
			url : uri + "?format=json", // FUCK U IE!
			traditional: true,
			type : "GET",
			data : data,
			dataType : "json",
			success : function(result, textStatus, jqXHR) {
				aplayer.base.debug('success: ' + textStatus);
				aplayer.base.set_playlist(result);
			},
			error: function (XMLHttpRequest, textStatus, errorThrown) {
				aplayer.base.debug('error: ' + errorThrown);
				// console.log(errorThrown, 'Error');
			}
		});
	}
};

/*********************************************************************************
 * Parses and sets the loaded playlist
 *********************************************************************************/
aplayer.base.set_playlist = function(result) {


	aplayer.base.debug('start - aplayer.base.set_playlist()');
	
	// store playlist
	aplayer.vars.result = result;
	playlist = result.media;
	
	// TODO: is this neccessary?
	// playlist.sort();

	aplayer.vars.playlist = aplayer.vars.playlist || [];
	
	
	
	
	// replace playlist with newly loaded one
	if(aplayer.vars.mode == 'replace') {
		aplayer.vars.playlist = playlist;
	}
	
	// add loaded playlist to current one
	if(aplayer.vars.mode == 'queue') {
		aplayer.vars.playlist = aplayer.vars.playlist.concat(playlist);
		aplayer.base.prev_next(aplayer.states.current);
	}

	// force start if replace mode
	if(aplayer.vars.mode == 'replace') {
		
		aplayer.base.debug('if(aplayer.vars.mode == replace)');
		
		aplayer.base.controls({action: 'play', index: aplayer.vars.offset, force_seek: aplayer.vars.force_seek});
	}
	
	// map the tracks to an uuid-indexed array
	aplayer.vars.uuid_map = new Array();
	for (i in aplayer.vars.playlist) {
		item = aplayer.vars.playlist[i];
		aplayer.vars.uuid_map[item.uuid] = i;
	}

	aplayer.base.debug('done - aplayer.base.set_playlist()');

	// console.log(result);

	aplayer.ui.playlist_display(aplayer, $('#aplayer_playlist'));
	
};




/*********************************************************************************
 * Player handling / parent-child communication and bindings
 *********************************************************************************/
aplayer.base.play_in_popup = function(uri, token, offset, mode, force_seek, source) {

	if(mode === undefined) {
		mode = "replace";
	}
	if(offset === undefined) {
		offset = 0;
	}
	if(force_seek === undefined) {
		force_seek = false;
	}
	if(source === undefined) {
		source = 'alibrary';
	}
	
	if(aplayer.vars.debug) {
		console.log('aplayer.base.play_in_popup() | uri, token, offset, mode, force_seek');
		console.log(uri, token, offset, mode, force_seek);
	}


	/*
	 * store play options, they are needed when the aplayer is ready and
	 * asks for them. (in 'remote_player_ready()')
	 */
	var play = {
		uri: uri,
		token: token,
		offset: offset,
		mode: mode,
		force_seek: force_seek,
		source: source
	};
	
	local.play = play;
	
	if(!aplayer.base.get_popup_lock()) {
		aplayer.base.grab_player(false);	
	}
	
};


/*********************************************************************************
 * Create or attach the aplayer window. 
 * Possible states:
 * - no window present: create it and load the aplayer html
 * - window present but no bindings: bind (if parent win reloaded in the meantime)
 * - window bresent and attached: use (no reload so far)
 * In each case - the popup calls the parents 'aplayer.base.remote_player_ready()'
 * when ready - and gets further action from there. 
 *********************************************************************************/
aplayer.base.grab_player = function(focus) {

	this.aplayer = false;

	// check if the player is already attached to the window
	if( typeof (local.aplayer) != 'undefined') {

		if(aplayer.vars.debug){
			console.log('found player. re-attach and call: this.aplayer.base.ready();');
		}

		this.aplayer = local.aplayer;
		this.aplayer.base.ready();
		
	} else {

		if(aplayer.vars.debug){
			console.log('found no player. create the popup or try to attach');
		}

		aplayer.base.lock_popup(2000);

		//var aplayer_win = window.open('', 'aplayer', 'width=' + asite.vars.aplayer_width + ', height=' + asite.vars.aplayer_height);
		
		var aplayer_win = window.open('', 'aplayer', 'width=' + 400 + ', height=' + 800);

		if(aplayer_win) {
		
			local.aplayer_win = aplayer_win;
		
			aplayer_win.opener = window;

			// load the player page if necessary
			if( typeof (aplayer_win.aplayer) == 'undefined') {
				
				aplayer_win.location.href = '/player/popup/';

			} else {

				this.aplayer = aplayer_win.aplayer;
				this.aplayer.base.ready();
				
			}

		} else {

			var message = 'Unable to open the Player-window. Please set your browser to allow popups from this site.';
			alert(message);
		}
	}

	if(focus) {
		
		try {
			local.aplayer_win.focus();
		} catch(err) {
			// pass
		};
	}

	return this.aplayer;
};

/*********************************************************************************
 * Called from the remote window as soon as the aplayer is ready.
 *********************************************************************************/
aplayer.base.remote_player_ready = function(remote_aplayer) {
	
	local.aplayer = remote_aplayer;

	local.aplayer.base.load(local.play);
	
};

/*********************************************************************************
 * Called from the remote window on unload,
 * or from Heartbeat interval in case the connection got lost
 *********************************************************************************/
aplayer.base.release_remote_player = function() {
	
	// Remove the local player instance
	try {
		delete local.aplayer;
	}
	catch(err) {
	
	};
	
	aplayer.base.stop_polling();
	// reset screen
	aplayer.ui.reset();
	
};






/*********************************************************************************
 * Interval loop. Should run as long as the player is doing something.
 * Polls information from the player and does some calculation, then triggers
 * needed display updates
 * Called from the window with the actual player!
 *********************************************************************************/
aplayer.base.interval = function() {

	if(local.type == 'popup') {
			
		// console.log('interval popup');
			
		var states = aplayer.states;
		
		// aquire information
		if(aplayer.backend == 'jwp') {
			states.position = aplayer.player.getPosition();
			states.duration = Math.round(aplayer.player.getDuration());
			try {
				states.state = aplayer.player.getState().toLowerCase();
			} catch(err) {
				states.state = 'unknown';
			};
			states.buffer = aplayer.player.getBuffer(); // allways 0 wth rtmp
		}
		
		states.position_rel = (((states.position + 1.4) / states.duration) * 100);
		
		states.total_tracks = aplayer.vars.playlist.length;
		
		aplayer.states_last = aplayer.states;
		aplayer.states = states;
	
		// Updates the local display
		aplayer.ui.update(aplayer);
		
		// Little hackish - update the parents aplayer (if parent exists...)
		try {
			
			/**/
			parent_win.aplayer.ui.update(aplayer);
			
			if(parent_win.local.aplayer_updated === undefined) {
				parent_win.local.aplayer_updated = 0;
			}
			
			parent_win.local.aplayer_updated += 1;
			
			if(! parent_win.local.timer) {
				parent_win.aplayer.base.start_polling(2000);
			}

		}
		catch(err) {
			// console.log(err, 'ERROR');
		};
		
		
		try {

			/*
			var media = aplayer.vars.playlist[aplayer.states.current];
			if(aplayer.vars.debug) {
				console.log(media);
			}
			*/
	
		}
		catch(err) {

		};
	}

	if(local.type == 'main') {

		//console.log('interval main');
		//console.log(local.aplayer_updated);
		
		// Lost heartbeat. So the aplayer maight be fucked up.. 
		if(local.aplayer_updated < 1) {
			aplayer.base.release_remote_player();
		}
		
		local.aplayer_updated = 0;
		
	}
	
};



/*********************************************************************************
 * Checks & sets prev/next/current
 *********************************************************************************/
aplayer.base.prev_next = function(index, uuid) {


	if(index === undefined) {
		var index = 0;
	}

	
	aplayer.states.current = index;	
	aplayer.states.uuid = uuid;
	if(index > 0) {
		aplayer.states.prev = index - 1;
	} else {
		aplayer.states.prev = false;
	}
	if(index < (aplayer.vars.playlist.length - 1)) {
		aplayer.states.next = index + 1;
	} else {
		aplayer.states.next = false;
	}
	
	// console.log(aplayer.states, 'states');

	
};



/*********************************************************************************
 * Backend callbacks. Should be normalized in backend-mapping
 * Does not do so much a.t.m.
 *********************************************************************************/
aplayer.base.on_play = function(index, uuid) {
	
	if(uuid === undefined) {
		var uuid = false;
	}
	aplayer.base.prev_next(index, uuid);
	
};

aplayer.base.on_complete = function() {
	
	if(aplayer.states.next) {
		aplayer.base.controls({action: 'play', index: aplayer.states.next });
		// aplayer.controls('play', aplayer.states.next);
	}
};


aplayer.base.subscribe_channel_data = function(channel) {
	console.log('aplayer.base.subscribe_channel_data: ', channel)
	aplayer.base.update_channel_data(channel)
	
}
aplayer.base.unsubscribe_channel_data = function() {
	console.log('aplayer.base.unsubscribe_channel_data: ')
	
}
aplayer.base.update_channel_data = function(channel) {
	console.log('aplayer.base.update_channel_data: ', channel)
	
	$.get(channel.resource_uri + 'on-air/', function(data) {
		if(data.playing && data.playing.item) {
			$.get(data.playing.item, function(media_data, start_next){

				aplayer.vars.playlist[aplayer.states.current].media = media_data;
				
				
				console.log('got data:', data)
				
				if (data.start_next) {
					console.log('next update:' + ((Math.floor(data.start_next) + 1) * 1000) );
					setTimeout(function() {
						aplayer.base.update_channel_data(channel);
					}, (Math.floor(data.start_next) + 1) * 1000)
				}

			});
		}
	})
	
	// aplayer.vars.playlist[aplayer.states.current].media
	
}

aplayer.base.controls = function(args) {
	
	// console.log(args);
	
	// alert(args.force_seek);
	
	aplayer.base.debug('aplayer.base.controls');
	
	var action = args.action || false;
	var index = args.index || false;

	if(args.index === undefined) {
		var index = false;
	} else {
		var index = args.index;
	}
	
	var uuid = args.uuid || false;
	var position = args.position || false;
	
	
	aplayer.base.debug('action: ' + action);
	aplayer.base.debug('index: ' + index);
	aplayer.base.debug('uuid: ' + uuid);
	
	var fast_polling = false;
	var update_ui = false;
	
	// console.log(action, index, uuid, position);
	
	// stop polling (we only need this during play action)
	aplayer.base.stop_polling();
	
	if(aplayer.backend == 'jwp') {
		var jwp = aplayer.player;
	}
	
	// re-map actions
	// TODO: check if polling needed
	if(action == 'pause') {
		
		if(aplayer.states.state != 'playing') {
			fast_polling = true;
		}
		
		jwp.pause();
	}
	
	
	if(action == 'stop') {

	    jwp.stop();
		fast_polling = false;
		update_ui = true;
		
	}
	
	if(action == 'play' && index !== false) {
		
		// cancel pending subscriptions
		aplayer.base.unsubscribe_channel_data();
		
		// switch to handle live streams
		if (aplayer.vars.source && aplayer.vars.source == 'alibrary') {
			var stream = aplayer.vars.playlist[index].stream;
			console.log('stream:', stream);
		}
		if (aplayer.vars.source && aplayer.vars.source == 'abcast') {
			var channel = aplayer.vars.result;
			
			console.log('channel:', channel);
			aplayer.vars.playlist = [];
			aplayer.vars.playlist[0] = channel;
			
			
			aplayer.base.subscribe_channel_data(channel);
			
			var stream = channel.stream;
		}
		
		
		
		if(aplayer.vars.debug) {
			console.log(stream);
		}
		
		console.log('play via: ' + aplayer.vars.stream_mode);
		
		
		if(aplayer.vars.stream_mode == 'rtmp') {
			var pl = { 'file': stream.file, 
		            	'streamer': stream.rtmp_host + stream.rtmp_app + '/',
		            	'title': stream.media_name,
		            	'mediaid': stream.uuid,
		            	'index': index
		              }
	              
	        aplayer.base.debug('mode: ' + 'rtmp');
		    aplayer.base.debug('file: ' + stream.file);
		    aplayer.base.debug('streamer: ' +  stream.rtmp_host + stream.rtmp_app + '/');
		    aplayer.base.debug('title: ' + stream.media_name);
		    aplayer.base.debug('mediaid: ' + stream.uuid);
		    aplayer.base.debug('index: ' + index);
		}
		
		
	    if (aplayer.vars.stream_mode == 'html5') {
			var pl = {  'file': stream.uri, 
		            	'title': stream.media_name,
		            	'mediaid': stream.uuid,
		            	'index': index
		              }
	        aplayer.base.debug('mode: ' + 'html5');
		    aplayer.base.debug('uri: ' + stream.uri);
	    }
		
		if(aplayer.vars.debug) {
			console.log(pl);
		}
	    
	    
	              
	    jwprun = jwp.stop().load(pl).play();
	    
	    if(args.force_seek) {
	    	jwp.seek(args.force_seek);
	    }
	    
		fast_polling = true;
		update_ui = true;
		
	}
	
	if(action == 'seek' && position) {
		
		var p = aplayer.states.duration;
		p = p / 100 * position;
	  	
	  	//console.log(aplayer.states.duration, 'aplayer.states.duration');
	  	//console.log(p, 'p');

	  	if(uuid && uuid == aplayer.states.uuid) {
	  		
	  		// console.log('seek with SAME uuid');
	  		jwp.seek(p);
	  		
			fast_polling = true;
			update_ui = true;
	  		
	  	} else if (uuid){
	  		
	  		// console.log('seek with DIFFERENT uuid');
	  		var new_index = aplayer.vars.uuid_map[uuid];
	  		aplayer.base.controls({action: 'play', index: aplayer.vars.uuid_map[uuid]});

			fast_polling = true;
			update_ui = true;

	  	} else {
	  		
	  		// console.log('seek WITHOUT uuid');
	  		jwp.seek(p);
	  		
			fast_polling = true;
			update_ui = true;
	  		
	  	}
		
		
		
		
		if(uuid) {
		} else {
			uuid = aplayer.states.uuid;
			// console.log('no uuid.. - use current:', uuid);
			
		}
		
		// console.log('seek:', position);
		
	}
	
	if(fast_polling) {
		aplayer.base.start_polling();
	} else {
		// TODO: find best value
		aplayer.base.start_polling(2000);
	}
	if(update_ui) {
		
		// aplayer.ui.update(aplayer);
		
		aplayer.ui.playlist_display(aplayer, $('#aplayer_playlist'));
		
		if(index !== false) {
			aplayer.ui.screen_display(index);
		}
		
	}
	
	// log
	aplayer.base.log(action, index, uuid);
	
	// trigger interval
	aplayer.base.interval();
	
};





















/* UNUSED */
aplayer.controls = function(action, index, uuid) {
	
	var jwp = aplayer.player;
	
	if(aplayer.timer) {
		clearInterval(aplayer.timer); 
	}
	
	switch(action)
	{
		// play
		case 'play':
		  
			var stream = aplayer.vars.playlist[index].stream;	
			jwp.stop();

			var tpl = { 'file': stream.file, 
		            	'streamer': stream.rtmp_host + stream.rtmp_app + '/',
		            	'title': stream.media_name,
		            	'mediaid': stream.uuid,
		            	'index': index
		              }
		              
	    	
	    	jwp.load(tpl).play();	    	
	    	aplayer.timer = setInterval ( "aplayer.interval()", aplayer.vars.len_interval );
	    	
			aplayer.ui.screen_display(index);

			break;
			
		// pause (toggle)
		case 'pause':
		  	jwp.pause();
		 	break;
			
		// stop
		case 'stop':
		  	jwp.stop();
		 	break;
			
		// pause (toggle)
		case 'next':
		  	jwp.pause();
		 	break;
			
		// seek (abs, seconds)
		case 'seek':
		  	jwp.pause();
		 	break;
		 	
		// seek (percent, 0-100)
		case 'seek_p':
			var p = aplayer.vars.states.duration;
			p = p / 100 * index;
		  	jwp.seek(p);
		  	
		  	aplayer.timer = setInterval ( "aplayer.interval()", aplayer.vars.len_interval );
		  	
		 	break;
		 	
		// seek by uuid (used from parent, to allow 'mixed' playlists)
		case 'seek_by_uuid':
		
			var p = aplayer.vars.states.duration;
			p = p / 100 * index;
		  	
		  	
		  	var current_uuid = aplayer.vars.playlist[aplayer.vars.states.current].uuid;
		  	

		  	if(uuid == current_uuid) {
		  		jwp.seek(p);
		  	} else {
		  		var new_index = aplayer.vars.uuid_map[uuid];
		  		
		  		aplayer.controls('play', new_index);
		  		
		  		aplayer.controls('seek_p', index);
				
		  		
		  	}
		  	
		  	aplayer.timer = setInterval ( "aplayer.interval()", aplayer.vars.len_interval );

		 	break;
		 	

		 	
		 	
		default:
		  	break;
		  	
		 
	}
	
	
	aplayer.base.log(action, index, uuid);

	// trigger interval function for quick ui-refresh
	aplayer.interval();

	

};

aplayer.on_playlist = function(event) {
	
	var uuid = event.playlist[0].mediaid;
	var index = parseFloat(event.playlist[0].index);
	
	// console.log(uuid, 'uuid');
	// console.log(index, 'index');
	
	aplayer.vars.states.current = index;
	if(index > 0) {
		aplayer.vars.states.prev = index - 1;
	} else {
		aplayer.vars.states.prev = false;
	}
	if(index < (aplayer.vars.playlist.length - 1)) {
		aplayer.vars.states.next = index + 1;
	} else {
		aplayer.vars.states.next = false;
	}
	
	//console.log(aplayer.vars.states, 'states');
	
};

aplayer.on_complete = function(event) {
	if(aplayer.vars.states.next) {
		aplayer.controls('play', aplayer.vars.states.next);
	}

};








/*********************************************************************************
 * things needing refactoring
 *********************************************************************************/






// TODO: still needed?
aplayer.base.reload = function(uri, token, offset, mode) {
	
	if (offset === undefined) {
		offset = 0;
	}
	
	// load empty playlist (a.k.a. reset)
	jwplayer().stop().load({});
	
	// TODO: use mode from player call (queue/replace)
	aplayer.base.load(uri, offset, mode);
	
};












aplayer.interval = function() {
	
	
	/*
	//aplayer.vars.states.position = Math.round(aplayer.player.getPosition());
	aplayer.vars.states.position = aplayer.player.getPosition();
	aplayer.vars.states.duration = Math.round(aplayer.player.getDuration());
	
	aplayer.vars.states.position_rel = ((aplayer.vars.states.position / aplayer.vars.states.duration) * 100);
	
	
	// TODO: MAKE THIS BETTER!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	
	aplayer.vars.states.buffer = aplayer.player.getBuffer();
	aplayer.vars.states.state = aplayer.player.getState();
	
	$('body').removeClass('buffering');
	$('body').removeClass('playing');
	$('body').removeClass('paused');
	$('body').addClass(aplayer.vars.states.state.toLowerCase());
	
	$(document).attr('title', aplayer.vars.states.buffer + ' | ' + aplayer.vars.states.state);

	// update player _inside_ the popup
	asite.ui.play_update(aplayer, 610);
	
	// little hackish - update the parents aplayer (if parent exists...)
	try {
		parent_win.asite.ui.play_update(aplayer);
	}
	catch(err) {
	
	};
	
	*/
};












/*********************************************************************************
 * Start/stop backend polling
 *********************************************************************************/
aplayer.base.start_polling = function(interval) {
	
	if(interval === undefined) {
		interval = interval = aplayer.vars.len_interval;
	}
	
	if(local.timer) {
		clearInterval(local.timer);
	}
	
	local.timer = setInterval ( "aplayer.base.interval()", interval );
};
aplayer.base.stop_polling = function() {
	if(local.timer) {
		clearInterval(local.timer);
	}
};



/*********************************************************************************
 * popup locking. to prevent triggering the window multiple times
 *********************************************************************************/
aplayer.base.get_popup_lock = function() {
	if(typeof (local.popup_lock) != 'undefined') {
		return local.popup_lock;
	}
	return false;
};
aplayer.base.lock_popup = function(time) {
	if(time === undefined) {
		time = 3000;
	}
	local.popup_lock = true;
	setTimeout("aplayer.base.unlock_popup()", time);
	return time;
};
aplayer.base.unlock_popup = function() {
	local.popup_lock = false;
	return true;
};




/*********************************************************************************
 * logging / event tracking
 *********************************************************************************/
aplayer.base.log = function(action, index, uuid) {
	
	try {
		var item = aplayer.vars.playlist[aplayer.vars.states.current];
		var log_value = false;
		if(action == 'seek_by_uuid') {
			log_value = Math.round(index);
		}
		var log_string = item.name + ' - ' + item.artist.name;
	} catch(err) {
		var log_string = uuid;
	};


	//asite.base.log('track', action, log_string);
};





/*********************************************************************************
 * logging / event tracking
 *********************************************************************************/
aplayer.base.debug = function(text) {
	
	var d = new Date();
	var hour = d.getHours();
	var min = d.getMinutes();
	var sec = d.getSeconds();
	
	var time = hour + ':' + min + ':' + sec;
	
	$('.footer > .wrapper').prepend('<p>' + '<span>' + time + '</span> | ' + text + '</p>');
};