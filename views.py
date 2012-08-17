import time
import datetime
import json
from string import Template

from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect, Http404
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render_to_response, render
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.decorators import method_decorator
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt

from django.template.loader import render_to_string

from languageParser import parse

from settings import SITE_URL, MEDIA_URL

from ladder import updatePending
from ladder.models import Ladder, Team, Game, RatingHistory, LadderMembership, userToJson

from lib.common import JsonResponse, Result, MainView

# Global strings
CH_SAME_TEAM = 'You cannot challenge a team you are a member of'
CH_SUCCESS = 'Challenge sent successfully'
RED_NOT_MEMBER = 'The team you supplied has not joined the ladder spcified'
BLU_NOT_MEMBER = "The opponent's team you supplied has not joined the ladder specified"
IN_BOTH_TEAMS = "You are a member in both teams submitted.  This is not allowed"
ERROR_CREATING_TEAM = "There was an error creating the team"
ALREADY_MEMBER = "This team has already joined this ladder"
L_INCORRECT_SIZE = "The team you tried to join with is not the correct size, please join with a team with %i member(s)"
INVITE_SUBJECT = "Laddder Invitation"
INVITE_MESSAGE = "<p>You have been invited by $player to join the $ladderName ladder.  Please visit $url to join.</p><p>$player has also added this message:<br />$message</p>"

FROM_ADDRESS = 'bdixon@blizzard.com'

LOGIN_REQ = method_decorator(login_required)



class IndexView(MainView):
    @LOGIN_REQ
    def view(self, request):
        context = self._processRequest(request)
        teams = request.user.teams.all()
        teamIds = [t.id for t in teams]
        redGames = Game.objects.filter(red__in=teamIds)
        bluGames = Game.objects.filter(blu__in=teamIds)
        games = redGames | bluGames

        context['title'] = 'Ladder Index'
        context['ladders'] = json.dumps([ladder.json() for ladder in Ladder.objects.all()])
        context['games'] = games

        template = "ladder/index.html"

        return render(request, template, context)
    
    @LOGIN_REQ
    def language(self, request):
        res = Result()
        if request.method != 'POST':
            res.isError = True
            res.message = "Invalid method, use POST"

            return JsonResponse(res)
        
        query = request.POST.get('q', None)
        
        if query:
            try:
                obj = parse(query)
            except:
                res.isError = True
                res.message = "Could not understand your request"
                return JsonResponse(res, 500)
            try:
                ladder = Ladder.objects.get(name=obj['ladder'])
            except ObjectDoesNotExist:
                res.isError = True
                res.message = "The ladder requested was not found"
                return JsonResponse(res, 500)
            ## Red
            if obj['red'] in ['i', 'me']:
                try:
                    red = request.user.teams.filter(ladder=ladder)[0]
                    if ladder.teams.filter(name=obj['blu']).count() == 0:
                        res.isError = True
                        res.message = "Your opponent (%s) does not have any teams in the %s ladder" % (obj['blu'], ladder.name)
                        return JsonResponse(res, 500)
                except:
                    res.isError = True
                    res.message = "You do not have any teams in the %s ladder" % ladder.name
                    return JsonResponse(res, 500)
            else:
                try:
                    red = Team.objects.get(name=obj['red'])
                except ObjectDoesNotExist:
                    res.isError = True
                    res.message = "The team '%s' was not found" % obj['red']
                    return JsonResponse(res, 500)
            ## Blue
            if obj['blu'] in ['i', 'me']:
                try:
                    blu = request.user.teams.filter(ladder=ladder)[0]
                    if ladder.teams.filter(name=obj['red']).count() == 0:
                        res.isError = True
                        res.message = "Your opponent (%s) does not have any teams in the %s ladder" % (obj['red'], ladder.name)
                        return JsonResponse(res, 500)
                except:
                    res.isError = True
                    res.message = "You do not have any teams in the %s ladder" % ladder.name
                    return JsonResponse(res, 500)
            else:
                try:
                    blu = Team.objects.get(name=obj['blu'])
                except ObjectDoesNotExist:
                    res.isError = True
                    res.message = "The team '%s' was not found" % obj['blu']
                    return JsonResponse(res, 500)
            
            winner = red if obj['winner'] == 'red' else blu
            g = Game(red=red, blu=blu, ladder=ladder)
            g.save()
            g.update(winner)

            res.isSuccess = True
            res.message = g.json()
        else:
            res.isError = True
            res.message = "No query provided"

        return JsonResponse(res)
    
    @LOGIN_REQ
    def quick(self, request):
        res = Result()
        context = self._processRequest(request)
        serobj = context['request'].POST.get('q', False)
        if serobj:
            obj = json.loads(serobj)
            ladder = Ladder.objects.get(pk=obj['ladder'])
            red = Team.objects.get(pk=obj['red'])
            blu = Team.objects.get(pk=obj['blu'])
            games = []
            for n in xrange(obj['red_wins']):
                g = Game(ladder=ladder, red=red, blu=blu)
                g.save()
                g.update(red)
                games.append(g)
            for n in xrange(obj['blu_wins']):
                g = Game(ladder=ladder, red=red, blu=blu)
                g.save()
                g.update(blu)
                games.append(g)
            
            res.isSuccess = True    
            res.append([g.json() for g in games])
        else:
            res.isError = True
            res.message = "No query provided"
        
        return JsonResponse(res)


