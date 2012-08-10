
window.DEBUG = null;
var Ladder = new Class({
	initialize: function() {
		
	},
	icon: function(icon) {
		return '/static/images/icons/' + icon + '.png';
	}
});

var ActionBox = new Class({
	Implements: [Options, Events],
	options: {
		acceptLabel: 'Ok',
		declineLabel: 'Cancel',
		onAccept: function(){},
		onDecline: function(){}
	},
	initialize: function(options) {
		this.setOptions(options);
		this.element = new Element('div', {'class':'action-box'});
		this.acceptButton = new Jx.Button({
			label: this.options.acceptLabel,
			onClick: this.accept.bindWithEvent(this)
		}).addTo(this.element);
		this.declineButton = new Jx.Button({
			label: this.options.declineLabel,
			onClick: this.decline.bindWithEvent(this)
		}).addTo(this.element);
	},
	accept: function() {
		this.fireEvent('onAccept');
	},
	decline: function() {
		this.fireEvent('onDecline');
	},
	inject: function(el) {
		return this.element.inject(el);
	},
	setEnabled: function(enabled) {
		this.acceptButton.setEnabled(enabled);
		this.declineButton.setEnabled(enabled);
	}
})

var ActionBoxExt = new Class({
	Implements: [Options, Events],
	options: {
		acceptLabel: 'Ok',
		declineLabel: 'Cancel',
		onAccept: function(){},
		onDecline: function(){}
	},
	initialize: function(options) {
		this.setOptions(options);
		this.element = new Element('div', {'class':'action-box'});
		this.acceptButton = new Ext.Button({
			text: this.options.acceptLabel,
			renderTo: this.element
		});
		this.declineButton = new Ext.Button({
			text: this.options.declineLabel,
			renderTo: this.element
		});
	},
	accept: function() {
		this.fireEvent('onAccept');
	},
	decline: function() {
		this.fireEvent('onDecline');
	},
	inject: function(el) {
		return this.element.inject(el);
	},
	setEnabled: function(enabled) {
		this.acceptButton.setEnabled(enabled);
		this.declineButton.setEnabled(enabled);
	}
})

// AJAX Validate new team name
function validateTeamName(string) {
    req = new Request.JSON({
        url: "/ladder/team/validateName",
        method: 'get',
        onComplete: function(result) {
            //submit.setEnabled(result);
			return result;
        }
    }).get({'name':string});
}


function getTeamChart(team_id, ladder_id) {
	var div = new Element('div');
	var table = new HtmlTable();
	table.inject(div);
	var query = new Hash({
		team_id: team_id,
		ladder_id: ladder_id
	})
	new Request.JSON({
		method: 'get',
		url: '/ladder/team/getChart',
		onSuccess: function(result) {
			table.setHeaders([result.name])
			table.element.set('title', result.name)
			result.rows.each(function(row) {
				table.push([row.rating.toInt()]);
			})
			
			var mc = new MilkChart.Line(table.element, {
				showKey: false,
				showRowNames: false,
				showTicks: true,
				useZero: false
			});
			
			
		}
	}).send(query.toQueryString())
	
	return div
}

