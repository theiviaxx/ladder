""" package """

import datetime

from django.db.models import F

from models import Game


def updatePending(id_list=[]):
	timeout = 1
	expiration = datetime.datetime.now()
	td = datetime.timedelta(minutes=timeout)

	res = list(Game.objects.filter(status=Game.Pending, modified__lt=expiration - td))
	res += id_list
	for n in res:
		n.status = Game.Closed
		n.save()

	return len(res)