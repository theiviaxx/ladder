""" context_processors """

import json

def ladder(request):
    context = {}
    if request.user.is_authenticated():
        teams = request.user.teams.all()
        context['teams'] = teams
        context['userTeams'] = json.dumps([team.json() for team in teams])
        if not teams:
            newTeam = request.user.teams.create(name=request.user.username)
            newTeam.members.add(request.user)
            newTeam.save()

    return context