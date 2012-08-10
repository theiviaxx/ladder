from django.contrib import admin
from models import *


class LadderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'aggression', 'team_size')


class TeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'ladder', 'red', 'blu', 'red_change', 'blu_change', 'result')


class LadderMembershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'team', 'ladder', 'rating')


class RatingHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'rating', 'team', 'ladder')

admin.site.register(Ladder, LadderAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(LadderMembership, LadderMembershipAdmin)
admin.site.register(RatingHistory, RatingHistoryAdmin)