class TeamView(MainView):
    def __init__(self):
        MainView.__init__(self, Team)

    def index(self, request):
        if request.method == 'GET':
            return JsonResponse([team.json() for team in Team.objects.all()])
        elif request.method == 'POST':
            return self.create(request)
        else:
            return HttpResponse()

    #@LOGIN_REQ
    #def view(self, request, obj_id):
    #    return super(TeamView, self).view(request, obj_id)
    
    def get(self, request, obj_id, requestData={}):
        context = requestData
        if request.GET.get('json', False):
            res = Result()
            res.isSuccess = True
            res.append(context['object'].json())
            
            return JsonResponse(res)

        redGames = Game.objects.filter(red__exact=context['id'], status=Game.Closed)
        bluGames = Game.objects.filter(blu__exact=context['id'], status=Game.Closed)
        games = redGames | bluGames

        game_hist = []
        for n in games:
            obj = {
                'opponent': n.blu if context['object'] == n.red else n.red,
                'ladder': n.ladder,
                'status': n.status,
                'win': n.result == context['object'],
                'date': n.created,
                'delta': n.red_change if context['object'] == n.red else n.blu_change,
            }
            game_hist.append(obj)

        context['games'] = game_hist
        context['isMember'] = True if (context['object'].members.filter(username=context['request'].user.username).count()) > 0 else False

        return render(request, 'ladder/team.html', context)

    @LOGIN_REQ
    def create(self, request):
        #self._processRequest(request)
        teamName = request.POST.get('name', None)
        members = request.POST.getlist('members')

        if teamName and members:
            team = Team()
            team.name = teamName
            team.save()

            for n in members:
                try:
                    team.members.create(username=n)
                except:
                    user = User.objects.get(username=n)
                    team.members.add(user)
        else:
            return JsonResponse('false')

        return JsonResponse(team.json())

    @LOGIN_REQ
    def validateName(self, request):
        #self._processRequest(request)
        t = Team.objects.filter(name=request.GET.get('name', None))

        res = Result()
        res.isSuccess = True
        res.append(not bool(len(t)))

        return JsonResponse(res)

    def ratingGraph(self, request, obj_id):
        res = Result()
        team = Team.objects.get(pk=obj_id)
        ladderID = request.GET.get('ladder', None)
        if ladderID:
            try:
                ladder = Ladder.objects.get(pk=ladderID)
            except ObjectDoesNotExist:
                raise Http404
        else:
            try:
                ladder = RatingHistory.objects.filter(team=team).latest().ladder
            except ObjectDoesNotExist:
                raise Http404

        ratings = RatingHistory.objects.filter(ladder=ladder, team=team).order_by('id')
        
        data = {
            'title': ladder.name,
            'rows': [[int(rating.rating),] for rating in ratings],
            'rowNames': [],
            'colNames': [team.name,],
        }
        res.isSuccess = True
        res.append(data)

        return JsonResponse(data)

    def history(self, request, obj_id):
        team = Team.objects.get(pk=obj_id)
        limit = request.GET.get('limit', None)

        redGames = Game.objects.filter(red__exact=team.id, status=Game.Closed)
        bluGames = Game.objects.filter(blu__exact=team.id, status=Game.Closed)
        games = redGames | bluGames

        if limit:
            games = games[:int(limit)]
        
        res = Result()
        res.isSuccess = True
        for game in games:
            res.append(game.json())

        return JsonResponse(res)

    def mail(self):
        """ Send mail to team members notifying htem a team has been created """
        pass


