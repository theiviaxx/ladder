// Ladder

(function(global) {
    var Ladder = {};
    if (typeof exports !== 'undefined') {
        if (typeof module !== 'undefined') {
            module.exports = Ladder;
        }
        else {
            exports = Ladder;
        }
    }
    else {
        global.Ladder = Ladder;
    }

    Ladder.agressionGauge = function() {
        $$('.aggression').each(function(item) {
            var a = item.get('text').toInt();
            item.empty();
            new Element('div', {'class': 'green'}).inject(item);
            if (a >= 400) {
                new Element('div', {'class': 'green'}).inject(item);
                if (a >= 800) {
                    new Element('div', {'class': 'green'}).inject(item);
                }
                else {
                    new Element('div').inject(item);
                }
            }
            else {
                new Element('div').inject(item);
                new Element('div').inject(item);
            }
        });
    };


    function handleURL(url, data) {
        data = new Hash(data || {});
        var el = $('swap');
        el.empty();
        el.set('load', {data:data.toQueryString()});
        el.load(url);
    }
    function setHeader(str) {
        $('mininav').set('text', str);
    }

    global.addEvent('domready', function() {
        // -- Add routes
        routie('ladder/:id', function(id) {
            handleURL('/ladder/ladder/' + id);
            Ladder.initLadder();
        });
        routie('ladder', function(id) {
            handleURL('/ladder/ladder');
        });
        routie('team/:id', function(id) {
            handleURL('/ladder/team/' + id);
        });
        routie('quick', function() {
            handleURL('/ladder/forms/manual');
        });
        routie('reportgame', function() {
            handleURL('/ladder/game');
        });
        // -- Ticker
        Ladder.tickerReq.GET();
        //tickerReq.periodical(60 * 1000); // 60s

        $$('.teamLink').each(function(link) {
            link.addEvent('click', function() {
                routie('team/' + link.id.replace('team_', ''));
            });
        });
        
        $('ladder_link').addEvent('click', function() {
            routie('ladder')
        });
        
        $('team_create').addEvent('click', function(e) {
            e.stop();
            Ladder.Team.create(this);
        });
        $('report_game_button').addEvent('click', function() {
            routie('reportgame')
        });
    });

    Ladder._clearWin = function(e) {
        if (e.target != this.div && !e.target.getParents().contains(this.div)) {
            this.div.destroy();
            window.removeEvent('click', Ladder.clearWin);
        }
    }
    Ladder.clearWin = Ladder._clearWin;

    Ladder.tickerReq = new Request.JSON({
        url: '/ladder/game/ticker',
        method: 'get',
        onSuccess: function(result) {
            var games = result.values;
            var el= $('ticker');
            games.each(function(game) {
                var div = new Element('div');
                new Element('div', {'class': 'tickerOverlay'}).inject(div);
                var str = "{name} {delta}";
                new Element('span', {
                    'class': (game.result === 0) ? 'green' : 'red',
                    html: str.substitute({
                        name: game.red.name,
                        delta: game.red_change.toInt()
                    })
                }).inject(div);
                new Element('br').inject(div);
                new Element('span', {
                    'class': (game.result === 0) ? 'red' : 'green',
                    html: str.substitute({
                        name: game.blu.name,
                        delta: game.blu_change.toInt()
                    })
                }).inject(div);

                div.inject(el);
            });
        }
    });

})(window);

Ladder.initLadder = function() {
    $$('#userTeams li').addEvent('mousedown', function(event){

        var clone = this.clone().setStyles(this.getCoordinates()).setStyles({
            opacity: 0.7,
            position: 'absolute'
        }).inject(document.body);
        clone.addClass('userTeamClone');
        clone.dataset.teamid = this.id.replace('team_', '');
        clone.hide();

        var drag = new Drag.Move(clone, {
            droppables: $('ladder'),
            onSnap: function() {
                event.stop();
                clone.show();
            },
            onDrop: function(dragging, el){
                dragging.destroy();
                if (el != null){
                    el.getElement('table').highlight('#7389AE', '#FFF');
                    new Request.JSON({
                        url: '/ladder/ladder/' + $('ladder').dataset.ladderid,
                        onSuccess: function(res) {
                            if (res.isSuccess) {
                                handleURL('/ladder/ladder/' + $('ladder').dataset.ladderid);
                            }
                            else {
                                Ladder.notify(res.message, 'error')
                            }
                        }
                    }).POST({team: dragging.dataset.teamid});
                }
            },
            onEnter: function(dragging, el){
                el.getElement('table').tween('background-color', '#98B5C1');
            },
            onLeave: function(dragging, el){
                el.getElement('table').tween('background-color', '#FFF');
            },
            onCancel: function(dragging){
                dragging.destroy();
            }
        });
        drag.start(event);
     });
}

