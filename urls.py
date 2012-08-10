from django.conf.urls.defaults import *

from views import index, team, ladder, game, debugView, user, forms, invite

urlpatterns = patterns('',
    # Root
    (r'^$', index.view),
    (r'^language$', index.language),
    (r'^quick$', index.quick),
    # Ladder views
    (r'^ladder$', ladder.index),
    (r'^ladder/(?P<obj_id>\d+)$', ladder.view),
    (r'^(?P<obj_id>\d+)/manual$', ladder.manual),
    (r'^(?P<obj_id>\d+)/challenge$', ladder.challenge),
    # Team views
    (r'^team$', team.index),
    (r'^team/(?P<obj_id>\d+)$', team.view),
    (r'^team/(?P<obj_id>\d+)/history$', team.history),
    (r'^team/(?P<obj_id>\d+)/graph$', team.ratingGraph),
    (r'^team/validateName$', team.validateName),
    # Game views
    (r'^game$', game.index),
    (r'^game/(?P<obj_id>\d+)$', game.view),
    (r'^game/ticker$', game.ticker),
    # User views
    (r'^user/(?P<obj_id>\d+)$', user.view),
    (r'^user/(?P<obj_id>\d+)/history$', user.history),
    (r'^user/getTeams$', user.getTeams),
    (r'^user/query$', user.query),

    (r'^debug$', debugView),
    #(r'^autocomplete/ladder$', json.ladder),
    #(r'^autocomplete/team$', json.team),
    #(r'^autocomplete/ladderTeam$', json.ladderTeam),

    # Forms
    (r'^forms/quick$', forms.quick),
    (r'^forms/manual$', forms.manual),
    (r'^forms/join$', forms.join),
    (r'^forms/challenge$', forms.challenge),
    (r'^forms/invite$', forms.invite),
    (r'^forms/teamcreate$', forms.teamCreate),

    # Misc
    (r'^invite$', invite),
    (r'^debug$', debugView),
)