class LadderView(MainView):
    def __init__(self):
        MainView.__init__(self, Ladder)

    @LOGIN_REQ
    def index(self, request):
        context = self._processRequest(request)
        if request.GET.get('json', False):
            ladders = [ladder.json() for ladder in Ladder.objects.all()]
            return JsonResponse(ladders)
        context['ladders'] = Ladder.objects.all()
        context['title'] = 'Ladders'
        template = 'ladder/ladder.html'

        return render(request, template, context)
    
    @LOGIN_REQ
    def get(self, request, obj_id, requestData={}):
        context = requestData#self._processRequest(request, obj_id)
        members = context['object'].laddermembership_set.order_by('-rating__rating')
        userTeams = request.user.teams.all()

        context['members'] = members
        context['ladders'] = Ladder.objects.all()
        context['inLadder'] = True if Ladder.objects.filter(laddermembership__team__in=userTeams) else False
        context['teamsInLadder'] = userTeams.filter(laddermembership__ladder=obj_id)

        template = 'ladder/ladder_item.html'

        return render(request, template, context)
    
    @LOGIN_REQ
    def post(self, request, obj_id, requestData={}):
        return self.join(request, obj_id, requestData)

    @LOGIN_REQ
    def create(self, request):
        """ Create a new ladder """
        #self._processRequest(request)
        ladder = Ladder()
        ladder.name = request.POST.get('name', None)
        ladder.teasize = request.POST.get('size', 1)
        ladder.save()

        return HttpResponseRedirect('/ladder')

    @LOGIN_REQ
    def join(self, request, obj_id, context):
        """ Joins a team to a ladder """
        res = Result()
        teamId = context['request'].POST.get('team', None)

        if teamId:
            try:
                team = Team.objects.get(pk=teamId)
            except ObjectDoesNotExist:
                res.isError = True
                res.message = "Team not found"

                return JsonResponse(res)
            
            if context['object'].laddermembership_set.filter(team=team).count() > 0:
                res.isError = True
                res.message = ALREADY_MEMBER

                return JsonResponse(res)
            
            if len(team) != context['object'].team_size:
                res.isError = True
                res.message = L_INCORRECT_SIZE % context['object'].team_size

                return JsonResponse(res)
            
            # Get a new rating object
            rating = RatingHistory(team=team,ladder=context['object'])
            rating.save()

            lm = LadderMembership(team=team, ladder=context['object'], rating=rating)
            lm.save()

            res.isSuccess = True
            res.append(team.json())

            #self.mail_join(team)

            return JsonResponse(res)
        else:
            res.isError = True
            res.message = "No team provided"

            return JsonResponse(res)

    @LOGIN_REQ
    def manual(self, request, obj_id):
        """ Handles manual game entries """
        res = Result()
        message = ''
        error = False
        context = self._processRequest(request, obj_id)
        red = Team.objects.get(pk=request.POST.get('red', None))
        blu = Team.objects.get(name=request.POST.get('blu', None))
        games = request.POST.get('games', '').split(',')
        
        if request.user in red.members.all() and request.user in blu.members.all():
            error = True
            message = IN_BOTH_TEAMS
        try:
            red.laddermembership_set.get(ladder=context['object'])
        except ObjectDoesNotExist:
            message = RED_NOT_MEMBER
            error = True
        try:
            blu.laddermembership_set.get(ladder=context['object'])
        except ObjectDoesNotExist:
            message = BLU_NOT_MEMBER
            error = True
        if error:
            res.isError = True
            res.message = message
            return JsonResponse(res)

        forMail = []

        for game in games:
            winner = 'red' if game == '0' else 'blu'
            game = Game(
                ladder = context['object'],
                red = red,
                blu = blu,
                status = Game.Closed
            )
            game.save()
            game.update(winner)
            forMail.append(game)
            time.sleep(1)

        self.mail_manual(request.user, forMail)

        res.isSuccess = True
        res.message = message

        return JsonResponse(res)

    @LOGIN_REQ
    def challenge(self, request, obj_id):
        """ Handles manual challenges """
        res = Result()
        context = self._processRequest(request, obj_id)
        red = Team.objects.get(pk=request.POST.get('red', None))
        blu = Team.objects.get(pk=request.POST.get('blu', None))
        if request.user in blu.members.all():
            res.isError = True
            res.message = CH_SAME_TEAM

            return JsonResponse(res)

        game = Game(ladder=context['object'], red=red, blu=blu, status=Game.Open)
        game.save()

        res.isSuccess = True
        res.message = CH_SUCCESS

        #self.mail_challenge(challenge)

        return JsonResponse(res)

    def mail_join(self, team):
        """ Notify all members of team that the team has joined a ladder """
        mail('Team Join', 'ladder/email/ladder_join.html', {'ladder':context['object'], 'team': team}, [user.email for user in team.members.all()])

    def mail_challenge(self, challenge):
        """ Notify all members of blu team that a challenge has been issued """
        mail('You have been challenged!', 'ladder/email/challenge.html', {'object': challenge}, [user.email for user in challenge.blu.members.all()])

    def mail_manual(self, user, games):
        """ Notify all members of both teams that games were entered and their results """
        red = [user.email for user in games[0].red.members.all()]
        blu = [user.email for user in games[0].blu.members.all()]
        mail('Games have been entered', 'ladder/email/manual.html', {'games': games, 'user': user}, red + blu)


