import os

from django.db import models
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives

FROM_ADDR = 'theiviaxx@gmail.com'


def getImagePath(obj, fileName):
    h = hex(obj.id)
    path = '%s/%s%s' % (h[-2:], h[:2], os.path.splitext(fileName)[1])

    return path

def userToJson(user, context=None, **kwargs):
    obj = {
        'id': user.id,
        'username': user.username,
        'name': user.first_name + ' ' + user.last_name,
        'email': user.email,
    }

    if context == None:
        obj['teams'] = [team.json('user') for team in user.teams.all()]

    return obj


class Team(models.Model):
    name = models.CharField(max_length=255, unique=True)
    members = models.ManyToManyField(User, related_name="teams", null=True)

    def __unicode__(self):
        return self.name

    def __len__(self):
        return len(self.members.all())

    def json(self, context=None, **kwargs):
        obj = {
            'id': self.id,
            'name': self.name,
        }
        if context == "ladder" or context == 'game':
            if kwargs.get('ladder', None):
                membership = self.laddermembership_set.filter(ladder__id=kwargs['ladder'])
                obj['members'] = [userToJson(user, 'team') for user in self.members.all()]
                obj['rating'] = self.laddermembership_set.get(ladder__id=kwargs['ladder']).rating.rating
        elif context == 'user':
            obj['members'] = [userToJson(user, 'team') for user in self.members.all()]
            obj['ladders'] = [o.ladder.json('team', team=self.id) for o in self.laddermembership_set.all()]
        else:
            obj['members'] = [userToJson(user, 'team') for user in self.members.all()]
            obj['ladders'] = [o.ladder.json('team', team=self.id) for o in self.laddermembership_set.all()]

        return obj
    
    def email(self, subject, message):
        to = [u.email for u in self.members.all()]
        text_content = message
        html_content = message
        msg = EmailMultiAlternatives(subject, text_content, FROM_ADDR, to)
        msg.attach_alternative(html_content, "text/html")
        msg.send()


class Ladder(models.Model):
    name = models.CharField(max_length=255, unique=True)
    team_size = models.SmallIntegerField()
    teams = models.ManyToManyField(Team, through="LadderMembership")
    aggression = models.FloatField(default=400.0)
    description = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def json(self, context=None, **kwargs):
        obj = {
            'id': self.id,
            'name': self.name,
            'team_size': self.team_size,
            'aggression': self.aggression,
            'description': self.description,
        }
        if context == 'team':
            obj['rating'] = self.laddermembership_set.get(team__id=kwargs['team']).rating.rating
        elif context == 'game':
            pass
        else:
            obj['teams'] = [o.team.json('ladder', ladder=self.id) for o in self.laddermembership_set.all()]

        return obj


class RatingHistory(models.Model):
    rating = models.FloatField(default=1000.0)
    team = models.ForeignKey(Team)
    ladder = models.ForeignKey(Ladder)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = "created"
        ordering = ['-created']

    def json(self):
        obj = {
            'id': self.id,
            'rating': self.rating,
            'created': self.created.isoformat(),
        }

        return obj


class LadderMembership(models.Model):
    team = models.ForeignKey(Team)
    ladder = models.ForeignKey(Ladder)
    rating = models.ForeignKey(RatingHistory)
    k = models.IntegerField(default=25)
    joined = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "<LadderMembership: %i" % self.rating.rating

    def modifyRating(self):
        if self.rating.rating > 2100:
            self.k = 15
            if self.rating.rating > 2400:
                self.k = 10

        return self


class Game(models.Model):
    # Class Enums
    Open = 0
    Closed = 1
    Pending = 2
    Expired = 3

    ladder = models.ForeignKey(Ladder, related_name="ladder", blank=True, null=True)
    red = models.ForeignKey(Team, blank=True, null=True, related_name="red")
    blu = models.ForeignKey(Team, blank=True, null=True, related_name="blu")
    result = models.ForeignKey(Team, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True, auto_now_add=True)
    red_change = models.FloatField(blank=True, null=True)
    blu_change = models.FloatField(blank=True, null=True)
    status = models.IntegerField(default=0)

    def __unicode__(self):
        return "%s vs. %s" % (self.red.name if self.red else None, self.blu.name if self.blu else None)

    class Meta:
        get_latest_by = "modified"
        ordering = ['-modified']

    def json(self, context=None):
        ladderID = self.ladder.id if self.ladder else None
        obj = {
            'id': self.id,
            'ladder': self.ladder.json('game') if self.ladder else None,
            'red': self.red.json('game', ladder=ladderID) if self.red else None,
            'blu': self.blu.json('game', ladder=ladderID) if self.blu else None,
            'red_change': self.red_change,
            'blu_change': self.blu_change,
            'created': self.created.isoformat(),
            'modified': self.modified.isoformat(),
            'status': self.status,
            'result': self.result.id if self.result else None
        }

        return obj

    def update(self, result):
        self.status = Game.Pending
        red = self.red
        blu = self.blu

        if result == red:
            # Red team won
            self.result = self.red
            self.red_change, self.blu_change = self.__gameMath(red, blu)
        elif result ==  blu:
            # Blu team won
            self.result = self.blu
            self.blu_change, self.red_change = self.__gameMath(blu, red)
        else:
            # Tie
            pass
        self.save()

        return self

    def __gameMath(self, win, lose):
        """
        Performs the game math based on winning expectancy using the ELO rating method.
        http://en.wikipedia.org/wiki/Elo_rating_system
        Formulas:
            Ea = Qa / ( Qa + Qb )
            Eb = Qb / ( Qa + Qb )
            Qa = 10 ^ ( Ra / v )
            Qb = 10 ^ ( Rb / v )
            v = ~400 - Agression
            For each 400 rating points of advantage over the opponent, the chance of
            winning is magnified ten times in comparison to the opponent's chance of winning

            Ea + Eb = 1

            `Ra = Ra + K(Sa - Ea)
            R = Rating
            K = Team's K value
            S = Points scored
            E = Winning expectancy
        """
        ladder = self.ladder

        # Get winner/loser objects
        wMember = win.laddermembership_set.get(ladder=ladder)
        wRating = wMember.rating.rating
        lMember = lose.laddermembership_set.get(ladder=ladder)
        lRating = lMember.rating.rating

        # Calculate winning expectancies for each team
        wQ = float(10**(float(wRating) / ladder.aggression))
        lQ = float(10**(float(lRating) / ladder.aggression))
        wExpectancy = wQ / (wQ + lQ)
        lExpectancy = 1.0 - wExpectancy

        # Modify the ratings
        # Scores are 1 and 0 for winning and losing
        # Create new RatingHistory objects for each
        winRating = RatingHistory(team=win, ladder=ladder)
        winRating.rating = wRating + (wMember.k * (1 - wExpectancy))
        winRating.save()
        wMember.rating = winRating
        # Adjust rating as necessary
        wMember.modifyRating()
        wMember.save()
        winDelta = winRating.rating - wRating

        loseRating = RatingHistory(team=lose, ladder=ladder)
        loseRating.rating = lRating + (lMember.k * (0 - lExpectancy))
        loseRating.save()
        # Adjust rating as necessary
        lMember.rating = loseRating
        lMember.modifyRating()
        lMember.save()
        loseDelta = loseRating.rating - lRating

        return (winDelta, loseDelta)