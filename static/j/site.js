(function(global) {
    global.UBD = this;

    this.hist = new HashListener();
    this.ladder = {};

    this.handleURL = function(url, data) {
        data = new Hash(data || {});
        var el = $('swap');
        el.empty();
        el.set('load', {data:data.toQueryString()});
        el.load(url);
    }

    this.init = function() {
        var self = this;
        $$('.teamLink').each(function(link) {
            link.addEvent('click', function() {
                self.hist.updateHash('team/' + link.id.replace('team_', ''));
            });
        });

        // Navigation
        $('home_link').addEvent('click', function() {
            self.hist.updateHash('1');
        });
        $('ladder_link').addEvent('click', function() {
            self.hist.updateHash('ladder');
        });
        $('tourn_link').addEvent('click', function() {
            self.hist.updateHash('tourn');
        });
        $('report_game_button').addEvent('click', function() {
            self.hist.updateHash('reportgame');
        });
        $('team_create').addEvent('click', function(e) {
            e.stop();

            if ($('createTeamPopup')) {
                $('createTeamPopup').destroy();
            }
            
            var div = new Element('div', {
                id: 'createTeamPopup',
                'class': 'triangle-border left',
                styles: {
                    top: this.getPosition().y - 60, // height of popup
                    left: this.getPosition().x + this.getWidth() + 20 // width of triangle
                     // for arrow
                }
            });
            div.load('/ladder/forms/teamcreate')
            div.inject(document.body);

            var clearWin = function(e) {
                if (e.target != div && !e.target.getParents().contains(div)) {
                    div.destroy();
                    global.removeEvent('click', clearWin);
                }
            }
            global.addEvent('click', clearWin)
        });

        $('quickGameMenu').addEvent('click', function() {
            var div = new Element('div', {
                id: 'win',
                load: {
                    url: '/ladder/forms/quick',
                    onSuccess: function() {
                        var clearWin = function(e) {
                            if (e.target != div && !e.target.getParents().contains(div)) {
                                div.destroy();
                                global.removeEvent('click', clearWin);
                            }
                        }
                        global.addEvent('click', clearWin);
                    }
                }
            }).inject(document.body);
            div.load();
            div.position({
                relativeTo: $('report_game_button'),
                position: 'bottomLeft',
                edge: 'bottomLeft'
            });
        });

        this.initHistory();
    }.bind(this);

    this.initHistory = function() {
        var self = this;
        this.hist.start();
        this.hist.addEvent('hashChanged', function(hash) {
            switch (hash.slice(0,4)) {
                case 'ladd':
                    var path = hash.split('/');
                    if (path.length > 1) {
                        self.handleURL('/ladder/ladder/' + path[1]);
                    }
                    else {
                        self.handleURL('/ladder/ladder');
                        $$('nav div').removeClass('current');
                        $('ladder_link').addClass('current');
                    }
                    $$('#userTeams li').addEvent('mousedown', function(event){
                        var shirt = this;
                        var clone = shirt.clone().setStyles(shirt.getCoordinates()).setStyles({
                            opacity: 0.7,
                            position: 'absolute'
                        }).inject(document.body);
                        clone.addClass('userTeamClone');
                        clone.dataset.teamid = shirt.id.replace('team_', '');
                        clone.hide();

                        var drag = new Drag.Move(clone, {
                            droppables: $('ladder'),
                            onSnap: function() {
                                event.stop();
                                clone.show();
                            },
                            onDrop: function(dragging, cart){
                                dragging.destroy();
                                if (cart != null){
                                    cart.getElement('table').highlight('#7389AE', '#FFF');
                                    new Request.JSON({
                                        url: '/ladder/ladder/' + $('ladder').dataset.ladderid,
                                        data: 'team=' + dragging.dataset.teamid,
                                        onSuccess: function(res) {
                                            if (res.isSuccess) {
                                                self.handleURL('/ladder/ladder/' + $('ladder').dataset.ladderid);
                                            }
                                            else {
                                                self.notify(res.message, 'error')
                                            }
                                        }
                                    }).POST();
                                }
                            },
                            onEnter: function(dragging, cart){
                                cart.getElement('table').tween('background-color', '#98B5C1');
                            },
                            onLeave: function(dragging, cart){
                                cart.getElement('table').tween('background-color', '#FFF');
                            },
                            onCancel: function(dragging){
                                dragging.destroy();
                            }
                        });
                        drag.start(event);
                    });
                    break;
                case 'team':
                    var path = hash.split('/');
                    if (path.length > 1) {
                        if (path[1] == 'create') {
                            var data = new Hash({
                                
                            });
                            self.handleURL('/ladder/forms/teamcreate', data);
                        }
                        else {
                            self.handleURL('/ladder/team/' + path[1]);
                        }
                    }
                    break;
                case 'quic':
                    self.handleURL('/ladder/forms/manual');
                    break;
                case 'repo':
                    self.handleURL('/report');
                    break;
                case 'tour':
                    self.handleURL('/tourn/1');
                    $$('nav div').removeClass('current');
                    $('tourn_link').addClass('current');
                    break;
                default:
                    $('swap').empty();
                    $$('nav div').removeClass('current');
                    $('home_link').addClass('current');
                    break;
            }
        });
    }.bind(this);

    this.notify = function(message, type, timeout) {
        var timeout = timeout || 10;
        var el = $('notify');
        el.addEvent('click', el.hide);
        var msg = new Element('div', {text: message})
        switch(type) {
            case 'error':
                msg.setStyles({
                    'background-color': '#dd4b39',
                    'border-color': '#900',
                    color: '#fff'
                });
                break;
            default:
                msg.setStyles({
                    'background-color': '#fef7cb',
                    'border-color': '#ffe475',
                    color: '#000'
                });
                break;
        }
        el.empty();
        msg.inject(el);
        el.reveal();
        el.dissolve.delay(timeout * 1000, el) // 30 sec
    }

})(window);