class GameView(MainView):
    def __init__(self):
        MainView.__init__(self, Game)

    @LOGIN_REQ
    def index(self, request):
        context = self._processRequest(request)
        if request.method == 'GET':
            updatePending()
            teams = request.user.teams.all()
            qs = Q()
            for n in teams:
                qs |= Q(red=n)
                qs |= Q(blu=n)
            
            games = []
            for n in Game.objects.filter(qs, Q(status=Game.Open) | Q(status=Game.Pending)):
                games.append({
                    'game': n,
                    'red_rating': n.red.laddermembership_set.filter(ladder=n.ladder)[0].rating.rating,
                    'blu_rating': n.blu.laddermembership_set.filter(ladder=n.ladder)[0].rating.rating,
                })
            context['games'] = games
            template = 'ladder/game.html'

            return render(request, template, context)
        elif request.method == 'POST':
            return self.create(request)
        else:
            pass
    
    @LOGIN_REQ
    def get(self, request, obj_id, requestData={}):
        updatePending()
        context = requestData
        teams = request.user.teams.all()
        qs = Q()
        for n in teams:
            qs |= Q(red=n)
            qs |= Q(blu=n)
        
        games = []
        for n in Game.objects.filter(qs, status=Game.Open):
            games.append({
                'game': n,
                'red_rating': n.red.laddermembership_set.filter(ladder=n.ladder)[0].rating.rating,
                'blu_rating': n.blu.laddermembership_set.filter(ladder=n.ladder)[0].rating.rating,
            })
        context['games'] = games
        template = 'ladder/game.html'

        return render(request, template, context)
    
    @LOGIN_REQ
    def post(self, request, obj_id, requestData={}):
        return self.update(request, obj_id, requestData)
    
    @LOGIN_REQ
    def put(self, request, obj_id, requestData={}):
        context = requestData
        res = Result()
        status = context['PUT'].get('status', None)
        if status:
            context['object'].status = int(status)
            context['object'].save()

            res.isSuccess = True
            res.message = "Status update to %i" % context['object'].status
        else:
            res.isError = True
            res.message = "Status was missing or invalid"    
        
        return JsonResponse(res)

    def create(self, request):
        res = Result()
        #context = self._processRequest(request)

        ladder = Ladder.objects.get(pk=request.POST.get('lid', None))
        red = Team.objects.get(pk=request.POST.get('red', None))
        blu = Team.objects.get(pk=request.POST.get('blu', None))

        if len(set(red.members.all()).intersection(blu.members.all())) > 0:
            res.isError = True
            res.message = CH_SAME_TEAM
            
            return JsonResponse(res)

        game = Game()
        game.ladder = ladder
        game.red = red
        game.blu = blu
        game.save()

        res.isSuccess = True
        res.message = CH_SUCCESS

        #mail('You have been challenged!', 'ladder/email/game.html', {'object': game}, [user.email for user in game.blu.members.all()])

        return JsonResponse(res)

    def ticker(self, request):
        res = Result()
        res.isSuccess = True
        for g in Game.objects.filter(status=Game.Closed)[:5]:
            res.append(g.json())

        return JsonResponse(res)

    def update(self, request, obj_id, context):
        """
        Does the maths for the result of the game and closes it out
        """
        
        updatePending()
        res = Result()
        request.POST
        
        if context['object'].status != 0:
            res.isError = True
            res.message = "This game is not open"
            
            return JsonResponse(res)

        if context['request'].user in context['object'].red.members.all() or context['request'].user in context['object'].blu.members.all():
            result = request.POST.get('result', None)
            if not result:
                res.isError = True
                res.message = "Incorrect result type, int required"
                
                return JsonResponse(res)

            context['object'].update(Team.objects.get(pk=result))

            # Send the emails of the results
            red = [user.email for user in context['object'].red.members.all()]
            blu = [user.email for user in context['object'].blu.members.all()]
            #mail('Game has ended', 'ladder/email/game.html', {'game': context['object'], 'user': context['request'].user}, red + blu)
            res.isSuccess = True
            res.message = "Game is now closed"
            res.append(context['object'].json())
        else:
            res.isError = True
            res.message = 'You are not a member of either team for this game.'

        return JsonResponse(res)

    def __send(self, red, blu):
        """
        Send the email to all users involved
        """
        for player in red.teams.all():
            # email(player.email)
            pass
        for player in blu.teams.all():
            # email(player.email)
            pass