// Challenge team form
Ladder.ChallengeDirectForm = new Class({
	Implements: [Options, Events],
	options: {
		helpText: 'Which team would you like to challenge with?',
		teamSize: 1,
		teams: []
	},
	initialize: function(ladder, user, blu, options) {
		this.setOptions(options);
		this.ladder = ladder;
		this.user = user;
		this.blu = blu;		
	},
	open: function() {
		this.content = this.build();
		this.dialog = new Jx.Dialog({
	        label: "Challenge Team",
			image: $LADDER.icon('bomb'),
	        modal: true,
			collapse: false,
			width: 450,
			height: 330,
	        content: this.content
	    });
		
	    this.dialog.open();
		new OverText(this.wagers);
	},
	close: function() {
		this.fireEvent('close')
		this.dialog.close();
		this.content.dispose();
	},
	build: function() {
		var div = new Element('div');
		
		var help = new Element('h3').inject(div);
		help.set('text', this.options.helpText);
		
		var teamSelect = new Element('select').inject(div);
		this.options.teams.each(function(team){
			if (team.members.length == this.options.teamSize) {
					var opt = new Element('option', {value:team.id}).inject(teamSelect);
					opt.set('text', team.name);
				}
		}, this);
		
		this.wagers = new Element('textarea', {'alt':'Extra wagers'}).inject(div);
		
		var self = this;
		
		var actions = new ActionBox({
			onAccept: function() {
				this.setEnabled(false);
				this.acceptButton.setImage('/static/images/throbber.gif');
				query = new Hash({
					lid: self.ladder,
					red: teamSelect.getSelected()[0].value,
					blu: self.blu,
					extra: self.wagers.value
				})
				new Request.JSON({
					method: 'post',
					url: '/ladder/challenge/create',
					onSuccess: function(res) {
						if (res.success) {
							$NOTI.show({
								title: 'Success',
								message: res.message
							})
						}
						else {
							$NOTI.show({
								title: 'Failed',
								message: res.message
							})
						}
						self.close();
					}
				}).send(query.toQueryString())
			},
			onDecline: function() {
				this.dialog.close();
			}.bind(this),
			
		});
		actions.inject(div);
		
		return div;
	}
})
Ladder.JoinForm = new Class({
	Implements: [Options, Events],
	options: {
		helpText: 'Please choose to join the ladder with an existing team or create a new one',
		teamSize: 1,
		blu: false,
		onlyNew: false,
		teams: []
	},
	initialize: function(ladder_id, user, options) {
		this.setOptions(options);
		this.ladder_id = ladder_id;
		this.user = user;
		this.minHeight = 260;
		this.success = false;
		this.dialog = null;
		this.isNew = 1;
		this.teamName = null;
		this.teamMembers = [this.user];
	},
	open: function() {
		this.content = this.build();
		this.dialog = new Jx.Dialog({
	        label: "Join Ladder",
	        modal: true,
	        width: 400,
			height: this.minHeight + (this.options.teamSize * 32),
	        content: this.content,
			onClose: function() {this.close()}.bind(this)
	    });
		
	    this.dialog.open();
	},
	close: function() {
		this.fireEvent('close', [this.success, this.teamName]);
		this.content.dispose();
	},
	build: function() {
		var div = new Element('div');
		
		var self = this;
		
		var actions = new ActionBox({
			acceptLabel: 'Join',
			onAccept: function() {
				this.setEnabled(false);
				this.acceptButton.setImage('/static/images/throbber.gif');
				self.validate();
			},
			onDecline: function() {
				self.dialog.close();
			},
			
		});
		actions.inject(div);
		
		var data = new Hash({
			ladder: this.ladder_id,
			onlyNew: Number(this.options.onlyNew),
			blu: Number(this.options.blu),
		})
		var content = new Element('div').inject(div);
		content.set('load', {evalScripts:true,data:data.toQueryString()});
		content.load('/ladder/forms/join');
		
		return div;
	},
	validate: function() {
		this.isNew = Number($('isNew').value);
		this.teamName = (this.isNew) ? $('team_name').value : $('join_ext').getSelected()[0].get('text');
		
		if (this.isNew) {
			this.teamName = $('team_name').value;
			new Request.JSON({
				url: "/ladder/team/validateName",
				method: 'get',
				onComplete: function(result) {
					if (result) {
						var query = new Hash({
							name: this.teamName,
							newTeam: this.isNew
						}).toQueryString();
						
						$$('.members').each(function(member) {
							query += "&members=" + member.value;
						})
						new Request.JSON({
							method: 'post',
							url: '/ladder/' + this.ladder_id + '/join',
							onSuccess: function(result) {
								this.success = result[0];
								this.teamName = result[1];
								this.dialog.close();
							}.bind(this)
						}).send(query)
					}
					else {
						$NOTI.show({
							title: 'Join Failed',
							message: 'Team name is not valid'
						})
					}
				}.bind(this)
			}).get({'name':this.teamName});
		}
		else {
			this.teamName = $('join_ext').getSelected()[0].get('text');
			var query = new Hash({
				name: this.teamName
			}).toQueryString();
			
			new Request.JSON({
				method: 'post',
				url: '/ladder/' + this.ladder_id + '/join',
				onSuccess: function(result) {
					this.success = result[0];
					this.teamName = result[1];
					this.dialog.close();
				}.bind(this)
			}).send(query)
		}
		
	}
})

