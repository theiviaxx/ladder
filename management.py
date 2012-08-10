import os
import sys
from django.conf import settings
from django.db.models import signals
from django.core.management.color import color_style

def link_app_media(sender, verbosity, **kwargs):
    """
    This function is called whenever django's `post_syncdb` signal is fired.
    It looks if the sending app has its own media directory by first checking
    if ``sender`` has a variable named ``MEDIA_DIRNAME`` specified and falling
    back to ``settings.APP_MEDIA_DIRNAME`` and as a last solution just using
    'app_media'. If a directory with this name exists under the app directory
    and has a subdirectory named as the app itself, this subdirectory is then
    symlinked to the ``MEDIA_ROOT`` directory, if it doesn't already exist.

    Example:

        An app called ``foo.bar`` (as listed in INSTALLED_APPS) needs to
        distribute some JavaScript files. The files are stored in
        `foo/bar/media/bar/js/*`. in `foo/bar/models.py` the follwoing is defined:

            MEDIA_DIRNAME = 'media'

        Now, whenever `manage.py syncdb` is run, the directory
        `foo/bar/media/bar` is linked to MEDIA_ROOT/bar and therefore the
        JavaScript files are accessible in the templates or as form media via:

            {{ MEDIA_ROOT }}bar/js/example.js

    Note: The MEDIA_DIRNAME is specified in the models.py instead of the
    __init__.py because the imported models.py module is what gets passed as
    ``sender`` to the signal handler and because apps need a models.py anyway
    to get picked up by the syncdb command.

    The symlink will not be created if a resource with the destination name
    already exists.

    """
    app_name = sender.__name__.split('.')[-2]
    app_dir = os.path.dirname(sender.__file__)

    try:
        APP_MEDIA_DIRNAME = sender.MEDIA_DIRNAME
    except AttributeError:
        APP_MEDIA_DIRNAME = getattr(settings, 'APP_MEDIA_DIRNAME', 'app_media')

    app_media = os.path.join(app_dir, APP_MEDIA_DIRNAME, app_name)
    if os.path.exists(app_media):
        dest = os.path.join(settings.MEDIA_ROOT, app_name)
        if not os.path.exists(dest):
            try:
                os.symlink(app_media, dest) # will not work on windows.
                if verbosity > 1:
                    print "symlinked app_media dir for app: %s" % app_name
            except:
                # windows users should get a note, that they should copy the
                # media files to the destination.
                error_msg   = "Failed to link media for '%s'\n" % app_name
                instruction = ("Please copy the media files to the MEDIA_ROOT",
                    "manually\n")
                sys.stderr.write(color_style().ERROR(str(error_msg)))
                sys.stderr.write(" ".join(instruction))

signals.post_syncdb.connect(link_app_media)