class UserView(MainView):
    def __init__(self):
        MainView.__init__(self, User)

    def view(self, request, obj_id):
        #self._processRequest(request, obj_id)

        res = Result()
        res.isSuccess = True
        res.append(userToJson(context['object']))

        return JsonResponse(res)

    def history(self, request, obj_id, returnType=None):
        context = self._processRequest(request, obj_id)
        res = Result()
        limit = request.GET.get('limit', None)

        teams = context['object'].teams.values_list('id', flat=True).order_by('id')
        games = Game.objects.filter(Q(red__in=teams) | Q(blu__in=teams))
        if limit:
            games = games[:int(limit)]
        
        if returnType == 'object':
            return games
        elif returnType == 'json':
            return [game.json() for game in games]
        else:
            res.isSuccess = True
            res.append([game.json() for game in games])
            return JsonResponse(res)
        

    def getTeams(self, request):
        userID = request.GET.get('id', None)
        teamSize = request.GET.get('team_size', None)
        data = False
        if userID:
            obj = User.objects.get(pk=userID)
            teams = obj.teams.all()
            if teamSize:
                teams = teams.filter(laddermembership__ladder__team_size=int(teamSize))

            data = [team.json() for team in teams]
        
        res = Result()
        res.isSuccess = True
        res.append(data)

        return JsonResponse(res)

    @csrf_exempt
    def query(self, request):
        q = request.POST.get('search', '')
        results = []
        res = Result()
        if q:
            users = User.objects.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
            for n in users:
                results.append([n.id, n.username])
            res.isSuccess = True
            res.append(results)
        else:
            res.isError = True
            res.message = 'No search query provided'

        return JsonResponse(res)