Ladder.ManualEntryForm = new Class({
	Implements: [Options, Events],
	options: {
		teams: []
	},
	initialize: function(user, options) {
		this.setOptions(options);
		this.user = user;
		this.ladder = null;
		this.ladders = [];
		this.content = this.build();
		this.height = 260;
		this.games = [];
		this.rowId = 0;
		
		this.entryTable = new HtmlTable();
		this.entryTable.element.addClass('manual-game-entry')
	},
	open: function() {
		this.dialog = new Jx.Dialog({
	        label: "Maual Game Entry",
	        modal: true,
			move: false,
			collapse: false,
	        width: 400,
			height: this.height,
	        content: this.content,
			onClose: function() {this.close()}.bind(this)
	    });
		
	    this.dialog.open();
		DEBUG = this.dialog;
	},
	close: function() {
		this.content.dispose();
		this.fireEvent('close', []);
	},
	build: function() {
		var div = new Element('div');
		
		var self = this;
		
		var actions = new ActionBox({
			onAccept: function() {
				this.setEnabled(false);
				this.acceptButton.setImage('/static/images/throbber.gif');
				self.validate();
			},
			onDecline: function() {
				self.dialog.close();
			},
			
		});
		actions.inject(div);
		
		var content = new Element('div').inject(div);
		content.set('load', {
			evalScripts:true,
			onComplete: function() {
				$('ladder_select').addEvent('change', function() {
					this.ladder = $('ladder_select').getSelected()[0].value;
					var postData = {id:this.ladder};
					new Autocompleter.Request.JSON($('blu_team'), '/ladder/autocomplete/ladderTeam', {
						postVar: 'search',
						postData: postData,
						zIndex: 1001
					})
				}.bind(this))
				$('red_team').addEvent('change', function() {
					this.__resetGames();
				}.bind(this));
				$('blu_team').addEvent('keyup', function() {
					this.__resetGames();
				}.bind(this));
				
				new Jx.Button({
					label: 'Add Entry',
					image: $LADDER.icon('add'),
					onClick: function() {
						var entry = this.buildEntryRow($('red_team').getSelected()[0].get('text'), $('blu_team').value);
						//entry.inject('manual_game')
						this.entryTable.push(entry);
					}.bind(this)
				}).addTo('manual_game');
				this.entryTable.inject('manual_game');
			}.bind(this)
		});
		content.load('/ladder/forms/manual');
		
		return div;
	},
	buildEntryRow: function(red, blu) {
		var div = new Element('div', {'class':'manual-game-entry'});
		var rowId = this.rowId;
		var red = new Jx.Button({
			label: red,
			image: $LADDER.icon('user_red'),
			toggle:true
		}).addTo(div);
		var blu = new Jx.Button({
			label: blu,
			image: $LADDER.icon('user'),
			toggle:true
		}).addTo(div);
		
		that = this;
		
		new Jx.ButtonSet({
	        onChange: function(){
				that.__setGame(this.activeButton.getLabel(), rowId);
	        }
	    }).add(red, blu)
		
		this.rowId += 1;
		
		this.height += 32;
		$('manual_game').setStyle('height', $('manual_game').getHeight() + 32)
		this.dialog.resize(400, this.height);
		
		return [red.domObj, blu.domObj]
	},
	validate: function() {
		this.ladder = $('ladder_select').getSelected()[0].value;
		if (this.ladder > 0) {
			var data = new Hash({
				ladder: this.ladder,
				red: $('red_team').getSelected()[0].value,
				blu: $('blu_team').value,
				games: this.games.join(',')
			}).toQueryString();
			
			new Request.JSON({
				method: 'post',
				url: '/ladder/' + this.ladder + '/manual',
				onSuccess: function(res) {
					var success = res[0];
					var message = res[1];
					
					if (success) {
						$NOTI.show({
							message: "All games added successfuly"
						})
						this.close();
						console.log(this.ladder);
						location.href = '/ladder/' + this.ladder
					}
					else {
						$NOTI.show({
							title: "Error",
							message: message
						})
						this.bSubmit.setEnabled(true);
						this.bSubmit.setLabel('Send')
					}
				}.bind(this)
			}).send(data);
		}
	},
	__resetGames: function() {
		this.game = [];
		this.entryTable.empty();
		this.height = 260;
		this.dialog.resize(400, this.height);
	},
	__setGame: function(teamName, row) {
		var red = $('red_team').getSelected()[0].get('text');
		this.games[row] = (teamName == red) ? 0 : 1;
		
		return true
	}
});
Ladder.ChallengeForm = new Class({
	Implements: [Options, Events],
	options: {},
	initialize: function(options) {
		
	},
	open: function() {
		this.content = this.build();
		this.dialog = new Jx.Dialog({
	        label: "Challenge New Team",
	        modal: true,
			move: false,
			collapse: false,
	        width: 400,
			height: 400,
	        content: this.content,
			onClose: function() {this.close()}.bind(this)
	    });
		
	    this.dialog.open();
		DEBUG = this.dialog;
	},
	close: function() {
		this.content.dispose();
		this.fireEvent('close', []);
	},
	build: function() {
		var div = new Element('div');
		
		var actions = new ActionBox({
			onAccept: function() {
				this.validate();
			}.bind(this),
			onDecline: function() {
				this.dialog.close();
			}.bind(this),
			
		});
		actions.inject(div);
		
		var content = new Element('div').inject(div);
		content.set('load', {
			evalScripts:true,
			onComplete: function() {
				$('ladder_select').addEvent('change', function() {
					this.ladder = $('ladder_select').getSelected()[0].value;
					var postData = {id:this.ladder};
					new Autocompleter.Request.JSON($('blu_team'), '/ladder/autocomplete/ladderTeam', {
						postVar: 'search',
						postData: postData,
						zIndex: 1001
					})
				}.bind(this))
				
				new OverText($('wagers'));
			}.bind(this)
		});
		content.load('/ladder/forms/challenge');
		this.actions = actions;
		return div;
	},
	validate: function() {
		this.actions.acceptButton.setEnabled(false);
		this.actions.acceptButton.setLabel('Sending...')
		this.ladder = $('ladder_select').getSelected()[0].value;
		this.wagers = $('wagers').value;
		if (this.ladder > 0) {
			var data = new Hash({
				ladder: this.ladder,
				red: $('red_team').getSelected()[0].value,
				blu: $('blu_team').value,
				wagers: this.wagers
			}).toQueryString();
			
			new Request.JSON({
				method: 'post',
				url: '/ladder/' + this.ladder + '/challenge',
				onSuccess: function(res) {
					var success = res[0];
					var message = res[1];
					
					if (success) {
						$NOTI.show({
							message: "Challenge Sent"
						})
						this.close();
						location.href = '/ladder/' + this.ladder
					}
					else {
						$NOTI.show({
							title: "Error",
							message: message
						})
						this.actions.acceptButton.setEnabled(true);
						this.actions.acceptButton.setLabel('Send')
					}
				}.bind(this)
			}).send(data);
		}
	}
})
Ladder.InviteForm = new Class({
	Implements: Events,
	initialize: function() {
		
	},
	open: function() {
		this.content = this.build();
		this.dialog = new Jx.Dialog({
	        label: "Invite A Friend",
	        modal: true,
			move: false,
			collapse: false,
	        width: 550,
			height: 300,
	        content: this.content,
			onClose: function() {this.close()}.bind(this)
	    });
		
	    this.dialog.open();
	},
	close: function() {
		this.content.dispose();
		this.fireEvent('close', []);
	},
	build: function() {
		var div = new Element('div');
		
		var self = this;
		
		var actions = new ActionBox({
			onAccept: function() {
				this.setEnabled(false);
				this.acceptButton.setImage('/static/images/throbber.gif');
				self.validate();
			},
			onDecline: function() {
				self.dialog.close();
			}.bind(this),
			
		});
		actions.inject(div);
		
		var content = new Element('div').inject(div);
		content.set('load', {
			evalScripts:true
		});
		content.load('/ladder/forms/invite');
		this.actions = actions;
		return div;
	},
	validate: function(){
		var query = new Hash({
			ladder: $('ladder_select').getSelected()[0].value,
			player: $('player').value,
			message: $('message').value
		})
		if (query.ladder == 0) {
			$NOTI.show({
				message: "Please select a ladder first"
			})
			this.actions.setEnabled(true);
			this.actions.acceptButton.setImage('');
			return false;
		}
		new Request({
			method: 'post',
			url: '/ladder/invite',
			onSuccess: function() {
				this.dialog.close();
			}.bind(this)
		}).send(query.toQueryString())
	}
})






