Ladder.Team = {
    getChart: function(teamid) {
        var chart = new MilkChart.Line('rating_table', {
            useZero: false,
            showKey: false,
            background: '#eeebdf'
        });
        chart.load({
            url: '/ladder/team/' + teamid + '/graph',
            method: 'get'
        });
        
        $$('.ratingswap').each(function(item) {
            item.addEvent('click', function() {
                chart.load({
                    url: '/ladder/team/' + teamid + '/graph',
                    method: 'get',
                    data: {ladder: item.dataset.ladderid}
                });
            })
        });
    },
    buildShowMore: function(teamid) {
        var showMoreButton = $('showMoreButton');
        if (showMoreButton) {
            showMoreButton.addEvent('click', function() {
                var gamesTable = new HtmlTable('games_table');
                new Request.JSON({
                    url: '/ladder/team/' + teamid + '/history',
                    onSuccess: function(res) {
                        gamesTable.empty();
                        res.values.each(function(item) {
                            //var icon = new Image();
                            var opp, delta;
                            if (item.red.id == teamid) {
                                opp = item.blu;
                                delta = item.red_change;
                            }
                            else {
                                opp = item.red;
                                delta = item.blu_change;
                            }
                            
                            var arrow = new Element('div');
                            arrow.className = (delta >= 0) ? 'arrowGreen' : 'arrowRed';
                            gamesTable.push([
                                new Element('a', {href: '#team/' + opp.id, text: opp.name}),
                                new Element('a', {href: '#ladder/' + item.ladder.id, text: item.ladder.name}),
                                new Date(item.modified).format("%b %e, %Y"),
                                new Element('span', {text: Math.abs(delta.toInt())}).grab(arrow, 'top')
                            ], {
                                'class': (opp.id == item.result) ? 'loss': 'win'
                            });
                        });
                        $('showMoreButton').destroy();
                    }
                }).GET();
            });
        }
    },
    create: function(callingelement) {
        if ($('createTeamPopup')) {
            $('createTeamPopup').destroy();
        }
        
        var div = new Element('div', {
            id: 'createTeamPopup',
            'class': 'triangle-border left',
            styles: {
                top: callingelement.getPosition().y - 60, // height of popup
                left: callingelement.getPosition().x + callingelement.getWidth() + 20 // width of triangle
                // for arrow
            }
        });
        div.load('/ladder/forms/teamcreate')
        div.inject(document.body);
        Ladder.clearWin.div = div;
        window.addEvent('click', Ladder.clearWin)
    }
}

Ladder.Report = {
    addEvents: function() {
        $$('.redTeam, .bluTeam').each(function(item) {
            item.addEvent('click', function(e) {
                e.stop();
                var url = (this.dataset.gameid) ? '/ladder/game/' + this.dataset.gameid : '/tourn/match/' + this.dataset.matchid;
                new Request.JSON({
                    url: url,
                    headers: {"X-CSRFToken": Cookie.read('csrftoken')},
                    onSuccess: function(res) {
                        if (res.isSuccess) {
                            item.parentNode.parentNode.destroy();
                        }
                        Ladder.notify(res.message);
                    }
                }).POST({result: this.dataset.teamid});
            });
        });
    },
    runTimer: function(c, s) {
        var s = s || 60;
        var game = {counter: s};
        function drawCircle(c) {
            var ctx = c.getContext('2d');
            ctx.clearRect(0,0,16,16);
            ctx.beginPath();
            ctx.moveTo(8,8);
            var end = (this.counter * 6) * (Math.PI / 180);
            ctx.arc(8,8,8,0,end);
            ctx.closePath();
            ctx.lineWidth = 1;
            ctx.lineStyle = 'rgb(0,0,0)';
            ctx.fill();
            this.counter--;
            if (this.counter < 0) {
                clearInterval(func);
                Ladder.Report.finalize(c.parentNode.dataset.gameid)
                c.parentNode.destroy();
            }
        }
        var func = drawCircle.periodical(1000, game, c);
    },
    finalize: function(id) {
        new Request.JSON({
            url: '/ladder/game/' + id,
            emulation: false,
            headers: {"X-CSRFToken": Cookie.read('csrftoken')},
            onSuccess: function(res) {
                if (res.isError) {
                    Ladder.notify(res.message, 'error');
                }
            }
        }).PUT({status: 1});
    },
    addUndo: function() {
        $$('.undo').each(function(item) {
            var c = item.getElement('canvas');
            var mod = moment(Date.parse(c.get('text'))).add('m', 1);
            var now = moment();
            var timeLeft = mod.diff(now, 'seconds');
            
            if (timeLeft > -1) {
                Ladder.Report.runTimer(c, timeLeft);
                item.addEvent('click', function(e) {
                    e.stop();
                    new Request.JSON({
                        url: '/ladder/game/' + item.dataset.gameid,
                        emulation: false,
                        headers: {"X-CSRFToken": Cookie.read('csrftoken')},
                        onSuccess: function(res) {
                            
                        },
                        onFailure: function(res) {
                            
                        }
                    }).DELETE();
                })
            }
            else {
                Ladder.Report.finalize(item.dataset.gameid);
                item.parentNode.destroy();
            }
        });
    }
}

Ladder.notify = function(message, type, timeout) {
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