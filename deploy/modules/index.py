# -*- coding: utf-8 -*-
from server import tasks, exposed
from server.render.html import default


class index(default):

	@exposed
	def index(self, *args, **kwargs):
		template = self.getEnv().get_template("index.html")
		return template.render(start=True)

	#@tasks.PeriodicTask(24 * 60)
	def backup(self, *args, **kwargs):
		"""
		Backup job kick-off for Google Cloud Storage.

		Steps for setting up:

		1. Create a bucket named "backup-dot-YOUR-APPID" in Google Cloud Storage
		2. Set the following permissions on Google Cloud Console IAM
		   (https://console.cloud.google.com/iam-admin/iam) for the user
		   YOUR-APPID@appspot.gserviceaccount.com:

			- Datastore > Cloud Datastore Import Export Admin
			- Storage > Storage Admin

		   (see screenshot here: https://docs.viur.is/images/backup-settings.png)

		Note: This will only work on App Engine projects that are associated with a billing account.
		"""
		from server import conf
		import json, logging, httplib
		from datetime import datetime
		from google.appengine.api import urlfetch, app_identity

		webapp = conf["viur.wsgiApp"]

		appid = app_identity.get_application_id()
		bucket = "backup-dot-%s" % appid

		access_token, _ = app_identity.get_access_token("https://www.googleapis.com/auth/datastore")

		timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

		output_url_prefix = "gs://%s/%s" % (bucket, timestamp)

		entity_filter = {
			"kinds": webapp.request.get_all("kind"),
			"namespace_ids": webapp.request.get_all("namespace_id")
		}

		request = {
			"project_id": appid,
			"output_url_prefix": output_url_prefix,
			"entity_filter": entity_filter
		}

		headers = {
			"Content-Type": "application/json",
			"Authorization": "Bearer " + access_token
		}

		url = "https://datastore.googleapis.com/v1/projects/%s:export" % appid

		try:
			result = urlfetch.fetch(
				url=url,
				payload=json.dumps(request),
				method=urlfetch.POST,
				deadline=60,
				headers=headers
			)

			if result.status_code == httplib.OK:
				logging.info(result.content)

			elif result.status_code >= 500:
				logging.error(result.content)

			else:
				logging.warning(result.content)

		except urlfetch.Error:
			logging.exception("Failed to initiate export.")

		logging.info("Daily backup queued")


index.html = True
