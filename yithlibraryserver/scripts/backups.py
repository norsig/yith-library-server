# Yith Library Server is a password storage server.
# Copyright (C) 2013-2015 Lorenzo Gil Sanchez <lorenzo.gil.sanchez@gmail.com>
#
# This file is part of Yith Library Server.
#
# Yith Library Server is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Yith Library Server is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Yith Library Server.  If not, see <http://www.gnu.org/licenses/>.

import datetime

from pyramid_sqlalchemy import Session

from sqlalchemy import extract
import transaction

from yithlibraryserver.backups.email import send_passwords
from yithlibraryserver.compat import urlparse
from yithlibraryserver.scripts.utils import safe_print, setup_simple_command
from yithlibraryserver.scripts.utils import get_user_display_name
from yithlibraryserver.user.models import User


def get_all_users(when):
    hour = when.hour
    return Session.query(User).filter(
        User.send_passwords_periodically==True,
        User.email_verified==True,
        extract('hour', User.creation)==hour,
    ).order_by(User.creation)


def get_selected_users(*emails):
    for email in emails:
        for user in Session.query(User).filter(
                User.email==email
        ).order_by(User.creation):
            yield user


def send_backups_via_email():
    result = setup_simple_command(
        "send_backups_via_email",
        "Send a password backup to users.",
    )
    if isinstance(result, int):
        return result
    else:
        settings, closer, env, args = result

    try:
        request = env['request']

        if len(args) == 0:
            now = datetime.datetime.utcnow()
            if now.day == 1:
                user_iterator = get_all_users(now)
            else:
                user_iterator = tuple()
        else:
            user_iterator = get_selected_users(*args)

        tx = transaction.begin()

        public_url_root = settings['public_url_root']
        preferences_link = urlparse.urljoin(
            public_url_root,
            request.route_path('user_preferences'))
        backups_link = urlparse.urljoin(
            public_url_root,
            request.route_path('backups_index'))

        for user in user_iterator:
            if user.email:
                sent = send_passwords(request, user,
                                      preferences_link, backups_link)
                if sent:
                    safe_print('Passwords sent to %s' %
                               get_user_display_name(user))

        tx.commit()

    finally:
        closer()


if __name__ == '__main__':  # pragma: no cover
    send_backups_via_email()