class FormsView(object):
    @LOGIN_REQ
    def quick(self, request):
        games = user.history(request, request.user.id, returnType='object')
        recent = []
        existing = {}
        for g in games:
            id = "%i%i%i" % (g.ladder.id, g.red.id, g.blu.id)
            di = "%i%i%i" % (g.ladder.id, g.blu.id, g.red.id)
            if not existing.has_key(id) and not existing.has_key(di):
                recent.append(g)
                existing[id] = True
        context = {}
        context['games'] = json.dumps([game.json() for game in recent])
        template = 'ladder/quick_game.html'
        
        return render(request, template, context)
    
    def manual(self, request):
        teams = request.user.teams.all()
        ladders = Ladder.objects.all()
        context = self._processRequest(request)
        context['user'] = request.user
        context['user_json'] = json.dumps({'id':request.user.id,'name':request.user.username})
        context['teams_json'] = json.dumps([team.json() for team in teams])
        context['ladders_json'] = json.dumps([ladder.json() for ladder in ladders])
        context['teams'] = teams
        context['ladders'] = ladders

        template = 'ladder/forms/manual_ext.html'
        
        return render(request, template, context)

    def join(self, request):
        ladderID = request.GET.get('ladder', None)
        onlyNew = int(request.GET.get('onlyNew', False))
        blu = int(request.GET.get('blu', False))
        if ladderID:
            ladder = Ladder.objects.get(pk=ladderID)
            teams = [team for team in request.user.teams.all() if team.members.count() == ladder.team_size]

            context = {
                'user': request.user,
                'user_json': json.dumps({'id':request.user.id,'name':request.user.username}),
                'teams_json': json.dumps([team.json() for team in teams]),
                'ladders_json': json.dumps(ladder.json()),
                'team_size': ladder.team_size - 1,
                'teams': teams,
                'ladder': ladder,
                'onlyNew': onlyNew,
                'blu': blu,
            }
            context['MEDIA_URL'] = MEDIA_URL
            return render_to_response('ladder/forms/join.html', context)
        return HttpResponse()

    def challenge(self, request):
        teams = request.user.teams.all()
        ladders = Ladder.objects.all()
        context = {
            'user': request.user,
            'user_json': json.dumps({'id':request.user.id,'name':request.user.username}),
            'teams_json': json.dumps([team.json() for team in teams]),
            'ladders_json': json.dumps([ladder.json() for ladder in ladders]),
            'teams': teams,
            'ladders': ladders,
            'needsOpponent': True,
        }
        return render_to_response('ladder/forms/challenge.html', context)

    def invite(self, request):
        ladders = Ladder.objects.all()
        context = {
            'user': request.user,
            'ladders': ladders,
        }
        return render_to_response('ladder/forms/invite.html', context)

    def teamCreate(self, request):
        context = {
            'user': request.user,
            'ajax': request.is_ajax()
        }
        context['MEDIA_URL'] = MEDIA_URL
        return render_to_response('ladder/forms/teamCreate.html', context)


# Single functions
def debugView(request):
    context = {'title':'Debug',
               'request':request,
               'get':request.GET.items(),
               'post':request.POST.items()
               }
    return render_to_response('ladder/email/invite.html', context)

def invite(request):
    player = request.POST.get('player', None)
    message = request.POST.get('message', None)
    ladderID = request.POST.get('ladder', None)

    if ladderID:
        ladder = Ladder.objects.get(pk=ladderID)
        #to = ['%s@blizzard.com' % player]
        to = ['theiviaxx@gmail.com']

        mail("Ladder invitation", 'ladder/email/invite.html', {'ladder': ladder, 'user': request.user, 'message': message}, to)

    return HttpResponse()

def mail(subject, template, context, to):
    to = to if isinstance(to, list) else [to,]

    context['url'] = SITE_URL

    #html = render_to_string(template, context)
    html = '<style type="text/css">table td {border: solid 1px #82c963;}</style><table><tr><td>Some stuff1</td></tr></table>'

    txt = 'this is plain text1'
    # msg = EmailMultiAlternatives(subject, txt, FROM_ADDRESS, to, headers={'Content-Transfer-Encoding':'7bit'})
    # msg.attach_alternative(html, 'text/html')
    # msg.send()


index = IndexView()
team = TeamView()
ladder = LadderView()
game = GameView()
user = UserView()
forms = FormsView()